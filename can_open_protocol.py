
import can
import time 
import asyncio
from typing import List
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

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
        """
        Listen for a response from the node on the CAN bus.
        
        Args:
            bus (can.Bus): The CAN bus instance.
            timeout (float): Time to wait for a response.
        
        Returns:
            can.Message or None: The received message or None if no response.
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
    def start_listener(bus: can.Bus, resolution=16, queue: asyncio.Queue = None):
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


#testing with gui and queue begins here    

# Deques to store voltage histories

history_len = 100
ch_data = [deque([0.0] * history_len, maxlen=history_len) for _ in range(3)]

fig, axs = plt.subplots(4, 1, figsize=(8, 8), gridspec_kw={'height_ratios': [1,1,1,0.5]}, sharex=True)
fig.canvas.manager.set_window_title("Pressure Transducer Readings")

names = ["PT1401", "PT1402", "PT1403"]
lines = []

for i, ax in enumerate(axs[:3]):
    line, = ax.plot([], [], lw=2)
    lines.append(line)
    
    if i == 0:
        ax.set_ylim(0, 150)   # PT1401: 0–150 
    else:
        ax.set_ylim(0, 300)   # PT1402 & PT1403: 0–300 

    ax.set_xlim(0, history_len)
    ax.set_ylabel("Pressure")
    ax.set_title(names[i])
    ax.grid(True)


axs[-1].axis('off') 

axs[-1].set_xlabel("Sample Index")

temp_text = axs[-1].text(0.5, 0.5, "Waiting for temperature data...", 
                         fontsize=24, ha='center', va='center', transform=axs[-1].transAxes)


queue = asyncio.Queue()

last_temps = [None, None, None]

async def consumer_task():
    global last_temps
    while True:
        node_id, data_type, values = await queue.get()

        if data_type == 'voltage':
            scaled_pressures = [
                values[0] * 30.0,   # PT1401: 5V -> 100 bar
                values[1] * 60.0,   # PT1402: 5V -> 300 bar
                values[2] * 60.0    # PT1403: 5V -> 300 bar
            ]
            for i in range(3):
                ch_data[i].append(scaled_pressures[i])
        elif data_type == 'temperature':
            if node_id == 0x182:
                last_temps = values[:2]

        queue.task_done()


def update_plot():
    x = list(range(history_len))
    for i in range(3):
        lines[i].set_data(x, list(ch_data[i]))

    for ax in axs[:3]:
        ax.relim()
        ax.autoscale_view()

    # Update temperature text
    if None not in last_temps:
        temp_str = (f"T01: {last_temps[0]:.1f} °C    "
                    f"T02: {last_temps[1]:.1f} °C")

    else:
        temp_str = "Waiting for temperature data..."
    temp_text.set_text(temp_str)

    plt.draw()
    plt.pause(0.01)  

async def main():
    channel = "PCAN_USBBUS1"
    bustype = "pcan"
    bitrate = 500000

    try:
        bus = can.interface.Bus(channel=channel, interface=bustype, bitrate=bitrate)
    except Exception as e:
        print(f"Failed to connect to CAN bus: {e}")
        return

    CanOpen.start_listener(bus, resolution=16, queue=queue)

    consumer = asyncio.create_task(consumer_task())

    try:
        while plt.fignum_exists(fig.number):
            update_plot()
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        consumer.cancel()
        await consumer

if __name__ == "__main__":
    asyncio.run(main())