import can
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time
import threading
import queue
from can_simulator import can_sim

# CAN ID to module name
MODULE_NAMES = {
    0x600: "Analog Out Module",
    0x613: "Analog In Module"
}

# Store latest analog input values
analog_in_ch1 = deque(maxlen=100)
analog_in_ch2 = deque(maxlen=100)
timestamps = deque(maxlen=100)

# Create a Queue to safely share messages between threads
message_queue = queue.Queue()

def decode_current(raw_value: int) -> float:
    """Map a 16-bit raw value to a current in milliamps (4–20 mA)."""
    return 4.0 + (16.0 * raw_value / 65535)

def decode_flowrate(fourtwentyvalue):
    min_flow = 0
    max_flow = 50
    flow_rate = min_flow + (fourtwentyvalue - 4.0) * (max_flow - min_flow) / 16.0
    return flow_rate

def parse_message(msg: can.Message):
    can_id = msg.arbitration_id
    data = list(msg.data)
    module_name = MODULE_NAMES.get(can_id, f"Unknown Module (0x{can_id:X})")

    if can_id == 0x613:
        # Channel 1: bytes 2–3
        raw_ch1 = data[2] + (data[3] << 8)
        # Channel 2: bytes 4–5
        raw_ch2 = data[2] + (data[3] << 8)

        current_ch1 = decode_current(raw_ch1)
        current_ch2 = decode_current(raw_ch2)

        now = time.time()
        analog_in_ch1.append(decode_flowrate(current_ch1))
        analog_in_ch2.append(current_ch2)
        timestamps.append(now)

        print(f"[{module_name}] CH1: {current_ch1:.2f} mA | CH2: {current_ch2:.2f} mA")

    else:
        raw_counter = data[2] + (data[3] << 8)
        print(f"[{module_name}] ID: 0x{can_id:X}, Counter: {raw_counter}")

def animate(i):
    """Updates the live plot."""
    if len(timestamps) > 0:
        plt.cla()
        plt.plot(timestamps, analog_in_ch1, label="Channel 1 (L/s)", color='blue')
        #plt.plot(timestamps, analog_in_ch2, label="Channel 2 (mA)", color='green')
        plt.xlabel("Time (s)")
        plt.ylabel("Flowrate (L/s)")
        plt.ylim(0,100)
        plt.legend(loc="upper left")
        plt.tight_layout()

def can_reader(channel='can_sim', bustype='virtual'):
    """Reads messages from the CAN bus and puts them into the queue."""
    print("CAN Reader started...")
    bus = can.interface.Bus(channel=channel, interface=bustype)

    try:
        for msg in bus:
            message_queue.put(msg)  # Put each message into the queue
    except KeyboardInterrupt:
        print("Reader stopped.")
    finally:
        bus.shutdown()
        print("CAN bus closed properly.")

def reader_thread():
    """Start CAN reader in a separate thread."""
    can_reader()

def message_processing_thread():
    """Process CAN messages from the queue."""
    while True:
        try:
            msg = message_queue.get(timeout=1)  # Block until a message is available
            parse_message(msg)
        except queue.Empty:
            pass  # No message available

if __name__ == "__main__":
    # Start CAN simulation in a separate thread
    sim_thread = threading.Thread(target=can_sim, daemon=True)
    sim_thread.start()

    # Give time for virtual bus to initialize
    time.sleep(1)

    # Start the CAN reader thread
    reader_thread = threading.Thread(target=reader_thread, daemon=True)
    reader_thread.start()

    # Start the message processing thread
    processing_thread = threading.Thread(target=message_processing_thread, daemon=True)
    processing_thread.start()

    # Start the matplotlib animation in the main thread
    ani = animation.FuncAnimation(plt.gcf(), animate, interval=500)
    plt.show()

    # Keep the main thread
