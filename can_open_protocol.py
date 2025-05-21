import can
import time 
import asyncio
from typing import List


import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from collections import deque
import csv
from datetime import datetime



class CanOpen:

    @staticmethod
    def spo_configure(index, subindex, value, size, can_bus, cob_id):

        """send spo messages using canopen standard
           to build SPO msg --> length 8 bytes, cob_id = 0x600+node_id, bytes[command, index lo, index hi, subindex, data 1, data 2, data 3, data 4]
           command byte = write req [ 2f, 2B, 27, 23]; write resp 0x60; read req 0x40; read resp [4f, 4B, 47, 43, 42],  error resp 0x80

        Args:
            index (2bytes): index register
            subindex (1 byte): subindex register
            value (<= 4bytes): what is the data
            size (1<int<4): how many bytes in message
            can_bus (can.bus): can bus
            cob_id (4bytes): 0x600+node_id
        """
        cs_dict = {1: 0x2F, 2: 0x2B,3:0x27, 4: 0x23}
        cs = cs_dict[size]
        data = [cs, index & 0xFF, (index >> 8) & 0xFF, subindex] + list(value.to_bytes(size, 'little'))
        data += [0x00] * (8 - len(data))
        msg = can.Message(cob_id, data=data, is_extended_id=False)
        can_bus.send(msg)
        print(f"Sent message: COB-ID=0x{cob_id:X}, Data={data}")

        # Always listen for a response immediately after sending
        response = CanOpen.listen_for_responses(can_bus, 1.0)
        if response:
            print(f"Received response: COB-ID=0x{response.arbitration_id:X}, Data={response.data.hex()}")
        else:
            print(f"No response received within {1} seconds for COB-ID 0x{cob_id:X}")

    @staticmethod
    def listen_for_responses(bus, atimeout):
        """listen for response from commissioning

        Args:
            bus (CAN.bus): canbus
            atimeout (float): how long to wait

        Returns:
            list[int]: message or nothing if nothing on bus
        """
        start_time = time.time()
        while time.time() - start_time < atimeout:
            msg = bus.recv(timeout=0.1)  # Timeout of 100ms for each recv call
            if msg:
                return msg
        return None


    @staticmethod
    def reset_node_id(node_ids, can_bus):
        """run once when node_id changed

        Args:
            node_ids (int[]): which ones were changed to be reset
            can_bus (can.bus): canbus
        """
        for element in node_ids:
            cob_id = 0x600+element
            CanOpen.spo_configure(0x1011, 2,0x64616F6C, 4, can_bus, cob_id)

    @staticmethod
    def commission_adc(node_ids, can_bus, num_can_msgs):
        """setup tpdos for canopen adc module, will be found at 0x180+ node id

        Args:
            node_ids (int[]): node ids - sdo setup messages sent to 0x600+node id, configuring such that tpdo
            can_bus (can.bus): canbus
            num_can_msgs (int): number of tpdos to setup
        """
        tpdo_config_index = 0x1800 + (num_can_msgs - 1)
        tpdo_map_index = 0x1A00 + (num_can_msgs - 1)
        nvm_index = 0x1010
        mnt_index = 0x1F80

        for element in node_ids:
            cob_id = 0x600+element
            for i in range(num_can_msgs):
                tpdo_config_index = 0x1800 + i
                tpdo_map_index = 0x1A00 + i
                #1 is COB_ID, 2 transmission type, 3 inhibit time, 5 event timer
                #CanOpen.spo_configure(mnt_index, 0, 0x02,1, can_bus, cob_id ) #pre-operational set
                CanOpen.spo_configure(tpdo_config_index, 1, 0x80000000 | (0x180 + element), 4, can_bus, cob_id) #disable at index 1
                CanOpen.spo_configure(tpdo_config_index, 5, 0x0064, 2, can_bus, cob_id) #0x0064 is 100 in dec. event timer set to 100ms
                CanOpen.spo_configure(tpdo_map_index, 0, 0x00000000, 1, can_bus, cob_id ) #set msg to 0
                for j in range(4):
                    subindex = j + 1
                    mapping_entry = (0x6401 << 16) | (subindex << 8) | 0x10
                    CanOpen.spo_configure(tpdo_map_index, subindex, mapping_entry, 4, can_bus, cob_id) #assign msgs to tpdo
                CanOpen.spo_configure(tpdo_map_index, 0, 0x04, 1, can_bus, cob_id ) #set msg to 4
                CanOpen.spo_configure(tpdo_config_index, 1, 0x00000000 | (0x180 + element), 4, can_bus, cob_id) #re-enable at index 1
            CanOpen.spo_configure(mnt_index, 0, 0x02,1, can_bus, cob_id ) #pre-operational set
            CanOpen.spo_configure(nvm_index, 1, 0x65766173,4, can_bus, cob_id) #save to eeprom

    @staticmethod
    def operational(node_ids, can_bus):
        """Set nodes to operational

        Args:
            node_ids (_type_): Node ID in byte form
            can_bus (_type_): can bus object i.e can_bus = can.interface.Bus(...)
        """
        nmt_id  = 0x0000

        for element in node_ids:
            payload = [0x01, element]
            print(payload)
            msg = can.Message(arbitration_id=nmt_id, data=payload, is_extended_id=False)
            can_bus.send(msg)

    @staticmethod
    def parse_5vadc_tpdo(msg, resolution):
        data = []
        min_raw = 0
        max_raw = (2**resolution-1)  
        voltage_range = 10.0 / (max_raw - min_raw)

        for i in range(0, 8, 2):  # Each channel is 2 bytes
            raw = int.from_bytes(msg.data[i:i+2], byteorder='little', signed=True)
            # Clamp if needed
            if raw < min_raw:
                voltage = 0.0
            elif raw > max_raw:
                voltage = 5.0
            else:
                voltage = (raw - min_raw) * voltage_range
            data.append(voltage)

        return data
    
    @staticmethod    
    def parse_temp_tpdo(msg):
        data = []
        scale = 10  
        offset = 0  

        for i in range(0, 8, 2):
            raw = int.from_bytes(msg.data[i:i+2], byteorder='little', signed=True)
            temperature = (raw * 0.1)  # each count = 0.1 °C
            data.append(temperature)
        return data
    
    @staticmethod     
    def generate_uint_16bit_msg(val1, val2, val3, val4):
        sig_1 = val1.to_bytes(2, byteorder='little', signed=False)
        sig_2 = val2.to_bytes(2, byteorder='little', signed=False)
        sig_3 = val3.to_bytes(2, byteorder='little', signed=False)
        sig_4 = val4.to_bytes(2, byteorder='little', signed=False)

        msg_bytes = sig_1 + sig_2 + sig_3 + sig_4  # Combine all into one bytes object
        msg = list(msg_bytes)  # Convert to flat list of ints

        return msg

    @staticmethod     
    def generate_outmm_msg(pump_on, pump_speed):

        if pump_speed < 0:
            pump_speed = 0
        elif pump_speed >100:
            pump_speed = 100
        else: 
            pump_speed = pump_speed

        raw_out1 = pump_speed* 655

        if pump_on == 1:
            raw_out2 = 65535
        else:
            raw_out2 = 0

        return raw_out1, raw_out2

    
    @staticmethod
    def start_listener(bus: can.Bus, resolution, queue: asyncio.Queue = None):
        pt_id = 0x181
        tc_id_map = {0x182: 2, 0x183: 3, 0x184: 4, 0x185: 5}

        class _AsyncListener(can.Listener):
            def on_message_received(self, msg):
                if msg.arbitration_id == pt_id:
                    node_id = msg.arbitration_id
                    voltages = CanOpen.parse_5vadc_tpdo(msg, resolution)
                    print(f"Node {node_id}: {voltages}")
                    if queue:
                        asyncio.create_task(queue.put((node_id, 'voltage', voltages)))
                elif msg.arbitration_id in tc_id_map:
                    node_id = msg.arbitration_id
                    temps = CanOpen.parse_temp_tpdo(msg)
                    print(f"Node {node_id}: {temps}")
                    if queue:
                        asyncio.create_task(queue.put((node_id, 'temperature', temps)))

        return can.Notifier(bus, [_AsyncListener()], loop=asyncio.get_running_loop())
    
    @staticmethod
    async def send_can_message(can_bus: can.Bus, can_id: int, data: List[int]):
        """nonblocking can_sender (hopefully)

        Args:
            can_bus (can.Bus): can bus
            can_id (int): can address of target
            data (List[int]): msg

        Raises:
            ValueError: exception error
        """
        if len(data) > 8:
            raise ValueError("CAN data cannot exceed 8 bytes")

        msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)

        try:
            can_bus.send(msg)
            print(f"[SEND] Sent CAN message: COB-ID=0x{can_id:X}, Data={data}")
        except can.CanError as e:
            print(f"[ERROR] Failed to send CAN message: {e}")



#testing with gui and queue begins here    


history_len = 100
ch_data = [deque([0.0] * history_len, maxlen=history_len) for _ in range(3)]

class PumpControlWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.pump_on_checkbox = QCheckBox("Pump ON")
        self.speed_label = QLabel("Speed (%)")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(0)
        self.speed_entry = QLineEdit("0")

        self.speed_slider.valueChanged.connect(self.update_entry)
        self.speed_entry.editingFinished.connect(self.update_slider)

        layout = QVBoxLayout()
        layout.addWidget(self.pump_on_checkbox)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.speed_slider)
        layout.addWidget(self.speed_entry)
        self.setLayout(layout)

    def update_entry(self, val):
        self.speed_entry.setText(str(val))

    def update_slider(self):
        try:
            val = int(self.speed_entry.text())
            if 0 <= val <= 100:
                self.speed_slider.setValue(val)
        except ValueError:
            pass

    def get_state(self):
        return int(self.pump_on_checkbox.isChecked()), self.speed_slider.value()

class PlotCanvas(FigureCanvas):
    def __init__(self):
        self.fig, self.axs = plt.subplots(4, 1, figsize=(8, 8), gridspec_kw={'height_ratios': [1, 1, 1, 0.5]}, sharex=True)
        super().__init__(self.fig)
        self.names = ["PT1401", "PT1402", "PT1403"]
        self.lines = []
        self.last_temps = [None, None]

        for i, ax in enumerate(self.axs[:3]):
            line, = ax.plot([], [], lw=2)
            self.lines.append(line)
            if i == 0:
                ax.set_ylim(0, 150)
            else:
                ax.set_ylim(0, 300)
            ax.set_xlim(0, history_len)
            ax.set_ylabel("Pressure")
            ax.set_title(self.names[i])
            ax.grid(True)

        self.axs[-1].axis('off')
        self.axs[-1].set_xlabel("Sample Index")
        self.temp_text = self.axs[-1].text(0.5, 0.5, "Waiting for temperature data...",
                                         fontsize=14, ha='center', va='center', transform=self.axs[-1].transAxes)

    def update_plot(self):
        x = list(range(history_len))
        for i in range(3):
            self.lines[i].set_data(x, list(ch_data[i]))
        for ax in self.axs[:3]:
            ax.relim()
            ax.autoscale_view()
        if None not in self.last_temps:
            temp_str = f"T01: {self.last_temps[0]:.1f} °C    T02: {self.last_temps[1]:.1f} °C"
        else:
            temp_str = "Waiting for temperature data..."
        self.temp_text.set_text(temp_str)
        self.draw()

class MainWindow(QWidget):
    def __init__(self, bus, queue):
        super().__init__()
        self.setWindowTitle("Pump Control & Plot")
        self.bus = bus
        self.queue = queue

        self.pump_control = PumpControlWidget()
        self.plot_canvas = PlotCanvas()

        layout = QHBoxLayout()
        layout.addWidget(self.pump_control, 1)
        layout.addWidget(self.plot_canvas, 3)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)

        self.log_file = open('pump_data_log.csv', 'w', newline='')
        self.csv_writer = csv.writer(self.log_file)
        self.csv_writer.writerow([
            "Timestamp", "PT1401 ()", "PT1402 ()", "PT1403 ()",
            "T01 (°C)", "T02 (°C)", "Pump On", "Pump Speed (%)", "Pump Speed (RPM)"
        ])


        asyncio.create_task(self.consumer_task())
        asyncio.create_task(self.pump_sender_task())

    async def consumer_task(self):
        while True:
            node_id, data_type, values = await self.queue.get()
            timestamp = datetime.now().isoformat()

            if data_type == 'voltage':
                scaled_pressures = [
                    values[0] * 30.0,  # PT1401: 0-5V -> 0-150 bar
                    values[1] * 60.0,  # PT1402: 0-5V -> 0-300 bar
                    values[2] * 60.0   # PT1403: 0-5V -> 0-300 bar
                ]
                for i in range(3):
                    ch_data[i].append(scaled_pressures[i])
                self.last_pressures = scaled_pressures  # Save for logging
            elif data_type == 'temperature':
                if node_id == 0x182:
                    self.plot_canvas.last_temps = values[:2]
                    self.last_temps = values[:2]  # Save for logging

            self.queue.task_done()


    async def pump_sender_task(self):
        while True:
            pump_on, speed = self.pump_control.get_state()
            raw1, raw2 = CanOpen.generate_outmm_msg(pump_on, speed)
            data = CanOpen.generate_uint_16bit_msg(int(raw1), int(raw2), 0, 0)
            await CanOpen.send_can_message(self.bus, 0x600, data)

            # Log only if pressure and temperature data have been received
            if hasattr(self, 'last_pressures') and hasattr(self, 'last_temps'):
                timestamp = datetime.now().isoformat()
                rpm = speed * 17.2  # 0-100% -> 0-1720 RPM
                self.csv_writer.writerow([
                    timestamp,
                    *self.last_pressures,
                    *self.last_temps,
                    pump_on,
                    speed,
                    rpm
                ])
                self.log_file.flush()  # Ensure data is written to disk

            await asyncio.sleep(0.05)


    def update_plot(self):
        self.plot_canvas.update_plot()
        
    def closeEvent(self, event):
        self.log_file.close()
        event.accept()


async def main_async():
    channel = "PCAN_USBBUS1"
    bustype = "pcan"
    bitrate = 500000

    try:
        bus = can.interface.Bus(channel=channel, interface=bustype, bitrate=bitrate)
    except Exception as e:
        print(f"Failed to connect to CAN bus: {e}")
        return

    queue = asyncio.Queue()

    CanOpen.start_listener(bus, resolution=16, queue=queue)

    app = QApplication(sys.argv)
    window = MainWindow(bus, queue)
    window.show()

    while True:
        await asyncio.sleep(0.01)
        app.processEvents()

if __name__ == "__main__":
    asyncio.run(main_async())