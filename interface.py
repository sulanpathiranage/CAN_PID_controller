import sys
import can
import time 
import asyncio
from typing import List
from can_open_protocol import CanOpen
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox, 
    QFormLayout, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from collections import deque
import csv
from datetime import datetime
from pid_controller import PIDController
import pyqtgraph as pg

history_len = 100
ch_data = [deque([0.0] * history_len, maxlen=history_len) for _ in range(3)]

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
        self.plot_area = QVBoxLayout()
        self.label_area = QVBoxLayout()

        self.pressure_names = ["PT1401", "PT1402", "PT1403"]
        self.temperature_names = ["T01", "T02"]
        self.last_temps = [None, None]

        self.pressure_curves = []
        self.temperature_curves = []

        # Plot pressure graphs
        for i, name in enumerate(self.pressure_names):
            pw = pg.PlotWidget(title=name)
            pw.setLabel('left', "Pressure", units='psi')
            pw.setLabel('bottom', "Time", units='s')
            pw.setYRange(0, 150 if i == 0 else 300)
            pw.setXRange(0, 10)
            pw.showGrid(x=True, y=True)
            pw.getAxis("bottom").setTickSpacing(1, 0.5)
            pw.getAxis("left").setStyle(tickFont=pg.Qt.QtGui.QFont("Arial", 10))
            curve = pw.plot(pen=pg.mkPen('b', width=2))
            self.pressure_curves.append(curve)
            self.plot_area.addWidget(pw)

        # Plot temperature graph
        temp_widget = pg.PlotWidget(title="Temperatures")
        temp_widget.setLabel('left', "Temperature", units='°C')
        temp_widget.setLabel('bottom', "Time", units='s')
        temp_widget.setYRange(0, 150)
        temp_widget.setXRange(0, 10)
        temp_widget.showGrid(x=True, y=True)
        temp_widget.getAxis("left").setStyle(tickFont=pg.Qt.QtGui.QFont("Arial", 10))

        # Add legend to differentiate curves
        legend = temp_widget.addLegend()

        # Create curves for T01 and T02 with different colors
        curve1 = temp_widget.plot(pen=pg.mkPen('r', width=2), name="T01")
        curve2 = temp_widget.plot(pen=pg.mkPen('g', width=2), name="T02")

        # Store curves for later updates
        self.temperature_curves = [curve1, curve2]

        # Add single widget to layout
        self.plot_area.addWidget(temp_widget)



        self.layout.addLayout(self.plot_area, 5)

    def update_plot(self):
        time_axis = [i * 0.1 for i in range(history_len)]  # Last 10 seconds
        for i in range(3):
            self.pressure_curves[i].setData(time_axis, list(ch_data[i]))
        if hasattr(self, 'temperature_data'):
            for i in range(2):
                self.temperature_curves[i].setData(time_axis, list(self.temperature_data[i]))

        if self.last_temps and None not in self.last_temps:
            self.temp_readout.setText(
                f"<b>T01:</b> {self.last_temps[0]:.1f} °C<br><b>T02:</b> {self.last_temps[1]:.1f} °C"
            )



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
        self.plot_canvas = PyqtgraphPlotWidget()
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
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)

        asyncio.create_task(self.consumer_task())
        asyncio.create_task(self.pump_sender_task())
        
        self.last_pressures = [0.0, 0.0, 0.0]
        self.last_temps = [0.0, 0.0]

    def toggle_can_connection(self):
        if not self.can_connected:
            try:
                self.bus = can.interface.Bus(channel="PCAN_USBBUS1", interface="pcan", bitrate=500000)
                CanOpen.start_listener(self.bus, resolution=16, queue=self.queue)
                asyncio.create_task(self.pump_sender_task())
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
            node_id, data_type, values = await self.queue.get()
            timestamp = datetime.now().isoformat()

            if data_type == 'voltage':
                scaled_pressures = [
                    values[0] * 30.0,
                    values[1] * 60.0,
                    values[2] * 60.0
                ]
                for i in range(3):
                    ch_data[i].append(scaled_pressures[i])
                self.last_pressures = scaled_pressures
                self.sensor_display.update_pressures(scaled_pressures)

            elif data_type == 'temperature':
                if node_id == 0x182:
                    self.plot_canvas.last_temps = values[:2]
                    self.plot_canvas.temperature_data = [
                        deque([values[0]] * history_len, maxlen=history_len),
                        deque([values[1]] * history_len, maxlen=history_len)
                    ]
            
            elif data_type == '4-20mA':
                self.sensor_display.update_feedback(values[0], values[1])


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
                await CanOpen.send_can_message(self.bus, 0x600, data)

            if self.logging:
                timestamp = datetime.now().isoformat()
                rpm = speed * 17.2
                self.csv_writer.writerow([
                    timestamp,
                    *self.last_pressures,
                    *self.last_temps,
                    pump_on,
                    speed,
                    rpm
                ])
                self.log_file.flush()

            await asyncio.sleep(0.05)

    def update_plot(self):
        self.plot_canvas.update_plot()
        
    def closeEvent(self, event):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        event.accept()




async def main_async():
    queue = asyncio.Queue()

    app = QApplication(sys.argv)
    window = MainWindow(bus=None, queue=queue)  # Don't pass the bus initially
    window.show()

    asyncio.create_task(window.consumer_task())

    while True:
        await asyncio.sleep(0.01)
        app.processEvents()


if __name__ == "__main__":
    asyncio.run(main_async())