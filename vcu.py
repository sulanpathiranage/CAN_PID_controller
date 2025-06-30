# vcu.py
import os
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"

import sys
import asyncio
from typing import List, Dict, Any, Union, Tuple

from pglive.sources.live_plot_widget import LivePlotWidget
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_axis_range import LiveAxisRange
from pglive.sources.data_connector import DataConnector

# PySide6 Imports
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget,
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal as pyqtSignal
from PySide6.QtGui import QFont, QPen, QBrush

# Local imports
from pid_controller import PIDController
from app_stylesheets import Stylesheets
from NH3_pump_control import NH3PumpControlScene
from NH3_vaporizer_control import NH3VaporizerControlScene
from data_manager import SystemDataManager
from log_manager import AppLogger

# Define the logging columns: (key_name, header_name, formatter_string)
# key_name: Used to retrieve data from the dictionary passed to log_data.
# header_name: Appears in the CSV header.
# formatter_string: f-string style format (e.g., ".1f", ".0f", or "" for default str()).
LOGGING_COLUMNS_DEFINITION: List[Tuple[str, str, str]] = [
    ("pt1401", "PT1401 (psi)", ".1f"),
    ("pt1402", "PT1402 (psi)", ".1f"),
    ("pt1403", "PT1403 (psi)", ".1f"),
    ("t01", "T01 (°C)", ".1f"),
    ("t02", "T02 (°C)", ".1f"),
    ("heater_temp", "Heater (°C)", ".1f"),
    ("pump_on_status", "Pump On", ""), # No specific float/int formatting, just its value
    ("commanded_pump_speed", "Commanded Pump Speed (%)", ".1f"),
    ("pump_feedback", "Pump Feedback (%)", ".1f"),
    ("flow_rate_feedback", "Flow Rate Feedback (kg/h)", ".1f"),
]

class PyqtgraphPlotWidget(QWidget):
    # ... (remains the same as previous concise version)
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager
        self.layout = QHBoxLayout(self)
        plot_layout = QVBoxLayout()
        self.history_len = self.data_manager.history_len

        self.pressure_connectors = []
        self.temperature_connectors = []
        self.pressure_live_lines = []
        self.temperature_live_lines = []

        pressure_titles = ["PT1401", "PT1402", "PT1403"]
        self.pressure_plots, self.pressure_connectors, self.pressure_live_lines = self._create_sensor_plots(
            plot_layout, pressure_titles, Qt.green, 0, 5, 'o'
        )

        self.temp_widget = LivePlotWidget(
            title="Temperatures",
            x_range_controller=LiveAxisRange(roll_on_tick=30),
            y_range_controller=LiveAxisRange(fixed_range=[10, 30])
        )
        self.temperature_live_lines = [
            LiveLinePlot(pen=QPen(Qt.red, 3), auto_fill_history=True, symbol='s', symbolSize=8),
            LiveLinePlot(pen=QPen(Qt.blue, 3), auto_fill_history=True, symbol='t', symbolSize=8),
        ]
        for curve in self.temperature_live_lines:
            self.temp_widget.addItem(curve)
        plot_layout.addWidget(self.temp_widget)

        self.temperature_connectors = [
            DataConnector(self.temperature_live_lines[0], max_points=self.history_len, update_rate=30),
            DataConnector(self.temperature_live_lines[1], max_points=self.history_len, update_rate=30),
        ]

        self.layout.addLayout(plot_layout)

        self.data_manager.pressure_updated.connect(self._on_pressure_data_updated)
        self.data_manager.temperature_updated.connect(self._on_temperature_data_updated)

    def _create_sensor_plots(self, layout, titles, color, y_min, y_max, symbol):
        widgets = []
        connectors = []
        lines = []
        for title in titles:
            widget = LivePlotWidget(
                title=title,
                x_range_controller=LiveAxisRange(roll_on_tick=30),
                y_range_controller=LiveAxisRange(fixed_range=[y_min, y_max])
            )
            plot = LiveLinePlot(pen=QPen(color, 3), auto_fill_history=True, symbol=symbol, symbolSize=8)
            widget.addItem(plot)
            layout.addWidget(widget)
            widgets.append(widget)
            lines.append(plot)
            connectors.append(DataConnector(plot, max_points=self.history_len, update_rate=30))
        return widgets, connectors, lines

    def _on_pressure_data_updated(self, pressures: List[float]):
        for i, connector in enumerate(self.pressure_connectors):
            if i < len(pressures):
                connector.cb_append_data_point(pressures[i])

    def _on_temperature_data_updated(self, temperatures: List[float]):
        if len(temperatures) >= 2:
            self.temperature_connectors[0].cb_append_data_point(temperatures[0])
            self.temperature_connectors[1].cb_append_data_point(temperatures[1])

    def update_plot(self):
        for plot_widget in self.pressure_plots:
            plot_widget.update()
        self.temp_widget.update()


class PermanentRightHandDisplay(QWidget):
    # ... (remains the same as previous concise version)
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager

        rightHandVerticalLayout = QVBoxLayout(self)

        self.eStopButton = QPushButton("E-STOP")
        self.eStopButton.setFixedSize(150, 100)
        self.eStopButton.setStyleSheet(Stylesheets.EStopPushButtonStyleSheet())
        self.eStopButton.clicked.connect(self.toggleEStop)

        rightHandVerticalLayout.addWidget(QLabel("Safety Critical Info Label 1"))
        rightHandVerticalLayout.addWidget(QLabel("Safety Critical Info Label 2"))
        rightHandVerticalLayout.addWidget(QLabel("Safety Critical Info Label 3"))

        self.safetyControlPushButtonOne = QPushButton("Safety Control One")
        self.safetyControlPushButtonOne.setFixedSize(150, 80)
        self.safetyControlPushButtonOne.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        rightHandVerticalLayout.addWidget(self.safetyControlPushButtonOne)

        self.safetyControlPushButtonTwo = QPushButton("Safety Control Two")
        self.safetyControlPushButtonTwo.setFixedSize(150, 80)
        self.safetyControlPushButtonTwo.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        rightHandVerticalLayout.addWidget(self.safetyControlPushButtonTwo)

        rightHandVerticalLayout.addWidget(self.eStopButton)

        self.data_manager.e_stop_toggled.connect(self._update_e_stop_button_text)

    def toggleEStop(self):
        self.data_manager.toggle_e_stop_state()

    def _update_e_stop_button_text(self, is_active: bool):
        self.eStopButton.setText("E-STOP\nACTIVE" if is_active else "E-STOP")


class PumpControlWidget(QWidget):
    # ... (remains the same as previous concise version)
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        group = QGroupBox("Pump Control")
        group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        form_layout = QGridLayout(group)

        self.pump_on_checkbox = QCheckBox("Pump ON")
        self.pump_on_checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        form_layout.addWidget(QLabel("Pump State:"), 0, 0)
        form_layout.addWidget(self.pump_on_checkbox, 0, 1, 1, 2)

        # Fix start
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(0)
        # Fix end

        self.speed_entry = QLineEdit("0", fixedWidth=50, alignment=Qt.AlignmentFlag.AlignCenter)

        form_layout.addWidget(QLabel("Speed:"), 1, 0)
        form_layout.addWidget(self.speed_slider, 1, 1)
        form_layout.addWidget(self.speed_entry, 1, 2)

        self.output_label = QLabel("PID Output: -- %")
        form_layout.addWidget(self.output_label, 2, 0, 1, 3)

        self.speed_slider.valueChanged.connect(self.update_entry)
        self.speed_entry.editingFinished.connect(self.update_slider)

        layout.addWidget(group)
        layout.addStretch(1)

    def update_entry(self, val: int):
        self.speed_entry.setText(str(val))

    def update_slider(self):
        try:
            val = int(self.speed_entry.text())
            if 0 <= val <= 100:
                self.speed_slider.setValue(val)
        except ValueError:
            pass

    def get_state(self) -> tuple[int, int]:
        return int(self.pump_on_checkbox.isChecked()), self.speed_slider.value()


class SensorDisplayWidget(QWidget):
    # ... (remains the same as previous concise version)
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager
        layout = QVBoxLayout(self)

        self.pump_feedback_label = QLabel("Pump Feedback: -- %", styleSheet="font-size: 14px;")
        self.flow_feedback_label = QLabel("Flow Rate: -- L/min", styleSheet="font-size: 14px;")
        layout.addWidget(self.pump_feedback_label)
        layout.addWidget(self.flow_feedback_label)

        layout.addWidget(QLabel("Pressure Sensors", styleSheet=Stylesheets.LabelStyleSheet()))
        self.pressure_labels = [
            QLabel(f"PT140{i+1}: -- psi", alignment=Qt.AlignmentFlag.AlignLeft, styleSheet=Stylesheets.LabelStyleSheet())
            for i in range(3)
        ]
        for label in self.pressure_labels:
            layout.addWidget(label)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Temperature Sensors", styleSheet=Stylesheets.LabelStyleSheet()))
        self.temperature_labels = [
            QLabel(f"{name}: -- °C", alignment=Qt.AlignmentFlag.AlignLeft, styleSheet=Stylesheets.LabelStyleSheet())
            for name in ["T01", "T02", "Heater"]
        ]
        for label in self.temperature_labels:
            layout.addWidget(label)

        layout.addStretch()

        self.data_manager.pressure_updated.connect(self.update_pressures)
        self.data_manager.temperature_updated.connect(self.update_temperatures)
        self.data_manager.pump_feedback_updated.connect(self.update_feedback)

    def update_feedback(self, pump_feedback: float, flow_rate: float):
        self.pump_feedback_label.setText(f"Pump Feedback: {pump_feedback:.1f} %")
        self.flow_feedback_label.setText(f"Flow Rate: {flow_rate:.1f} L/min")

    def update_pressures(self, pressures: List[float]):
        for i, pressure in enumerate(pressures):
            self.pressure_labels[i].setText(f"PT140{i+1:02d}: {pressure:.1f} psi")

    def update_temperatures(self, temperatures: List[float]):
        for i, temp in enumerate(temperatures):
            if i == 2:
                self.temperature_labels[i].setText(f"Heater: {temp:.1f} °C")
            else:
                self.temperature_labels[i].setText(f"T0{i+1}: {temp:.1f} °C")


class PIDControlWidget(QWidget):
    # ... (remains the same as previous concise version)
    def __init__(self):
        super().__init__()
        self.pid_enabled = False
        self.controller = PIDController()
        self._last_computed_output = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("PID Controller", styleSheet=Stylesheets.LabelStyleSheet()))
        self.output_label = QLabel("PID Output: -- %", styleSheet=Stylesheets.LabelStyleSheet())
        layout.addWidget(self.output_label)

        self.kp_input = QDoubleSpinBox(value=1.0)
        self.ki_input = QDoubleSpinBox(value=0.0)
        self.kd_input = QDoubleSpinBox(value=0.0)
        self.setpoint_input = QDoubleSpinBox(value=100.0)

        spinboxes = [self.kp_input, self.ki_input, self.kd_input, self.setpoint_input]
        labels = ["Kp", "Ki", "Kd", "Setpoint"]

        for label, spinbox in zip(labels, spinboxes):
            spinbox.setRange(0, 1000)
            spinbox.setDecimals(2)
            layout.addWidget(QLabel(label))
            layout.addWidget(spinbox)

        self.toggle_button = QPushButton("Enable PID", checkable=True)
        self.toggle_button.setStyleSheet("""
            background-color: #007ACC;
            color: white;
            font-weight: bold;
            border-radius: 5px;
        """)
        self.toggle_button.clicked.connect(self.toggle_pid)
        layout.addWidget(self.toggle_button)

    def toggle_pid(self):
        self.pid_enabled = self.toggle_button.isChecked()
        self.toggle_button.setText("Disable PID" if self.pid_enabled else "Enable PID")
        self.controller.reset()
        self._last_computed_output = None if not self.pid_enabled else self._last_computed_output
        self.output_label.setText(f"PID Output: {'--' if not self.pid_enabled else f'{self._last_computed_output:.1f}'} %")


    def compute_output(self, measured_value: float) -> Union[float, None]:
        self.update_pid_params()
        if self.pid_enabled:
            output = self.controller.calculate(measured_value)
            self._last_computed_output = output
            self.output_label.setText(f"PID Output: {output:.1f} %")
            return output
        else:
            self._last_computed_output = None
            self.output_label.setText("PID Output: -- %")
            return None

    def update_pid_params(self):
        self.controller.set_params(self.kp_input.value(), self.ki_input.value(), self.kd_input.value())
        self.controller.set_setpoint(self.setpoint_input.value())

    def get_last_computed_output(self) -> Union[float, None]:
        return self._last_computed_output


class PumpControlWindow(QWidget):
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager
        self.logger = AppLogger()

        self.setWindowTitle("Instrumentation Dashboard")
        self.setMinimumSize(1200, 900)
        self.setStyleSheet("color: white; background-color: #212121;")

        # Initialize sub-widgets
        self.pump_control = PumpControlWidget()
        self.plot_canvas = PyqtgraphPlotWidget(self.data_manager)
        self.sensor_display = SensorDisplayWidget(self.data_manager)
        self.pid_control = PIDControlWidget()
        self.permanentRightHandControl = PermanentRightHandDisplay(self.data_manager)

        # Logging UI components
        self.log_filename_entry = QLineEdit(placeholderText="Enter log filename...")
        self.log_button = QPushButton("Start Logging", clicked=self._toggle_logging, styleSheet=Stylesheets.GenericPushButtonStyleSheet())

        # CAN connection UI components
        self.connect_button = QPushButton("Connect CAN", clicked=self._toggle_can_connection, styleSheet=Stylesheets.GenericPushButtonStyleSheet())

        self.status_bar = QLabel("Status: Idle", alignment=Qt.AlignmentFlag.AlignCenter, styleSheet=Stylesheets.LabelStyleSheet(), wordWrap=True)

        # Main layout configuration
        main_layout = QHBoxLayout(self)

        scroll_area = QScrollArea(widgetResizable=True, horizontalScrollBarPolicy=Qt.ScrollBarPolicy.ScrollBarAlwaysOff, styleSheet=Stylesheets.GenericScrollAreaStyleSheet())
        side_panel_content = QWidget()
        scroll_area.setWidget(side_panel_content)
        side_panel_layout = QVBoxLayout(side_panel_content)

        side_panel_layout.addWidget(self.pump_control)
        side_panel_layout.addWidget(self.sensor_display)
        side_panel_layout.addWidget(self.pid_control)

        log_row = QHBoxLayout(spacing=5)
        log_row.addWidget(QLabel("Log File:"))
        log_row.addWidget(self.log_filename_entry)
        
        side_panel_layout.addLayout(log_row) 
        side_panel_layout.addWidget(self.log_button)
        side_panel_layout.addWidget(self.connect_button)
        side_panel_layout.addWidget(self.status_bar)
        side_panel_layout.addStretch()

        scroll_area.setFixedWidth(320)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.plot_canvas, stretch=1)
        main_layout.addWidget(self.permanentRightHandControl) # Corrected typo, was permanentRightHandControl

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_gui_and_can_commands)
        self.timer.start(100)

        self.data_manager.can_connection_status_changed.connect(self._update_can_button_and_status)
        self.data_manager.can_error.connect(self._show_can_error_message)

    def _toggle_can_connection(self):
        self.data_manager.toggle_can_connection()

    def _update_can_button_and_status(self, is_connected: bool):
        self.status_bar.setText("Status: CAN Connected" if is_connected else "Status: Idle")
        self.status_bar.setStyleSheet("""
            background-color: #228B22; /* Green */
            color: white;
            padding: 4px;
            border-radius: 5px;
        """ if is_connected else """
            background-color: #333; /* Dark gray */
            color: white;
            padding: 4px;
            border-radius: 5px;
        """)
        self.connect_button.setText("Disconnect CAN" if is_connected else "Connect CAN")

    def _show_can_error_message(self, message: str):
        QMessageBox.critical(self, "CAN Error", message)
        self.status_bar.setText(f"Status: CAN Error - {message}")
        self.status_bar.setStyleSheet("""
            background-color: #DC143C; /* Crimson Red */
            color: white;
            padding: 4px;
            border-radius: 5px;
        """)

    def _toggle_logging(self):
        if not self.logger.is_logging:
            filename = self.log_filename_entry.text().strip()
            
            # Use the pre-defined LOGGING_COLUMNS_DEFINITION
            if self.logger.start_logging(filename, columns_config=LOGGING_COLUMNS_DEFINITION):
                self.log_button.setText("Stop Logging")
                self.log_filename_entry.setEnabled(False)
            else:
                QMessageBox.warning(self, "Logging Error", "Failed to start logging. Check filename and permissions.")
        else:
            self.logger.stop_logging()
            self.log_button.setText("Start Logging")
            self.log_filename_entry.setEnabled(True)

    def _update_gui_and_can_commands(self):
        self.plot_canvas.update_plot()

        pump_on, manual_speed = self.pump_control.get_state()
        measured_pressure = self.data_manager.last_pressures[0]
        pid_output = self.pid_control.compute_output(measured_pressure)
        self.data_manager.update_commanded_pump_state(pump_on, manual_speed, pid_output)

        if self.logger.is_logging:
            commanded_speed_for_log = pid_output if pid_output is not None else manual_speed
            commanded_speed_for_log = max(0.0, min(100.0, float(commanded_speed_for_log if commanded_speed_for_log is not None else 0.0)))

            # Construct the data dictionary with raw values, using the defined keys
            data_to_log = {
                "pt1401": self.data_manager.last_pressures[0],
                "pt1402": self.data_manager.last_pressures[1],
                "pt1403": self.data_manager.last_pressures[2],
                "t01": self.data_manager.last_temps[0],
                "t02": self.data_manager.last_temps[1],
                "heater_temp": self.data_manager.last_temps[2],
                "pump_on_status": pump_on,
                "commanded_pump_speed": commanded_speed_for_log,
                "pump_feedback": self.data_manager.last_pump_feedback,
                "flow_rate_feedback": self.data_manager.last_flow_rate,
            }
            
            self.logger.log_data(data_to_log)

    def closeEvent(self, event):
        self.logger.stop_logging()
        self.data_manager.close_can_connection()
        event.accept()


class PAndIDGraphicWindow(QWidget):
    # ... (remains the same as previous concise version)
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager

        self.setWindowTitle("P&ID Schematics")
        self.setMinimumSize(800, 800)
        self.setStyleSheet("color: white; background-color: #212121;")

        tabWindowLayout = QVBoxLayout(self)
        self.nh3pump = NH3PumpControlScene(data_manager=data_manager)
        self.nh3vaporizer = NH3VaporizerControlScene()

        self.tab_widget = QTabWidget(styleSheet=Stylesheets.TabWidgetStyleSheet())

        nh3_pump_test_tab = QWidget(styleSheet="background-color: #2e2e2e;")
        nh3_vaporizer_test_tab = QWidget(styleSheet="background-color: #2e2e2e;")

        QVBoxLayout(nh3_pump_test_tab).addWidget(self.nh3pump)
        QVBoxLayout(nh3_vaporizer_test_tab).addWidget(self.nh3vaporizer)

        self.tab_widget.addTab(nh3_pump_test_tab, "NH3 PUMP TEST-1")
        self.tab_widget.addTab(nh3_vaporizer_test_tab, "NH3 VAPORIZER TEST-1")
        tabWindowLayout.addWidget(self.tab_widget)

        self.data_manager.pressure_updated.connect(lambda p: asyncio.create_task(self.nh3pump.run_plots(p[0], "PT10401")))
        self.data_manager.pressure_updated.connect(lambda p: asyncio.create_task(self.nh3pump.run_plots(p[1], "PT10402")))
        self.data_manager.temperature_updated.connect(lambda t: asyncio.create_task(self.nh3pump.run_plots(t[0], "TI10401")))
        self.data_manager.temperature_updated.connect(lambda t: asyncio.create_task(self.nh3pump.run_plots(t[1], "TI10402")))
        self.data_manager.temperature_updated.connect(lambda t: asyncio.create_task(self.nh3pump.run_plots(t[2], "Heater")))
        self.data_manager.pump_feedback_updated.connect(lambda p, f: asyncio.create_task(self.nh3pump.run_plots(p, "PUMP")))
        self.data_manager.pump_feedback_updated.connect(lambda p, f: asyncio.create_task(self.nh3pump.run_plots(f, "FE01")))


async def main_async():
    app = QApplication(sys.argv)

    data_manager = SystemDataManager(history_len=100)

    pAndIdGraphicWindow = PAndIDGraphicWindow(data_manager=data_manager)

    controlWindow = PumpControlWindow(data_manager=data_manager)

    pAndIdGraphicWindow.show()
    controlWindow.show()

    while True:
        await asyncio.sleep(0.01)
        app.processEvents()

if __name__ == "__main__":
    os.environ["QT_OPENGL"] = "software"
    print(f"QT_OPENGL set to: {os.environ.get('QT_OPENGL')}")

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    asyncio.run(main_async())