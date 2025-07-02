import can
import time

def read_bus_timed(bus, duration=3):
    print(f"Reading CAN bus for {duration} seconds...")
    end_time = time.time() + duration
    while time.time() < end_time:
        msg = bus.recv(timeout=0.1)
        if msg:
            print(f"ID: 0x{msg.arbitration_id:X} DLC: {msg.dlc} Data: {msg.data.hex()} Timestamp: {msg.timestamp:.3f}")


                   


def read_bus_continous(channel,bitrate):
    
    print(f"Starting PCAN CAN Sniffer on channel '{channel}' with bitrate {bitrate}...")

    bus = can.interface.Bus(channel=channel, interface='pcan', bitrate=bitrate)

    try:
        for msg in bus:
            print(f"ID: 0x{msg.arbitration_id:X} DLC: {msg.dlc} Data: {msg.data.hex()} Timestamp: {msg.timestamp:.3f}")
    except KeyboardInterrupt:
        print("\nSniffer stopped.")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    channel = "PCAN_USBBUS1"
    bustype = "pcan"
    bitrate = 500e3
    read_bus_continous(channel, bitrate)
