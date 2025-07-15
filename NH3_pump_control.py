import asyncio
from typing import List, Dict, Any, Union, Tuple, Callable

from PySide6.QtWidgets import (
    QWidget, QPushButton, QGraphicsScene, QGraphicsView,
    QGraphicsProxyWidget, QGraphicsTextItem, QVBoxLayout,
    QLabel, QDoubleSpinBox, QCheckBox, QSpacerItem, QSizePolicy,
    QHBoxLayout
)
from PySide6.QtCore import (
    Qt, QLineF, QPointF, QRectF, QTimer, Signal
)
from PySide6.QtGui import (
    QFont, QColor, QPen, QPainter, QPolygonF
)

from app_stylesheets import Stylesheets
from SchematicHelper import (
    CreatePlotButton, SchematicHelperFunctions, CreatePlotLabel,
    CreatePlotWindow, SensorPlot
)

from functools import partial
from data_manager import SystemDataManager


class NH3PumpControlScene(QWidget):
    """
    Main schematic control interface for the NH3 pump system.

    This class builds the interactive GUI for visualizing sensor values,
    toggling digital valve outputs, and controlling heater/pump setpoints.
    """
    def __init__(self, data_manager: SystemDataManager):
        """
        Initializes the NH3PumpControlScene GUI.

        Args:
            data_manager (SystemDataManager): Handles CAN data communication and setpoint updates.
        """        
        super().__init__()

        self.data_manager = data_manager

        # Valve states (used to toggle open/close)
        # self.esv10401ValveState = False
        self.fv10106ValveState = False
        self.sv10107ValveState = False
        self.fv10129ValveState = False
        self.fv10131ValveState = False

        # Main layout setup
        verticalLayout = QVBoxLayout()
        horizontalButtonLayout = QHBoxLayout()
        self.nh3_pump_label = QLabel("NH3 PUMP TEST-1")

        # Scene and view setup for drawing schematic
        self.systemControlScene = QGraphicsScene()
        self.systemControlView = QGraphicsView(self.systemControlScene)
        self.systemControlView.setStyleSheet(Stylesheets.GraphicsViewStyleSheet())
        self.systemControlView.setRenderHints(self.systemControlView.renderHints() | QPainter.RenderHint.Antialiasing)

        self.sensors: dict[str, SensorPlot] = {} # Maps sensor names to their live plot widgets

        sensor_defs = [
            ("PT10120", "pressure", (160, -190), "psi", True),
            ("PT10130",  "pressure", (610, -190), "psi", True),
            ("PT10118", "pressure", (-50, 350), "psi", True),
            ("PT10110", "pressure", (-525, -75), "psi", True),
            ("PT10134", "pressure", (400, -480), "psi", True),  # Added PT10134
            ("TI10111", "temperature", (-625, -75), "°C", True),
            ("TI10115", "temperature", (-480, 130), "°C", True),
            ("TI10116", "temperature", (-480, 300), "°C", True),
            ("TI10117", "temperature", (-150, 350), "°C", True),
            ("TI01", "temperature", (350, 260), "°C", True),
            ("TI10121", "temperature", (310, -190), "°C", True),
            ("TI10119", "temperature", (720, -190), "°C", True),
            ("TI10122", "temperature", (530, -190), "°C", True),  # Added TI10122
            ("FT10124", "flow_feedback", (810, -190), "kg/h", True),
            ("FT10106", "flow_feedback", (-500, -325), "kg/h", True),
            ("PIC10126", "flow_feedback", (600, -480), "psig", True),

            ("PumpFeedback", "pump_feedback", (-40, 60), "%", True),
        ]

        for name, kind, pos, units, live in sensor_defs:
            current_sensor_plot = SensorPlot( # Use a distinct variable name for clarity
                self.systemControlScene,
                name,
                self.data_manager,
                kind,
                pos,
                units,
                live
            )
            self.sensors[name] = current_sensor_plot


            if kind == "pressure":
                idx = self.data_manager.pressure_sensor_names.index(name)
                self.data_manager.pressure_updated.connect(
                    lambda vals, i=idx, s_plot=current_sensor_plot: s_plot.update_value(vals[i])
                )
            elif kind == "temperature":
                idx = self.data_manager.temperature_sensor_names.index(name)
                self.data_manager.temperature_updated.connect(
                    lambda vals, i=idx, s_plot=current_sensor_plot: s_plot.update_value(vals[i])
                )
            elif kind == "flow_feedback":
                # Use partial to pre-apply current_sensor_plot as the last argument
                # The lambda will then receive the 4 signal values first
                self.data_manager.pump_feedback_updated.connect(
                    # ft1024_val and pic_val are the 3rd and 4th floats
                    # This lambda needs to match the 4 floats emitted by the signal
                    lambda pump_val, flow_val, ft1024_val, pic_val, s_plot=current_sensor_plot: s_plot.update_value(flow_val)
                )
            elif kind == "pump_feedback":
                # Similarly for pump_feedback
                self.data_manager.pump_feedback_updated.connect(
                    lambda pump_val, flow_val, ft1024_val, pic_val, s_plot=current_sensor_plot: s_plot.update_value(pump_val)
                )
        # Zoom and Grid Controls
        self.zoomInButton = QPushButton("Zoom In")
        self.zoomOutButton = QPushButton("Zoom Out")
        self.zoomInButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.zoomOutButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.gridToggle = QCheckBox("Toggle Grid")
        self.gridToggle.setStyleSheet(Stylesheets.CheckBoxStyleSheet())
        self.gridToggle.setChecked(True)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        horizontalButtonLayout.addWidget(self.nh3_pump_label)
        horizontalButtonLayout.addItem(self.horizontalSpacer)
        horizontalButtonLayout.addWidget(self.zoomInButton)
        horizontalButtonLayout.addWidget(self.zoomOutButton)
        horizontalButtonLayout.addWidget(self.gridToggle)
        self.zoomInButton.clicked.connect(partial(SchematicHelperFunctions.zoom_in, self.systemControlView))
        self.zoomOutButton.clicked.connect(partial(SchematicHelperFunctions.zoom_out, self.systemControlView))
        self.gridToggle.stateChanged.connect(self.toggleGrid)

        # Digital Output Controls (valves): Label + Toggle button
        # Format: Label (shows state), Button (toggles state)
        # self.esv10401Label = CreatePlotLabel(self.systemControlScene, -750, -325)
        # # self.esv10401Label.setLabelText("CLOSED")
        # self.esv10401Button = CreatePlotButton(
        #     self.systemControlScene,
        #     partial(self._toggle_digital_output, self.esv10401Label, 'esv10401ValveState', 0),
        #     "Toggle", -750, -285
        # )

        # self.fv10106Label = CreatePlotLabel(self.systemControlScene, -500, -325)
        # self.fv10106Label.setLabelText("CLOSED")
        # self.fv10106Button = CreatePlotButton(
        #     self.systemControlScene,
        #     partial(self._toggle_digital_output, self.fv10106Label, 'fv10106ValveState', 1),
        #     "Toggle", -500, -285
        # )

        # ESV 10107 Valve
        self.esv10107Label = CreatePlotLabel(self.systemControlScene, -350, -250)
        self.esv10107Label.setLabelText("CLOSED") # Initial state text

        # Create a QPushButton for interaction
        self.esv10107PushButton = QPushButton("ESV-10107: CLOSED") # Initial text for the button
        self.esv10107PushButton.setCheckable(True)
        self.esv10107PushButton.setFixedSize(100, 40) # Adjust size as needed
        self.esv10107PushButton.setStyleSheet(Stylesheets.TogglePushButtonStyleSheet())

        # Add the QPushButton to the scene via a proxy widget
        esv10107_button_proxy = self.systemControlScene.addWidget(self.esv10107PushButton)
        esv10107_button_proxy.setPos(-350, -210) # Position where you want the interactive button

        # Connect the QPushButton's toggled signal to the _toggle_digital_output
        self.esv10107PushButton.toggled.connect(
            partial(self._toggle_digital_output,
                    self.esv10107PushButton,            # The actual QPushButton
                    "ESV-10107",                        # Base name for button caption
                    self.data_manager.set_esv1,     # Data manager set function
                    self.esv10107Label                 # The CreatePlotLabel to update graphically
                   )
        )
        # Connect data manager's signal to update button's checked state and CreatePlotLabel's text/color
        self.data_manager.esv1_state_toggled.connect(self.esv10107PushButton.setChecked)
        # Also connect to a slot that updates the CreatePlotLabel's text/color
        self.data_manager.esv1_state_toggled.connect(
            partial(self._update_plot_label_from_state, self.esv10107Label, "ESV-10107")
        )


        # ESV 10112 Valve
        self.esv10112Label = CreatePlotLabel(self.systemControlScene, -425, -80)
        self.esv10112Label.setLabelText("CLOSED") # Initial state text

        # Create a QPushButton for interaction
        self.esv10112PushButton = QPushButton("ESV-10112: CLOSED") # Initial text for the button
        self.esv10112PushButton.setCheckable(True)
        self.esv10112PushButton.setFixedSize(100, 40) # Adjust size as needed
        self.esv10112PushButton.setStyleSheet(Stylesheets.TogglePushButtonStyleSheet())

        # Add the QPushButton to the scene via a proxy widget
        esv10112_button_proxy = self.systemControlScene.addWidget(self.esv10112PushButton)
        esv10112_button_proxy.setPos(-425, -50) # Position where you want the interactive button

        # Connect the QPushButton's toggled signal to the _toggle_digital_output
        self.esv10112PushButton.toggled.connect(
            partial(self._toggle_digital_output,
                    self.esv10112PushButton,            # The actual QPushButton
                    "ESV-10112",                        # Base name for button caption
                    self.data_manager.set_esv2,     # Data manager set function
                    self.esv10112Label                 # The CreatePlotLabel to update graphically
                   )
        )
        # Connect data manager's signal to update button's checked state and CreatePlotLabel's text/color
        self.data_manager.esv2_state_toggled.connect(self.esv10112PushButton.setChecked)
        # Also connect to a slot that updates the CreatePlotLabel's text/color
        self.data_manager.esv2_state_toggled.connect(
            partial(self._update_plot_label_from_state, self.esv10112Label, "ESV-10112")
        )



        # self.fv10131Label = CreatePlotLabel(self.systemControlScene, 710, -60)
        # self.fv10131Label.setLabelText("CLOSED")
        # self.fv10131Button = CreatePlotButton(
        #     self.systemControlScene,
        #     partial(self._toggle_digital_output, self.fv10131Label, 'fv10131ValveState', 3),
        #     "Toggle", 710, -20
        # )

        # Heater Setpoint Input tied to sensor position
        heater_sensor_plot = self.sensors.get("TI10119")
        heater_sensor_pos_x = heater_sensor_plot.schematic_label.labelProxy.pos().x()
        heater_sensor_pos_y = heater_sensor_plot.schematic_label.labelProxy.pos().y()

        # self.heaterSetPointInput = SchematicHelperFunctions.CreateSetpointInput(
        #     scene=self.systemControlScene,
        #     xPos=heater_sensor_pos_x,
        #     yPos=heater_sensor_pos_y + heater_sensor_plot.schematic_label.labelProxy.size().height() -100, # Below current value
        #     min_val=0.0,
        #     max_val=150.0, # Adjust max as per your heater's capability
        #     step=0.1,
        #     # initial_val=self.data_manager.commanded_heater_setpoint,
        #     units="°C",
        #     label_text="Heater SP"
        # )
        # # Connect to SystemDataManager's update method
        # self.heaterSetPointInput.valueChanged.connect(
        #     lambda val: asyncio.create_task(self.data_manager.update_heater_setpoint(val))
        # )
        # # Connect DataManager's signal back to update the input box if setpoint changes internally (e.g., Modbus read)
        # self.data_manager.heater_setpoint_changed.connect(self.heaterSetPointInput.setValue)

        # Pump Setpoint Input tied to pump feedback position
        # Get position of the "PumpFeedback" sensor label from self.sensors dict
        pump_sensor_plot = self.sensors.get("PumpFeedback")
        pump_sensor_pos_x = pump_sensor_plot.schematic_label.labelProxy.pos().x()
        pump_sensor_pos_y = pump_sensor_plot.schematic_label.labelProxy.pos().y()

        # self.pumpSetPointInput = SchematicHelperFunctions.CreateSetpointInput(
        #     scene=self.systemControlScene,
        #     xPos=pump_sensor_pos_x,
        #     yPos=pump_sensor_pos_y + pump_sensor_plot.schematic_label.labelProxy.size().height() -100, # Below current value
        #     min_val=0.0,
        #     max_val=100.0, # Pump speed is typically 0-100%
        #     step=1.0,
        #     initial_val=self.data_manager._commanded_pid_output, # Use PID setpoint for pump control
        #     units="%",
        #     label_text="Pump SP"
        # )
        # Connect to SystemDataManager's update method
        # self.pumpSetPointInput.valueChanged.connect(self.data_manager.update_pid_setpoint)
        # Connect DataManager's signal back to update the input box if setpoint changes internally
        # self.data_manager.pid_setpoint_changed.connect(self.pumpSetPointInput.setValue)

        # Add Coordinate grid
        SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)

        # Draw system components: Labels, valves, boxes, and connection lines
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 50, 155, 25, "HV123\nL119-PID-101", -905, 125)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 50, 155, 25, "HV115\nL119-PID-101", -550, -475)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 26, 125, 13, "CHEM VENT", 905, -250)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 26, 125, 13, "CHEM VENT", 900, 40)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 26, 125, 13, "CHEM VENT", 900, 310)

        # SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "ESV\n10401", -700, -250)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n01", 150, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "P1\n01", 50, -150)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PSV\n10402", 600, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FV\n10129", -75, -600)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FV\n10106", -500, -250)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "SV\n10107", -400, -250)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "SV\n10112", -425, 0)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10117", -150, 300)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10118", -50, 300)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10119", 725, -100)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10120", 200, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10121", 300, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "FIC", "10124", 700, 100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "FI", "10124", 800, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10134", 400, -400)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PIC", "10126", 600, -400)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "01", 400, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10122", 550, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10123", 600, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "FIC", "10106", -550, -250)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10110", -500, 0)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10111", -600, 0)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10115", -550, 150)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10116", -550, 300)

        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 200, 200, "PUMP SPEED", -100, -50)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 180, 180, "HEATER", 360, -50)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 100, 200, "CHILLER\nE-10114", -300, 150)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 60, 30, "E-105", -700, 210)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 100, 100, "N2 GAS\nCYLINDER", -900, -200)

        # SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=750, yPos=30, size=20, label="Valve")
        # SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=-675, yPos=-150, size=20, label="ESV 10401")
        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=-475, yPos=-150, size=20, label="FV 10106")
        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=-375, yPos=-150, size=20, label="SV 10107")
        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=-50, yPos=-500, size=20, label="FV 10129")

        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -600, -260, 910, -260, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -600, -260, -600, -150, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -375, -200, -375, -150, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -475, -200, -475, -150, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -525, -200, -525, -150, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -670, 241, -670, 275, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 900, 30, 900, -260, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 30, 910, 30, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 225, -50, 225, 30, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 325, -50, 325, 30, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 125, 150, 125, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 75, -100, 75, -50, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 575, -50, 575, 30, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 625, -50, 625, 30, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 825, -50, 825, 30, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 750, -50, 750, 30, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 30, 675, 300, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 300, 910, 300, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 125, 650, 125, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 700, 30, 700, 100, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 425, 130, 425, 200, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 425, -350, 425, -260, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 625, -350, 625, -260, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -200, 250, 0, 250, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 0, 250, 0, 150, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -250, 150, -250, 100, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -250, 100, -750, 100, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -475, 50, -475, 100, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -475, 100, -475, 100, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -300, 225, -640 , 225, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -670, 275, -300, 275, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -525, 225, -525, 200, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -525, 275, -525, 300, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -575, 50, -575, 100, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -300, 100, -300, -150, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -300, -150, -800, -150, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -400, -500, 900, -500, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 900, -500, 900, -260, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -125, 300, -125, 250, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -25, 300, -25, 250, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -50, -550, -50, -500, thickness=2)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -400, 50, -400, 100, thickness=2)

        # Adjust zoom
        self.systemControlView.scale(0.9, 0.9)

        # Add everything to main layout
        verticalLayout.addLayout(horizontalButtonLayout)
        verticalLayout.addWidget(self.systemControlView)
        self.setLayout(verticalLayout)

    def toggleGrid(self):
        """Adds or removes the coordinate grid from the schematic scene based on the checkbox state."""
        if self.gridToggle.isChecked():
            SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)
        else:
            SchematicHelperFunctions.RemoveCoordinateGrid(self.systemControlScene)



    def _toggle_digital_output(self, button: QPushButton, base_name: str,
                               datamanager_set_function: Callable[[bool], None],
                               datamanager_state_signal: Signal,
                               plot_label: CreatePlotLabel = None): # Added optional plot_label
        """
        Toggles a digital output (e.g., valve) based on a QCheckableButton's state,
        updates its caption, commands the data manager, and optionally updates a CreatePlotLabel.

        This function is designed to be connected to the 'toggled' signal of a QPushButton.

        Args:
            button (QPushButton): The QCheckableButton instance that emitted the signal.
            base_name (str): The base name for the button's caption (e.g., "ESV-10107").
            datamanager_set_function (Callable[[bool], None]): The method in data_manager to call
                                                               to command the new state.
            datamanager_state_signal (Signal): The PySide6 signal from data_manager that emits
                                               the current state of this specific output.
                                               (Used for connections in __init__).
            plot_label (CreatePlotLabel, optional): An optional CreatePlotLabel to update visually.
        """
        checked_state = button.isChecked()

        # Update the button's text immediately for visual feedback
        self._update_button_caption(button, base_name, checked_state)

        # If a CreatePlotLabel is provided, update its text and color as well
        if plot_label:
            self._update_plot_label_from_state(plot_label, checked_state)

        # Call the data manager's set function to command the new state
        datamanager_set_function(checked_state)

        # Reminder: The connection `datamanager_state_signal.connect(button.setChecked)`
        # and `datamanager_state_signal.connect(partial(self._update_plot_label_from_state, plot_label, base_name))`
        # MUST be made ONCE in the __init__ method for external synchronization.


    def _update_button_caption(self, btn: QPushButton, base_name: str, open_state: bool):
        """
        Updates the text of a QCheckableButton to show its open/closed state.
        Args:
            btn (QPushButton): The QCheckableButton instance.
            base_name (str): The base name of the valve (e.g., "ESV-10107").
            open_state (bool): True if the valve is open, False if closed.
        """
        btn.setText(f"{base_name}: {'OPEN' if open_state else 'CLOSED'}")

    def _update_plot_label_from_state(self, label: CreatePlotLabel, open_state: bool):
        """
        Updates a CreatePlotLabel's text and color based on the valve's state.
        This is a helper for the CreatePlotLabel visual representation.
        """
        if open_state:
            label.setLabelText("OPEN")
            label.setLabelColorGreen()
        else:
            label.setLabelText("CLOSED")
            label.setLabelColorRed()  








    def _update_valve_label(self, label: CreatePlotLabel, is_open: bool):
        """
        Updates a valve's label color and text based on whether it is open or closed.

        Args:
            label (CreatePlotLabel): The label to update.
            is_open (bool): Whether the valve is open (True) or closed (False).
        """
        if is_open:
            label.setLabelText("OPEN")
            label.setLabelColorGreen()
        else:
            label.setLabelText("CLOSED")
            label.setLabelColorRed()