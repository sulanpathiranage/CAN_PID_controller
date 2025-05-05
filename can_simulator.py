import can_reader

import can_reader
import threading
import time

def can_sender(channel, bustype, can_id, base_data, interval):
    """Send CAN messages in a thread

    Args:
        channel (_type_): CAN port e.g. USB1
        bustype (_type_): can interface e.g. PCAN
        can_id (_type_): can address e.g. 0x600
        base_data (hex array - 8bytes): some data, third and fourth byte are just counters
        interval (int): period of messages 
    """
    bus = can_reader.interface.Bus(channel=channel, bustype=bustype)
    counter = 1

    try:
        while True:
            # Clone the base data and insert counters at byte 2 and 3
            data = base_data[:]
            data[2] = counter & 0xFF        # 3rd byte
            data[3] = (counter >> 8) & 0xFF # 4th byte

            msg = can_reader.Message(arbitration_id=can_id,
                              data=data,
                              is_extended_id=False)
            bus.send(msg)
            print(f"[0x{can_id:X}] Sent: {msg.data.hex()} (Counter: {counter})")
            counter += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"Sender for 0x{can_id:X} stopped.")

def main():
    channel = 'PCAN_USBBUS1'
    bustype = 'pcan'

    thread_600 = threading.Thread(
        target=can_sender,
        args=(channel, bustype, 0x600, [0x01, 0x02, 0x00, 0x00, 0x05, 0x06, 0x07, 0x08], 1),
        daemon=True
    )

    thread_613 = threading.Thread(
        target=can_sender,
        args=(channel, bustype, 0x613, [0xAA, 0xBB, 0x00, 0x00, 0xEE, 0xFF, 0x11, 0x22], 1.5),
        daemon=True
    )

    thread_600.start()
    thread_613.start()

    print("Simulating CAN messages with changing counters... Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped all senders.")


if __name__ == "__main__":
    main()
