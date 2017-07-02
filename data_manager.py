import asyncio
import can
from collections import deque
from typing import List, Dict, Any, Union

from PySide6.QtCore import QObject, Signal as pyqtSignal


# SystemDataManager will just *store* the commanded speed/PID output
# as provided by the GUI, and the sender task will use it.
from can_open_protocol import CanOpen

class SystemDataManager(QObject):
    # Signals to communicate updates to the GUI
    pressure_updated = pyqtSignal(list)
    temperature_updated = pyqtSignal(list)
    pump_feedback_updated = pyqtSignal(float, float)
    e_stop_toggled = pyqtSignal(bool)
    can_connection_status_changed = pyqtSignal(bool) # Signal for CAN connection status
    can_error = pyqtSignal(str) # Signal for CAN errors

    def __init__(self, history_len: int = 100):
        super().__init__()
        self._history_len = history_len
        self._ch_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(3)]
        self._temp_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(3)]
        self._eStopValue = False
        self._testingFlag = False # Added testingFlag as it's used in can_open_protocol
        self._last_pressures = [0.0, 0.0, 0.0]
        self._last_temps = [0.0, 0.0, 0.0]
        self._last_pump_feedback = 0.0
        self._last_flow_rate = 0.0
        self.INVALID_TEMP_MARKER = -3276.8

        # CAN communication attributes and tasks, now managed internally
        self._bus = None
        self._can_connected = False
        self._can_data_queue = asyncio.Queue(maxsize=20) # SystemDataManager now owns its queue
        self._consumer_task = None
        self._pump_sender_task = None
        self._esv_sender_task = None # Task for ESV valve control

        # Internal state to hold commanded values received from the GUI
        self._commanded_pump_on = 0
        self._commanded_manual_speed = 0
        self._commanded_pid_output = None # None indicates PID is not active/output not used

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

    def update_pressure_data(self, values: List[float]):
        """Updates internal pressure data and emits signal."""
        if len(values) >= 3:
            scaled_pressures = [values[0] * 30.0, values[1] * 60.0, values[2] * 60.0]
            for i in range(3):
                self._ch_data[i].append(scaled_pressures[i])
            self._last_pressures = scaled_pressures
            self.pressure_updated.emit(scaled_pressures)

    def update_temperature_data(self, values: List[float]):
        """Updates internal temperature data and emits signal."""
        if len(values) < 3:
            print(f"Warning: Temperature data received with unexpected length: {len(values)}. Expected >=3.")
            return

        incoming_temps = values[:3]
        is_invalid_reading = all(t == self.INVALID_TEMP_MARKER for t in incoming_temps)

        if not is_invalid_reading:
            self._last_temps = incoming_temps
            for i in range(3):
                self._temp_data[i].append(incoming_temps[i])

        self.temperature_updated.emit(self._last_temps)

    def update_current_data(self, pump_percent: float, flow_kg_per_h: float):
        """Updates internal pump feedback and flow rate data and emits signal."""
        self._last_pump_feedback = pump_percent
        self._last_flow_rate = flow_kg_per_h
        self.pump_feedback_updated.emit(pump_percent, flow_kg_per_h)

    def reset_pressure_data(self):
        """Resets pressure data to zeros."""
        self._last_pressures = [0.0, 0.0, 0.0]
        for i in range(3):
            self._ch_data[i].clear()
            self._ch_data[i].extend([0.0] * self._history_len)
        self.pressure_updated.emit(self._last_pressures)

    def reset_temperature_data(self):
        """Resets temperature data to zeros."""
        self._last_temps = [0.0, 0.0, 0.0]
        for i in range(3):
            self._temp_data[i].clear()
            self._temp_data[i].extend([0.0] * self._history_len)
        self.temperature_updated.emit(self._last_temps)

    def reset_feedback_data(self):
        """Resets pump feedback and flow rate data to zeros."""
        self._last_pump_feedback = 0.0
        self._last_flow_rate = 0.0
        self.pump_feedback_updated.emit(self._last_pump_feedback, self._last_flow_rate)

    def toggle_e_stop_state(self):
        """Toggles the E-STOP state."""
        self.eStopValue = not self.eStopValue

    def update_commanded_pump_state(self, pump_on: int, manual_speed: int, pid_output: Union[float, None]):
        """
        Updates the internal state for the pump sender task.
        Called by the GUI (PumpControlWindow) when pump controls or PID state changes.
        """
        self._commanded_pump_on = pump_on
        self._commanded_manual_speed = manual_speed
        self._commanded_pid_output = pid_output

    def toggle_can_connection(self):
        """
        Toggles the CAN bus connection.
        If not connected, attempts to establish a connection and start async tasks.
        If connected, shuts down the CAN bus and cancels async tasks.
        Emits signals to update the UI.
        """
        if not self._can_connected:
            try:
                # Attempt to connect to the CAN bus
                self._bus = can.interface.Bus(channel="PCAN_USBBUS1", interface="pcan", bitrate=500000)
                # Clear the queue before starting listener to prevent processing stale data
                while not self._can_data_queue.empty():
                    self._can_data_queue.get_nowait()
                    self._can_data_queue.task_done()
                
                CanOpen.operational([126], self._bus)

                CanOpen.start_listener(self._bus, resolution=16, data_queue=self._can_data_queue)

                self._can_connected = True
                self.can_connection_status_changed.emit(True)

                # Start the async tasks
                self._consumer_task = asyncio.create_task(self._consumer_task_loop())
                self._pump_sender_task = asyncio.create_task(self._pump_sender_task_loop())
                self._esv_sender_task = asyncio.create_task(self._esv_sender_task_loop())

            except Exception as e:
                self.can_error.emit(f"Failed to connect to CAN: {e}")
                self._can_connected = False
                self.can_connection_status_changed.emit(False) # Emit false on failure

        else:
            # When disconnecting:
            try:
                # Cancel all running async tasks
                if self._consumer_task:
                    self._consumer_task.cancel()
                    self._consumer_task = None
                if self._pump_sender_task:
                    self._pump_sender_task.cancel()
                    self._pump_sender_task = None
                if self._esv_sender_task:
                    self._esv_sender_task.cancel()
                    self._esv_sender_task = None

                if self._bus:
                    self._bus.shutdown() # Shut down the CAN bus
                self._bus = None
                self._can_connected = False
                self.can_connection_status_changed.emit(False)

                # Reset all sensor values to 0
                self.reset_pressure_data()
                self.reset_temperature_data()
                self.reset_feedback_data()

            except Exception as e:
                self.can_error.emit(f"Error during CAN disconnection: {e}")
                # Even if there's an error during shutdown, try to mark as disconnected
                self._can_connected = False
                self.can_connection_status_changed.emit(False)


    async def _consumer_task_loop(self):
        """
        An asynchronous task that continuously retrieves structured data messages from the CAN data queue.
        It processes the received data and updates the SystemDataManager's internal state.
        """
        while True:
            try:
                message: Dict[str, Any] = await self._can_data_queue.get()
            except asyncio.CancelledError:
                print("Consumer task cancelled.")
                break
            except Exception as e:
                self.can_error.emit(f"Error getting CAN message: {e}")
                await asyncio.sleep(0.1) # Prevent busy-waiting on error
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

    async def _pump_sender_task_loop(self):
        """
        An asynchronous task responsible for sending pump control commands over CAN bus.
        It uses the commanded state (manual or PID-controlled) stored in the data manager.
        """
        while True:
            await asyncio.sleep(0.05) # Send pump commands every 50 milliseconds

            # Get the commanded pump state from SystemDataManager's internal variables
            pump_on = self._commanded_pump_on
            manual_speed = self._commanded_manual_speed
            pid_output = self._commanded_pid_output

            # Determine final pump speed: PID output if active, otherwise manual speed
            speed = pid_output if pid_output is not None else manual_speed

            # Ensure speed is within bounds [0, 100]
            speed = max(0.0, min(100.0, speed if speed is not None else 0.0))

            # Generate raw CAN message data for pump control
            raw1, raw2 = CanOpen.generate_outmm_msg(pump_on, speed)
            data = CanOpen.generate_uint_16bit_msg(int(raw1), int(raw2), 0, 0)

            if self._can_connected and self._bus:
                try:
                    # Pass eStopValue and testingFlag from the data manager
                    await CanOpen.send_can_message(self._bus, 0x600, data,
                                                   self.eStopValue)
                except Exception as e:
                    self.can_error.emit(f"CAN Send Error (Pump): {str(e)}")

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
            self.toggle_can_connection() # Use the existing toggle logic to shut down