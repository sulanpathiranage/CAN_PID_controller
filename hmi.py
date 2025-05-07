import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg


class PIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0
        self.previous_error = 0

    def update(self, setpoint, pv, dt):
        error = setpoint - pv
        self.integral += error * dt
        derivative = (error - self.previous_error) / dt if dt > 0 else 0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.previous_error = error
        return output


class PIDTuner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CANa.py")
        self.resize(1000, 800)

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.create_controls()
        self.create_plots()

        self.num_vars = 9
        self.time = 0
        self.dt = 0.1
        self.setpoint = 1.0
        self.variables = [0.0 for _ in range(self.num_vars)]
        self.data = [[] for _ in range(self.num_vars)]
        self.time_data = []

        self.pid = PIDController()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_process)
        self.timer.start(int(self.dt * 1000))

    def create_controls(self):
        control_layout = QGridLayout()

        self.kp_edit = self.add_labeled_line_edit(control_layout, "Kp", "1.0", 0)
        self.ki_edit = self.add_labeled_line_edit(control_layout, "Ki", "0.0", 1)
        self.kd_edit = self.add_labeled_line_edit(control_layout, "Kd", "0.0", 2)
        self.sp_edit = self.add_labeled_line_edit(control_layout, "Setpoint", "1.0", 3)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.update_parameters)
        control_layout.addWidget(apply_btn, 4, 0, 1, 2)

        self.layout.addLayout(control_layout)

    def add_labeled_line_edit(self, layout, label, default, row):
        lbl = QLabel(label)
        edit = QLineEdit(default)
        layout.addWidget(lbl, row, 0)
        layout.addWidget(edit, row, 1)
        return edit

    def update_parameters(self):
        try:
            self.pid.kp = float(self.kp_edit.text())
            self.pid.ki = float(self.ki_edit.text())
            self.pid.kd = float(self.kd_edit.text())
            self.setpoint = float(self.sp_edit.text())
        except ValueError:
            print("Invalid PID or Setpoint input.")

    def create_plots(self):
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plots = []
        self.curves = []

        for i in range(3):  # 3 rows
            for j in range(3):  # 3 columns
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

        # Simulate PID output on variable 0
        control_output = self.pid.update(self.setpoint, self.variables[0], self.dt)
        self.variables[0] += (control_output - self.variables[0]) * 0.1

        for i in range(1, self.num_vars):
            self.variables[i] += 0.05 * (np.random.rand() - 0.5)

        # Append new data
        for i in range(self.num_vars):
            self.data[i].append(self.variables[i])

        # Truncate to max length
        max_len = 100
        if len(self.time_data) > max_len:
            self.time_data = self.time_data[-max_len:]
            for i in range(self.num_vars):
                self.data[i] = self.data[i][-max_len:]

        # Update plots
        for i in range(self.num_vars):
            self.curves[i].setData(self.time_data, self.data[i])



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PIDTuner()
    window.show()
    sys.exit(app.exec())
