import asyncio
import can
from collections import deque
from typing import List, Dict, Any, Union

from PySide6.QtCore import QObject, Signal as pyqtSignal
from fault_manager import FaultManager


from can_open_protocol import CanOpen

class SystemDataManager(QObject):
    pressure_updated = pyqtSignal(list)
    temperature_updated = pyqtSignal(list)
    pump_feedback_updated = pyqtSignal(float, float, float)
    e_stop_toggled = pyqtSignal(bool)
    esv1_state_toggled = pyqtSignal(bool)
    esv2_state_toggled = pyqtSignal(bool)
    mfm1_setpoint_updated = pyqtSignal(float)   # 0‑100 %
    mfm2_setpoint_updated = pyqtSignal(float)
    pic_setpoint_updated = pyqtSignal(float)
    can_connection_status_changed = pyqtSignal(bool) 
    can_error = pyqtSignal(str) 
    interlock1_detected = pyqtSignal(bool, list) # channel_index, [lw, ls, hw, hs]
    interlock2_detected = pyqtSignal(bool, list) # channel_index, [lw, ls, hw, hs]
    interlock3_detected = pyqtSignal(bool, list) # channel_index, [lw, ls, hw, hs]
    interlock4_detected = pyqtSignal(bool, list) # channel_index, [lw, ls, hw, hs]



    # pt_info = {
    #     "PT10110": 30,
    #     "PT10120": 60,
    #     "PT10130": 60,
    #     "PT10118": 60,
    # }
    # tc_designators = ["TI10111","TI10115","TI10116","TI10117"]
    pt_info = {
       "PT10110": 30, 
       "PT10120": 60, 
       "PT10130": 60, 
       "PT10118": 60, 
       "PT10117": 60
    }
    tc_designators = ["TI10111","TI10115","TI10116","TI10117", "TI01","TI10121", "TI10119"]

    deditec_info = {
        "PumpFeedback": 100,    # percent
        "FT1024":       32.8,   # kg/h
        "FT10106":      32.8    # kg/h
    }

    pt_designators   = list(pt_info)         
    deditec_feedback = list(deditec_info)    


    def __init__(self, history_len: int = 100):
        super().__init__()
        self._history_len = history_len
        
        self._ch_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(len(self.pt_designators))]
        self._temp_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(len(self.tc_designators))]
        self._deditec_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(len(self.deditec_feedback))]
        
        self._eStopValue = False
        
        self._last_pressures = [0.0] * len(self.pt_designators)
        self._last_temps = [0.0] * len(self.tc_designators)
        self._last_deditec = [0.0] * len(self.deditec_feedback)  
        
        self.mfm_setpoints = [0.0, 0.0]
        self.pic_setpoint = 0.0


        self.INVALID_TEMP_MARKER = -3276.8
        self.interlock_flag = False

        self.esv_state = [0, 0]
        self._esv1_cmd = False
        self._esv2_cmd = False
        
        self._bus = None
        self._can_connected = False
        self._can_data_queue = asyncio.Queue(maxsize=20) 
        self._consumer_task = None
        self._sender_task = None

        self._commanded_pump_on = 0
        self._commanded_manual_speed = 0
        self._commanded_pid_output = None 

        self._sensor_data_sources: Dict[str, Union[deque, str]] = {}

        self.mfm1_setpoint_updated.emit(self.mfm_setpoints[0])
        self.mfm2_setpoint_updated.emit(self.mfm_setpoints[1])
        
        for i, designator in enumerate(self.pt_designators):
            if i < len(self._ch_data):
                self._sensor_data_sources[designator] = self._ch_data[i]
            else:
                print(f"Warning: _ch_data does not have enough deques for {designator}")
        
        for i, designator in enumerate(self.tc_designators):
            if i < len(self._temp_data):
                self._sensor_data_sources[designator] = self._temp_data[i]
            else:
                print(f"Warning: _temp_data does not have enough deques for {designator}")

        for i, designator in enumerate(self.deditec_feedback):
            if i < len(self._deditec_data):
                self._sensor_data_sources[designator] = self._deditec_data[i]
            else:
                print(f"Warning: _deditec_data does not have enough deques for {designator}")


    @property
    def history_len(self) -> int:
        return self._history_len

    @property
    def ch_data(self) -> List[deque]:
        return self._ch_data

    @property
    def temp_data(self) -> List[deque]:
        return self._temp_data

    @property
    def eStopValue(self) -> bool:
        return self._eStopValue

    @eStopValue.setter
    def eStopValue(self, value: bool):
        if self._eStopValue != value:
            self._eStopValue = value
            self.e_stop_toggled.emit(value)
            if value:
                self._commanded_pump_on = 0
                self._commanded_manual_speed = 0
                self._commanded_pid_output = 0.0

                self.esv_state[:] = [0] * len(self.esv_state)

    def set_pic(self, value: float):
        if self.pic_setpoint != value:
            self.pic_setpoint = value
            self.pic_setpoint_updated.emit(value)

    def set_mfm1(self, percent: float):
        """percent must be 0‑100."""
        self.mfm_setpoints[0] = max(0.0, min(100.0, percent))
        self.mfm1_setpoint_updated.emit(self.mfm_setpoints[0])

    def set_mfm2(self, percent: float):
        self.mfm_setpoints[1] = max(0.0, min(100.0, percent))
        self.mfm2_setpoint_updated.emit(self.mfm_setpoints[1])

    def get_mfm1(self) -> float:  return self.mfm_setpoints[0]
    def get_mfm2(self) -> float:  return self.mfm_setpoints[1]


    def set_esv1(self, state: bool):
        self._esv1_cmd = state
        self.update_commanded_esv_state()
        self.esv1_state_toggled.emit(state)

    def set_esv2(self, state: bool):
        self._esv2_cmd = state
        self.update_commanded_esv_state()
        self.esv2_state_toggled.emit(state)

    @property
    def last_pressures(self) -> List[float]:
        return self._last_pressures

    @property
    def last_temps(self) -> List[float]:
        return self._last_temps

    @property
    def last_deditec(self) -> List[float]:
        return self._last_deditec

    @property
    def deditec_feedback_names(self) -> List[str]:
        return self.deditec_feedback

    @property
    def can_connected(self) -> bool:
        return self._can_connected
    
    @property
    def pressure_sensor_names(self) -> List[str]:
        return self.pt_designators

    @property
    def temperature_sensor_names(self) -> List[str]:
        return self.tc_designators

    @property
    def flow_sensor_names(self) -> List[str]:
        return self.deditec_feedback

    def _bar_to_psi(self, barg: float) -> float:
        return barg * 14.5038
    
    def get_pic(self) -> float:
        return self.pic_setpoint

    def trigger_initial_setpoint_emits(self):
        """
        Emits the current setpoint values to ensure GUI elements are initialized.
        This should be called after all GUI connections are established.
        """
        self.mfm1_setpoint_updated.emit(self.mfm_setpoints[0])
        self.mfm2_setpoint_updated.emit(self.mfm_setpoints[1])
        self.pic_setpoint_updated.emit(self.pic_setpoint)
    
    @staticmethod    
    def mA_to_scale(current_mA, scale):
        if current_mA < 4:
            return 0.0
        elif current_mA > 20:
            current_mA = 20
        return ((current_mA - 4) / 16.0) * scale

    def get_sensor_deque(self, designator: str) -> Union[deque, None]:
        """
        Retrieves the deque (history) for a sensor using its designator string.
        Returns None if no deque is associated (e.g., for single-value sensors like flow).
        """
        source = self._sensor_data_sources.get(designator)
        if isinstance(source, deque):
            return source
        return None 
    
    def get_latest_sensor_value(self, designator: str) -> float:
        """
        Retrieves the latest value for a sensor using its designator string.
        This is the single easy reference point for current sensor readings.
        """
        source = self._sensor_data_sources.get(designator)
        
        if isinstance(source, deque):
            if source: # Check if deque is not empty
                return source[-1] # Return the last (latest) value from the deque
            else:
                return 0.0 # Deque is empty, return default
             
        
        print(f"Warning: Sensor designator '{designator}' not found or no data. Returning 0.0.")
        return 0.0

    def update_pressure_data(self, raw_voltages: list[float]):
        if len(raw_voltages) < len(self.pt_info):
            self.can_error.emit("Short pressure packet")
            return

        for i, (name, full_scale) in enumerate(self.pt_info.items()):
            scaled = raw_voltages[i] * full_scale
            self._last_pressures[i] = scaled
            self._ch_data[i].append(scaled)

        self.interlock_trigger() 
        self.pressure_updated.emit(self._last_pressures) 

    def update_temperature_data(self, values: List[float]):
        """Updates internal temperature data and emits signal."""
        if len(values) < len(self.tc_designators):
            print(f"Warning: Temperature data received with unexpected length: {len(values)}. Expected {len(self.tc_designators)}.")
            return

        incoming_temps = values[:len(self.tc_designators)]
        is_invalid_reading = all(t == self.INVALID_TEMP_MARKER for t in incoming_temps)

        if not is_invalid_reading:
            for i in range(len(self.tc_designators)):
                if i < len(incoming_temps):
                    self._last_temps[i] = incoming_temps[i] 
                    if i < len(self._temp_data): 
                        self._temp_data[i].append(incoming_temps[i])
            
            self.interlock_trigger() 
        self.temperature_updated.emit(self._last_temps)

    def update_current_data(self, mA: list[float]):
        # if len(mA) < len(self.deditec_info):
        #     return                                       # silent drop

        for i, (name, full_scale) in enumerate(self.deditec_info.items()):
            val = SystemDataManager.mA_to_scale(mA[i], full_scale)
            self._last_deditec[i] = val
            self._deditec_data[i].append(val)

        self.pump_feedback_updated.emit(
            self._last_deditec[self.deditec_feedback.index("PumpFeedback")],
            self._last_deditec[self.deditec_feedback.index("FT1024")],
            self._last_deditec[self.deditec_feedback.index("FT10106")]
        )

        self.interlock_trigger()



    def reset_deditec_data(self):
        for i in range(len(self.deditec_feedback)):
            self._last_deditec[i] = 0.0
            self._deditec_data[i].clear()
            self._deditec_data[i].extend([0.0] * self._history_len)
        self.pump_feedback_updated.emit(0.0, 0.0,0.0)


    def reset_pressure_data(self):
        """Resets pressure data to zeros."""
        for i in range(len(self.pt_designators)):
            self._last_pressures[i] = 0.0 
            self._ch_data[i].clear()
            self._ch_data[i].extend([0.0] * self._history_len) 
        self.pressure_updated.emit(self._last_pressures)

    def reset_temperature_data(self):
        """Resets temperature data to zeros."""
        for i in range(len(self.tc_designators)):
            self._last_temps[i] = 0.0 
            self._temp_data[i].clear()
            self._temp_data[i].extend([0.0] * self._history_len)
        self.temperature_updated.emit(self._last_temps)

    def toggle_e_stop_state(self):
        """Toggles the E-STOP state."""
        self.eStopValue = not self.eStopValue

    def update_commanded_pump_state(self, pump_on: int, manual_speed: int, pid_output: Union[float, None]):
        """
        Updates the internal state for the pump sender task.
        Called by the GUI (PumpControlWindow) when pump controls or PID state changes.
        """
        if not self.eStopValue and not self.interlock_flag:
            self._commanded_pump_on = pump_on
            self._commanded_manual_speed = manual_speed
            self._commanded_pid_output = pid_output
        else:
            self._commanded_pump_on = 0
            self._commanded_manual_speed = 0
            self._commanded_pid_output = 0.0

    def update_commanded_esv_state(self):
        if self.eStopValue or self.interlock_flag:
            self.esv_state = [0, 0]
        else:
            self.esv_state[0] = int(self._esv1_cmd)
            self.esv_state[1] = int(self._esv2_cmd)

    def toggle_can_connection(self):
        """
        Toggles the CAN bus connection.
        If not connected, attempts to establish a connection and start async tasks.
        If connected, shuts down the CAN bus and cancels async tasks.
        Emits signals to update the UI.
        """
        if not self._can_connected:
            try:
                self._bus = can.interface.Bus(channel="PCAN_USBBUS1", interface="pcan", bitrate=500000)
                while not self._can_data_queue.empty():
                    self._can_data_queue.get_nowait()
                    self._can_data_queue.task_done()
                
                CanOpen.operational([0x23], self._bus)

                CanOpen.start_listener(self._bus, resolution=16, data_queue=self._can_data_queue)

                self._can_connected = True
                self.can_connection_status_changed.emit(True)

                self._consumer_task = asyncio.create_task(self._consumer_task_loop())
                self._sender_task = asyncio.create_task(self._sender_task_loop())

            except Exception as e:
                self.can_error.emit(f"Failed to connect to CAN: {e}")
                self._can_connected = False
                self.can_connection_status_changed.emit(False)

        else:
            try:
                if self._consumer_task:
                    self._consumer_task.cancel()
                    self._consumer_task = None
                if self._sender_task:
                    self._sender_task.cancel()
                    self._sender_task = None
                if self._bus:
                    self._bus.shutdown() 
                self._bus = None
                self._can_connected = False
                self.can_connection_status_changed.emit(False)

                self.reset_pressure_data()
                self.reset_temperature_data()
                self.reset_deditec_data()
                self.interlock_flag = False

            except Exception as e:
                self.can_error.emit(f"Error during CAN disconnection: {e}")
                self._can_connected = False
                self.can_connection_status_changed.emit(False)

    def interlock_trigger(self):
        """
        Evaluates various sensor values against defined limits to determine the
        overall system interlock status.
        This method uses get_latest_sensor_value for sensor readings.
        It should be called after sensor data has been updated.
        """
        def psi(barg):
            return barg * 14.5038
        
        no_hi_limit = 1e6
        no_lo_limit = -1e6


        pt10110_val = self.get_latest_sensor_value("PT10110")
        pt10120_val = self.get_latest_sensor_value("PT10120")
        ti10119_val = self.get_latest_sensor_value("TI10119") 
        try:
            ft_index = self.deditec_feedback.index("FT1024")
            ft1024_val = self._last_deditec[ft_index]
        except ValueError:
            ft1024_val = 0.0




        interlock1 = FaultManager.limit_fault(pt10110_val, self._bar_to_psi(2), no_lo_limit, self._bar_to_psi(7), no_hi_limit) 
    
        interlock2 = FaultManager.limit_fault(pt10120_val, self._bar_to_psi(15), no_lo_limit, self._bar_to_psi(19), self._bar_to_psi(20))
        if ti10119_val == self.INVALID_TEMP_MARKER:
            interlock3 = [False, False, False, False] 
        else:
            interlock3 = FaultManager.limit_fault(ti10119_val, 47, 45, 55, 60) 
            # interlock3 = FaultManager.limit_fault(ti10119_val, 0, 45, 55, 60)  #FOR TESTING ONLY!!
        # interlock4 = FaultManager.limit_fault(ft1024_val, 25, 20, 675, no_hi_limit)
        interlock4 = FaultManager.limit_fault(ft1024_val, no_lo_limit, 20, 675, no_hi_limit) #FOR TESTING ONLY!!


        if any(interlock1):
            self.interlock1_detected.emit(True, interlock1)
        else:
            self.interlock1_detected.emit(False, interlock1)

        if any(interlock2):
            self.interlock2_detected.emit(True, interlock2)
        else:
            self.interlock2_detected.emit(False, interlock2)

        if any(interlock3):
            self.interlock3_detected.emit(True, interlock3)
        else:
            self.interlock3_detected.emit(False, interlock3)

        if any(interlock4):
            self.interlock4_detected.emit(True, interlock4)
        else:
            self.interlock4_detected.emit(False, interlock4)

        self.interlock_flag = (
            interlock1[1] or interlock1[3] or
            interlock2[1] or interlock2[3] or
            interlock3[1] or interlock3[3] or
            interlock4[1] or interlock4[3]
        )

        if self.interlock_flag and not self.eStopValue:
            self.eStopValue = True

    async def _consumer_task_loop(self):
        while True:
            try:
                message: Dict[str, Any] = await self._can_data_queue.get()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.can_error.emit(f"Queue error: {e}")
                await asyncio.sleep(0.1)
                continue

            try:
                if "voltage" in message:
                    self.update_pressure_data(message["voltage"])

                if "temperature" in message:
                    self.update_temperature_data(message["temperature"])

                if "fourtwenty" in message:                    
                    self.update_current_data(message["fourtwenty"])
            except Exception as e:
                self.can_error.emit(f"Consumer processing error: {e}")
            finally:
                self._can_data_queue.task_done()

        await(0.1)



    async def _sender_task_loop(self):
        """
            send signals to i/o handler. 
            pump state is a state defined by [bool ON, int speed]
            esv_state is defined by [esv1, esv2 ...]
        """
        send_interval = 0.1

        while True:
            await asyncio.sleep(send_interval)
            
            try:
                manual_speed = self._commanded_manual_speed
                pid_output = self._commanded_pid_output
                speed = pid_output if pid_output is not None else manual_speed
                speed = max(0.0, min(100.0, float(speed if speed is not None else 0.0)))
                pump_state = [self._commanded_pump_on, speed]
                
                self.update_commanded_esv_state() 
                system_shutdown = self._eStopValue or self.interlock_flag
                
                if self._can_connected and self._bus:
                    await CanOpen.send_outputs(self._bus, system_shutdown, pump_state, self.esv_state, self.mfm_setpoints, self.pic_setpoint)

            except asyncio.CancelledError:
                print("Sender task cancelled.")
                break
            except Exception as e:
                self.can_error.emit(f"CAN Send Error (Sender Task): {str(e)}")
                await asyncio.sleep(0.1)


    def close_can_connection(self):
        """
        Cleanly shuts down the CAN connection and cancels tasks when the application exits.
        This method is called by the GUI's close event.
        """
        if self._can_connected:
            self.toggle_can_connection()