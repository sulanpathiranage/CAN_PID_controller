import can

def sniff_pcan(channel='PCAN_USBBUS1', bitrate=250000):
    
    print(f"Starting PCAN CAN Sniffer on channel '{channel}' with bitrate {bitrate}...")

    bus = can.interface.Bus(channel=channel, bustype='pcan', bitrate=bitrate)

    try:
        for msg in bus:
            print(f"ID: 0x{msg.arbitration_id:X} DLC: {msg.dlc} Data: {msg.data.hex()} Timestamp: {msg.timestamp:.3f}")
    except KeyboardInterrupt:
        print("\nSniffer stopped.")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    sniff_pcan()
