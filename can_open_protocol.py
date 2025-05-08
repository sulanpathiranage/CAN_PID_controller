import can

class can_open:

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

    def changed_node_id(node_ids, can_bus):
        """run once when node_id changed

        Args:
            node_ids (int[]): which ones were changed to be reset
            can_bus (can.bus): canbus
        """
        for element in node_ids:
            cob_id = 0x600+element
            can_open.spo_configure(0x1011, 2,0x64616F6C, 4, can_bus, cob_id)

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
                can_open.spo_configure(tpdo_config_index, 1, 0x80000000 | (0x180 + element), 4, can_bus, cob_id) #disable at index 1
                can_open.spo_configure(tpdo_config_index, 5, 0x0064, 2, can_bus, cob_id) #0x0064 is 100 in dec. event timer set to 100ms
                can_open.spo_configure(tpdo_map_index, 0, 0x00000000, 1, can_bus, cob_id ) #set msg to 0
                for j in range(4):
                    subindex = j + 1
                    mapping_entry = (0x6401 << 16) | (subindex << 8) | 0x10
                    can_open.spo_configure(tpdo_map_index, subindex, mapping_entry, 4, can_bus, cob_id) #assign msgs to tpdo
                can_open.spo_configure(tpdo_map_index, 0, 0x04, 1, can_bus, cob_id ) #set msg to 4
                can_open.spo_configure(tpdo_config_index, 1, 0x00000000 | (0x180 + element), 4, can_bus, cob_id) #re-enable at index 1
            can_open.spo_configure(mnt_index, 0, 0x02,1, can_bus, cob_id ) #pre-operational set
            can_open.spo_configure(nvm_index, 1, 0x65766173,4, can_bus, cob_id) #save to eeprom

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



def main():
    channel = "PCAN_USBBUS1"
    bustype = "pcan"
    bitrate = 500e3
    bus = can.interface.Bus(channel=channel, interface=bustype, bitrate = bitrate)
    try: 
        #can_open.changed_node_id([0x01, 0x02], bus)
        #print("Node ID Reset!")
        can_open.commission_adc([0x01,0x02], bus, 2)
        can_open.operational([0x01, 0x02], bus)
        print("Initialized")
    except KeyboardInterrupt: 
        print("Initialized")
    finally: 
        bus.shutdown()
        print("Bus shutdown")

    
if __name__ == "__main__":
    main()
