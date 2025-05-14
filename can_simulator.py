import can
import threading
import time
import random

def flow_sensor_simulator(channel, bustype, can_id, base_data, interval):
    """Simulate CAN messages with flow sensor readings (4–20 mA)."""

    bus = can.interface.Bus(channel=channel, interface=bustype)
    flow_value = 4.0  # Start at 4 mA

    try:
        while True:
            # Map the flow_value (4-20 mA) to a 16-bit integer (0-65535)
            raw_value = int((flow_value - 4.0) * (65535.0 / 16.0))  # Convert mA to raw 16-bit value

            # Clone the base data and insert flow sensor readings
            data = base_data[:]
            data[2] = raw_value & 0xFF        # 3rd byte (low byte)
            data[3] = (raw_value >> 8) & 0xFF # 4th byte (high byte)

            msg = can.Message(arbitration_id=can_id,
                              data=data,
                              is_extended_id=False)
            bus.send(msg)
            print(f"[0x{can_id:X}] Sent: {msg.data.hex()} (Flow: {flow_value:.2f} mA)")

            # Increase flow_value, wrapping around if it goes above 20
            flow_value += 0.5  # Simulate flow increase
            flow_value = flow_value + random.uniform(-0.3, 0.3)
            if flow_value > 20.0:
                flow_value = 4.0  # Reset to 4 mA if it exceeds 20 mA

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"Flow simulator for 0x{can_id:X} stopped.")
        
def can_sender(channel, bustype, can_id, base_data, interval):
    """Send CAN messages 

    Args:
        channel (_type_): CAN port e.g. USB1
        bustype (_type_): can interface e.g. PCAN
        can_id (_type_): can address e.g. 0x600
        base_data (hex array - 8bytes): some data, third and fourth byte are just counters
        interval (int): period of messages 
    """
    bus = can.interface.Bus(channel=channel, interface=bustype)
    counter = 1

    try:
        while True:
            # Clone the base data and insert counters at byte 2 and 3
            data = base_data[:]
            data[2] = counter*100 & 0xFF        # 3rd byte
            data[3] = (counter*100 >> 8) & 0xFF # 4th byte

            msg = can.Message(arbitration_id=can_id,
                              data=data,
                              is_extended_id=False)
            bus.send(msg)
            print(f"[0x{can_id:X}] Sent: {msg.data.hex()} (Counter: {counter})")
            counter += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"Sender for 0x{can_id:X} stopped.")

def can_sim():
    channel = 'can_sim'
    bustype = 'virtual'
    thread_600 = threading.Thread(
    target=can_sender,
    args=(channel, bustype, 0x600, [0x01, 0x02, 0x00, 0x00, 0x05, 0x06, 0x07, 0x08], 1.5),
    daemon=True
    )
    thread_613 = threading.Thread(
    target=flow_sensor_simulator,
    args=(channel, bustype, 0x613, [0xAA, 0x10, 0x00, 0x0A, 0xEE, 0xFF, 0x11, 0x22], 1.5),
    daemon=True
    )
    thread_600.start()
    thread_613.start()

    
def main():
    print("Simulating CAN messages... Press Ctrl+C to stop.")
    can_sim()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped all senders.")


if __name__ == "__main__":
    main()
