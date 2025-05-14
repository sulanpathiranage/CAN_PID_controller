import can
import pcan_sniffer
import time 

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
    def parse_tpdo(data_bytes):
        """parse message from tpdo

        Args:
            data_bytes (): payload from can message to parse

        Raises:
            ValueError: if can message is not 8 bytes -- lost bytes

        Returns:
            values (float[]): list of values contained in can message
        """
        if len(data_bytes) != 8:
            raise ValueError("TPDO frame should be exactly 8 bytes")
        values = []
        for i in range(0, 8, 2):
            val = int.from_bytes(data_bytes[i:i+2], byteorder='little')
            values.append(val)
        return values



def main():
    channel = "PCAN_USBBUS1"
    bustype = "pcan"
    bitrate = 500e3
    bus = can.interface.Bus(channel=channel, interface=bustype, bitrate = bitrate)
    try: 
        #CanOpen.changed_node_id([0x01, 0x02], bus)
        #print("Node ID Reset!")
        CanOpen.commission_adc([0x01,0x02], bus, 2)
        print("Commissioned!")
        pcan_sniffer.read_bus_timed(bus, 10)
        CanOpen.operational([0x01, 0x02], bus)
        pcan_sniffer.read_bus_timed(bus, 5)
        print("Initialized")
    except KeyboardInterrupt: 
        print("Initialized")
    finally: 
        bus.shutdown()
        print("Bus shutdown")

    
if __name__ == "__main__":
    main()
