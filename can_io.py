
import can
import time 
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
from can_open_protocol import CanOpen


class CANIO:

    @staticmethod
    def parse_5vadc_tpdo(msg: can.Message, resolution):
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


        for i in range(0, 8, 2):
            raw = int.from_bytes(msg.data[i:i+2], byteorder='little', signed=True)
            temperature = (raw * 0.1)  # each count = 0.1 °C
            data.append(temperature)
        return data
    
    @staticmethod
    def mA_to_percent(current_mA):
        if current_mA < 4:
            return 0.0
        elif current_mA > 20:
            current_mA = 20
        return ((current_mA - 4) / 16.0) * 100.0
    
    @staticmethod    
    def mA_to_flow(current_mA, full_scale=32.8):
        if current_mA < 4:
            return 0.0
        elif current_mA > 20:
            current_mA = 20
        return ((current_mA - 4) / 16.0) * full_scale
    
    @staticmethod
    def parse_i_tpdo(msg):
        currents = []
        for i in range(0, 8, 2):
            raw = int.from_bytes(msg.data[i:i+2], "little", signed=False)
            currents.append((raw / 65535) * 50)
        return currents        


    
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
    def digital_to_16bitanalog(digitalval):
        if  digitalval == 1:
            output = 0xFFFF
        elif digitalval == 0:
            output = 0
        else: 
            raise ValueError("digital value error!")

        return output
    
    @staticmethod
    def percent_to_16bitanalog(percent):
        if  percent == 100:
            output = 0xFFFF
        elif percent == 0:
            output = 0
        else: 
            output = (percent/100)*65535

        return output
    
    @staticmethod
    def process_to_16bitanalog(process_scale, process_max):
        raw_four_value = 13109 #physically verified bit value that outputs 4 mA
        raw_max_value = 65535 #16bit scale
        four_twenty_scale = raw_max_value - raw_four_value # 20mA bit value - 4mA bit value
        if  process_scale == process_max:
            output = raw_max_value
        elif process_scale <= 0:
            output = raw_four_value
        else: 
            output = ((process_scale/process_max)*four_twenty_scale) + raw_four_value

        return int(output)


    @staticmethod     
    def generate_outmm_msg1(pump_on, pump_speed, mfm1_state, mfm2_state):

        # if pump_speed < 0:
        #     pump_speed = 0
        # elif pump_speed >100:
        #     pump_speed = 100
        # else: 
        #     pump_speed = pump_speed

        # raw_out1 = pump_speed* 655
        raw_out1 = CANIO.process_to_16bitanalog(pump_speed, 100)

        raw_out2 = CANIO.digital_to_16bitanalog(pump_on)

        raw_out3 = CANIO.process_to_16bitanalog(mfm1_state, 32.8)
        raw_out4 = CANIO.process_to_16bitanalog(mfm2_state, 32.8)

        return raw_out1, raw_out2, raw_out3, raw_out4
    
    @staticmethod     
    def generate_outmm_msg2(alicat_state):

        raw_out1 = CANIO.process_to_16bitanalog(alicat_state, 250)

        return raw_out1
    
    
    @staticmethod
    def generic_dout_msg(out1, out2, out3, out4, arbitration_id):
        aout1 = CANIO.digital_to_16bitanalog(out1)
        aout2 = CANIO.digital_to_16bitanalog(out2)
        aout3 = CANIO.digital_to_16bitanalog(out3)
        aout4 = CANIO.digital_to_16bitanalog(out4)
        payload = CANIO.generate_uint_16bit_msg(aout1, aout2, aout3, aout4)
        msg = can.Message(arbitration_id=arbitration_id, is_extended_id=False, data = payload)
        return msg

    @staticmethod
    def start_listener(bus: can.Bus, data_queue: asyncio.Queue): # type: ignore
        """
        Starts a CAN bus listener that parses incoming messages and puts structured data
        into a single asyncio.Queue.
        :param bus: The python-can bus object to listen on.
        :param resolution: Resolution parameter for ADC parsing (e.g., 16-bit).
        :param data_queue: The single asyncio.Queue to put structured parsed messages into.
                        Each message will be a dictionary with 'node_id', 'data_type', 'values', and 'timestamp'.
        """

        can_ids = {
            0x180 : "micromod",
            0x181 : "micromod",
            0x182 : "tc_mm",
            0x183 : "tc_mm",
            0x184 : "tc_mm",
            0x185 : "tc_mm",
            0x1A3 : "deditec",
            0x2A3 : "deditec",
            0x3A3 : "deditec",
            0x4A3 : "deditec"
            }   
        micromod_map = [0x180, 0x181]
        tc_mm_map = [0x182,0x183,0x184,0x185]
        deditec_map = [0x1A3, 0x2A3, 0x3A3, 0x4A3]


        class _AsyncListener(can.Listener):
            """
            Internal asynchronous CAN message listener.
            This class defines how incoming CAN messages are handled.
            """

            def __init__(self):
                super().__init__()
                self.delta_time = time.time()
                self.message_buffer = defaultdict(dict)
                self.expected_ids = set(can_ids)
            def on_message_received(self, msg: can.Message):
                rec_id = msg.arbitration_id
                if rec_id not in can_ids:
                    return
                message_type = can_ids[rec_id]
                self.message_buffer[rec_id][message_type] = msg

                received_ids = set(self.message_buffer.keys())
                current_time = time.time()

                if (self.expected_ids == received_ids) or (current_time - self.delta_time >= 0.4):
                    
                    voltages = []
                    temps = []
                    currents = []

                    for i in micromod_map:
                        try:
                            v_data = self.message_buffer[i]["micromod"]
                            voltages.extend(CANIO.parse_5vadc_tpdo(v_data, 16))
                        except Exception:
                            print(f"Warning: Micromod message for ID {hex(i)} missing. Appending 16 zeros.")
                            voltages.extend(CANIO.parse_5vadc_tpdo(can.Message(arbitration_id=0, data=[0]*8), 16))

                    for j in tc_mm_map:
                        try:
                            tc_data = self.message_buffer[j]["tc_mm"]
                            temps.extend(CANIO.parse_temp_tpdo(tc_data))
                        except KeyError:
                            print(f"Warning: 'tc_mm' missing at buffer[{j}]")
                            temps.extend(CANIO.parse_temp_tpdo(can.Message(arbitration_id=0, data=[0]*8)))

                    for k in deditec_map:
                        try:
                            deditec_data = self.message_buffer[k]["deditec"]
                            currents.extend(CANIO.parse_i_tpdo(deditec_data))
                        except KeyError:
                            print(f"Warning: 'deditec' missing at buffer[{k}]")
                            currents.extend(CANIO.parse_i_tpdo(can.Message(arbitration_id=0, data=[0]*8)))

                    parsed_message = {
                        "timestamp": datetime.now().isoformat(),
                        "voltage": voltages,
                        "temperature": temps,
                        "fourtwenty": currents,
                    }

                    self.message_buffer.clear()

                    try:
                        data_queue.put_nowait(parsed_message)
                    except asyncio.QueueFull:
                        try:
                            data_queue.get_nowait()
                            data_queue.put_nowait(parsed_message)
                        except Exception as e:
                            print(f"Error handling full queue: {e}")

                    self.delta_time = current_time


        return can.Notifier(bus, [_AsyncListener()], loop=asyncio.get_running_loop())




    @staticmethod
    async def send_outputs(can_bus: can.BusABC, data_queue: asyncio.Queue):
        out_minimodul1_id = 0x600
        out_minimodul2_id = 0x601
        out_minimod_id = 0x191
        outputs: Dict[str, Any] = await data_queue.get()
        try:
            if "estop_flag" in outputs:
                eStopFlag = outputs["eStopFlag"]
            if "pump_state" in outputs:
                pump_state = outputs["pump_state"]
            if "esv_state" in outputs:
                esv_state = outputs["esv_state"]
            if "mfm_state" in outputs:
                mfm_state = outputs["mfm_state"]
            if "pic_state" in outputs:
                pic_state = outputs["pic_state"]
        except:
            print("OUTPUT QUEUE HANDLING ERROR")
        heaterOn = True
        if eStopFlag:
            msg_outmm = can.Message(arbitration_id=out_minimodul1_id, data=[00]*8, is_extended_id=False)
            msg_outmm1 = can.Message(arbitration_id=out_minimodul2_id, data=[00]*8, is_extended_id=False)
            msg_minimod = CANIO.generic_dout_msg(0, 0, 0 ,0, out_minimod_id)

        else:
            speed = max(0.0, min(100.0, pump_state[1] if pump_state[1] is not None else 0.0))
            raw1, raw2, raw3, raw4 = CANIO.generate_outmm_msg1(pump_state[0], speed, mfm_state[0], mfm_state[1])
            raw5 = CANIO.generate_outmm_msg2(pic_state)
            data_minimodul2 = CANIO.generate_uint_16bit_msg(int(raw5),0,0,0)
            data_minimodul = CANIO.generate_uint_16bit_msg(int(raw1), int(raw2), int(raw3), int(raw4))
            msg_outmm = can.Message(arbitration_id=out_minimodul1_id, data=data_minimodul, is_extended_id=False)
            msg_outmm1 = can.Message(arbitration_id=out_minimodul2_id, data=data_minimodul2, is_extended_id=False)
            msg_minimod = CANIO.generic_dout_msg(heaterOn, esv_state[0], esv_state[1] ,0, out_minimod_id)
        try:
            can_bus.send(msg_outmm)
            can_bus.send(msg_outmm1)
            can_bus.send(msg_minimod)
        except Exception as e:
                print(f"CAN Send Error: {e}")


import can
import time
from datetime import datetime
from collections import defaultdict
from multiprocessing import Queue
from typing import Dict, List, Optional, Any, Type


class CANWorker(can.Listener):
    def __init__(self, bus: can.BusABC,  rx_queue: Queue, tx_queue: Queue, io_utilities: Type[CANIO]):
        super().__init__()
        self.bus = bus
        self.rx_queue = rx_queue
        self.tx_queue = tx_queue

        self.device_mappings = {
            "micromod": [0x180, 0x181],
            "tc_mm": [0x182, 0x183, 0x184, 0x185], 
            "deditec": [0x1A3, 0x2A3, 0x3A3, 0x4A3]
        }
        
        # Build reverse lookup
        self.can_ids = {}
        for device_type, ids in self.device_mappings.items():
            for can_id in ids:
                self.can_ids[can_id] = device_type
        
        self.expected_ids = set(self.can_ids.keys())

        self.message_buffer = defaultdict(dict)
        self.last_received_time = time.time()
        self.timeout = 0.4  # seconds

        self.notifier = can.Notifier(bus, [self])

    def on_message_received(self, msg: can.Message):
        rec_id = msg.arbitration_id
        if rec_id not in self.can_ids:
            return

        msg_type = self.can_ids[rec_id]
        self.message_buffer[rec_id][msg_type] = msg
        self.last_received_time = time.time()

        if set(self.message_buffer.keys()) == self.expected_ids:
            self.emit_snapshot()

    def emit_snapshot(self):
        voltages, temps, currents = [], [], []

        for rec_id in self.device_mappings["micromod"]:
            msg = self._get_message(rec_id, "micromod")
            voltages.extend(CanOpen.parse_5vadc_tpdo(msg, 16))

        for rec_id in self.device_mappings["tc_mm"]:
            msg = self._get_message(rec_id, "tc_mm")
            temps.extend(CanOpen.parse_temp_tpdo(msg))

        for rec_id in self.device_mappings["deditec"]:
            msg = self._get_message(rec_id, "deditec")
            currents.extend(CanOpen.parse_i_tpdo(msg))

        parsed = {
            "timestamp": datetime.now().isoformat(),
            "voltage": voltages,
            "temperature": temps,
            "fourtwenty": currents
        }

        try:
            self.rx_queue.put_nowait(parsed)
        except:
            try: self.rx_queue.get_nowait()
            except: pass
            self.rx_queue.put_nowait(parsed)

        self.message_buffer.clear()

    def _get_message(self, rec_id: int, msg_type: str) -> can.Message:
        return self.message_buffer.get(rec_id, {}).get(msg_type, can.Message(arbitration_id=rec_id, data=[0] * 8))

    def check_timeout_and_emit(self):
        now = time.time()
        if self.message_buffer and (now - self.last_received_time >= self.timeout):
            self.emit_snapshot()

    def send_outputs(self):
        if not self.tx_queue:
            print("NO SENDER QUEUE!")
            return

        try:
            outputs: Dict[str, Any] = self.tx_queue.get_nowait()

            out_minimodul1_id = 0x600
            out_minimodul2_id = 0x601
            out_minimod_id = 0x191

            pump_state = outputs.get("pump_state", [0, 0])
            esv_state = outputs.get("esv_state", [0, 0])
            mfm_state = outputs.get("mfm_state", [0, 0])
            pic_state = outputs.get("pic_state", 0)
            heaterOn = True

            speed = max(0.0, min(100.0, pump_state[1] if pump_state[1] is not None else 0.0))
            raw1, raw2, raw3, raw4 = CANIO.generate_outmm_msg1(pump_state[0], speed, mfm_state[0], mfm_state[1])
            raw5 = CANIO.generate_outmm_msg2(pic_state)

            data_minimodul2 = CANIO.generate_uint_16bit_msg(int(raw5), 0, 0, 0)
            data_minimodul = CANIO.generate_uint_16bit_msg(int(raw1), int(raw2), int(raw3), int(raw4))

            msg_outmm = can.Message(arbitration_id=out_minimodul1_id, data=data_minimodul, is_extended_id=False)
            msg_outmm1 = can.Message(arbitration_id=out_minimodul2_id, data=data_minimodul2, is_extended_id=False)
            msg_minimod = CANIO.generic_dout_msg(heaterOn, esv_state[0], esv_state[1], 0, out_minimod_id)

            self.bus.send(msg_outmm)
            self.bus.send(msg_outmm1)
            self.bus.send(msg_minimod)

        except Exception as e:
            print(f"[CANWorker] Error sending outputs: {e}")

    def run(self):
        while True:
            self.check_timeout_and_emit()
            self.send_outputs()
            time.sleep(0.01) 

    def stop(self):
        self._running = False
        self.notifier.stop()