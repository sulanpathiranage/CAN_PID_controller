
import can
import time 
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict


class CANIO:

    @staticmethod
    def parse_micromod(msg, resolution):
        data = []
        min_raw = 0
        max_raw = (2**resolution-1)  
        voltage_range = 10.0 / (max_raw - min_raw)

        for i in range(0, 8, 2):  # Each channel is 2 bytes
            raw = int.from_bytes(msg.data[i:i+2], byteorder='little', signed=True)
            if raw < min_raw:
                voltage = 0.0
            elif raw > max_raw:
                voltage = 5.0
            else:
                voltage = (raw - min_raw) * voltage_range
            data.append(voltage)

        return data
    
    @staticmethod
    def parse_deditec(msg):
        currents = []
        for i in range(0, 8, 2):
            raw = int.from_bytes(msg.data[i:i+2], "little", signed=False)
            currents.append((raw / 65535) * 50)
        return currents   
    
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
    def generate_uint_16bit_msg(val1, val2, val3, val4):
        sig_1 = val1.to_bytes(2, byteorder='little', signed=False)
        sig_2 = val2.to_bytes(2, byteorder='little', signed=False)
        sig_3 = val3.to_bytes(2, byteorder='little', signed=False)
        sig_4 = val4.to_bytes(2, byteorder='little', signed=False)

        msg_bytes = sig_1 + sig_2 + sig_3 + sig_4  # Combine all into one bytes object
        msg = list(msg_bytes)  # Convert to flat list of ints

        return msg

    @staticmethod     
    def generate_pump_msg(pump_on, pump_speed):

        if pump_speed < 0:
            pump_speed = 0
        elif pump_speed >100:
            pump_speed = 100
        else: 
            pump_speed = pump_speed

        raw_out1 = pump_speed* 655

        raw_out2 = CANIO.digital_to_16bitanalog(pump_on)

        return raw_out1, raw_out2
    
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
    def generic_dout_msg(out1, out2, out3, out4, arbitration_id):
        aout1 = CANIO.digital_to_16bitanalog(out1)
        aout2 = CANIO.digital_to_16bitanalog(out2)
        aout3 = CANIO.digital_to_16bitanalog(out3)
        aout4 = CANIO.digital_to_16bitanalog(out4)
        payload = CANIO.generate_uint_16bit_msg(aout1, aout2, aout3, aout4)
        msg = can.Message(arbitration_id=arbitration_id, is_extended_id=False, data = payload)
        return msg

    @staticmethod
    def start_listener(bus: can.Bus, resolution, data_queue: asyncio.Queue):
        """
        Starts a CAN bus listener that parses incoming messages and puts structured data
        into a single asyncio.Queue.
        :param bus: The python-can bus object to listen on.
        :param resolution: Resolution parameter for ADC parsing (e.g., 16-bit).
        :param data_queue: The single asyncio.Queue to put structured parsed messages into.
                        Each message will be a dictionary with 'node_id', 'data_type', 'values', and 'timestamp'.
        """

        # can_ids = {
        #     0x180 : "micromod",
        #     0x181 : "micromod",
        #     0x182 : "tc_mm",
        #     0x183 : "tc_mm",
        #     0x184 : "tc_mm",
        #     0x185 : "tc_mm",
        #     0x1A3 : "deditec",
        #     0x2A3 : "deditec",
        #     0x3A3 : "deditec",
        #     0x4A3 : "deditec"
        #     }   
        # micromod_map = [0x180, 0x181]
        # tc_mm_map = [0x182,0x183,0x184,0x185]
        # deditec_map = [0x1A3, 0x2A3, 0x3A3, 0x4A3]
        can_ids = {
            0x181 : "micromod",
            0x182 : "tc_mm",
            0x1FE : "deditec",
            }   
        micromod_map = [0x181]
        tc_mm_map = [0x182]
        deditec_map = [0x1FE]

        class _AsyncListener(can.Listener):
            """
            Internal asynchronous CAN message listener.
            This class defines how incoming CAN messages are handled.
            """
            def __init__(self):
                super().__init__()
                self.delta_time = time.time()
                self.message_buffer = defaultdict(dict)


            def on_message_received(self, msg: can.Message):
                rec_id = msg.arbitration_id                
                if rec_id not in can_ids: 
                    pass
                else:
                    message_type = can_ids[rec_id] 
                    self.message_buffer[rec_id][message_type] = msg
                    expected_ids = set(can_ids)
                    received_ids = set(self.message_buffer.keys())

                    if expected_ids == received_ids or time.time()-self.delta_time >= 0.2:
                        voltages = []
                        temps = []
                        currents = []
                        for i in micromod_map: 
                            voltages.extend(CANIO.parse_5vadc_tpdo(self.message_buffer[i]["micromod"],16))

                        for j in tc_mm_map: 

                            try:
                                tc_data = self.message_buffer[j]["tc_mm"]
                                temps.extend(CANIO.parse_temp_tpdo(tc_data))
                            except KeyError:
                                print(f"Warning: 'tc_mm' missing at buffer[{j}]")

                        for k in deditec_map: 
                            try:
                                deditec_data = self.message_buffer[k]["deditec"]
                                currents.extend(CANIO.parse_i_tpdo(deditec_data))
                            except KeyError:
                                print(f"Warning: 'deditec' missing at buffer[{k}]")


                        parsed_message = {
                            "timestamp": datetime.now().isoformat(),
                            "voltage": voltages,
                            "temperature": temps,
                            "fourtwenty": currents
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
                        self.delta_time = time.time()

        return can.Notifier(bus, [_AsyncListener()], loop=asyncio.get_running_loop())



    @staticmethod
    async def send_outputs(can_bus, eStopFlag, pump_state, esv_state):
        out_minimodul_id = 0x600
        out_minimod_id = 0x191
        if eStopFlag:
            msg_outmm = can.Message(arbitration_id=out_minimodul_id, data=[00]*8, is_extended_id=False)
            msg_minimod = CANIO.generic_dout_msg(0, 0, 0 ,0, out_minimod_id)

        else:
            speed = max(0.0, min(100.0, pump_state[1] if pump_state[1] is not None else 0.0))
            raw1, raw2 = CANIO.generate_pump_msg(pump_state[0], speed)
            data_minimodul = CANIO.generate_uint_16bit_msg(int(raw1), int(raw2), 0, 0)
            msg_outmm = can.Message(arbitration_id=out_minimodul_id, data=data_minimodul, is_extended_id=False)
            msg_minimod = CANIO.generic_dout_msg(esv_state[0], esv_state[1], 0 ,0, out_minimod_id)
        try:
            can_bus.send(msg_outmm)
            can_bus.send(msg_minimod)
        except Exception as e:
                print(f"CAN Send Error: {e}")

       


