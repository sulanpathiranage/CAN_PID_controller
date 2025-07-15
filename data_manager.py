import asyncio
import can
from collections import deque
from typing import List, Dict, Any, Union
from datetime import datetime
import csv

from PySide6.QtCore import QObject, Signal as pyqtSignal
from fault_manager import FaultManager


from can_open_protocol import CanOpen
from pid_controller import PIDController

class SystemDataManager(QObject):
    pressure_updated = pyqtSignal(list)
    temperature_updated = pyqtSignal(list)
    pump_feedback_updated = pyqtSignal(float, float, float, float)
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
    interlock_checked = pyqtSignal(bool)
    start_log = pyqtSignal(bool)
    log_name  = pyqtSignal(str)
    pid_output_updated = pyqtSignal(float) 
    pid_enabled_status_changed = pyqtSignal(bool) 
    pid_setpoint_updated = pyqtSignal(float)


    # pt_info = {
    #     "PT10110": 30,
    #     "PT10120": 60,
    #     "PT10130": 60,
    #     "PT10118": 60,
    # }
    # tc_designators = ["TI10111","TI10115","TI10116","TI10117"]
    pt_info = {
       "PT10110": 30, 
       "PT10123": 60, 
       "PT10130": 60, 
       "PT10120": 60, 
       "PT10134": 60,
       "PT10118": 30
    }
    tc_designators = ["TI10111","TI10115","TI10116","TI10117", "TI01","TI10121", "TI10119","TI10122"]

    deditec_info = {
        "PumpFeedback": 100,    # percent
        "FT10124":      32.8,   # kg/h
        "FT10106":      32.8,    #kg/h
        "PIC10126":     250     #psig
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
        self.interlock_begin = False
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
        self.pid_controller = PIDController() 
        self._pid_enabled = False #
        self._commanded_pid_output = 0.0 
        self._pid_setpoint = 0.0
        self._last_pid_calc_time = asyncio.get_event_loop().time()

        self.pid_controller.set_params(1.0, 0.0, 0.0)
        self.pid_controller.set_setpoint(self._pid_setpoint)

        self._sensor_data_sources: Dict[str, Union[deque, str]] = {}

        self.mfm1_setpoint_updated.emit(self.mfm_setpoints[0])
        self.mfm2_setpoint_updated.emit(self.mfm_setpoints[1])
        self.pid_enabled_status_changed.emit(self._pid_enabled)
        
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

        self._logging_enabled = False
        self._log_file = None
        self._csv_writer = None
        self._log_filename = ""
        self._last_log_time = 0.0 
        self.start_log.connect(self.toggle_logging) 
        self.log_name.connect(self.set_log_filename)


    def set_log_filename(self, name: str):
        """Sets the base filename for the log file."""
        self._log_filename = name
        print(f"Log filename set to: {self._log_filename}")

    def toggle_logging(self, enable: bool):
        """
        Enables or disables logging to a CSV file.
        A new file is created each time logging is enabled.
        """
        if enable and not self._logging_enabled:
            # Generate a timestamped filename if no base name is set
            if not self._log_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_path = f"log_data_{timestamp}.csv"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_path = f"{self._log_filename}_{timestamp}.csv"

            try:
                self._log_file = open(log_file_path, 'w', newline='')
                self._csv_writer = csv.writer(self._log_file)

                # Write header row
                header = ["Timestamp"]
                header.extend(self.pt_designators) # Pressure sensors
                header.extend(self.tc_designators) # Temperature sensors
                header.extend(self.deditec_feedback) # Deditec feedbacks (Flow, PumpFeedback)
                header.extend(["MFM1_Setpoint", "MFM2_Setpoint", "PIC_Setpoint"]) # Command setpoints
                header.extend(["Pump_On_Cmd", "Manual_Pump_Speed_Cmd", "PID_Output_Cmd"]) # Commanded states
                header.extend(["ESV1_State_Cmd", "ESV2_State_Cmd"]) # ESV commands
                header.extend(["E-Stop", "Interlock_Flag"]) # System states

                self._csv_writer.writerow(header)
                self._logging_enabled = True
                self._last_log_time = asyncio.get_event_loop().time() # Reset time on start
                self._logger_task = asyncio.create_task(self._log_data_task()) 
                print(f"Logging started to: {log_file_path}")

            except Exception as e:
                print(f"Error starting log: {e}")
                self.can_error.emit(f"Log start error: {e}")
                self._logging_enabled = False
                if self._log_file:
                    self._log_file.close()
                self._log_file = None
                self._csv_writer = None

        elif not enable and self._logging_enabled:
            if self._log_file:
                self._log_file.close()
                print(f"Logging stopped for: {self._log_filename}")
            self._logging_enabled = False
            self._log_file = None
            self._csv_writer = None
            self._log_filename = "" 
            try:
                self._logger_task.cancel() 
            except:
                print("Couldn't close log task!")


    async def _log_data_task(self):
        """Asynchronous task to periodically log system data."""
        log_interval = 0.5 # 2 Hz logging rate (every 0.5 seconds)

        while True:
            await asyncio.sleep(log_interval)

            if self._logging_enabled and self._csv_writer:
                try:
                    current_time = asyncio.get_event_loop().time()
                    # Only log if enough time has passed, ensuring fixed frequency
                    if (current_time - self._last_log_time) >= log_interval - 0.001: # Small tolerance
                        self._last_log_time = current_time

                        row_data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")]

                        # Add sensor data
                        for designator in self.pt_designators:
                            row_data.append(self.get_latest_sensor_value(designator))
                        for designator in self.tc_designators:
                            row_data.append(self.get_latest_sensor_value(designator))
                        for designator in self.deditec_feedback:
                            row_data.append(self.get_latest_sensor_value(designator))

                        # Add commanded setpoints
                        row_data.append(self.mfm_setpoints[0])
                        row_data.append(self.mfm_setpoints[1])
                        row_data.append(self._pid_setpoint) # Use _pid_setpoint for the PID setpoint

                        # Add commanded states
                        row_data.append(self._commanded_pump_on)
                        row_data.append(self._commanded_manual_speed)
                        row_data.append(self._commanded_pid_output)

                        # Add ESV states
                        row_data.append(self.esv_state[0])
                        row_data.append(self.esv_state[1])

                        # Add system flags
                        row_data.append(self._eStopValue)
                        row_data.append(self.interlock_flag)

                        self._csv_writer.writerow(row_data)
                        self._log_file.flush() 

                except asyncio.CancelledError:
                    print("Log data task cancelled.")
                    break
                except Exception as e:
                    print(f"Error writing to log file: {e}")
                    self.can_error.emit(f"Log write error: {e}")
                    # Consider stopping logging if a persistent error occurs
                    # self.toggle_logging(False)

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

    def set_pid_kp(self, value: float):
        self.pid_controller.kp = value

    def set_pid_ki(self, value: float):
        self.pid_controller.ki = value

    def set_pid_kd(self, value: float):
        self.pid_controller.kd = value

    def set_pid_setpoint(self, value: float):
        self.pid_controller.set_setpoint(value)
        self._pid_setpoint = value
        self.pid_setpoint_updated.emit(value) 

    def set_pid_enabled(self, enabled: bool):
        if self._pid_enabled != enabled:
            self._pid_enabled = enabled
            self.pid_enabled_status_changed.emit(enabled)
            if enabled:
                self.pid_controller.reset() # Important: reset integral/derivative on enable
                self.pid_controller.set_setpoint(self._pid_setpoint)
            else:

                self._commanded_pid_output = 0.0
                self.pid_output_updated.emit(0.0) 


    def set_interlock_begin(self, value: bool):
        if self.interlock_begin != value:
            self.interlock_begin = value
            self.interlock_checked.emit(value)
        
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
    
    def _psi_to_bar(self, barg: float) -> float:
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
            self._last_deditec[self.deditec_feedback.index("FT10124")],
            self._last_deditec[self.deditec_feedback.index("FT10106")],
            self._last_deditec[self.deditec_feedback.index("PIC10126")]
        )

        self.interlock_trigger()


    def _perform_pid_calculation(self):
        """
        Performs the PID calculation based on FT10124 feedback.
        Should be called periodically in the data processing loop.
        """
        if self._pid_enabled:
            current_time = asyncio.get_event_loop().time()
            dt = current_time - self._last_pid_calc_time
            self._last_pid_calc_time = current_time

            measured_value = self.get_latest_sensor_value("FT10124")

            if measured_value is not None:
                pid_output = self.pid_controller.calculate(measured_value, dt)

                self._commanded_pid_output = pid_output

                self.pid_output_updated.emit(pid_output)
            else:
                # Handle case where FT10124 data might not be available or is invalid
                print("Warning: FT10124 data not available for PID calculation.")
                self._commanded_pid_output = 0.0 # Safe default
                self.pid_output_updated.emit(0.0)
        # Else, if PID is not enabled, _commanded_pid_output remains at its last value
        # (which should be 0.0 if it was properly disabled by set_pid_enabled)


    def reset_deditec_data(self):
        for i in range(len(self.deditec_feedback)):
            self._last_deditec[i] = 0.0
            self._deditec_data[i].clear()
            self._deditec_data[i].extend([0.0] * self._history_len)
        self.pump_feedback_updated.emit(0.0, 0.0,0.0, 0.0)


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

    def toggle_interlocks(self):
        """Toggles the E-STOP state."""
        self.interlock_begin = not self.interlock_begin

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
  
        
        no_hi_limit = 1e6
        no_lo_limit = -1e6


        pt10110_val = self.get_latest_sensor_value("PT10110")
        pt10120_val = self.get_latest_sensor_value("PT10120")
        ti10119_val = self.get_latest_sensor_value("TI10119") 
        try:
            ft_index = self.deditec_feedback.index("FT10124")
            FT10124_val = self._last_deditec[ft_index]
        except ValueError:
            FT10124_val = 0.0

        interlock1 = [False, False, False, False]
        interlock2 = [False, False, False, False]
        interlock3 = [False, False, False, False]
        interlock4 = [False, False, False, False]



        if self.interlock_begin:
            interlock1 = FaultManager.limit_fault(pt10110_val, self._bar_to_psi(2), no_lo_limit, self._bar_to_psi(7), no_hi_limit) 
        
            interlock2 = FaultManager.limit_fault(pt10120_val, self._bar_to_psi(15), no_lo_limit, self._bar_to_psi(19), self._bar_to_psi(20))
            if ti10119_val == self.INVALID_TEMP_MARKER:
                interlock3 = [True, True, True, True] 
            else:
                interlock3 = FaultManager.limit_fault(ti10119_val, 47, 45, 55, 60) 
                # interlock3 = FaultManager.limit_fault(ti10119_val, 0, 45, 55, 60)  #FOR TESTING ONLY!!
            # interlock4 = FaultManager.limit_fault(FT10124_val, 25, 20, 675, no_hi_limit)
            interlock4 = FaultManager.limit_fault(FT10124_val, no_lo_limit, 20, 675, no_hi_limit) #FOR TESTING ONLY!!


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

            await asyncio.sleep(0.1)





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