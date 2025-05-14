import pid_controller
import can
import threading
import time
import can_open_protocol
#TODO sampling rates

def io_fn():
    while True:
        print("INPUTS HERE")
        time.sleep(1)

def gui_fn():
    while True:
        print("gui here")
        time.sleep(1)

    

def main():
    io_thread = threading.Thread(target=io_fn, daemon= True)
    gui_thread = threading.Thread(target = gui_fn, daemon= True)


if __name__ == "__main__":
    main()



