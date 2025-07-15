import os
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"

import sys
import asyncio
from typing import List, Dict, Any, Union, Tuple

from pglive.sources.live_plot_widget import LivePlotWidget
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_axis_range import LiveAxisRange
from pglive.sources.data_connector import DataConnector
from pyqtgraph.graphicsItems.LegendItem import LegendItem


# PySide6 Imports
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal as pyqtSignal
from PySide6.QtGui import QFont, QPen, QBrush, QColor

# Local imports
from pid_controller import PIDController
from app_stylesheets import Stylesheets
from NH3_pump_control import NH3PumpControlScene
from NH3_vaporizer_control import NH3VaporizerControlScene
from data_manager import SystemDataManager



class CustomLiveAxisRange(LiveAxisRange):
    def __init__(self, historylen):
        super().__init__(roll_on_tick=historylen)
        self.historylen = historylen
        self.tick_duration = 0.1  # 1 tick = 0.1 seconds

    def update_range(self, num_points):
        """
        Called internally by pglive to update the x-axis range.
        Override this method to customize x-axis rolling behavior.
        """
        window_seconds = self.historylen * self.tick_duration

        if num_points < self.historylen:
            x_min = 0
            x_max = num_points * self.tick_duration
        else:
            x_max = num_points * self.tick_duration
            x_min = x_max - window_seconds

        self.set_range(x_min, x_max)

class PyqtgraphPlotWidget(QWidget):
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager
        self.layout = QHBoxLayout(self)
        plot_layout = QVBoxLayout()
        self.history_len = self.data_manager.history_len

        self.pressure_plot_elements: Dict[str, Tuple[LivePlotWidget, DataConnector, LiveLinePlot]] = {}
        self.temperature_plot_elements: Dict[str, Tuple[LivePlotWidget, DataConnector, LiveLinePlot]] = {}
        self.flow_plot_elements: Dict[str, Tuple[LivePlotWidget, DataConnector, LiveLinePlot]] = {}


        for designator in self.data_manager.pressure_sensor_names:
            widget, connector, line = self._create_single_sensor_plot(
                plot_layout, designator, Qt.green, 0, 65)
            self.pressure_plot_elements[designator] = (widget, connector, line)

        self.temp_widget = LivePlotWidget(
            title="Temperatures",
            x_range_controller=CustomLiveAxisRange(historylen=self.history_len),
            y_range_controller=LiveAxisRange(fixed_range=[0, 100])
        )
        plot_layout.addWidget(self.temp_widget)

        self.temp_legend_widget = QWidget()
        legend_layout = QHBoxLayout(self.temp_legend_widget)
        legend_layout.setSpacing(15)
        legend_layout.setContentsMargins(5, 5, 5, 5)
        plot_layout.addWidget(self.temp_legend_widget) 


        temp_colors = [Qt.red, Qt.blue, Qt.darkYellow, Qt.magenta, Qt.cyan, Qt.gray, Qt.darkGreen, Qt.darkCyan]
        # temp_symbols = ['s', 't', 'd', 'p', 'h', '+', 'x'] # Different symbols for clarity

        for i, designator in enumerate(self.data_manager.temperature_sensor_names):
            if i < len(temp_colors):
                color = temp_colors[i]
                color_q = QColor(temp_colors[i])
                line = LiveLinePlot(pen=QPen(color, 3), auto_fill_history=True)
                self.temp_widget.addItem(line)
                connector = DataConnector(line, max_points=self.history_len, update_rate=30)
                self.temperature_plot_elements[designator] = (self.temp_widget, connector, line)

                # Create legend entry (colored square + label)
                label = QLabel(f"{designator}")
                label.setStyleSheet(f"""
                    background-color: {color_q.name()};
                    border: 1px solid black;
                    padding: 4px;
                    border-radius: 3px;
                    color: white;
                    font-weight: bold;
                """)
                legend_layout.addWidget(label)
            else:
                print(f"Warning: Not enough colors for temperature sensor {designator}. Skipping plot line.")


        if self.data_manager.deditec_feedback:
            flow_name = self.data_manager.deditec_feedback[0]
            widget, connector, line = self._create_single_sensor_plot(plot_layout, flow_name, Qt.cyan, 0, 101)
            self.flow_plot_elements[flow_name] = (widget, connector, line)
            


        self.layout.addLayout(plot_layout)

        self.data_manager.pressure_updated.connect(self._on_pressure_data_updated)
        self.data_manager.temperature_updated.connect(self._on_temperature_data_updated)
        self.data_manager.pump_feedback_updated.connect(self._on_pump_feedback_updated)




    def _create_single_sensor_plot(self, layout, title, color, y_min, y_max):
        """Helper to create and add a single LivePlotWidget with one LiveLinePlot."""
        widget = LivePlotWidget(
            title=title,
            x_range_controller=CustomLiveAxisRange(historylen=self.history_len),
            y_range_controller=LiveAxisRange(fixed_range=[y_min, y_max])
        )
        pen=QPen(color, 3) 
        plot_line = LiveLinePlot(pen = pen, auto_fill_history=True)
        widget.addItem(plot_line)
        layout.addWidget(widget)
        connector = DataConnector(plot_line, max_points=self.history_len, update_rate=30)
        return widget, connector, plot_line


    def _on_pressure_data_updated(self, pressures: List[float]):
        """Updates individual pressure plots with new data."""
        for i, designator in enumerate(self.data_manager.pressure_sensor_names):
            if designator in self.pressure_plot_elements and i < len(pressures):
                _, connector, _ = self.pressure_plot_elements[designator]
                connector.cb_append_data_point(pressures[i])

    def _on_temperature_data_updated(self, temperatures: List[float]):
        """Updates the combined temperature plot with new data for each line."""
        for i, designator in enumerate(self.data_manager.temperature_sensor_names):
            if designator in self.temperature_plot_elements and i < len(temperatures):
                _, connector, _ = self.temperature_plot_elements[designator]
                connector.cb_append_data_point(temperatures[i])

    def _on_pump_feedback_updated(self, pump_percent: float, flow1_kg_per_h: float,flow2_kg_per_h: float ):
        """Updates the flow rate plot with new data."""
        if self.data_manager.flow_sensor_names:
            flow_designator = self.data_manager.flow_sensor_names[0]
            if flow_designator in self.flow_plot_elements:
                _, connector, _ = self.flow_plot_elements[flow_designator]
                connector.cb_append_data_point(pump_percent)

    def update_plot(self):
        """Forces plot updates for all widgets."""
        for widget, _, _ in self.pressure_plot_elements.values():
            widget.update()
        self.temp_widget.update() 
        for widget, _, _ in self.flow_plot_elements.values(): 
            widget.update()


class PermanentRightHandDisplay(QWidget):
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager

        layout = QVBoxLayout(self)

        self.eStopButton = QPushButton("E-STOP")
        self.eStopButton.setFixedSize(150, 100)
        self.eStopButton.setStyleSheet(Stylesheets.EStopPushButtonStyleSheet())
        self.eStopButton.clicked.connect(self.toggleEStop)
        layout.addWidget(self.eStopButton)

        self.interlockBeginButton = QCheckBox("ENABLE INTERLOCKS")
        self.interlockBeginButton.setFixedSize(150, 100)
        # self.eStopButton.setStyleSheet(Stylesheets.EStopPushButtonStyleSheet())
        self.interlockBeginButton.clicked.connect(self.toggleInterlock)
        layout.addWidget(self.interlockBeginButton)

        self._interlock_labels: list[QLabel] = []
        for idx in range(1, 5):
            lbl = QLabel(f"Interlock {idx}: OK")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(Stylesheets.LabelStyleGreen())   # green “OK”
            layout.addWidget(lbl)
            self._interlock_labels.append(lbl)


        self.esv1Button = QPushButton("ESV 10107")
        self.esv1Button.setCheckable(True)
        self.esv1Button.setFixedSize(150, 80)
        self.esv1Button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.esv1Button.toggled.connect(self.toggleESV1)
        self.esv1Button.toggled.connect(
            lambda checked: self._update_esv_caption(self.esv1Button,
                                                     "ESV‑10107", checked)
        )        
        layout.addWidget(self.esv1Button)

        self.esv2Button = QPushButton("ESV 10112")
        self.esv2Button.setCheckable(True)
        self.esv2Button.setFixedSize(150, 80)
        self.esv2Button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.esv2Button.toggled.connect(self.toggleESV2)
        self.esv2Button.toggled.connect(
            lambda checked: self._update_esv_caption(self.esv2Button,
                                                     "ESV‑10112", checked)
        )        
        layout.addWidget(self.esv2Button)

        self.data_manager.e_stop_toggled.connect(self._update_e_stop_button_text)
        self.data_manager.esv1_state_toggled.connect(self.esv1Button.setChecked)
        self.data_manager.esv2_state_toggled.connect(self.esv2Button.setChecked)

        self.data_manager.interlock1_detected.connect(
            lambda active, flags: self.on_interlock(0, active, flags))
        self.data_manager.interlock2_detected.connect(
            lambda active, flags: self.on_interlock(1, active, flags))
        self.data_manager.interlock3_detected.connect(
            lambda active, flags: self.on_interlock(2, active, flags))
        self.data_manager.interlock4_detected.connect(
            lambda active, flags: self.on_interlock(3, active, flags))

    def on_interlock(self, label_index: int, active: bool, fl: list[bool]):
        """fl = [lowWarn, lowAlarm, highWarn, highAlarm]"""
        label = self._interlock_labels[label_index]

        if not active:                       
            label.setText(f"Interlock {label_index+1}: OK")
            label.setStyleSheet(Stylesheets.LabelStyleGreen())
            return

        lw, ls, hw, hs = fl

        if ls or hs:                      
            state_txt = "LOW ALARM" if ls else "HIGH ALARM"
            label.setStyleSheet(Stylesheets.LabelStyleRed())
        else:                             # warnings only
            state_txt = "LOW WARN" if lw else "HIGH WARNING"
            label.setStyleSheet(Stylesheets.LabelStyleYellow())   

        label.setText(f"Interlock {label_index+1}: {state_txt}")

    def _update_esv_caption(self, btn: QPushButton, base: str, open_: bool):
        btn.setText(f"{base}: {'OPEN' if open_ else 'CLOSED'}")

    def toggleEStop(self):
        self.data_manager.toggle_e_stop_state()

    def toggleInterlock(self):
        self.data_manager.toggle_interlocks()

    def toggleESV1(self, checked):
        self.data_manager.set_esv1(checked)
        

    def toggleESV2(self, checked):
        self.data_manager.set_esv2(checked)

    def _update_e_stop_button_text(self, state: bool):
        text = "E-STOP ON" if state else "E-STOP OFF"
        self.eStopButton.setText(text)



class PumpControlWidget(QWidget):
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

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(0)

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
class ProcessControlWidgets(QWidget):
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager

        main_layout = QVBoxLayout(self)  # Main layout of this widget

        group = QGroupBox("Process Control", self)
        group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        layout = QGridLayout()
        group.setLayout(layout)  # Set the grid layout to the group box

        self.mfm1_slider = QDoubleSpinBox()
        self.mfm1_slider.setRange(0.0, 100.0)
        self.mfm1_slider.valueChanged.connect(lambda v: self.data_manager.set_mfm1(float(v)))
        layout.addWidget(QLabel("MFM 1 Setpoint (max 32.8 kg/h):"), 0, 0)
        layout.addWidget(self.mfm1_slider, 0, 1)

        self.mfm2_slider = QDoubleSpinBox()
        self.mfm2_slider.setRange(0.0, 100.0)
        self.mfm2_slider.valueChanged.connect(lambda v: self.data_manager.set_mfm2(float(v)))
        layout.addWidget(QLabel("MFM 2 Setpoint (max 32.8 kg/h):"), 1, 0)
        layout.addWidget(self.mfm2_slider, 1, 1)

        self.pic_slider = QDoubleSpinBox()
        self.pic_slider.setRange(0.0, 100.0)
        self.pic_slider.setDecimals(2)
        self.pic_slider.setSingleStep(0.1)
        self.pic_slider.valueChanged.connect(lambda v: self.data_manager.set_pic(float(v)))
        layout.addWidget(QLabel("PIC Setpoint ('%' of psig range):"), 2, 0)
        layout.addWidget(self.pic_slider, 2, 1)

        main_layout.addWidget(group)

        self.data_manager.mfm1_setpoint_updated.connect(self.mfm1_slider.setValue)
        self.data_manager.mfm2_setpoint_updated.connect(self.mfm2_slider.setValue)
        self.data_manager.pic_setpoint_updated.connect(self.pic_slider.setValue)
        
        self.data_manager.trigger_initial_setpoint_emits()



class SensorDisplayWidget(QWidget):
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager
        layout = QVBoxLayout(self)

        self._pump_name, self.flow1_name, self.flow2_name, self.pic_name  = data_manager.deditec_feedback

        self.pump_feedback_label = QLabel(f"{self._pump_name}: -- %")
        self.flow1_feedback_label = QLabel(f"{self.flow1_name}: -- kg/h")
        self.flow2_feedback_label = QLabel(f"{self.flow2_name}: -- kg/h")
        self.pic_feedback_label = QLabel(f"{self.pic_name}: -- psig")
        layout.addWidget(self.pump_feedback_label)
        layout.addWidget(self.flow1_feedback_label)
        layout.addWidget(self.flow2_feedback_label)
        layout.addWidget(self.pic_feedback_label)


        layout.addWidget(QLabel("Pressure Sensors", styleSheet=Stylesheets.LabelStyleSheet()))
        self.pressure_labels = []
        for name in self.data_manager.pressure_sensor_names:
            label = QLabel(f"{name}: -- psi", alignment=Qt.AlignmentFlag.AlignLeft, styleSheet=Stylesheets.LabelStyleSheet())
            self.pressure_labels.append(label)
            layout.addWidget(label)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Temperature Sensors", styleSheet=Stylesheets.LabelStyleSheet()))
        self.temperature_labels = []
        for name in self.data_manager.temperature_sensor_names:
            label = QLabel(f"{name}: -- °C", alignment=Qt.AlignmentFlag.AlignLeft, styleSheet=Stylesheets.LabelStyleSheet())
            self.temperature_labels.append(label)
            layout.addWidget(label)

        layout.addStretch()

        self.data_manager.pressure_updated.connect(self.update_pressures)
        self.data_manager.temperature_updated.connect(self.update_temperatures)
        self.data_manager.pump_feedback_updated.connect(self.update_feedback)

    def update_feedback(self, pump_percent: float, flow_rate1: float, flow_rate2:float, pressure:float):
        self.pump_feedback_label.setText(f"{self._pump_name}: {pump_percent:.1f} %")
        self.flow1_feedback_label.setText(f"{self.flow1_name}: {flow_rate1:.1f} kg/h")
        self.flow2_feedback_label.setText(f"{self.flow2_name}: {flow_rate2:.1f} kg/h")
        self.pic_feedback_label.setText(f"{self.pic_name}: {pressure:.1f} psig")



    def update_pressures(self, pressures: List[float]):
        for i, pressure in enumerate(pressures):
            if i < len(self.pressure_labels) and i < len(self.data_manager.pressure_sensor_names):
                self.pressure_labels[i].setText(f"{self.data_manager.pressure_sensor_names[i]}: {pressure:.1f} psi")

    def update_temperatures(self, temperatures: List[float]):
        for i, temp in enumerate(temperatures):
            if i < len(self.temperature_labels) and i < len(self.data_manager.temperature_sensor_names):
                self.temperature_labels[i].setText(f"{self.data_manager.temperature_sensor_names[i]}: {temp:.1f} °C")


class PIDControlWidget(QWidget):

    def __init__(self, data_manager: SystemDataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager 


        main_layout = QVBoxLayout(self)
        group = QGroupBox("PID Control", self)
        group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout = QGridLayout(group)

        self.output_label = QLabel("PID Output: -- %")
        
        self.output_label.setStyleSheet("color: #333;")
        layout.addWidget(self.output_label, 0, 0, 1, 2)
        self.toggle_button = QPushButton("Enable PID", checkable=True)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:checked {
                background-color: #DC3545; /* Red when checked/enabled */
            }
        """)

        layout.addWidget(self.toggle_button, 1, 0, 1, 2) # Span 2 columns

        self.kp_input = QDoubleSpinBox(value=1.0)
        self.ki_input = QDoubleSpinBox(value=0.0)
        self.kd_input = QDoubleSpinBox(value=0.0)
        self.setpoint_input = QDoubleSpinBox(value=0)

        spinboxes = [self.kp_input, self.ki_input, self.kd_input, self.setpoint_input]
        labels = ["Kp", "Ki", "Kd", "Flow Setpoint"] # Assuming "Flow Setpoint" directly corresponds to PID setpoint
        index = 2
        for label, spinbox in zip(labels, spinboxes):
            spinbox.setRange(0, 1000)
            spinbox.setDecimals(2)
            layout.addWidget(QLabel(label), index , 0)
            layout.addWidget(spinbox, index, 1)
            index += 1

        main_layout.addWidget(group)

        self._connect_signals()
        self._update_ui_from_data_manager_initial()

    def _connect_signals(self):
        self.kp_input.valueChanged.connect(self.data_manager.set_pid_kp)
        self.ki_input.valueChanged.connect(self.data_manager.set_pid_ki)
        self.kd_input.valueChanged.connect(self.data_manager.set_pid_kd)
        self.setpoint_input.valueChanged.connect(self.data_manager.set_pid_setpoint)

        self.data_manager.pid_output_updated.connect(self._update_output_display)
        self.data_manager.pid_enabled_status_changed.connect(self._update_toggle_button_state)
        self.data_manager.pid_setpoint_updated.connect(self.setpoint_input.setValue) # Connect to the correct setpoint signal

    def _update_output_display(self, output_value: float):
        """Updates the displayed PID output."""
        self.output_label.setText(f"PID Output: {output_value:.2f} %")

    def _update_toggle_button_state(self, enabled: bool):
        """Updates the toggle button's checked state and text based on PID enabled status."""
        self.toggle_button.setChecked(enabled)
        self.toggle_button.setText("Disable PID" if enabled else "Enable PID")

    def _update_ui_from_data_manager_initial(self):
        """
        Retrieves initial PID parameters and state from the SystemDataManager
        and sets the GUI elements accordingly.
        """
        self.kp_input.setValue(self.data_manager.pid_controller.kp)
        self.ki_input.setValue(self.data_manager.pid_controller.ki)
        self.kd_input.setValue(self.data_manager.pid_controller.kd)
        self.setpoint_input.setValue(self.data_manager._pid_setpoint) 

        self._update_toggle_button_state(self.data_manager._pid_enabled)
        self._update_output_display(self.data_manager._commanded_pid_output) 


class PumpControlWindow(QWidget):
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager
        self.setWindowTitle("Instrumentation Dashboard")
        self.setMinimumSize(1200, 900)
        self.setStyleSheet("color: white; background-color: #212121;")

        self.pump_control = PumpControlWidget()
        self.plot_canvas = PyqtgraphPlotWidget(self.data_manager)
        self.sensor_display = SensorDisplayWidget(self.data_manager)
        self.pid_control = PIDControlWidget(self.data_manager)
        self.process_control = ProcessControlWidgets(self.data_manager)
        self.permanentRightHandControl = PermanentRightHandDisplay(self.data_manager)

        self.log_filename_entry = QLineEdit(placeholderText="Enter log filename...")
        self.log_button = QPushButton("Start Logging", clicked=self._toggle_logging, styleSheet=Stylesheets.GenericPushButtonStyleSheet())

        self.connect_button = QPushButton("Connect CAN", clicked=self._toggle_can_connection, styleSheet=Stylesheets.GenericPushButtonStyleSheet())

        self.status_bar = QLabel("Status: Idle", alignment=Qt.AlignmentFlag.AlignCenter, styleSheet=Stylesheets.LabelStyleSheet(), wordWrap=True)

        main_layout = QHBoxLayout(self)

        scroll_area = QScrollArea(widgetResizable=True, horizontalScrollBarPolicy=Qt.ScrollBarPolicy.ScrollBarAlwaysOff, styleSheet=Stylesheets.GenericScrollAreaStyleSheet())
        side_panel_content = QWidget()
        scroll_area.setWidget(side_panel_content)
        side_panel_layout = QVBoxLayout(side_panel_content)
        side_panel_layout.addWidget(self.connect_button)
        log_row = QHBoxLayout(spacing=5)
        log_row.addWidget(QLabel("Log File:"))
        log_row.addWidget(self.log_filename_entry)
        side_panel_layout.addLayout(log_row)
        side_panel_layout.addWidget(self.log_button)
        side_panel_layout.addWidget(self.status_bar)
        side_panel_layout.addWidget(self.pump_control)
        side_panel_layout.addWidget(self.pid_control)
        side_panel_layout.addWidget(self.process_control)
        side_panel_layout.addWidget(self.sensor_display)




        side_panel_layout.addStretch()

        scroll_area.setFixedWidth(320)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.plot_canvas, stretch=1)
        main_layout.addWidget(self.permanentRightHandControl)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_gui_and_can_commands)
        self.timer.start(100)

        self.data_manager.start_log.connect(self._update_logging_button_state)

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
        # Determine the *next* state of logging
        is_currently_logging = self.log_button.text() == "Stop Logging" # Or check self.data_manager._logging_enabled

        if not is_currently_logging:
            filename = self.log_filename_entry.text().strip()
            self.data_manager.log_name.emit(filename)
            self.data_manager.start_log.emit(True) 
        else:
            self.data_manager.start_log.emit(False) # Tell the data manager to stop logging



    def _update_logging_button_state(self, is_logging: bool):
        """Updates the log button's text and filename entry state."""
        self.log_button.setText("Stop Logging" if is_logging else "Start Logging")
        self.log_filename_entry.setEnabled(not is_logging)
        if is_logging:
            self.log_button.setStyleSheet("""
                QPushButton {
                    background-color: #DC143C; /* Red when logging */
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #C21136; }
                QPushButton:pressed { background-color: #A70F2C; }
            """)
        else:
            self.log_button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet()) # Revert to default green


    def _update_gui_and_can_commands(self):
        self.plot_canvas.update_plot()

        pump_on, manual_speed = self.pump_control.get_state()
        pid_output_from_data_manager = self.data_manager._commanded_pid_output
        self.data_manager.update_commanded_pump_state(pump_on, manual_speed, pid_output_from_data_manager)

        

    def closeEvent(self, event):
        self.data_manager.close_can_connection()
        event.accept()


class PAndIDGraphicWindow(QWidget):
    def __init__(self, data_manager: SystemDataManager):
        super().__init__()
        self.data_manager = data_manager

        self.setWindowTitle("P&ID Schematics")
        self.setMinimumSize(800, 800)
        self.setStyleSheet("color: white; background-color: #212121;")

        tabWindowLayout = QVBoxLayout(self)
        self.nh3pump = NH3PumpControlScene(self.data_manager)
        # self.nh3vaporizer = NH3VaporizerControlScene()

        self.tab_widget = QTabWidget(styleSheet=Stylesheets.TabWidgetStyleSheet())

        nh3_pump_test_tab = QWidget(styleSheet="background-color: #2e2e2e;")
        nh3_vaporizer_test_tab = QWidget(styleSheet="background-color: #2e2e2e;")

        QVBoxLayout(nh3_pump_test_tab).addWidget(self.nh3pump)
        # QVBoxLayout(nh3_vaporizer_test_tab).addWidget(self.nh3vaporizer)

        self.tab_widget.addTab(nh3_pump_test_tab, "NH3 PUMP TEST-1")
        tabWindowLayout.addWidget(self.tab_widget)


        



async def main_async():

    app = QApplication(sys.argv)
    data_manager = SystemDataManager(history_len=6000)
    pAndIdGraphicWindow = PAndIDGraphicWindow(data_manager=data_manager)
    controlWindow = PumpControlWindow(data_manager=data_manager)

    pAndIdGraphicWindow.show()
    controlWindow.show()

    while True:
        await asyncio.sleep(0.01)
        app.processEvents()

if __name__ == "__main__":
    # os.environ["QT_OPENGL"] = "software"
    # print(f"QT_OPENGL set to: {os.environ.get('QT_OPENGL')}")

    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    asyncio.run(main_async())