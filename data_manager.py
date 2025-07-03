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
    pump_feedback_updated = pyqtSignal(float, float)
    e_stop_toggled = pyqtSignal(bool)
    can_connection_status_changed = pyqtSignal(bool) # Signal for CAN connection status
    can_error = pyqtSignal(str) # Signal for CAN errors
    pressure_fault_detected = pyqtSignal(int, list) # channel_index, [lw, ls, hw, hs]
    temperature_fault_detected = pyqtSignal(int, list) # channel_index, [lw, ls, hw, hs]

    # Designators for pressure, temperature, and flow sensors
    pt_designators = ["PT10110", "PT10120", "PT10130", "PT10134", "PTC10126"]
    tc_designators = ["TI10111","TI10115","TI10116","TI10119","HEATER"]
    ft_designators = ["FI10124", "FIC10124"]

    def __init__(self, history_len: int = 100):
        super().__init__()
        self._history_len = history_len
        
        # Initialize deques based on the number of designators
        self._ch_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(len(self.pt_designators))]
        self._temp_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(len(self.tc_designators))]
        
        self._eStopValue = False
        self._testingFlag = False
        
        # _last_pressures and _last_temps store the latest *single* value for each sensor
        self._last_pressures = [0.0] * len(self.pt_designators)
        self._last_temps = [0.0] * len(self.tc_designators)
        self._last_pump_feedback = 0.0
        self._last_flow_rate = 0.0 # This will hold the single latest flow rate
        
        self.INVALID_TEMP_MARKER = -3276.8
        self.interlock_flag = False
        
        self._bus = None
        self._can_connected = False
        self._can_data_queue = asyncio.Queue(maxsize=20) 
        self._consumer_task = None
        self._sender_task = None

        self._commanded_pump_on = 0
        self._commanded_manual_speed = 0
        self._commanded_pid_output = None 
        self._commanded_esv_n2_on = 0

        self._sensor_data_sources: Dict[str, Union[deque, str]] = {}
        
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

        if self.ft_designators:
            for designator in self.ft_designators:
                self._sensor_data_sources[designator] = "_last_flow_rate"


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
                self._commanded_esv_n2_on = 0

    @property
    def testingFlag(self) -> bool:
        return self._testingFlag

    @property
    def last_pressures(self) -> List[float]:
        return self._last_pressures

    @property
    def last_temps(self) -> List[float]:
        return self._last_temps

    @property
    def last_pump_feedback(self) -> float:
        return self._last_pump_feedback

    @property
    def last_flow_rate(self) -> float:
        return self._last_flow_rate

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
        return self.ft_designators

    def _bar_to_psi(self, barg: float) -> float:
        return barg * 14.5038

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
        elif isinstance(source, str) and source == "_last_flow_rate":
            return self._last_flow_rate # Direct access for flow
        
        print(f"Warning: Sensor designator '{designator}' not found or no data. Returning 0.0.")
        return 0.0

    def update_pressure_data(self, values: List[float]):
        """Updates internal pressure data and emits signal."""
        if len(values) < len(self.pt_designators):
            print(f"Warning: Pressure data received with unexpected length: {len(values)}. Expected {len(self.pt_designators)}.")
            # Pad with repeated value of PT10120 (index 1) or a constant
            padded = values + [values[1]] * (len(self.pt_designators) - len(values))
            values = padded

        scaled_pressures = [
            values[0] * 30.0, # Example scaling
            values[1] * 60.0, # Example scaling
            values[2] * 60.0, # Example scaling
            values[3] * 60.0, # Example scaling
            values[4] * 60.0  # Example scaling
        ]

        # Update _last_pressures (latest single value) and append to history deques
        for i in range(len(self.pt_designators)):
            if i < len(scaled_pressures): # Ensure data exists for this index
                self._last_pressures[i] = scaled_pressures[i] # Update latest single value
                # Directly append to the deque through the _ch_data list
                if i < len(self._ch_data): # Defensive check
                    self._ch_data[i].append(scaled_pressures[i])

        self.interlock_trigger() # Re-evaluate overall interlock after any data update
        self.pressure_updated.emit(self._last_pressures) # Emit current latest values

    def update_temperature_data(self, values: List[float]):
        """Updates internal temperature data and emits signal."""
        if len(values) < len(self.tc_designators):
            print(f"Warning: Temperature data received with unexpected length: {len(values)}. Expected {len(self.tc_designators)}.")
            last_known = values[-1] if values else 25.0
            values = values + [last_known] * (len(self.tc_designators) - len(values))

        incoming_temps = values[:len(self.tc_designators)]
        is_invalid_reading = all(t == self.INVALID_TEMP_MARKER for t in incoming_temps)

        if not is_invalid_reading:
            # Update _last_temps (latest single value) and append to history deques
            for i in range(len(self.tc_designators)):
                if i < len(incoming_temps): # Ensure data exists for this index
                    self._last_temps[i] = incoming_temps[i] # Update latest single value
                    # Directly append to the deque through the _temp_data list
                    if i < len(self._temp_data): # Defensive check
                        self._temp_data[i].append(incoming_temps[i])
            
            self.interlock_trigger() # Call interlock_trigger after all sensor updates
        self.temperature_updated.emit(self._last_temps)

    def update_current_data(self, pump_percent: float, flow_kg_per_h: float):
        """Updates internal pump feedback and flow rate data and emits signal."""
        self._last_pump_feedback = pump_percent
        self._last_flow_rate = flow_kg_per_h # Update latest single value for flow

        self.interlock_trigger() # Call interlock_trigger after all sensor updates
        self.pump_feedback_updated.emit(pump_percent, flow_kg_per_h)

    def reset_pressure_data(self):
        """Resets pressure data to zeros."""
        for i in range(len(self.pt_designators)):
            self._last_pressures[i] = 0.0 # Reset latest single value
            self._ch_data[i].clear()
            self._ch_data[i].extend([0.0] * self._history_len) # Reset history deque
        self.pressure_updated.emit(self._last_pressures)

    def reset_temperature_data(self):
        """Resets temperature data to zeros."""
        for i in range(len(self.tc_designators)):
            self._last_temps[i] = 0.0 # Reset latest single value
            self._temp_data[i].clear()
            self._temp_data[i].extend([0.0] * self._history_len) # Reset history deque
        self.temperature_updated.emit(self._last_temps)

    def reset_feedback_data(self):
        """Resets pump feedback and flow rate data to zeros."""
        self._last_pump_feedback = 0.0
        self._last_flow_rate = 0.0 # Reset latest single value
        self.pump_feedback_updated.emit(self._last_pump_feedback, self._last_flow_rate)

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

    def update_commanded_esv_state(self, esv_n2_on: int):
        """
        Updates the internal state for the ESV sender task.
        """
        if not self.eStopValue and not self.interlock_flag:
            self._commanded_esv_n2_on = esv_n2_on
        else:
            self._commanded_esv_n2_on = 0

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
                self.reset_feedback_data()
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


        PT10110_val = self.get_latest_sensor_value("PT10110")
        PT10120_val = self.get_latest_sensor_value("PT10120")
        ti10119_val = self.get_latest_sensor_value("TI10119") 
        fi10124_val = self.get_latest_sensor_value("FI10124")




        interlock1 = FaultManager.limit_fault(PT10110_val, self._bar_to_psi(2), no_lo_limit, self._bar_to_psi(7), no_hi_limit) 
        interlock2 = FaultManager.limit_fault(PT10120_val, self._bar_to_psi(15), no_lo_limit, self._bar_to_psi(19), self._bar_to_psi(20))
        if ti10119_val == self.INVALID_TEMP_MARKER:
            interlock3 = [False, False, False, False] 
        else:
            interlock3 = FaultManager.limit_fault(ti10119_val, 47, 45, 55, 60) 
        interlock4 = FaultManager.limit_fault(fi10124_val, 25, 20, 675, no_hi_limit) 

        self.interlock_flag = (
            interlock1[1] or interlock1[3] or
            interlock2[1] or interlock2[3] or
            interlock3[1] or interlock3[3] or
            interlock4[1] or interlock4[3]
        )

        if self.interlock_flag and not self.eStopValue:
            self.eStopValue = True

    async def _consumer_task_loop(self):
        """
        Async task that continuously retrieves structured data messages from the CAN data queue.
        """
        while True:
            try:
                message: Dict[str, Any] = await self._can_data_queue.get()
            except asyncio.CancelledError:
                print("Consumer task cancelled.")
                break
            except Exception as e:
                self.can_error.emit(f"Error getting CAN message: {e}")
                await asyncio.sleep(0.1) 
                continue

            data_type = message.get("data_type")
            values = message.get("values")

            if data_type == 'voltage':
                self.update_pressure_data(values)
            elif data_type == 'temperature':
                self.update_temperature_data(values)
            elif data_type == '4-20mA':
                self.update_current_data(values["pump_percent"], values["flow_kg_per_h"])

            self._can_data_queue.task_done()

    async def _sender_task_loop(self):
        """
            send signals to i/o handler. 
            pump state is a state defined by [bool ON, int speed]
            esv_state is defined by [esv1, esv2 ...]
        """
        send_interval = 0.05

        while True:
            await asyncio.sleep(send_interval)
            
            try:
                manual_speed = self._commanded_manual_speed
                pid_output = self._commanded_pid_output
                speed = pid_output if pid_output is not None else manual_speed
                speed = max(0.0, min(100.0, float(speed if speed is not None else 0.0)))
                pump_state = [self._commanded_pump_on, speed]
                
                esv_state= [self._commanded_esv_n2_on, 0]

                system_shutdown = self._eStopValue or self.interlock_flag

                if self._can_connected and self._bus:
                    await CanOpen.send_outputs(self._bus, system_shutdown, pump_state, esv_state)

            except asyncio.CancelledError:
                print("Sender task cancelled.")
                break
            except Exception as e:
                self.can_error.emit(f"CAN Send Error (Sender Task): {str(e)}")
                await asyncio.sleep(0.1)

    async def _esv_sender_task_loop(self):
        """
        An asynchronous task for continuously sending CAN messages to control an ESV (Emergency Shut-off Valve)
        based on the E-STOP state.
        This assumes the ESV state is directly tied to the E-STOP.
        """
        while True:
            await asyncio.sleep(0.1) # Send ESV command less frequently, e.g., every 100ms

            # The ESV state is derived from the eStopValue.
            # Assuming True eStopValue means ESV should be 'closed' (safe state)
            # and False means ESV is 'open' (normal operation).
            if self.eStopValue:
                # E-STOP active, close valve (example data)
                data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            else:
                # E-STOP inactive, open valve (example data)
                data = [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

            if self._can_connected and self._bus:
                try:
                    await CanOpen.send_can_message(self._bus, 0x191, data,
                                                   self.eStopValue) # test_flag parameter
                except Exception as e:
                    self.can_error.emit(f"CAN Send Error (ESV): {str(e)}")

    def close_can_connection(self):
        """
        Cleanly shuts down the CAN connection and cancels tasks when the application exits.
        This method is called by the GUI's close event.
        """
        if self._can_connected:
            self.toggle_can_connection()