import can

class can_open:
    def commission_adc(node_ids, can_bus):
        """setup tpdos for canopen adc module, will be found at 0x180+ node id

        Args:
            node_ids (_type_): node ids - sdo setup messages sent to 0x600+node id, configuring such that tpdo
            can_bus (_type_): _description_
        """
        for element in node_ids:
            cob_id = 0x600+element
            restore_default_msg = 0x1011 #TODO
            disable_msg = 0x1800 #TODO 
            msg_lng_msg, event_time_msg, map1_4_msg, set_msg


            
            print(payload)
            msg = can.Message(arbitration_id=nmt_id, data=payload, is_extended_id=False)
            can_bus.send(msg)

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
        can_open.initialize_nodes([0x01, 0x02], bus)
        print("Initialized")
    except KeyboardInterrupt: 
        print("Initialized")
    finally: 
        bus.shutdown()
        print("Bus shutdown")

    
if __name__ == "__main__":
    main()
