import sys
import can
import time
import asyncio
from typing import List
from can_open_protocol import CanOpen, CanData
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QFormLayout, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtGui import QFont
from collections import deque
import csv
from datetime import datetime
from pid_controller import PIDController
import pyqtgraph as pg

from pglive.kwargs import Axis
from pglive.sources.live_plot_widget import LivePlotWidget
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_axis_range import LiveAxisRange


history_len = 300  # example buffer length

class PumpControlWidget(QWidget):
    def __init__(self):
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
        self.output_label.setStyleSheet("font-size: 14px; color: #2e8b57;")

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
        layout.addStretch(1)

        self.setLayout(layout)

    def update_entry(self, val):
        self.speed_entry.setText(str(val))

    def update_slider(self):
        try:
            val = int(self.speed_entry.text())
            if 0 <= val <= 100:
                self.speed_slider.setValue(val)
        except ValueError:
            pass

    def get_state(self):
        return int(self.pump_on_checkbox.isChecked()), self.speed_slider.value()

class PyqtgraphPlotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)

        plot_layout = QVBoxLayout()

        # Initialize data storage attributes for plotting
        self.pressure_data_buffers = [deque([0.0]*history_len, maxlen=history_len) for _ in range(3)]
        self.temperature_data_buffers = [deque([0.0]*history_len, maxlen=history_len) for _ in range(2)]
        # Store data connectors to push data later
        self.pressure_connectors = []
        self.temperature_connectors = []


        # Pressure plots - one per sensor
        self.pressure_plots = []
        for i, title in enumerate(["PT1401", "PT1402", "PT1403"]):
            widget = LivePlotWidget(
                title=title,
                x_range_controller=LiveAxisRange(roll_on_tick=30),
                y_range_controller=LiveAxisRange(fixed_range=[0, 100])  # adjust range as needed
            )
            plot = LiveLinePlot(pen='g')
            widget.addItem(plot)
            plot_layout.addWidget(widget)
            self.pressure_plots.append(widget)

            # DataConnector manages the data feeding
            connector = DataConnector(plot, max_points=history_len, update_rate=30)
            self.pressure_connectors.append(connector)

        # Temperature combined plot (two curves)
        temp_widget = LivePlotWidget(
            title="Temperatures",
            x_range_controller=LiveAxisRange(roll_on_tick=30),
            y_range_controller=LiveAxisRange(fixed_range=[-20, 120])  # example range for temp
        )
        temp_curve1 = LiveLinePlot(pen='r')
        temp_curve2 = LiveLinePlot(pen='g')
        temp_widget.addItem(temp_curve1)
        temp_widget.addItem(temp_curve2)
        plot_layout.addWidget(temp_widget)

        self.temperature_connectors = [
            DataConnector(temp_curve1, max_points=history_len, update_rate=30),
            DataConnector(temp_curve2, max_points=history_len, update_rate=30),
        ]

        self.layout.addLayout(plot_layout)

    def update_plot(self):
        # This method is called by a QTimer to update the plots.
        # It takes the latest value from the internal data buffers and pushes it to the connectors.

        # Append new pressure data points
        for i, connector in enumerate(self.pressure_connectors):
            if i < len(self.pressure_data_buffers):
                connector.cb_append_data_point(self.pressure_data_buffers[i][-1]) # Use cb_append_data_point for single point

        # Append new temperature data points if available
        for i, connector in enumerate(self.temperature_connectors):
            if i < len(self.temperature_data_buffers):
                connector.cb_append_data_point(self.temperature_data_buffers[i][-1]) # Use cb_append_data_point for single point

class SensorDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
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
        pressure_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(pressure_title)

        # Pressure labels
        for name in ["PT1401", "PT1402", "PT1403"]:
            label = QLabel(f"{name}: -- psi")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet("font-size: 14px;")
            self.pressure_labels.append(label)
            layout.addWidget(label)

        layout.addSpacing(10)  # Spacer between sections

        # Temperature section title
        temp_title = QLabel("Temperature Sensors")
        temp_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(temp_title)

        # Temperature labels
        for name in ["T01", "T02"]:
            label = QLabel(f"{name}: -- °C")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet("font-size: 14px;")
            self.temperature_labels.append(label)
            layout.addWidget(label)

        layout.addStretch()
        self.setLayout(layout)

    def update_feedback(self, pump_feedback, flow_rate):
        self.pump_feedback_label.setText(f"Pump Feedback: {pump_feedback:.1f} %")
        self.flow_feedback_label.setText(f"Flow Rate: {flow_rate:.1f} L/min")


    def update_pressures(self, pressures):
        for i, pressure in enumerate(pressures):
            self.pressure_labels[i].setText(f"PT140{i+1:02d}: {pressure:.1f} psi")

    def update_temperatures(self, temperatures):
        for i, temp in enumerate(temperatures):
            self.temperature_labels[i].setText(f"T0{i+1}: {temp:.1f} °C")


class PIDControlWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.pid_enabled = False
        self.controller = PIDController()

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.output_label = QLabel("PID Output: -- %")
        self.output_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(QLabel("PID Controller"))

        layout.addWidget(self.output_label)

        self.kp_input = QDoubleSpinBox(); self.kp_input.setValue(1.0)
        self.ki_input = QDoubleSpinBox(); self.ki_input.setValue(0.0)
        self.kd_input = QDoubleSpinBox(); self.kd_input.setValue(0.0)
        self.setpoint_input = QDoubleSpinBox(); self.setpoint_input.setValue(100.0)

        for spinbox in [self.kp_input, self.ki_input, self.kd_input, self.setpoint_input]:
            spinbox.setRange(0, 1000); spinbox.setDecimals(2)

        layout.addWidget(QLabel("Kp")); layout.addWidget(self.kp_input)
        layout.addWidget(QLabel("Ki")); layout.addWidget(self.ki_input)
        layout.addWidget(QLabel("Kd")); layout.addWidget(self.kd_input)
        layout.addWidget(QLabel("Setpoint")); layout.addWidget(self.setpoint_input)

        self.toggle_button = QPushButton("Enable PID")
        self.toggle_button.setStyleSheet("""
            background-color: #007ACC;
            color: white;
            font-weight: bold;
            border-radius: 5px;
        """)
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_pid)
        layout.addWidget(self.toggle_button)

    def toggle_pid(self):
        self.pid_enabled = self.toggle_button.isChecked()
        self.toggle_button.setText("Disable PID" if self.pid_enabled else "Enable PID")
        self.controller.reset()

    def update_pid_params(self):
        kp = self.kp_input.value()
        ki = self.ki_input.value()
        kd = self.kd_input.value()
        setpoint = self.setpoint_input.value()
        self.controller.set_params(kp, ki, kd)
        self.controller.set_setpoint(setpoint)

    def compute_output(self, measured_value):
        self.update_pid_params()
        if self.pid_enabled:
            output = self.controller.calculate(measured_value)
            self.output_label.setText(f"PID Output: {output:.1f} %")
            return output
        else:
            self.output_label.setText("PID Output: -- %")
            return None


class MainWindow(QWidget):
    def __init__(self, bus, queue):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI';
                font-size: 12pt;
            }
            QGroupBox {
                border: 1px solid #aaa;
                border-radius: 6px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ccc;
            }
            QLineEdit, QLabel {
                padding: 2px;
            }
            """)

        self.setWindowTitle("Instrumentation Dashboard")
        self.setMinimumSize(1200, 800)
        self.bus = bus
        self.queue = queue

        self.pump_control = PumpControlWidget()
        self.plot_canvas = PyqtgraphPlotWidget() # This is the instance where data buffers live
        self.sensor_display = SensorDisplayWidget()
        self.pid_control = PIDControlWidget()

        # Logging control
        self.logging = False
        self.log_file = None
        self.csv_writer = None
        self.can_connected = False


        self.log_filename_entry = QLineEdit()
        self.log_filename_entry.setPlaceholderText("Enter log filename...")
        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)


        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("Log File:"))
        log_layout.addWidget(self.log_filename_entry)
        log_layout.addWidget(self.log_button)
        log_widget = QWidget()
        log_widget.setLayout(log_layout)

        # Layout setup
        layout = QHBoxLayout()
        side_panel = QVBoxLayout()
        side_panel.addWidget(self.pump_control)
        side_panel.addWidget(self.sensor_display)
        side_panel.addWidget(log_widget)
        side_panel.addWidget(self.pid_control)

        layout.addLayout(side_panel, 1)
        layout.addWidget(self.plot_canvas, 3)
        self.status_bar = QLabel("Status: Idle")
        layout.addWidget(self.status_bar, alignment=Qt.AlignmentFlag.AlignBottom)
        self.setLayout(layout)

        self.bus = None
        self.connect_button = QPushButton("Connect CAN")
        self.connect_button.clicked.connect(self.toggle_can_connection)
        side_panel.addWidget(self.connect_button)


        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_ui) # Renamed to avoid confusion
        self.timer.start(100) # Update plot UI every 100ms

        # These tasks are started in main_async, no need to start here again
        # asyncio.create_task(self.consumer_task())
        # asyncio.create_task(self.pump_sender_task())

        self.last_pressures = [0.0, 0.0, 0.0]
        self.last_temps = [0.0, 0.0]

    def toggle_can_connection(self):
        if not self.can_connected:
            try:
                self.bus = can.interface.Bus(channel="PCAN_USBBUS1", interface="pcan", bitrate=500000)
                CanOpen.start_listener(self.bus, resolution=16, queue=self.queue)
                # Ensure pump_sender_task is running only if connected
                # asyncio.create_task(self.pump_sender_task()) # This will be started once in main_async
                self.status_bar.setText("Status: CAN Connected")
                self.connect_button.setText("Disconnect CAN")
                self.can_connected = True
            except Exception as e:
                QMessageBox.critical(self, "CAN Error", f"Failed to connect to CAN: {e}")
                self.status_bar.setText("Status: CAN Connection Failed")
        else:
            try:
                if self.bus:
                    self.bus.shutdown()
                self.bus = None
                self.can_connected = False
                self.connect_button.setText("Connect CAN")
                self.status_bar.setText("Status: CAN Disconnected")
            except Exception as e:
                QMessageBox.warning(self, "Disconnect Error", f"Error during CAN disconnection: {e}")

    def toggle_logging(self):
        if not self.logging:
            filename = self.log_filename_entry.text().strip()
            if not filename:
                QMessageBox.warning(self, "Missing Filename", "Please enter a log filename.")
                return

            if not filename.endswith(".csv"):
                filename += ".csv"

            try:
                self.log_file = open(filename, 'w', newline='')
                self.csv_writer = csv.writer(self.log_file)
                self.csv_writer.writerow([
                    "Timestamp", "PT1401 (psi)", "PT1402 (psi)", "PT1403 (psi)",
                    "T01 (°C)", "T02 (°C)", "Pump On", "Pump Speed (%)", "Pump Speed (RPM)"
                ])
                self.logging = True
                self.log_button.setText("Stop Logging")
                self.log_filename_entry.setEnabled(False)
                print(f"Logging started: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
        else:
            # Stop logging
            self.logging = False
            if self.log_file:
                self.log_file.close()
                self.log_file = None
            self.csv_writer = None
            self.log_button.setText("Start Logging")
            self.log_filename_entry.setEnabled(True)
            print("Logging stopped.")


    async def consumer_task(self):
        while True:
            data: CanData = await self.queue.get()
            timestamp = datetime.now().isoformat()

            if data.voltage is not None:
                scaled_pressures = [
                    data.voltage[0] * 30.0,
                    data.voltage[1] * 60.0,
                    data.voltage[2] * 60.0
                ]
                # Append to the deque buffers in plot_canvas directly
                for i in range(len(scaled_pressures)):
                    self.plot_canvas.pressure_data_buffers[i].append(scaled_pressures[i])

                self.last_pressures = scaled_pressures
                self.sensor_display.update_pressures(scaled_pressures)

            elif data.temperature is not None:
                if data.node_id == 0x182:
                    # Append to the deque buffers in plot_canvas directly
                    if len(data.temperature) >= 2: # Ensure enough temperature data
                        self.plot_canvas.temperature_data_buffers[0].append(data.temperature[0])
                        self.plot_canvas.temperature_data_buffers[1].append(data.temperature[1])
                        self.last_temps = data.temperature[:2]
                        self.sensor_display.update_temperatures(data.temperature[:2])

            elif data.current_4_20mA is not None:
                self.sensor_display.update_feedback(data.current_4_20mA[0], data.current_4_20mA[1])

            self.queue.task_done()


    async def pump_sender_task(self):
        while True:
            pump_on, manual_speed = self.pump_control.get_state()
            measured_pressure = self.last_pressures[0] if hasattr(self, 'last_pressures') else 0.0
            pid_speed = self.pid_control.compute_output(measured_pressure)
            speed = pid_speed if pid_speed is not None else manual_speed

            raw1, raw2 = CanOpen.generate_outmm_msg(pump_on, speed)
            data = CanOpen.generate_uint_16bit_msg(int(raw1), int(raw2), 0, 0)

            if self.can_connected and self.bus:
                try:
                    await CanOpen.send_can_message(self.bus, 0x600, data)
                except Exception as e:
                    self.status_bar.setText(f"CAN Send Error: {str(e)}")

            if self.logging:
                timestamp = datetime.now().isoformat()
                rpm = speed * 17.2 # Assuming a conversion factor
                self.csv_writer.writerow([
                    timestamp,
                    *self.last_pressures,
                    *self.last_temps,
                    pump_on,
                    speed,
                    rpm
                ])
                self.log_file.flush() # Ensure data is written to disk

            await asyncio.sleep(0.05) # Send pump commands at 20Hz

    def update_plot_ui(self): # Renamed this method
        self.plot_canvas.update_plot()

    def closeEvent(self, event):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        if self.can_connected and self.bus:
            self.bus.shutdown() # Ensure CAN bus is shut down
        event.accept()


async def main_async():
    queue = asyncio.Queue()

    app = QApplication(sys.argv)
    window = MainWindow(bus=None, queue=queue)
    window.show()

    # Start the async tasks
    asyncio.create_task(window.consumer_task())
    asyncio.create_task(window.pump_sender_task())

    # This loop keeps the Qt event loop and asyncio event loop running
    while True:
        await asyncio.sleep(0.01) # Small sleep to yield to other asyncio tasks
        app.processEvents() # Process Qt events

if __name__ == "__main__":
    asyncio.run(main_async())