import os
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"  # Force pyqtgraph to use PyQt6


import sys
import asyncio
import csv
from datetime import datetime
from collections import deque
from typing import List, Dict, Any

import can
import pyqtgraph as pg

import matplotlib
matplotlib.use('QtAgg')

# PyQt6 Imports
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QFont

# Local imports
from pid_controller import PIDController
from app_stylesheets import Stylesheets
from NH3_pump_control import NH3PumpControlScene
from NH3_vaporizer_control import NH3VaporizerControlScene
from can_open_protocol import CanOpen 

class SystemDataManager(QObject):
    """
    Manages all shared system data, including sensor readings, E-STOP status,
    and historical data for plots. Emits signals when data updates.
    """
    # Signals to emit when data updates
    pressure_updated = pyqtSignal(list)         # Emits [PT1401, PT1402, PT1403]
    temperature_updated = pyqtSignal(list)      # Emits [T01, T02, Heater]
    pump_feedback_updated = pyqtSignal(float, float) # Emits pump_percent, flow_kg_per_h
    e_stop_toggled = pyqtSignal(bool)           # Emits True if active, False if inactive
    # Add more signals for other control parameters if needed

    def __init__(self, history_len: int = 100):
        super().__init__()
        self._history_len = history_len

        # Deques to store historical pressure data for three channels
        self._ch_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(3)]
        # Deques to store historical temperature data for three channels
        self._temp_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(3)]

        self._eStopValue = False    # Internal state for E-STOP
        self._testingFlag = False   # Internal state for testing flag

        self._last_pressures = [0.0, 0.0, 0.0]
        self._last_temps = [0.0, 0.0, 0.0]
        self._last_pump_feedback = 0.0
        self._last_flow_rate = 0.0

    @property
    def history_len(self) -> int:
        """Returns the length of data history kept for plots."""
        return self._history_len

    @property
    def ch_data(self) -> List[deque]:
        """Returns the historical pressure data deques."""
        return self._ch_data

    @property
    def temp_data(self) -> List[deque]:
        """Returns the historical temperature data deques."""
        return self._temp_data

    @property
    def eStopValue(self) -> bool:
        """Returns the current E-STOP status."""
        return self._eStopValue

    @eStopValue.setter
    def eStopValue(self, value: bool):
        """Sets the E-STOP status and emits a signal if the value changes."""
        if self._eStopValue != value:
            self._eStopValue = value
            self.e_stop_toggled.emit(value)

    @property
    def testingFlag(self) -> bool:
        """Returns the current testing flag status."""
        return self._testingFlag

    @property
    def last_pressures(self) -> List[float]:
        """Returns the last received pressure values."""
        return self._last_pressures

    @property
    def last_temps(self) -> List[float]:
        """Returns the last received temperature values."""
        return self._last_temps

    @property
    def last_pump_feedback(self) -> float:
        """Returns the last received pump feedback value."""
        return self._last_pump_feedback

    @property
    def last_flow_rate(self) -> float:
        """Returns the last received flow rate value."""
        return self._last_flow_rate

    def update_pressure_data(self, values: List[float]):
        """
        Updates internal pressure data and emits pressure_updated signal.
        Scales raw voltage values to psi.
        :param values: Raw voltage values from CAN.
        """
        # Ensure values has at least 3 elements before accessing indices
        if len(values) >= 3:
            scaled_pressures = [values[0] * 30.0, values[1] * 60.0, values[2] * 60.0]
            for i in range(3):
                self._ch_data[i].append(scaled_pressures[i])
            self._last_pressures = scaled_pressures
            self.pressure_updated.emit(scaled_pressures)

    def update_temperature_data(self, values: List[float]):
        """
        Updates internal temperature data and emits temperature_updated signal.
        Assumes values are already scaled or correctly represent temperatures.
        :param values: Temperature values from CAN.
        """
        if len(values) >= 3: # Ensure enough values for T01, T02, Heater
            for i in range(3):
                self._temp_data[i].append(values[i])
            self._last_temps = values[:3]
            self.temperature_updated.emit(values[:3])

    def update_current_data(self, pump_percent: float, flow_kg_per_h: float):
        """
        Updates internal pump feedback and flow rate data and emits pump_feedback_updated signal.
        :param pump_percent: The pump feedback in percentage.
        :param flow_kg_per_h: The flow rate in kg/h.
        """
        self._last_pump_feedback = pump_percent
        self._last_flow_rate = flow_kg_per_h
        self.pump_feedback_updated.emit(pump_percent, flow_kg_per_h)

    def toggle_e_stop_state(self):
        """Toggles the internal E-STOP state."""
        self.eStopValue = not self.eStopValue # Uses the property setter to emit signal


class PermanentRightHandDisplay(QWidget):
    """
    A QWidget class that creates a permanent display panel on the right side of the main window.
    It includes an E-STOP button and labels for displaying safety-critical information.
    """
    def __init__(self, data_manager: SystemDataManager):
        """
        Initializes the PermanentRightHandDisplay widget.
        Sets up the layout, E-STOP button, safety labels, and control push buttons.
        :param data_manager: Reference to the SystemDataManager for E-STOP state management.
        """
        super().__init__()
        self.data_manager = data_manager # Store reference to data manager

        # Create Layout
        rightHandVerticalLayout = QVBoxLayout()

        # Create Contents
        self.eStopButton = QPushButton("E-STOP")
        self.eStopButton.setFixedSize(150, 100)
        self.eStopButton.setStyleSheet(Stylesheets.EStopPushButtonStyleSheet())
        # Connect the E-STOP button's clicked signal to the toggleEStop method
        self.eStopButton.clicked.connect(self.toggleEStop)

        self.safetyLabelOne = QLabel("Safety Critical Info Label 1")
        self.safetyLabelTwo = QLabel("Safety Critical Info Label 2")
        self.safetyLabelThree = QLabel("Safety Critical Info Label 3")

        self.safetyControlPushButtonOne = QPushButton("Safety Control One")
        self.safetyControlPushButtonOne.setFixedSize(150, 80)
        self.safetyControlPushButtonOne.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        self.safetyControlPushButtonTwo = QPushButton("Safety Control Two")
        self.safetyControlPushButtonTwo.setFixedSize(150, 80)
        self.safetyControlPushButtonTwo.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        # Put contents in layout
        rightHandVerticalLayout.addWidget(self.safetyLabelOne)
        rightHandVerticalLayout.addWidget(self.safetyLabelTwo)
        rightHandVerticalLayout.addWidget(self.safetyLabelThree)
        rightHandVerticalLayout.addWidget(self.safetyControlPushButtonOne)
        rightHandVerticalLayout.addWidget(self.safetyControlPushButtonTwo)
        rightHandVerticalLayout.addWidget(self.eStopButton)

        # Set self "PermanentRightHandDisplay" widget layout
        self.setLayout(rightHandVerticalLayout)

        # Connect to data manager's e-stop signal to update button text if state changes externally
        self.data_manager.e_stop_toggled.connect(self._update_e_stop_button_text)

    def toggleEStop(self):
        """
        Toggles the global eStopValue flag via the SystemDataManager.
        The button text is updated by the connected signal.
        """
        self.data_manager.toggle_e_stop_state()

    def _update_e_stop_button_text(self, is_active: bool):
        """
        Slot to update the E-STOP button text based on the SystemDataManager's state.
        :param is_active: True if E-STOP is active, False otherwise.
        """
        if is_active:
            self.eStopButton.setText("E-STOP\nACTIVE")
        else:
            self.eStopButton.setText("E-STOP")

class PumpControlWidget(QWidget):
    """
    A QWidget class that provides a control interface for the NH3 pump.
    Allows users to turn the pump ON/OFF and adjust its speed.
    """
    def __init__(self):
        """
        Initializes the PumpControlWidget.
        Sets up the pump ON/OFF checkbox, speed slider, speed entry field, and PID output label.
        Connects signals for slider and entry field updates.
        """
        super().__init__()

        self.pump_on_checkbox = QCheckBox("Pump ON")
        self.pump_on_checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(0)

        self.speed_entry = QLineEdit("0")
        self.speed_entry.setFixedWidth(50)
        self.speed_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.output_label = QLabel("PID Output: -- %")
        #self.output_label.setStyleSheet(Stylesheets.LabelStyleSheet()) # Commented out stylesheet

        # Connect signals for value changes
        self.speed_slider.valueChanged.connect(self.update_entry)
        self.speed_entry.editingFinished.connect(self.update_slider)

        layout = QVBoxLayout()

        group = QGroupBox("Pump Control")
        group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        form_layout = QGridLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(10, 10, 10, 10)

        form_layout.addWidget(QLabel("Pump State:"), 0, 0)
        form_layout.addWidget(self.pump_on_checkbox, 0, 1, 1, 2)

        form_layout.addWidget(QLabel("Speed:"), 1, 0)
        form_layout.addWidget(self.speed_slider, 1, 1)
        form_layout.addWidget(self.speed_entry, 1, 2)

        form_layout.addWidget(self.output_label, 2, 0, 1, 3)

        group.setLayout(form_layout)
        layout.addWidget(group)
        layout.addStretch(1) # Adds stretchable space

        self.setLayout(layout)

    def update_entry(self, val: int):
        """
        Updates the text of the speed_entry QLineEdit with the current value from the slider.
        :param val: The integer value from the speed slider.
        """
        self.speed_entry.setText(str(val))

    def update_slider(self):
        """
        Updates the value of the speed_slider based on the text entered in the speed_entry QLineEdit.
        Includes error handling for non-integer or out-of-range input.
        """
        try:
            val = int(self.speed_entry.text())
            if 0 <= val <= 100:
                self.speed_slider.setValue(val)
        except ValueError:
            # Ignore invalid input
            pass

    def get_state(self) -> tuple[int, int]:
        """
        Returns the current state of the pump control.
        :return: A tuple containing (pump_on_state (int: 0=OFF, 1=ON), pump_speed (int: 0-100)).
        """
        return int(self.pump_on_checkbox.isChecked()), self.speed_slider.value()

class PyqtgraphPlotWidget(QWidget):
    """
    A QWidget class that displays real-time pressure and temperature data using pyqtgraph.
    It creates multiple plot widgets for individual pressure sensors and a combined plot for temperatures.
    """
    def __init__(self, data_manager: SystemDataManager):
        """
        Initializes the PyqtgraphPlotWidget.
        Sets up the layout, plot widgets for pressure and temperature, and initializes plot curves.
        :param data_manager: Reference to the SystemDataManager to access historical data.
        """
        super().__init__()
        self.data_manager = data_manager # Store reference to data manager

        self.layout = QHBoxLayout(self)
        self.plot_area = QVBoxLayout()

        self.pressure_names = ["PT1401", "PT1402", "PT1403"]
        self.temperature_names = ["T01", "T02", "Heater"]

        self.pressure_curves = []
        self.temperature_curves = []

        # Plot pressure graphs
        for i, name in enumerate(self.pressure_names):
            pw = pg.PlotWidget(title=name)
            pw.setLabel('left', "Pressure", units='psi')
            pw.setLabel('bottom', "Time", units='s')
            pw.setYRange(0, 150 if i == 0 else 300) # Different Y-range for PT1401 vs others
            pw.setXRange(0, 10) # X-range fixed to 10 seconds (history_len * 0.1s update interval)
            pw.showGrid(x=True, y=True)
            pw.getAxis("bottom").setTickSpacing(1, 0.5)
            # Corrected setStyle call
            pw.getAxis("left").setStyle(tickFont=QFont("Arial", 10))
            curve = pw.plot(pen=pg.mkPen('b', width=2)) # Blue pen for pressure curves
            self.pressure_curves.append(curve)
            self.plot_area.addWidget(pw)

        # Plot temperature graph
        temp_widget = pg.PlotWidget(title="Temperatures")
        temp_widget.setLabel('left', "Temperature", units='°C')
        temp_widget.setLabel('bottom', "Time", units='s')
        temp_widget.setYRange(0, 150)
        temp_widget.setXRange(0, 10)
        temp_widget.showGrid(x=True, y=True)
        # Corrected setStyle call
        temp_widget.getAxis("left").setStyle(tickFont=QFont("Arial", 10))

        # Add legend to differentiate curves
        # legend = temp_widget.addLegend()

        # Create curves for T01, T02, and Heater with different colors
        curve1 = temp_widget.plot(pen=pg.mkPen('r', width=2), name="T01") # Red for T01
        curve2 = temp_widget.plot(pen=pg.mkPen('g', width=2), name="T02") # Green for T02
        curve3 = temp_widget.plot(pen=pg.mkPen('b', width=2), name="Heater") # Blue for Heater

        # Store curves for later updates
        self.temperature_curves = [curve1, curve2, curve3]

        # Add single widget to layout
        self.plot_area.addWidget(temp_widget)
        self.layout.addLayout(self.plot_area, 5) # Add plot area to main layout with stretch factor

    def update_plot(self):
        """
        Updates the data for all pressure and temperature curves displayed in the plot widgets.
        Uses the data from the data_manager.
        """
        time_axis = [i * 0.1 for i in range(self.data_manager.history_len)]  # Last 10 seconds (assuming 100ms update)
        for i in range(3):
            self.pressure_curves[i].setData(time_axis, list(self.data_manager.ch_data[i])) # Update pressure curves
        for i in range(3):
            self.temperature_curves[i].setData(time_axis, list(self.data_manager.temp_data[i])) # Update temperature curves


class SensorDisplayWidget(QWidget):
    """
    A QWidget class that displays the current readings from various sensors
    (pressure, temperature, pump feedback, and flow rate) in a textual format.
    """
    def __init__(self, data_manager: SystemDataManager):
        """
        Initializes the SensorDisplayWidget.
        Sets up labels for pump feedback, flow rate, pressure sensors, and temperature sensors.
        :param data_manager: Reference to the SystemDataManager for sensor data.
        """
        super().__init__()
        self.data_manager = data_manager # Store reference to data manager
        layout = QVBoxLayout()
        self.pressure_labels = []
        self.temperature_labels = []

        # Feedback labels
        self.pump_feedback_label = QLabel("Pump Feedback: -- %")
        self.flow_feedback_label = QLabel("Flow Rate: -- L/min")
        self.pump_feedback_label.setStyleSheet("font-size: 14px;")
        self.flow_feedback_label.setStyleSheet("font-size: 14px;")

        layout.addWidget(self.pump_feedback_label)
        layout.addWidget(self.flow_feedback_label)

        # Pressure section title
        pressure_title = QLabel("Pressure Sensors")
        pressure_title.setStyleSheet(Stylesheets.LabelStyleSheet())
        layout.addWidget(pressure_title)

        # Pressure labels (PT1401, PT1402, PT1403)
        for name in ["PT1401", "PT1402", "PT1403"]:
            label = QLabel(f"{name}: -- psi")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet(Stylesheets.LabelStyleSheet()) # Corrected typo
            self.pressure_labels.append(label)
            layout.addWidget(label)

        layout.addSpacing(10)  # Spacer between sections

        # Temperature section title
        temp_title = QLabel("Temperature Sensors")
        temp_title.setStyleSheet(Stylesheets.LabelStyleSheet()) # Corrected typo
        layout.addWidget(temp_title)

        # Temperature labels (T01, T02, Heater)
        for name in ["T01", "T02", "Heater"]:
            label = QLabel(f"{name}: -- °C")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet(Stylesheets.LabelStyleSheet()) # Corrected typo
            self.temperature_labels.append(label)
            layout.addWidget(label)

        layout.addStretch() # Adds stretchable space at the bottom
        self.setLayout(layout)

        # Connect to data_manager signals to update display
        self.data_manager.pressure_updated.connect(self.update_pressures)
        self.data_manager.temperature_updated.connect(self.update_temperatures)
        self.data_manager.pump_feedback_updated.connect(self.update_feedback)


    def update_feedback(self, pump_feedback: float, flow_rate: float):
        """
        Updates the displayed pump feedback and flow rate values.
        :param pump_feedback: The pump feedback value (e.g., in percentage).
        :param flow_rate: The flow rate value (e.g., in L/min).
        """
        self.pump_feedback_label.setText(f"Pump Feedback: {pump_feedback:.1f} %")
        self.flow_feedback_label.setText(f"Flow Rate: {flow_rate:.1f} L/min")

    def update_pressures(self, pressures: List[float]):
        """
        Updates the displayed pressure sensor readings.
        :param pressures: A list of float values for PT1401, PT1402, PT1403.
        """
        for i, pressure in enumerate(pressures):
            self.pressure_labels[i].setText(f"PT140{i+1:02d}: {pressure:.1f} psi")

    def update_temperatures(self, temperatures: List[float]):
        """
        Updates the displayed temperature sensor readings.
        :param temperatures: A list of float values for T01, T02, Heater.
        """
        for i, temp in enumerate(temperatures):
            # If `temperatures` list is truly [T01, T02, Heater], this will work.
            if i == 2: # Assuming the third element is 'Heater'
                self.temperature_labels[i].setText(f"Heater: {temp:.1f} °C")
            else:
                self.temperature_labels[i].setText(f"T0{i+1}: {temp:.1f} °C")


class PIDControlWidget(QWidget):
    """
    A QWidget class that provides an interface for configuring and enabling/disabling
    a PID (Proportional-Integral-Derivative) controller.
    """
    def __init__(self):
        """
        Initializes the PIDControlWidget.
        Sets up input fields for Kp, Ki, Kd, and Setpoint, along with an enable/disable button.
        """
        super().__init__()
        self.pid_enabled = False # Flag to indicate if PID is active
        self.controller = PIDController() # Instance of the PID controller

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.output_label = QLabel("PID Output: -- %")
        self.output_label.setStyleSheet(Stylesheets.LabelStyleSheet()) # Corrected typo
        self.pid_label = QLabel("PID Controller")
        self.pid_label.setStyleSheet(Stylesheets.LabelStyleSheet()) # Corrected typo
        layout.addWidget(self.pid_label)

        layout.addWidget(self.output_label)

        # PID parameter input fields
        self.kp_input = QDoubleSpinBox()
        self.kp_input.setValue(1.0)
        self.ki_input = QDoubleSpinBox()
        self.ki_input.setValue(0.0)
        self.kd_input = QDoubleSpinBox()
        self.kd_input.setValue(0.0)
        self.setpoint_input = QDoubleSpinBox()
        self.setpoint_input.setValue(100.0)

        # Configure spin boxes
        for spinbox in [self.kp_input, self.ki_input, self.kd_input, self.setpoint_input]:
            spinbox.setRange(0, 1000)
            spinbox.setDecimals(2)

        layout.addWidget(QLabel("Kp"))
        layout.addWidget(self.kp_input)
        layout.addWidget(QLabel("Ki"))
        layout.addWidget(self.ki_input)
        layout.addWidget(QLabel("Kd"))
        layout.addWidget(self.kd_input)
        layout.addWidget(QLabel("Setpoint"))
        layout.addWidget(self.setpoint_input)

        self.toggle_button = QPushButton("Enable PID")
        self.toggle_button.setStyleSheet("""
            background-color: #007ACC;
            color: white;
            font-weight: bold;
            border-radius: 5px;
        """)
        self.toggle_button.setCheckable(True) # Make button checkable (toggles state)
        self.toggle_button.clicked.connect(self.toggle_pid)
        layout.addWidget(self.toggle_button)

    def toggle_pid(self):
        """
        Toggles the PID controller's enabled state.
        Updates the button text and resets the PID controller's internal state.
        """
        self.pid_enabled = self.toggle_button.isChecked()
        self.toggle_button.setText("Disable PID" if self.pid_enabled else "Enable PID")
        self.controller.reset() # Reset PID controller when enabling/disabling

    def update_pid_params(self):
        """
        Retrieves the Kp, Ki, Kd gains and setpoint from the input fields
        and updates the PIDController instance with these new parameters.
        """
        kp = self.kp_input.value()
        ki = self.ki_input.value()
        kd = self.kd_input.value()
        setpoint = self.setpoint_input.value()
        self.controller.set_params(kp, ki, kd)
        self.controller.set_setpoint(setpoint)

    def compute_output(self, measured_value: float) -> float | None:
        """
        Computes the PID output based on the measured value if the PID controller is enabled.
        Updates the PID output label.
        :param measured_value: The current measured process variable value.
        :return: The calculated PID output (e.g., control effort percentage) if enabled, otherwise None.
        """
        self.update_pid_params() # Always update params before computing
        if self.pid_enabled:
            output = self.controller.calculate(measured_value)
            self.output_label.setText(f"PID Output: {output:.1f} %")
            return output
        else:
            self.output_label.setText("PID Output: -- %")
            return None # No output if PID is disabled

class PumpControlWindow(QWidget):
    """
    The main control window of the application, integrating all other widgets
    for pump control, sensor display, plotting, and PID control.
    It also handles CAN bus communication and data logging functionalities.
    """
    def __init__(self, nh3_pump_pAndId, bus, can_data_queue: asyncio.Queue, data_manager: SystemDataManager):
        """
        Initializes the PumpControlWindow.
        Sets up the main layout, integrates sub-widgets, and configures CAN communication
        and logging controls.
        :param nh3_pump_pAndId: A reference to the P&ID graphic update function (e.g., nh3pump.run_plots).
        :param bus: The CAN bus object (can.interface.Bus), initially None.
        :param can_data_queue: A single asyncio.Queue for receiving structured CAN data messages.
        :param data_manager: Reference to the SystemDataManager for shared data and state.
        """
        super().__init__()
        self.data_manager = data_manager # Store reference to the central data manager

        self.setWindowTitle("Instrumentation Dashboard")
        self.setMinimumSize(1920, 1080)
        self.setStyleSheet("color: white; background-color: #212121;")

        # Initialize sub-widgets, passing data_manager where needed
        self.pump_control = PumpControlWidget()
        self.plot_canvas = PyqtgraphPlotWidget(self.data_manager) # Pass data_manager
        self.sensor_display = SensorDisplayWidget(self.data_manager) # Pass data_manager
        self.pid_control = PIDControlWidget()
        self.permanentRightHandControl = PermanentRightHandDisplay(self.data_manager) # Pass data_manager

        # Function to update the P&ID graphic (passed from PAndIDGraphicWindow)
        self.update_plot_function = nh3_pump_pAndId

        # Logging and CAN communication variables
        self.bus = bus # CAN bus object
        self.can_data_queue = can_data_queue # Single queue for incoming CAN data
        self.can_connected = False # Flag for CAN connection status
        self.logging = False # Flag for logging status
        self.log_file = None # File object for logging
        self.csv_writer = None # CSV writer object


        # Logging UI components
        self.log_filename_entry = QLineEdit()
        self.log_filename_entry.setPlaceholderText("Enter log filename...")

        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        self.log_button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        # CAN connection UI components
        self.connect_button = QPushButton("Connect CAN")
        self.connect_button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.connect_button.clicked.connect(self.toggle_can_connection)

        # Status bar
        self.status_bar = QLabel("Status: Idle")
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_bar.setStyleSheet(Stylesheets.LabelStyleSheet()) # Corrected typo

        # Main layout configuration
        main_layout = QHBoxLayout()

        # Scroll area for the side panel (controls and displays)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(Stylesheets.GenericScrollAreaStyleSheet())

        side_panel_content = QWidget()
        scroll_area.setWidget(side_panel_content)

        side_panel_layout = QVBoxLayout(side_panel_content)
        side_panel_layout.setContentsMargins(10, 10, 10, 10)

        # Add sub-widgets to the side panel
        side_panel_layout.addWidget(self.pump_control)
        side_panel_layout.addWidget(self.sensor_display)
        side_panel_layout.addWidget(self.pid_control) # Directly add the single PIDControlWidget instance

        # Log file input and button layout
        log_label = QLabel("Log File:")
        log_row = QHBoxLayout()
        log_row.setSpacing(5)
        log_row.addWidget(log_label)
        log_row.addWidget(self.log_filename_entry)
        log_row_widget = QWidget()
        log_row_widget.setLayout(log_row)

        side_panel_layout.addWidget(log_row_widget)
        side_panel_layout.addWidget(self.log_button)


        # Add remaining side panel widgets
        side_panel_layout.addWidget(self.connect_button)
        side_panel_layout.addWidget(self.status_bar)
        side_panel_layout.addStretch() # Adds stretchable space at the bottom of the side panel

        # Set fixed width for scroll area
        scroll_area.setFixedWidth(320)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.plot_canvas, stretch=1) # Add plot canvas to main layout with stretch

        # Overall window layout
        self.superLayout = QHBoxLayout()
        self.superLayout.addLayout(main_layout)
        self.superLayout.addWidget(self.permanentRightHandControl)

        self.setLayout(self.superLayout)

        # Timer for plot updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100) # Update plot every 100 milliseconds

        # Start asynchronous tasks
        asyncio.create_task(self.consumer_task())
        asyncio.create_task(self.pump_sender_task())


    def toggle_can_connection(self):
        """
        Toggles the CAN bus connection.
        If not connected, attempts to establish a connection using `python-can` and starts the CAN listener.
        If connected, shuts down the CAN bus.
        Updates the status bar and button text accordingly.
        """
        if not self.can_connected:
            try:
                # Attempt to connect to the CAN bus
                self.bus = can.interface.Bus(channel="PCAN_USBBUS1", interface="pcan", bitrate=500000)
                # Pass the single data queue to the CAN listener
                # NOTE: can_open_protocol.py's start_listener MUST be adapted to accept
                # a single queue and push structured messages to it.
                CanOpen.start_listener(self.bus, resolution=16, data_queue=self.can_data_queue)

                self.status_bar.setText("Status: CAN Connected")
                self.status_bar.setStyleSheet("""
                    background-color: #228B22; /* Green */
                    color: white;
                    padding: 4px;
                    border-radius: 5px;
                """)
                self.connect_button.setText("Disconnect CAN")
                self.can_connected = True
            except Exception as e:
                QMessageBox.critical(self, "CAN Error", f"Failed to connect to CAN: {e}")
                self.status_bar.setText("Status: CAN Connection Failed")
        else:
            try:
                if self.bus:
                    self.bus.shutdown() # Shut down the CAN bus
                self.bus = None
                self.can_connected = False
                self.connect_button.setText("Connect CAN")
                self.status_bar.setText("Status: Idle")
                self.status_bar.setStyleSheet("""
                    background-color: #333; /* Dark gray */
                    color: white;
                    padding: 4px;
                    border-radius: 5px;
                """)
            except Exception as e:
                QMessageBox.warning(self, "Disconnect Error", f"Error during CAN disconnection: {e}")

    def toggle_logging(self):
        """
        Toggles the data logging functionality.
        If not logging, prompts for a filename, opens a CSV file, and initializes the CSV writer.
        If logging, closes the CSV file.
        Updates the logging button text and filename entry field.
        """
        if not self.logging:
            filename = self.log_filename_entry.text().strip()
            if not filename:
                QMessageBox.warning(self, "Missing Filename", "Please enter a log filename.")
                return
            if not filename.endswith(".csv"):
                filename += ".csv" # Ensure .csv extension

            try:
                self.log_file = open(filename, 'w', newline='') # Open file in write mode
                self.csv_writer = csv.writer(self.log_file)
                # Write CSV header row
                self.csv_writer.writerow([
                    "Timestamp", "PT1401 (psi)", "PT1402 (psi)", "PT1403 (psi)",
                    "T01 (°C)", "T02 (°C)", "Pump On", "Pump Speed (%)", "Pump Speed (RPM)"
                ])
                self.logging = True
                self.log_button.setText("Stop Logging")
                self.log_filename_entry.setEnabled(False) # Disable filename entry while logging
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
        else:
            # Stop logging
            self.logging = False
            if self.log_file:
                self.log_file.close() # Close the log file
                self.log_file = None
            self.csv_writer = None
            self.log_button.setText("Start Logging")
            self.log_filename_entry.setEnabled(True) # Re-enable filename entry

    async def consumer_task(self):
        """
        An asynchronous task that continuously retrieves structured data messages from the single CAN data queue.
        It processes the received data and updates the SystemDataManager.
        """
        while True:
            # Sleep to allow other async tasks to run and prevent tight loop blocking
            # This controls how often the GUI attempts to process new CAN messages.
            await asyncio.sleep(0.1)

            # Retrieve a single structured message from the queue. This call will block until data is available.
            try:
                message: Dict[str, Any] = await self.can_data_queue.get()
            except asyncio.CancelledError:
                # Handle task cancellation gracefully if the queue is shut down
                break
            except Exception as e:
                print(f"Error getting message from queue: {e}")
                continue # Skip to next iteration on error

            # node_id = message.get("node_id")
            data_type = message.get("data_type")
            values = message.get("values")

            # Process data based on its type and update the data manager
            if data_type == 'voltage':
                self.data_manager.update_pressure_data(values)

            elif data_type == 'temperature':
                # The original code had a node_id check. Keep it if relevant for your system.
                # if node_id == 0x182:
                self.data_manager.update_temperature_data(values) # Assuming values is already [:3] or handled by DM

            elif data_type == '4-20mA':
                # Assuming values is a dict like {"pump_percent": X, "flow_kg_per_h": Y}
                self.data_manager.update_current_data(values["pump_percent"], values["flow_kg_per_h"])

            self.can_data_queue.task_done() # Mark task as done for the single queue

    async def pump_sender_task(self):
        """
        An asynchronous task responsible for sending pump control commands over CAN bus.
        It determines the pump speed (manual or PID-controlled), generates the CAN message,
        and sends it. It also handles continuous data logging if enabled.
        """
        while True:
            # Sleep to control the rate of sending pump commands
            await asyncio.sleep(0.05) # Send pump commands every 50 milliseconds

            pump_on, manual_speed = self.pump_control.get_state()
            # Get measured pressure from the data manager
            measured_pressure = self.data_manager.last_pressures[0]

            # Compute PID output from the PIDControlWidget instance
            pid_speed = self.pid_control.compute_output(measured_pressure)

            # Determine final pump speed: PID output if enabled, otherwise manual speed
            speed = pid_speed if pid_speed is not None else manual_speed

            # Generate raw CAN message data for pump control
            raw1, raw2 = CanOpen.generate_outmm_msg(pump_on, speed)
            data = CanOpen.generate_uint_16bit_msg(int(raw1), int(raw2), 0, 0)

            if self.can_connected and self.bus:
                try:
                    # Pass eStopValue and testingFlag from the data manager
                    await CanOpen.send_can_message(self.bus, 0x600, data,
                                                   self.data_manager.eStopValue,
                                                   False, # Assuming is_test_message is always False for pump control
                                                   self.data_manager.testingFlag)
                except Exception as e:
                    self.status_bar.setText(f"CAN Send Error: {str(e)}")

            if self.logging:
                timestamp = datetime.now().isoformat() # Current timestamp
                rpm = speed * 17.2 # Example conversion of speed (%) to RPM
                self.csv_writer.writerow([
                    timestamp,
                    *self.data_manager.last_pressures, # Unpack last pressure values from data manager
                    *self.data_manager.last_temps,     # Unpack last temperature values from data manager
                    pump_on,
                    speed,
                    rpm
                ])
                self.log_file.flush() # Ensure data is written to disk

    async def esv_valve_sender_task(self, state: bool):
        """
        An asynchronous task specifically for sending CAN messages to control an ESV (Emergency Shut-off Valve).
        :param state: Boolean indicating the desired state of the ESV (True for one state, False for another).
        """
        data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] if state else \
               [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        try:
            # Pass eStopValue and testingFlag from the data manager
            await CanOpen.send_can_message(self.bus, 0x191, data,
                                           self.data_manager.eStopValue,
                                           False, # Assuming is_test_message is always False for ESV
                                           self.data_manager.testingFlag)
        except Exception as e:
            self.status_bar.setText(f"CAN Send Error: {str(e)}")

    def update_plot(self):
        """
        Triggers the update of the pyqtgraph plots.
        Called periodically by a QTimer. The plot canvas now gets data directly from the data manager.
        """
        self.plot_canvas.update_plot()

    def closeEvent(self, event):
        """
        Overrides the QWidget's close event.
        Ensures the log file is properly closed when the window is shut down.
        :param event: The close event object.
        """
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        event.accept() # Accept the close event

class PAndIDGraphicWindow(QWidget):
    """
    A QWidget class that displays P&ID (Piping and Instrumentation Diagram) schematics.
    It uses QTabWidget to allow switching between different P&ID views (e.g., NH3 Pump, NH3 Vaporizer).
    """
    def __init__(self):
        """
        Initializes the PAndIDGraphicWindow.
        Sets up the tab widget and embeds the NH3 Pump and Vaporizer control scenes within tabs.
        """
        super().__init__()

        self.setWindowTitle("P&ID Schematics")
        self.setMinimumSize(800, 800)
        self.setStyleSheet("color: white; background-color: #212121;")

        tabWindowLayout = QVBoxLayout()
        self.nh3pump = NH3PumpControlScene() # Instance for NH3 pump P&ID
        self.nh3vaporizer = NH3VaporizerControlScene() # Instance for NH3 vaporizer P&ID

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(Stylesheets.TabWidgetStyleSheet())

        # Create Tab pages
        nh3_pump_test_tab = QWidget()
        nh3_vaporizer_test_tab = QWidget()

        nh3_pump_test_tab.setStyleSheet("background-color: #2e2e2e;")
        nh3_vaporizer_test_tab.setStyleSheet("background-color: #2e2e2e;")

        # Add labels and contents to tabs
        nh3_pump_test_tab_layout = QVBoxLayout(nh3_pump_test_tab)
        nh3_pump_test_tab_layout.addWidget(self.nh3pump) # Add the pump scene to its tab

        nh3_vaporizer_test_layout = QVBoxLayout(nh3_vaporizer_test_tab)
        nh3_vaporizer_test_layout.addWidget(self.nh3vaporizer) # Add the vaporizer scene to its tab

        self.tab_widget.addTab(nh3_pump_test_tab, "NH3 PUMP TEST-1")
        self.tab_widget.addTab(nh3_vaporizer_test_tab, "NH3 VAPORIZER TEST-1")
        tabWindowLayout.addWidget(self.tab_widget)
        self.setLayout(tabWindowLayout)

async def main_async():
    """
    The main asynchronous function that sets up the application.
    Initializes asyncio queues for CAN data, creates the GUI windows,
    and starts the Qt event loop along with asynchronous tasks.
    """
    # Create a single asyncio queue for all incoming CAN data messages
    main_can_queue = asyncio.Queue(maxsize=20) # Increased maxsize for buffer if needed

    app = QApplication(sys.argv) # Initialize the PyQt application

    # Create the central data manager
    data_manager = SystemDataManager(history_len=100)

    pAndIdGraphicWindow = PAndIDGraphicWindow() # Create the P&ID graphic window

    # Connect SystemDataManager signals to P&ID graphic update function (nh3pump.run_plots)
    # The lambda functions ensure only the relevant data is passed and the function is awaited.
    # Assumes nh3pump.run_plots is an async method or handles its own async execution.
    data_manager.pressure_updated.connect(lambda p: asyncio.create_task(pAndIdGraphicWindow.nh3pump.run_plots(p[0], "PT10401")))
    data_manager.pressure_updated.connect(lambda p: asyncio.create_task(pAndIdGraphicWindow.nh3pump.run_plots(p[1], "PT10402")))
    data_manager.temperature_updated.connect(lambda t: asyncio.create_task(pAndIdGraphicWindow.nh3pump.run_plots(t[0], "TI10401")))
    data_manager.temperature_updated.connect(lambda t: asyncio.create_task(pAndIdGraphicWindow.nh3pump.run_plots(t[1], "TI10402")))
    data_manager.temperature_updated.connect(lambda t: asyncio.create_task(pAndIdGraphicWindow.nh3pump.run_plots(t[2], "Heater")))
    data_manager.pump_feedback_updated.connect(lambda p, f: asyncio.create_task(pAndIdGraphicWindow.nh3pump.run_plots(p, "PUMP")))
    data_manager.pump_feedback_updated.connect(lambda p, f: asyncio.create_task(pAndIdGraphicWindow.nh3pump.run_plots(f, "FE01")))

    # Create the pump control window, passing necessary dependencies
    controlWindow = PumpControlWindow(
        pAndIdGraphicWindow.nh3pump.run_plots, # P&ID update function reference
        bus=None,                              # Initial bus (will be set on connect)
        can_data_queue=main_can_queue,         # The single CAN data queue
        data_manager=data_manager              # Central data manager
    )

    pAndIdGraphicWindow.show() # Display the P&ID window
    controlWindow.show() # Display the control window

    while True:
        await asyncio.sleep(0.01) # Short sleep to yield control
        app.processEvents() # Process PyQt events to keep the GUI responsive

if __name__ == "__main__":
    # Entry point of the application. Runs the main asynchronous function.
    asyncio.run(main_async())