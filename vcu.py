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

    

