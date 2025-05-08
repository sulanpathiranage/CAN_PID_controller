# pid_gui.py
import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg


class PIDTunerGUI(QWidget):
    def __init__(self, controller, setpoint=1.0, dt=0.1, num_vars=9):
        super().__init__()
        self.setWindowTitle("CANa.py")
        self.resize(1000, 800)

        self.controller = controller
        self.dt = dt
        self.setpoint = setpoint
        self.num_vars = num_vars

        self.time = 0
        self.variables = [0.0 for _ in range(num_vars)]
        self.data = [[] for _ in range(num_vars)]
        self.time_data = []

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.create_controls()
        self.create_plots()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_process)
        self.timer.start(int(self.dt * 1000))

    def create_controls(self):
        control_layout = QGridLayout()
        self.kp_edit = self.add_labeled_line_edit(control_layout, "Kp", "1.0", 0)
        self.ki_edit = self.add_labeled_line_edit(control_layout, "Ki", "0.0", 1)
        self.kd_edit = self.add_labeled_line_edit(control_layout, "Kd", "0.0", 2)
        self.sp_edit = self.add_labeled_line_edit(control_layout, "Setpoint", str(self.setpoint), 3)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_parameters)
        control_layout.addWidget(apply_btn, 4, 0, 1, 2)

        self.layout.addLayout(control_layout)

    def add_labeled_line_edit(self, layout, label, default, row):
        lbl = QLabel(label)
        edit = QLineEdit(default)
        layout.addWidget(lbl, row, 0)
        layout.addWidget(edit, row, 1)
        return edit

    def apply_parameters(self):
        try:
            self.controller.set_kp(float(self.kp_edit.text()))
            self.controller.set_ki(float(self.ki_edit.text()))
            self.controller.set_kd(float(self.kd_edit.text()))
            self.setpoint = float(self.sp_edit.text())
        except ValueError:
            print("Invalid input for PID or setpoint.")

    def create_plots(self):
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plots = []
        self.curves = []

        for i in range(3):
            for j in range(3):
                p = self.plot_widget.addPlot(row=i, col=j)
                p.setTitle(f"Variable {3*i + j + 1}")
                p.setYRange(-2, 2)
                curve = p.plot(pen=pg.intColor(3*i + j))
                self.plots.append(p)
                self.curves.append(curve)

        self.layout.addWidget(self.plot_widget)

    def update_process(self):
        self.time += self.dt
        self.time_data.append(self.time)

        control_output = self.controller.update(self.setpoint, self.variables[0], self.dt)
        self.variables[0] += (control_output - self.variables[0]) * 0.1

        for i in range(1, self.num_vars):
            self.variables[i] += 0.05 * (np.random.rand() - 0.5)

        for i in range(self.num_vars):
            self.data[i].append(self.variables[i])

        max_len = 100
        if len(self.time_data) > max_len:
            self.time_data = self.time_data[-max_len:]
            for i in range(self.num_vars):
                self.data[i] = self.data[i][-max_len:]

        for i in range(self.num_vars):
            self.curves[i].setData(self.time_data, self.data[i])

    # ---------- External Update Methods ----------
    def update_variable(self, index, value):
        if 0 <= index < self.num_vars:
            self.variables[index] = value

    def get_variable(self, index):
        if 0 <= index < self.num_vars:
            return self.variables[index]
        return None

    def set_setpoint(self, sp):
        self.setpoint = sp
        self.sp_edit.setText(str(sp))
