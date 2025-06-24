
import can
import time 
import asyncio
from datetime import datetime
from typing import List, Dict, Any


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
            node_ids (_type_): Node ID in byte form maybe dec...
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
        data = []

        for i in range(0, 8, 2):
            raw = int.from_bytes(msg.data[i:i+2], byteorder='little', signed=False)
            current = (raw / 65535) * 50  # Scale raw unsigned 16-bit to 0-50 mA
            data.append(current)

        # Interpret signals:
        pump_feedback_mA = data[0]
        flow_meter_mA = data[1]

        pump_percent = CanOpen.mA_to_percent(pump_feedback_mA)
        flow_kg_per_h = CanOpen.mA_to_flow(flow_meter_mA)

        return {
            "raw_currents_mA": data,
            "pump_percent": pump_percent,
            "flow_kg_per_h": flow_kg_per_h
        }



    
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
    def generate_outmm_msg(pump_on, pump_speed, 
                           #esv_n2_on
                           ):

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
    def digital_to_16bitanalog(digitalval):
        if  digitalval == 1:
            output = 0xFF
        elif digitalval == 0:
            output = 0
        else: 
            print("digital value error!")

        return output
    
    @staticmethod
    def generic_dout_msg(out1, out2, out3, out4, arbitration_id, can_bus):
        aout1 = CanOpen.digital_to_16bitanalog(out1)
        aout2 = CanOpen.digital_to_16bitanalog(out2)
        aout3 = CanOpen.digital_to_16bitanalog(out3)
        aout4 = CanOpen.digital_to_16bitanalog(out4)
        payload = CanOpen.generate_uint_16bit_msg(aout1, aout2, aout3, aout4)
        msg = can.Message(arbitration_id=arbitration_id, is_extended_id=False, data = payload)
        can_bus.send(msg)

    
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
        pt_id = 0x181  # Pressure Transducer CAN ID
        tc_id_map = {0x182: 2, 0x183: 3, 0x184: 4, 0x185: 5} # Thermocouple CAN IDs mapping (mapping might be unused now)
        fourtwenty_id = 0x1FE # 4-20mA sensor CAN ID

        print("Creating CAN listener...")

        class _AsyncListener(can.Listener):
            """
            Internal asynchronous CAN message listener.
            This class defines how incoming CAN messages are handled.
            """
            def on_message_received(self, msg: can.Message):
                """
                Callback method invoked when a CAN message is received.
                Parses the message based on arbitration ID and puts structured data
                into the provided data_queue.
                """
                node_id = msg.arbitration_id
                
                # Prepare a common message dictionary structure
                parsed_message: Dict[str, Any] = {
                    "node_id": node_id,
                    "timestamp": datetime.now().isoformat(), # Add a timestamp for consistency
                    "data_type": None, # Will be set below
                    "values": None     # Will be set below
                }

                if node_id == pt_id:
                    voltages = CanOpen.parse_5vadc_tpdo(msg, resolution)
                    parsed_message["data_type"] = 'voltage'
                    parsed_message["values"] = voltages
                elif node_id in tc_id_map:
                    temps = CanOpen.parse_temp_tpdo(msg)
                    parsed_message["data_type"] = 'temperature'
                    parsed_message["values"] = temps
                elif node_id == fourtwenty_id:
                    signal_data = CanOpen.parse_i_tpdo(msg)
                    parsed_message["data_type"] = '4-20mA'
                    parsed_message["values"] = signal_data # This will be a dict itself
                else:
                    # If the message ID is not recognized, skip processing or log it
                    # print(f"Unhandled CAN message ID: {hex(node_id)}")
                    return # Exit if unhandled ID

                # Try to put the structured message into the queue
                try:
                    data_queue.put_nowait(parsed_message)
                except asyncio.QueueFull:
                    # If queue is full, remove the oldest item and then add the new one
                    try:
                        data_queue.get_nowait() # Remove oldest
                        data_queue.put_nowait(parsed_message) # Add new
                        # print("Queue was full, dropped oldest message.") # Optional debug
                    except Exception as e:
                        print(f"Error handling full queue: {e}")

        # Create and return the CAN Notifier, which manages the listener in the asyncio loop
        return can.Notifier(bus, [_AsyncListener()], loop=asyncio.get_running_loop())

    
    @staticmethod
    async def send_can_message(can_bus: can.Bus, can_id: int, data: List[int], eStopFlag):
        """nonblocking can_sender 

        Args:
            can_bus (can.Bus): can bus
            can_id (int): can address of target
            data (List[int]): msg

        Raises:
            ValueError: exception error
        """
        
        if (eStopFlag) :
            msg = can.Message(arbitration_id=can_id, data=[0x00]*8, is_extended_id=False)
        else:
            if len(data) > 8:
                raise ValueError("CAN data cannot exceed 8 bytes")
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)

            try:
                can_bus.send(msg)
                #print(f"[SEND] Sent CAN message: COB-ID=0x{can_id:X}, Data={data}")
            except can.CanError as e:
                print(f"[ERROR] Failed to send CAN message: {e}")

        

def main():

    # === CONFIGURATION ===
    channel = "PCAN_USBBUS1"
    #bustype = "pcan"
    bustype = "virtual"
    bitrate = 500e3
    node_ids = [0x23]                # List of CANopen node IDs to configure
    num_tpdos = 3                    # How many TPDOs to setup per node

    # === SETUP CAN BUS ===
    try:
        can_bus = can.interface.Bus(channel=channel, bustype=bustype, bitrate=bitrate)
    except Exception as e:
        print(f"[ERROR] Failed to open CAN bus: {e}")
        return

    print("[INFO] CAN bus initialized")

    # === COMMISSION TPDOs ===
    try:
        CanOpen.commission_adc(node_ids, can_bus, num_tpdos)
        print("[INFO] TPDOs successfully configured")
    except Exception as e:
        print(f"[ERROR] TPDO configuration failed: {e}")
        return

    # === SEND NMT TO ENTER OPERATIONAL STATE ===
    try:
        CanOpen.operational(node_ids, can_bus)
        print("[INFO] Sent NMT operational command")
    except Exception as e:
        print(f"[ERROR] Failed to set operational mode: {e}")

if __name__ == "__main__":
    main()




