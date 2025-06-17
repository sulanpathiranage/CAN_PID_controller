import os
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"  # Force pyqtgraph to use PyQt6

import sys
import asyncio
import csv
from datetime import datetime
from collections import deque

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
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Local imports
from pid_controller import PIDController
from app_stylesheets import Stylesheets
from NH3_pump_control import NH3PumpControlScene
from NH3_vaporizer_control import NH3VaporizerControlScene
from can_open_protocol import CanOpen

history_len = 100
ch_data = [deque([0.0] * history_len, maxlen=history_len) for _ in range(3)]
temp_data  =  [deque([0.0] * history_len, maxlen=history_len) for _ in range(3)]

eStopValue = False 

testingFlag = False 

class PermanentRightHandDisplay(QWidget):
    def __init__(self):
        super().__init__()

        #Create Layout
        rightHandVerticalLayout = QVBoxLayout()

        #Create Contents
        self.eStopButton = QPushButton("E-STOP")
        self.eStopButton.setFixedSize(150, 100)
        self.eStopButton.setStyleSheet(Stylesheets.EStopPushButtonStyleSheet())
        self.eStopButton.clicked.connect(self.toggleEStop)

        # self.safetyLabelOne = QLabel("Safety Critical Info Label 1")
        # self.safetyLabelTwo = QLabel("Safety Critical Info Label 2")
        # self.safetyLabelThree = QLabel("Safety Critical Info Label 3")
        
        # self.safetyControlPushButtonOne = QPushButton("Safety Control One")
        # self.safetyControlPushButtonOne.setFixedSize(150, 80)
        # self.safetyControlPushButtonOne.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        # self.safetyControlPushButtonTwo = QPushButton("Safety Control Two")
        # self.safetyControlPushButtonTwo.setFixedSize(150, 80)
        # self.safetyControlPushButtonTwo.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        #Put contents in layout
        # rightHandVerticalLayout.addWidget(self.safetyLabelOne)
        # rightHandVerticalLayout.addWidget(self.safetyLabelTwo)
        # rightHandVerticalLayout.addWidget(self.safetyLabelThree)
        # rightHandVerticalLayout.addWidget(self.safetyControlPushButtonOne)
        # rightHandVerticalLayout.addWidget(self.safetyControlPushButtonTwo)
        rightHandVerticalLayout.addWidget(self.eStopButton)

        #Set self "PermanentRightHandDisplay" widget layout
        self.setLayout(rightHandVerticalLayout)

    def toggleEStop(self):
        global eStopValue
        if not (eStopValue):
            eStopValue = True
            self.eStopButton.setText("E-STOP\nACTIVE")
        else :
            eStopValue = False
            self.eStopButton.setText("E-STOP")

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
        #self.output_label.setStyleSheet(Stylesheets.LabelStyleSheet())

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
        self.temperature_names = ["T01", "T02", "Heater"]
        self.last_temps = [None, None, None]

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
        # legend = temp_widget.addLegend()

        # Create curves for T01 and T02 with different colors
        curve1 = temp_widget.plot(pen=pg.mkPen('r', width=2), name="T01")
        curve2 = temp_widget.plot(pen=pg.mkPen('g', width=2), name="T02")
        curve3 = temp_widget.plot(pen=pg.mkPen('b', width=2), name="Heater")

        # Store curves for later updates
        self.temperature_curves = [curve1, curve2, curve3]

        # Add single widget to layout
        self.plot_area.addWidget(temp_widget)
        self.layout.addLayout(self.plot_area, 5)

    def update_plot(self):
        time_axis = [i * 0.1 for i in range(history_len)]  # Last 10 seconds
        for i in range(3):
            self.pressure_curves[i].setData(time_axis, list(ch_data[i]))
        #if hasattr(self, 'temp_data'):
        for i in range(3):
            self.temperature_curves[i].setData(time_axis, list(temp_data[i]))


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
        pressure_title.setStyleSheet(Stylesheets.LabelStyleSheet())
        layout.addWidget(pressure_title)

        # Pressure labels
        for name in ["PT1401", "PT1402", "PT1403"]:
            label = QLabel(f"{name}: -- psi")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet(Stylesheets.LabelStlyeSheet())
            self.pressure_labels.append(label)
            layout.addWidget(label)

        layout.addSpacing(10)  # Spacer between sections

        # Temperature section title
        temp_title = QLabel("Temperature Sensors")
        temp_title.setStyleSheet(Stylesheets.LabelStlyeSheet())
        layout.addWidget(temp_title)

        # Temperature labels
        for name in ["T01", "T02", "Heater"]:
            label = QLabel(f"{name}: -- °C")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet(Stylesheets.LabelStlyeSheet())
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
        self.output_label.setStyleSheet(Stylesheets.LabelStlyeSheet())
        self.pid_label = QLabel("PID Controller")
        self.pid_label.setStyleSheet(Stylesheets.LabelStlyeSheet())
        layout.addWidget(self.pid_label)
                
        layout.addWidget(self.output_label)

        self.kp_input = QDoubleSpinBox()
        self.kp_input.setValue(1.0)
        self.ki_input = QDoubleSpinBox()
        self.ki_input.setValue(0.0)
        self.kd_input = QDoubleSpinBox()
        self.kd_input.setValue(0.0)
        self.setpoint_input = QDoubleSpinBox()
        self.setpoint_input.setValue(100.0)

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

class PumpControlWindow(QWidget):

    def __init__(self, nh3_pump_pAndId, bus, queue_List):
        super().__init__()

        self.setWindowTitle("Instrumentation Dashboard")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("color: white; background-color: #212121;")

        self.pump_control = PumpControlWidget()
        self.plot_canvas = PyqtgraphPlotWidget()
        self.sensor_display = SensorDisplayWidget()
        self.pid_control = PIDControlWidget()
        self.permanentRightHandControl = PermanentRightHandDisplay()

        self.update_plot_function = nh3_pump_pAndId

        # Logging control
        self.bus = bus
        self.queue_List = queue_List
        self.can_connected = False
        self.logging = False
        self.log_file = None
        self.csv_writer = None
        self.last_pressures = [0.0, 0.0, 0.0]
        self.last_temps = [0.0, 0.0, 0.0]
        self.last_pump_feedback = 0.0
        self.last_flow_rate = 0.0

        self.log_filename_entry = QLineEdit()
        self.log_filename_entry.setPlaceholderText("Enter log filename...")

        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        self.log_button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        self.connect_button = QPushButton("Connect CAN")
        self.connect_button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.connect_button.clicked.connect(self.toggle_can_connection)

        self.status_bar = QLabel("Status: Idle")
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_bar.setStyleSheet(Stylesheets.LabelStlyeSheet())

        main_layout = QHBoxLayout()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(Stylesheets.GenericScrollAreaStyleSheet())

        side_panel_content = QWidget()
        scroll_area.setWidget(side_panel_content)

        side_panel_layout = QVBoxLayout(side_panel_content)
        side_panel_layout.setContentsMargins(10, 10, 10, 10)

        side_panel_layout.addWidget(self.pump_control)
        side_panel_layout.addWidget(self.sensor_display)

        log_label = QLabel("Log File:")
        log_row = QHBoxLayout()
        log_row.setSpacing(5)
        log_row.addWidget(log_label)
        log_row.addWidget(self.log_filename_entry)
        log_row_widget = QWidget()
        log_row_widget.setLayout(log_row)

        side_panel_layout.addWidget(log_row_widget)
        side_panel_layout.addWidget(self.log_button)

        # Rebuild PID control layout to display Kp Ki Kd horizontally
        pid_label = QLabel("PID Controller")
        pid_label.setStyleSheet("font-weight: bold")
        pid_output_label = QLabel("PID Output: -- %")
        pid_output_label.setStyleSheet("font-size: 14px;")

        kp = QDoubleSpinBox()
        kp.setValue(1.0)
        ki = QDoubleSpinBox()
        ki.setValue(0.0)
        kd = QDoubleSpinBox()
        kd.setValue(0.0)
        setpoint = QDoubleSpinBox()
        setpoint.setValue(100.0)

        for box in [kp, ki, kd, setpoint]:
            box.setRange(0, 1000)
            box.setDecimals(2)

        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("Kp"))
        label_row.addWidget(QLabel("Ki"))
        label_row.addWidget(QLabel("Kd"))

        input_row = QHBoxLayout()
        input_row.addWidget(kp)
        input_row.addWidget(ki)
        input_row.addWidget(kd)

        setpoint_label = QLabel("Setpoint")

        enable_button = QPushButton("Enable PID")
        enable_button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        pid_group = QVBoxLayout()
        pid_group.addWidget(pid_label)
        pid_group.addWidget(pid_output_label)
        pid_group.addLayout(label_row)
        pid_group.addLayout(input_row)
        pid_group.addWidget(setpoint_label)
        pid_group.addWidget(setpoint)
        pid_group.addWidget(enable_button)

        pid_container = QWidget()
        pid_container.setLayout(pid_group)

        side_panel_layout.addWidget(pid_container)
        side_panel_layout.addWidget(self.connect_button)
        side_panel_layout.addWidget(self.status_bar)
        side_panel_layout.addStretch()

        scroll_area.setFixedWidth(320)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.plot_canvas, stretch=1)

        self.superLayout = QHBoxLayout()
        self.superLayout.addLayout(main_layout)
        self.superLayout.addWidget(self.permanentRightHandControl)

        self.setLayout(self.superLayout)

        #Timer stuff
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)

        asyncio.create_task(self.consumer_task())
        asyncio.create_task(self.producer_task())


    def toggle_can_connection(self):
        if not self.can_connected:
            try:
                self.bus = can.interface.Bus(channel="PCAN_USBBUS1", interface="pcan", bitrate=500000)
                CanOpen.start_listener(self.bus, resolution=16, queue_List=self.queue_List)
                asyncio.create_task(self.producer_task())

                self.status_bar.setText("Status: CAN Connected")
                self.status_bar.setStyleSheet("""
                    background-color: #228B22;
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
                    self.bus.shutdown()
                self.bus = None
                self.can_connected = False
                self.connect_button.setText("Connect CAN")
                self.status_bar.setText("Status: Idle")
                self.status_bar.setStyleSheet("""
                    background-color: #333;
                    color: white;
                    padding: 4px;
                    border-radius: 5px;
                """)
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
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
        else:
            self.logging = False
            if self.log_file:
                self.log_file.close()
                self.log_file = None
            self.csv_writer = None
            self.log_button.setText("Start Logging")
            self.log_filename_entry.setEnabled(True)

    async def consumer_task(self):


        # Create log file, hard code name for now
        # self.consumer_task_logging_toggle = True

        # if self.consumer_task_logging_toggle == True :
        #     try:
        #         self.consumer_log = open("Consumer_task_log.csv", 'w', newline='')
        #         self.consumer_csv_writer = csv.writer(self.consumer_log)
        #         self.consumer_csv_writer.writerow([
        #             "Timestamp", "PT1401 (psi)", "PT1402 (psi)", "PT1403 (psi)",
        #             "T01 (°C)", "T02 (°C)", "Pump Feedback", "Flow Rate"
        #         ])
        #     except Exception as e:
        #             QMessageBox.critical(self, "Error", f"Cannot open consumer task log file: {e}")
        #             self.consumer_task_logging_toggle = False # Disable logging if file cannot be created
        # else :
        #     print("No Consumer Task Log")

        while True:
            #print("Consumer!")

            await asyncio.sleep(0.2) # poll rate of 300 ms

            node_id_volt, data_type_volt, values_volt = await self.queue_List[0].get()
            node_id_temp, data_type_temp, values_temp = await self.queue_List[1].get()
            node_id_current, data_type_current, values_current = await self.queue_List[2].get()

            #print(node_id, data_type, values)

            # Moving the logging to the consumer task to log incoming data

            # # Testing plots with random data
            # testDataVal = random.uniform(5,10)
            # await self.update_plot_function(testDataVal, "TI10401")

            # testDataVal = random.uniform(5,10)
            # await self.update_plot_function(testDataVal, "TI10402")
            
            # testDataVal = random.uniform(5,10)
            # await self.update_plot_function(testDataVal, "PT10401")

            # testDataVal = random.uniform(5,10)
            # await self.update_plot_function(testDataVal, "PT10402")

            # testDataVal = random.uniform(5,10)
            # await self.update_plot_function(testDataVal, "PUMP_SPEED")

            # testDataVal = random.uniform(5,10)
            # await self.update_plot_function(testDataVal, "FE01")

            # Fix these functions at some point since data is already organized
            if data_type_volt == 'voltage':
                scaled_pressures = [values_volt[0] * 30.0, values_volt[1] * 60.0, values_volt[2] * 60.0]
                for i in range(3):
                    ch_data[i].append(scaled_pressures[i])
                self.last_pressures = scaled_pressures
                self.sensor_display.update_pressures(scaled_pressures)

                # Update plot with values (decide here which schematic is being used based on active schematic check box)
                await self.update_plot_function(values_volt[0], "PT10401")
                await self.update_plot_function(values_volt[1], "PT10402")

            if data_type_temp == 'temperature':
                if node_id_temp == 0x182:
                    self.plot_canvas.last_temps = values_temp[:3]
                    for i in range(3):
                        temp_data[i].append(values_temp[i])
                    self.sensor_display.update_temperatures(values_temp[:3])
                    self.last_temps = values_temp[:3]
                    print("Updating temperature")
                    # Update plot with values (decide here which schematic is being used based on active schematic check box)
                    await self.update_plot_function(values_temp[0], "TI10401")
                    await self.update_plot_function(values_temp[1], "TI10402")
                    await self.update_plot_function(values_temp[2], "Heater")
                    
            
            if data_type_current == '4-20mA':
                self.last_pump_feedback = values_current["pump_percent"]
                self.last_flow_rate = values_current["flow_kg_per_h"]
                print(f"Processing 4-20mA data: Node ID={node_id_current}, Data={values_current}")
                self.sensor_display.update_feedback(values_current["pump_percent"], values_current["flow_kg_per_h"])

                # Update plot with values (decide here which schematic is being used based on active schematic check box)
                await self.update_plot_function(values_current["pump_percent"], "PUMP")
                await self.update_plot_function(values_current["flow_kg_per_h"], "FE01")

            # if self.consumer_task_logging_toggle == True:
            #     timestamp = datetime.now().isoformat()
            #     self.consumer_csv_writer.writerow([
            #         timestamp,
            #         self.last_pressures[0], 
            #         self.last_pressures[1], 
            #         self.last_pressures[2],
            #         self.last_temps[0], 
            #         self.last_temps[1],
            #         self.last_pump_feedback,
            #         self.last_flow_rate,
            #     ])
            #     self.consumer_log.flush()

            self.queue_List[0].task_done()
            self.queue_List[1].task_done()
            self.queue_List[2].task_done()

    async def producer_task(self):
        while True:
            pump_on, manual_speed = self.pump_control.get_state()
            measured_pressure = self.last_pressures[0] if hasattr(self, 'last_pressures') else 0.0
            pid_speed = self.pid_control.compute_output(measured_pressure)
            speed = pid_speed if pid_speed is not None else manual_speed

            raw1, raw2 = CanOpen.generate_outmm_msg(pump_on, speed)
            data = CanOpen.generate_uint_16bit_msg(int(raw1), int(raw2), 0, 0)

            if self.can_connected and self.bus:
                try:
                    await CanOpen.send_can_message(self.bus, 0x600, data, False)
                except Exception as e:
                    self.status_bar.setText(f"CAN Send Error: {str(e)}")
                await CanOpen.send_can_message(self.bus, 0x600, data, False)

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

    # Figure out a new place to put this CAN gui interface layer for all sender and reciever tasks
    # as multiple GUI elements/windows need to access the same CAN recieving and sending functionality
    # consider creating a global sender queue that messages can be uploaded to and then processed by a singular 
    # sender thread, that way the .send_can_message can be blocking or non blocking without affecting anything else,
    # and can be accessed by anywhere in the program
    async def esv_valve_sender_task(self, state):

        data = []

        if state :
            data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        else :
            data = [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        
        try:
            await CanOpen.send_can_message(self.bus, 0x191, data, eStopValue, False, testingFlag)
        except Exception as e:
            self.status_bar.setText(f"CAN Send Error: {str(e)}")
        

    def update_plot(self):
        self.plot_canvas.update_plot()

    def closeEvent(self, event):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        event.accept()

class PAndIDGraphicWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("P&ID Schematics")
        self.setMinimumSize(800, 800)
        self.setStyleSheet("color: white; background-color: #212121;")

        tabWindowLayout = QVBoxLayout()
        self.nh3pump = NH3PumpControlScene()
        self.nh3vaporizer = NH3VaporizerControlScene()

        #Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(Stylesheets.TabWidgetStyleSheet())

        #Create Tab pages
        nh3_pump_test_tab = QWidget()
        nh3_vaporizer_test_tab = QWidget()
        
        nh3_pump_test_tab.setStyleSheet("background-color: #2e2e2e;")
        nh3_vaporizer_test_tab.setStyleSheet("background-color: #2e2e2e;")

        #Add labels and contents to tabs
        nh3_pump_test_tab_layout = QVBoxLayout(nh3_pump_test_tab)
        nh3_pump_test_tab_layout.addWidget(self.nh3pump)

        nh3_vaporizer_test_layout = QVBoxLayout(nh3_vaporizer_test_tab) #input is the parent widget
        nh3_vaporizer_test_layout.addWidget(self.nh3vaporizer)

        self.tab_widget.addTab(nh3_pump_test_tab, "NH3 PUMP TEST-1")
        self.tab_widget.addTab(nh3_vaporizer_test_tab, "NH3 VAPORIZER TEST-1")
        tabWindowLayout.addWidget(self.tab_widget)
        self.setLayout(tabWindowLayout)

async def main_async():

    voltage_queue = asyncio.Queue(maxsize=10)
    temperature_queue = asyncio.Queue(maxsize=10)
    four_to_20_current_queue = asyncio.Queue(maxsize=10)

    queue_List = [voltage_queue, temperature_queue, four_to_20_current_queue]

    app = QApplication(sys.argv)

    pAndIdGraphicWindow = PAndIDGraphicWindow()
    controlWindow = PumpControlWindow(pAndIdGraphicWindow.nh3pump.run_plots, bus=None, queue_List=queue_List)  # Don't pass the bus initially
    # Pump Control window needs major refactor so consumer task can live outside of it as it needs to access
    # items from PAndIdGraphicWindow which contains the NH3 Pump and Vaporizer control scenes which contain the plots
    # Consumer task needs to be a library like function so it is seperated from the GUI code to follow proper object oriented
    # encapusulation, passing in the functions consumer task needs to call is a temporary solution

    pAndIdGraphicWindow.show()
    controlWindow.show()

    #print("Windows created")


    #asyncio.create_task(controlWindow.consumer_task())

    while True:
        await asyncio.sleep(0.01)
        #print("Main Loop")
        app.processEvents()
        # await temperature_queue.put((0x182, 'temperature', [random.randint(1, 100) for _ in range(8)]))
        # await voltage_queue.put((0x182, 'voltage', [random.randint(1, 5) for _ in range(8)]))
        # await four_to_20_current_queue.put((0x1FE, '4-20mA', [random.randint(1, 100) for _ in range(8)]))


if __name__ == "__main__":
    asyncio.run(main_async())