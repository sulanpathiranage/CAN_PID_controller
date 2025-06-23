import os
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"  # Force pglive/pyqtgraph to use PySide6

import sys
import asyncio
import csv
from datetime import datetime
from collections import deque
from typing import List, Dict, Any, Union # Added Union for ClickableTextItem
import pyqtgraph as pg
import can
from pglive.sources.live_plot_widget import LivePlotWidget # Import LivePlotWidget
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_axis_range import LiveAxisRange
from pglive.sources.data_connector import DataConnector # Import DataConnector

# PySide6 Imports
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget,
    QGraphicsView, QGraphicsScene, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsPolygonItem
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal as pyqtSignal, QPointF
from PySide6.QtGui import QFont, QPen, QBrush, QPolygonF

# Local imports
from pid_controller import PIDController
from app_stylesheets import Stylesheets
from NH3_pump_control import NH3PumpControlScene
from NH3_vaporizer_control import NH3VaporizerControlScene
from can_open_protocol import CanOpen

class SystemDataManager(QObject):
    pressure_updated = pyqtSignal(list)
    temperature_updated = pyqtSignal(list)
    pump_feedback_updated = pyqtSignal(float, float)
    e_stop_toggled = pyqtSignal(bool)

    def __init__(self, history_len: int):
        super().__init__()
        self._history_len = history_len

        self._ch_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(3)]
        self._temp_data = [deque([0.0] * self._history_len, maxlen=self._history_len) for _ in range(3)]
        # New deque for pump feedback percentage
        self._pump_feedback_percent_data = deque([0.0] * self.history_len, maxlen=self.history_len)
        # New deque for flow rate
        self._flow_rate_data = deque([0.0] * self.history_len, maxlen=self.history_len)

        self._eStopValue = False
        self._testingFlag = False
        self._last_pressures = [0.0, 0.0, 0.0]
        self._last_temps = [0.0, 0.0, 0.0]
        self._last_pump_feedback = 0.0
        self._last_flow_rate = 0.0
        self.INVALID_TEMP_MARKER = -3276.8

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
    def pump_feedback_percent_data(self) -> deque:
        return self._pump_feedback_percent_data

    @property
    def flow_rate_data(self) -> deque:
        return self._flow_rate_data

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

    def update_pressure_data(self, values: List[float]):
        if len(values) >= 3:
            scaled_pressures = [values[0] * 30.0, values[1] * 60.0, values[2] * 60.0]
            for i in range(3):
                self._ch_data[i].append(scaled_pressures[i])
            self._last_pressures = scaled_pressures
            self.pressure_updated.emit(scaled_pressures)

    def update_temperature_data(self, values: List[float]):
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
        self._last_pump_feedback = pump_percent
        self._last_flow_rate = flow_kg_per_h
        # Append data to the new deques
        self._pump_feedback_percent_data.append(pump_percent)
        self._flow_rate_data.append(flow_kg_per_h)
        self.pump_feedback_updated.emit(pump_percent, flow_kg_per_h)

    def reset_pressure_data(self):
        self._last_pressures = [0.0, 0.0, 0.0]
        for i in range(3):
            self._ch_data[i].clear()
            self._ch_data[i].extend([0.0] * self._history_len)
        self.pressure_updated.emit(self._last_pressures)

    def reset_temperature_data(self):
        self._last_temps = [0.0, 0.0, 0.0]
        for i in range(3):
            self._temp_data[i].clear()
            self._temp_data[i].extend([0.0] * self._history_len)
            if hasattr(self, '_raw_temp_buffers'):
                self._raw_temp_buffers[i].clear()
        if hasattr(self, '_smoothed_temps'):
            self._smoothed_temps = [0.0, 0.0, 0.0]
        self.temperature_updated.emit(self._last_temps)

    def reset_feedback_data(self):
        self._last_pump_feedback = 0.0
        self._last_flow_rate = 0.0
        # Clear and re-initialize the feedback deques
        self._pump_feedback_percent_data.clear()
        self._pump_feedback_percent_data.extend([0.0] * self._history_len)
        self._flow_rate_data.clear()
        self._flow_rate_data.extend([0.0] * self._history_len)
        self.pump_feedback_updated.emit(self._last_pump_feedback, self._last_flow_rate)

    def toggle_e_stop_state(self):
        self.eStopValue = not self.eStopValue


class PyqtgraphPlotWidget(QWidget):
    """
    A QWidget class that displays real-time pressure and temperature data using pglive.
    It creates multiple plot widgets for individual pressure sensors and a combined plot for temperatures.
    All plots and connectors are managed in dictionaries for modular access.
    """
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager
        self.layout = QHBoxLayout(self)

        plot_layout = QVBoxLayout()
        self.history_len = self.data_manager.history_len

        # Dictionaries to store LiveLinePlot and DataConnector instances by signal name
        self.signal_plots: Dict[str, LiveLinePlot] = {}
        self.signal_connectors: Dict[str, DataConnector] = {}
        self.plot_widgets: Dict[str, LivePlotWidget] = {} # To store the LivePlotWidget instances themselves

        # --- Define Plot Widgets (Containers for Curves) ---
        # Pressure plots (each sensor gets its own LivePlotWidget)
        pressure_plot_configs = [
            {"key": "PT1401_plot", "title": "PT1401", "y_range": [0, 150], "roll_on_tick": self.history_len},
            {"key": "PT1402_plot", "title": "PT1402", "y_range": [0, 300], "roll_on_tick": self.history_len},
            {"key": "PT1403_plot", "title": "PT1403", "y_range": [0, 300], "roll_on_tick": self.history_len},
        ]
        for config in pressure_plot_configs:
            widget = LivePlotWidget(
                title=config['title'],
                x_range_controller=LiveAxisRange(roll_on_tick=config['roll_on_tick']),
                y_range_controller=LiveAxisRange(fixed_range=config['y_range'])
            )
            plot_layout.addWidget(widget)
            self.plot_widgets[config['key']] = widget # Store the LivePlotWidget by a unique key

        # Temperature combined plot (single LivePlotWidget for all temperature curves)
        temp_plot_key = "temperature_combined_plot"
        self.temp_widget = LivePlotWidget(
            title="Temperatures",
            x_range_controller=LiveAxisRange(roll_on_tick=self.history_len),
            y_range_controller=LiveAxisRange(fixed_range=[10, 100])
        )
        self.temp_widget.addLegend() # Add legend for combined plot to differentiate curves
        plot_layout.addWidget(self.temp_widget)
        self.plot_widgets[temp_plot_key] = self.temp_widget # Store the combined temp widget

        # --- NEW: Pump Feedback Plot ---
        pump_feedback_plot_key = "pump_feedback_plot"
        self.pump_feedback_widget = LivePlotWidget(
            title="Pump Feedback & Flow Rate",
            x_range_controller=LiveAxisRange(roll_on_tick=self.history_len), # Adjust roll_on_tick for 60s
            y_range_controller=LiveAxisRange(fixed_range=[0, 100]) # Example range for pump % and flow
        )
        self.pump_feedback_widget.addLegend()
        plot_layout.addWidget(self.pump_feedback_widget)
        self.plot_widgets[pump_feedback_plot_key] = self.pump_feedback_widget

        # --- Define Individual Signal Configurations and Create Plots/Connectors ---
        # This list holds the configuration for each line you want to plot.
        # It links a signal name (dict key) to its data index, color, and parent plot widget.
        self.signal_configs = [
            # Pressure Signals (each goes to its own dedicated plot widget)
            {"name": "PT1401", "data_type": "pressure", "data_index": 0, "color": 'g', "plot_widget_key": "PT1401_plot", "history_len_key": "history_len"},
            {"name": "PT1402", "data_type": "pressure", "data_index": 1, "color": 'g', "plot_widget_key": "PT1402_plot", "history_len_key": "history_len"},
            {"name": "PT1403", "data_type": "pressure", "data_index": 2, "color": 'g', "plot_widget_key": "PT1403_plot", "history_len_key": "history_len"},
            # Temperature Signals (all go to the combined temperature plot widget)
            {"name": "T01", "data_type": "temperature", "data_index": 0, "color": 'r', "plot_widget_key": temp_plot_key, "history_len_key": "history_len"},
            {"name": "T02", "data_type": "temperature", "data_index": 1, "color": 'b', "plot_widget_key": temp_plot_key, "history_len_key": "history_len"},
            {"name": "Heater", "data_type": "temperature", "data_index": 2, "color": 'w', "plot_widget_key": temp_plot_key, "history_len_key": "history_len"},
            # NEW: Pump Feedback Signals (go to the new pump feedback plot widget)
            {"name": "Pump_Percent", "data_type": "pump_feedback", "data_index": 0, "color": 'c', "plot_widget_key": pump_feedback_plot_key, "history_len_key": "history_len"},
            # {"name": "Flow_Rate", "data_type": "pump_feedback", "data_index": 1, "color": 'm', "plot_widget_key": pump_feedback_plot_key, "history_len_key": "pump_feedback_history_len"},
        ]

        # Loop through the signal configurations to create and store plots and connectors
        for config in self.signal_configs:
            signal_name = config['name']
            color = config['color']
            plot_widget = self.plot_widgets[config['plot_widget_key']]
            
            # Determine which history length to use
            max_points = getattr(self.data_manager, config['history_len_key'])

            # Create LiveLinePlot with explicit pen (width 1) and no filling
            plot_item = LiveLinePlot(
                pen=pg.mkPen(color, width=1), # Use pg.mkPen for clarity and control
                name=signal_name, # Name for legend
                fillLevel=None,   # Ensure no filling below the line
                fillBrush=None    # Ensure no filling brush is applied
            )
            plot_widget.addItem(plot_item)
            self.signal_plots[signal_name] = plot_item # Store plot item by its signal name

            # Create DataConnector for this plot item
            connector = DataConnector(plot_item, max_points=max_points, update_rate=30)
            self.signal_connectors[signal_name] = connector # Store connector by its signal name

        self.layout.addLayout(plot_layout)

        # Connect to data manager signals for updates
        # The update methods will now use the dictionaries for dynamism
        self.data_manager.pressure_updated.connect(self._on_pressure_data_updated)
        self.data_manager.temperature_updated.connect(self._on_temperature_data_updated)
        # NEW: Connect to pump_feedback_updated signal
        self.data_manager.pump_feedback_updated.connect(self._on_pump_feedback_updated)

    def _on_pressure_data_updated(self, pressures: List[float]):
        """
        Slot to handle pressure_updated signal from SystemDataManager.
        Updates specific pressure plots using their associated DataConnectors.
        """
        for config in self.signal_configs:
            if config['data_type'] == "pressure":
                idx = config['data_index']
                signal_name = config['name']
                if idx < len(pressures):
                    # Fetch the correct DataConnector using the signal name
                    self.signal_connectors[signal_name].cb_append_data_point(pressures[idx])
                    # print(f"Appended pressure[{idx}] ({signal_name}): {pressures[idx]}")

    def _on_temperature_data_updated(self, temperatures: List[float]):
        """
        Slot to handle temperature_updated signal from SystemDataManager.
        Updates specific temperature plots using their associated DataConnectors.
        """
        for config in self.signal_configs:
            if config['data_type'] == "temperature":
                idx = config['data_index']
                signal_name = config['name']
                if idx < len(temperatures):
                    # Fetch the correct DataConnector using the signal name
                    self.signal_connectors[signal_name].cb_append_data_point(temperatures[idx])
                    # print(f"Appended temperature[{idx}] ({signal_name}): {temperatures[idx]}")

    def _on_pump_feedback_updated(self, pump_percent: float, flow_kg_per_h: float):
        """
        Slot to handle pump_feedback_updated signal from SystemDataManager.
        Updates the pump feedback and flow rate plots.
        """
        # Update Pump_Percent plot
        self.signal_connectors["Pump_Percent"].cb_append_data_point(pump_percent)
        # Update Flow_Rate plot
        self.signal_connectors["Flow_Rate"].cb_append_data_point(flow_kg_per_h)
        # print(f"Appended pump feedback: {pump_percent}, flow rate: {flow_kg_per_h}")

    def get_signal_plot(self, signal_name: str) -> Union[LiveLinePlot, None]:
        """
        Returns the LiveLinePlot associated with the given signal name.
        This allows you to dynamically access a plot item using its name (e.g., to hide it or change its pen).
        """
        return self.signal_plots.get(signal_name)

    def get_signal_connector(self, signal_name: str) -> Union[DataConnector, None]:
        """
        Returns the DataConnector associated with the given signal name.
        This allows dynamic access to a data connector.
        """
        return self.signal_connectors.get(signal_name)


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
        self.setMinimumSize(1200, 900)
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
        self.status_bar.setWordWrap(True) # Added word wrap for long messages

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



        # Start asynchronous tasks
        asyncio.create_task(self.consumer_task())
        asyncio.create_task(self.pump_sender_task())


    def toggle_can_connection(self):
        """
        Toggles the CAN bus connection.
        If not connected, attempts to establish a connection.
        If connected, shuts down the CAN bus and resets all sensor values to 0.
        Updates the status bar and button text accordingly.
        """
        if not self.can_connected:
            try:
                # Attempt to connect to the CAN bus
                self.bus = can.interface.Bus(channel="PCAN_USBBUS1", interface="pcan", bitrate=500000)
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
            # When disconnecting:
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
                
                # Reset all sensor values to 0 via the data manager
                self.data_manager.reset_pressure_data()
                self.data_manager.reset_temperature_data()
                self.data_manager.reset_feedback_data()

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
            # Retrieve a single structured message from the queue. This call will block until data is available.
            try:
                # Ensure that CanOpen.start_listener puts dictionary objects
                # into the queue, or adjust this consumer_task to expect CanData objects.
                # Based on previous conversation, the CanOpen.start_listener needs to be updated
                # to put dictionaries (e.g., {'data_type': 'voltage', 'values': [...]})
                # into the queue, or this consumer_task needs to be adjusted.
                message: Dict[str, Any] = await self.can_data_queue.get()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error getting message from queue: {e}")
                continue

            data_type = message.get("data_type")
            values = message.get("values")

            if data_type == 'voltage':
                self.data_manager.update_pressure_data(values)

            elif data_type == 'temperature':
                self.data_manager.update_temperature_data(values)

            elif data_type == '4-20mA':
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
                    # Assuming CanOpen.send_can_message takes eStop and a test_flag.
                    # Original was (self.bus, 0x600, data, eStopValue, False, testingFlag)
                    await CanOpen.send_can_message(self.bus, 0x600, data,
                                                   self.data_manager.eStopValue)
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
            # Assuming CanOpen.send_can_message takes eStop and a test_flag.
            # Original was (self.bus, 0x191, data, eStopValue, False, testingFlag)
            await CanOpen.send_can_message(self.bus, 0x191, data,
                                           self.data_manager.eStopValue,
                                           False, # is_test_message parameter
                                           self.data_manager.testingFlag) # test_flag parameter
        except Exception as e:
            self.status_bar.setText(f"CAN Send Error: {str(e)}")

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
    main_can_queue = asyncio.Queue(maxsize=20) 

    app = QApplication(sys.argv) 
    data_manager = SystemDataManager(history_len=100)

    pAndIdGraphicWindow = PAndIDGraphicWindow() 

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

    controlWindow = PumpControlWindow(
        pAndIdGraphicWindow.nh3pump.run_plots, # P&ID update function reference
        bus=None,                              # Initial bus (will be set on connect)
        can_data_queue=main_can_queue,         # The single CAN data queue
        data_manager=data_manager              # Central data manager
    )

    pAndIdGraphicWindow.show() # Display the P&ID window
    controlWindow.show() 

    while True:
        await asyncio.sleep(0.01) 
        app.processEvents() 

if __name__ == "__main__":

    asyncio.run(main_async())