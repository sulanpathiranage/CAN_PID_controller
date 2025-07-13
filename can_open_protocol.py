
import can
import time 
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import struct


# def log_row_to_csv(filename: str, row: Dict[str, Any]) -> None:
#     """create csv
#     log_row_to_csv("can_reader.csv", parsed_message)

#     Args:
#         filename (str): string of csv filename
#         row (Dict[str, Any]): str is header, value is col data
#     """
#     new_df = pd.DataFrame([row])

#     if os.path.isfile(filename):
#         df = pd.read_csv(filename)

#         df = df.reindex(columns=df.columns.union(new_df.columns))
#         new_df = new_df.reindex(columns=df.columns)

#         df = pd.concat([df, new_df], ignore_index=True)
#     else:
#         df = new_df

    # df.to_csv(filename, index=False)

class CanOpen:
    timeout_timer = time.time()

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
        msg = can.Message(arbitration_id=cob_id, data=data, is_extended_id=False)
        # print(msg)
        can_bus.send(msg)
        # print(f"Sent message: COB-ID=0x{cob_id:X}, Data={data}")

        # Always listen for a response immediately after sending
        # response = CanOpen.listen_for_responses(can_bus, 1.0)
        # if response:
        #     # print(f"Received response: COB-ID=0x{response.arbitration_id:X}, Data={response.data.hex()}")
        # else:
        #     # print(f"No response received within {1} seconds for COB-ID 0x{cob_id:X}")

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
            CanOpen.pre_operational(node_ids, can_bus) #pre-operational set
            time.sleep(1)
            for i in range(num_can_msgs):
                tpdo_config_index = 0x1800 + i
                tpdo_map_index = 0x1A00 + i
                #1 is COB_ID, 2 transmission type, 3 inhibit time, 5 event timer
                base_cob_offset = 0x180 + (i * 0x100) 
                actual_tpdo_cob_id = base_cob_offset + element 
                time.sleep(0.1)
                tpdo_cob_id = 0x80000000 | (0x180 + element + i)
                CanOpen.spo_configure(tpdo_config_index, 1, actual_tpdo_cob_id, 4, can_bus, cob_id)
                time.sleep(0.1)
                CanOpen.spo_configure(tpdo_config_index, 3, 0x0000, 2, can_bus, cob_id)  # No inhibit time
                time.sleep(0.1)
                CanOpen.spo_configure(tpdo_map_index, 0, 0x00000000, 1, can_bus, cob_id ) #set msg to 0
                time.sleep(0.1)
                start_channel_for_this_tpdo = (i * 4) + 1 
                current_mapped_channels = 0 
                
                for j in range(4):
                    analog_channel_number = start_channel_for_this_tpdo + j 
                    if analog_channel_number > 16:
                        break 
                    mapping_entry = (0x6401 << 16) | (analog_channel_number << 8) | 0x10 
                    CanOpen.spo_configure(tpdo_map_index, j + 1, mapping_entry, 4, can_bus, cob_id) 
                    time.sleep(0.1)
                    current_mapped_channels += 1
                
                CanOpen.spo_configure(tpdo_map_index, 0, current_mapped_channels, 1, can_bus, cob_id)   
                CanOpen.spo_configure(tpdo_map_index, 0, 0x04, 1, can_bus, cob_id ) #set msg to 4
                time.sleep(0.1)
                CanOpen.spo_configure(tpdo_config_index, 1,actual_tpdo_cob_id, 4, can_bus, cob_id) #re-enable at index 1
                time.sleep(0.1)
                CanOpen.spo_configure(tpdo_config_index, 5, 0x0064, 2, can_bus, cob_id) #0x0064 is 100 in dec. event timer set to 100ms
                time.sleep(0.1)
        
            CanOpen.spo_configure(nvm_index, 1, 0x65766173,4, can_bus, cob_id) #save to eeprom
            time.sleep(0.1)

    @staticmethod
    def operational(node_ids, can_bus):
        """Set nodes to operational

        Args:
            node_ids (_type_): Node ID in byte form maybe dec...
            can_bus (_type_): can bus object i.e can_bus = can.interface.Bus(...)
        """
        nmt_id  = 0x0000

        for element in node_ids:
            payload = [0x01, element]
            msg = can.Message(arbitration_id=nmt_id, data=payload, is_extended_id=False)
            print(msg)
            can_bus.send(msg)

    @staticmethod
    def pre_operational(node_ids, can_bus):
        """Set nodes to operational

        Args:
            node_ids (_type_): Node ID in byte form maybe dec...
            can_bus (_type_): can bus object i.e can_bus = can.interface.Bus(...)
        """
        nmt_id  = 0x0000

        for element in node_ids:
            payload = [0x80, element]
            msg = can.Message(arbitration_id=nmt_id, data=payload, is_extended_id=False)
            print(msg)
            can_bus.send(msg)


    @staticmethod
    def reset_node(node_ids, can_bus):
        """Set nodes to operational

        Args:
            node_ids (_type_): Node ID in byte form maybe dec...
            can_bus (_type_): can bus object i.e can_bus = can.interface.Bus(...)
        """
        nmt_id  = 0x0000

        for element in node_ids:
            payload = [0x81, element]
            msg = can.Message(arbitration_id=nmt_id, data=payload, is_extended_id=False)
            print(msg)
            can_bus.send(msg)

    # ===== BELOW is general CANbus I/O ABOVE is configuring/working with specifically CANOPEN =======

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
    def flow_to_16bitanalog(flow):
        if  flow == 32.8:
            output = 0xFFFF
        elif flow == 0:
            output = 0
        else: 
            output = (32.8/100)*65535

        return output


    @staticmethod     
    def generate_outmm_msg1(pump_on, pump_speed, mfm1_state, mfm2_state):

        if pump_speed < 0:
            pump_speed = 0
        elif pump_speed >100:
            pump_speed = 100
        else: 
            pump_speed = pump_speed

        raw_out1 = pump_speed* 655

        raw_out2 = CanOpen.digital_to_16bitanalog(pump_on)

        raw_out3 = CanOpen.flow_to_16bitanalog(mfm1_state)
        raw_out4 = CanOpen.flow_to_16bitanalog(mfm2_state)

        return raw_out1, raw_out2, raw_out3, raw_out4
    
    @staticmethod     
    def generate_outmm_msg2(alicat_state):

        raw_out1 = CanOpen.percent_to_16bitanalog(alicat_state)

        return raw_out1
    
    
    @staticmethod
    def generic_dout_msg(out1, out2, out3, out4, arbitration_id):
        aout1 = CanOpen.digital_to_16bitanalog(out1)
        aout2 = CanOpen.digital_to_16bitanalog(out2)
        aout3 = CanOpen.digital_to_16bitanalog(out3)
        aout4 = CanOpen.digital_to_16bitanalog(out4)
        payload = CanOpen.generate_uint_16bit_msg(aout1, aout2, aout3, aout4)
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
        #TODO attach time object in CAN class
        micromod_map = [0x180, 0x181]
        tc_mm_map = [0x182,0x183,0x184,0x185]
        deditec_map = [0x1A3, 0x2A3, 0x3A3, 0x4A3]
        # can_ids = {
        #     0x181 : "micromod",
        #     0x182 : "tc_mm",
        #     0x1FE : "deditec",
        #     }   
        # micromod_map = [0x181]
        # tc_mm_map = [0x182]
        # deditec_map = [0x1FE]

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
#pass data into queue asynchronously
            def on_message_received(self, msg: can.Message):
                rec_id = msg.arbitration_id
                if rec_id not in can_ids:
                    return
                message_type = can_ids[rec_id]
                self.message_buffer[rec_id][message_type] = msg

                received_ids = set(self.message_buffer.keys())
                current_time = time.time()

                if (self.expected_ids == received_ids) or (current_time - self.delta_time >= 0.2):
                    if current_time - self.delta_time < 0.1:
                        # Too soon since last push, skip this cycle to throttle at 100ms
                        return

                    # process messages as before
                    voltages = []
                    temps = []
                    currents = []

                    for i in micromod_map:
                        try:
                            v_data = self.message_buffer[i]["micromod"]
                            voltages.extend(CanOpen.parse_5vadc_tpdo(v_data, 16))
                        except Exception:
                            print(f"Warning: Micromod message for ID {hex(i)} missing. Appending 16 zeros.")
                            voltages.extend(CanOpen.parse_5vadc_tpdo(can.Message(arbitration_id=0, data=[0]*8), 16))

                    for j in tc_mm_map:
                        try:
                            tc_data = self.message_buffer[j]["tc_mm"]
                            temps.extend(CanOpen.parse_temp_tpdo(tc_data))
                        except KeyError:
                            print(f"Warning: 'tc_mm' missing at buffer[{j}]")
                            temps.extend(CanOpen.parse_temp_tpdo(can.Message(arbitration_id=0, data=[0]*8)))

                    for k in deditec_map:
                        try:
                            deditec_data = self.message_buffer[k]["deditec"]
                            currents.extend(CanOpen.parse_i_tpdo(deditec_data))
                        except KeyError:
                            print(f"Warning: 'deditec' missing at buffer[{k}]")
                            currents.extend(CanOpen.parse_i_tpdo(can.Message(arbitration_id=0, data=[0]*8)))

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
    async def send_outputs(can_bus, eStopFlag, pump_state, esv_state, mfm_state, pic_state):
        out_minimodul1_id = 0x600
        out_minimodul2_id = 0x601
        out_minimod_id = 0x191
        heaterOn = True
        if eStopFlag:
            msg_outmm = can.Message(arbitration_id=out_minimodul1_id, data=[00]*8, is_extended_id=False)
            msg_outmm1 = can.Message(arbitration_id=out_minimodul2_id, data=[00]*8, is_extended_id=False)
            msg_minimod = CanOpen.generic_dout_msg(0, 0, 0 ,0, out_minimod_id)

        else:
            speed = max(0.0, min(100.0, pump_state[1] if pump_state[1] is not None else 0.0))
            raw1, raw2, raw3, raw4 = CanOpen.generate_outmm_msg1(pump_state[0], speed, mfm_state[0], mfm_state[1])
            raw5 = CanOpen.generate_outmm_msg2(pic_state)
            data_minimodul2 = CanOpen.generate_uint_16bit_msg(int(raw5),0,0,0)
            data_minimodul = CanOpen.generate_uint_16bit_msg(int(raw1), int(raw2), int(raw3), int(raw4))
            msg_outmm = can.Message(arbitration_id=out_minimodul1_id, data=data_minimodul, is_extended_id=False)
            msg_outmm1 = can.Message(arbitration_id=out_minimodul2_id, data=data_minimodul2, is_extended_id=False)
            msg_minimod = CanOpen.generic_dout_msg(heaterOn, esv_state[0], esv_state[1] ,0, out_minimod_id)
        try:
            can_bus.send(msg_outmm)
            can_bus.send(msg_outmm1)
            can_bus.send(msg_minimod)
        except Exception as e:
                print(f"CAN Send Error: {e}")

       

def main():

    channel = "PCAN_USBBUS1"
    bustype = "pcan"
    bitrate = 500e3
    node_ids = [0x23]          # List of CANopen node IDs to configure
    num_tpdos = 4                    # How many TPDOs to setup per node

    try:
        can_bus = can.interface.Bus(channel=channel, bustype=bustype, bitrate=bitrate)
    except Exception as e:
        print(f"Failed to open CAN bus: {e}")
        return

    print("CAN bus initialized")

    try:
        CanOpen.commission_adc(node_ids, can_bus, num_tpdos)
        print(" TPDOs successfully configured")
    except Exception as e:
        print(f"TPDO configuration failed: {e}")
        return
    time.sleep(1)
    try:
        CanOpen.reset_node(node_ids, can_bus)
        print("Sent NMT reset node command")
    except Exception as e:
        print(f"Failed to set operational mode: {e}")

    time.sleep(1)
    try:
        CanOpen.operational(node_ids, can_bus)
        print("Sent NMT operational command")
    except Exception as e:
        print(f"Failed to set operational mode: {e}")

# if __name__ == "__main__":
#     main()




