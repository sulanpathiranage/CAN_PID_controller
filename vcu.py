import pid_controller
import can
import asyncio 
import time
import can_open_protocol
#TODO sampling rates

def io_fn():
    channel = "PCAN_USBBUS1"
    bustype = "pcan"
    bitrate = 500e3
    bus = can.interface.Bus(channel=channel, interface=bustype, bitrate = bitrate)
    while True:
        can_open_protocol.parse_inputs()



def gui_fn():
    while True:
        print("gui here")
        time.sleep(1)

    

def main():
    try:
        io_thread = threading.Thread(target=io_fn, daemon= False)
        gui_thread = threading.Thread(target = gui_fn, daemon= False)

            
        io_thread.start()
        gui_thread.start()
        io_thread.join()
        gui_thread.join()  
    except KeyboardInterrupt:
        print("Program killed!")

if __name__ == "__main__":
    main()



