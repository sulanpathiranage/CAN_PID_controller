from PySide6.QtWidgets import (
    QWidget, QPushButton, QGraphicsScene, QGraphicsView,
    QGraphicsProxyWidget, QGraphicsTextItem, QVBoxLayout,
    QLabel, QDoubleSpinBox, QCheckBox, QSpacerItem, QSizePolicy,
    QHBoxLayout
)
from PySide6.QtCore import (
    Qt, QLineF, QPointF, QRectF
)
from PySide6.QtGui import (
    QFont, QColor, QPen, QPainter, QPolygonF
)

from app_stylesheets import Stylesheets
from SchematicHelper import (
    CreatePlotButton, SchematicHelperFunctions, CreatePlotLabel,
    CreatePlotWindow, CreateLivePlotWindow
)

from functools import partial
from can_open_protocol import CanOpen
from PySide6.QtCore import QTimer
from SchematicHelper import SensorPlot      # if in a separate file
from data_manager import SystemDataManager

class NH3PumpControlScene(QWidget):

    # valveState = True # for testing valve state initially set to true (open) , typically would be set based on actual message

    def __init__(self, data_manager: SystemDataManager):
        super().__init__()

        self.data_manager = data_manager

        #Assuming valve is closed initially
        self.esv10401ValveState = False
<<<<<<< HEAD
        self.fvValveState = False
=======
        self.blueValveState = False
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495

        #Create Layout
        verticalLayout = QVBoxLayout()
        horizontalButtonLayout = QHBoxLayout()
        self.nh3_pump_label = QLabel("NH3 PUMP TEST-1")

        #Create Graphics Scene, add to Graphics View Widget
        self.systemControlScene = QGraphicsScene()
        self.systemControlView = QGraphicsView(self.systemControlScene)
        self.systemControlView.setStyleSheet(Stylesheets.GraphicsViewStyleSheet())
        self.systemControlView.setRenderHints(self.systemControlView.renderHints() | QPainter.RenderHint.Antialiasing)

        self.sensors: dict[str, SensorPlot] = {}


        sensor_defs = [
            # name, type, index, position, units, live_plot
<<<<<<< HEAD
            ("TI10117", "temperature", 0, (-150, 350), "°C", True),
            ("PI10118", "pressure",   0, (-50, 350),   "bar", True),
=======
            ("TI10117", "temperature", 0, (-240, 210), "°C", True),
            ("PI10118", "pressure",   0, (10, 210),   "bar", True),
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
            ("PI10120", "pressure",    1, (160, -190), "bar", True),
            ("TI10121", "temperature", 1, (310, -190), "°C", True),
            ("FI10124", "flow_feedback", 0, (810, -190), "L/min", True),
            ("PUMP",    "pump_feedback", 0, (-40, 60), "RPM", True),
            ("TI10122", "temperature", 2, (510, -190), "°C", True),
            ("PI10123", "pressure",    2, (610, -190), "bar", True),
            ("TI01",    "temperature", 3, (350, 260), "°C", True),
            ("FIC10124","flow_feedback", 1, (700, 160), "L/min", True),
            ("HEATER",  "temperature", 4, (460, 50), "°C", True),
            ("PI10134", "pressure", 3, (400, -490), "bar", True),
            ("PIC10126", "pressure", 4, (600, -490), "bar", True),
<<<<<<< HEAD
            ("FIC10106", "flow_feedback", 2, (-575, -330), "L/min", True),
            ("TI10111", "temperature", 5, (-625, -75), "°C", True),
            ("PI10120", "pressure", 5, (-525, -75), "bar", True),
            ("TI10115", "temperature", 6, (-480, 130), "°C", True),
            ("TI10116", "temperature", 7, (-480, 300), "°C", True),
=======
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
        ]

        for name, sensor_type, index, pos, units, live in sensor_defs:
            sp = SensorPlot(
                self.systemControlScene,
                name,
                self.data_manager,
                sensor_type,
                index,
                pos,
                units,
                live
            )
            self.sensors[name] = sp

        #Create Zoom Buttons
        self.zoomInButton = QPushButton("Zoom In")
        self.zoomOutButton = QPushButton("Zoom Out")
        self.zoomInButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.zoomOutButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        #Create grid toggle
        self.gridToggle = QCheckBox("Toggle Grid")
        self.gridToggle.setStyleSheet(Stylesheets.CheckBoxStyleSheet())
        self.gridToggle.setChecked(True)

        #Create Spacer
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        #Add Zoom buttons and spacer to horizontal layout
        horizontalButtonLayout.addWidget(self.nh3_pump_label)
        horizontalButtonLayout.addItem(self.horizontalSpacer)
        horizontalButtonLayout.addWidget(self.zoomInButton)
        horizontalButtonLayout.addWidget(self.zoomOutButton)
        horizontalButtonLayout.addWidget(self.gridToggle)

        # Connect buttons
        self.zoomInButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_In, self.systemControlView))
        self.zoomOutButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_Out, self.systemControlView))
        self.gridToggle.stateChanged.connect(self.toggleGrid)

        #Create Labels
        self.esv10401Label = CreatePlotLabel(self.systemControlScene, -750, -325)
        self.esv10401Label.setLabelText("CLOSED")
<<<<<<< HEAD
        self.fvValveLabel = CreatePlotLabel(self.systemControlScene, 725, -60)
        self.fvValveLabel.setLabelText("CLOSED")
=======
        self.blueValveLabel = CreatePlotLabel(self.systemControlScene, 725, -60)
        self.blueValveLabel.setLabelText("CLOSED")
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
        self.heaterSetPointLabel = CreatePlotLabel(self.systemControlScene, 360, 50)
        self.heaterSetPointLabel.setLabelText("Set Point")
        self.heaterSetPointLabel.setLabelColorGreen()
        self.heatertempLabel = CreatePlotLabel(self.systemControlScene, 360, 100)
        self.heatertempLabel.setLabelText("Temp")
        self.heatertempLabel.setLabelColorGreen()

        # Create Plot buttons
<<<<<<< HEAD
        self.esv10401Button = CreatePlotButton(self.systemControlScene, lambda: self.toggleValve(self.esv10401Label, 'esv10401ValveState'), "Toggle", -750, -285)
        self.fvValveButton = CreatePlotButton(self.systemControlScene, lambda: self.toggleValve(self.fvValveLabel, 'fvValveState'), "Toggle", 725, -25)
=======
        self.esv10401Button = CreatePlotButton(self.systemControlScene, self.toggleEsv10401Valve, "Toggle", -290, -100)
        self.blueValveButton = CreatePlotButton(self.systemControlScene, self.toggleBlueValve, "Toggle", 725, -25)
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495

        #Add Coordinate grid
        SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)

        #Add Components to scene
<<<<<<< HEAD
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 50, 155, 25, "HV123\nL119-PID-101", -905, 125)  #NH3 WALL SUPPLY
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "HV115\nL119-PID-101", -250, -550)
=======
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "HV123\nL119-PID-101", -520, 0)  #NH3 WALL SUPPLY
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "HV115\nL119-PID-101", -250, -280)
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "CHEM VENT", 905, -280)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "CHEM VENT", 900, 50)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "CHEM VENT", 900, 325)

<<<<<<< HEAD
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "ESV\n10401", -700, -250)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n01", 150, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "P1\n01", 50, -150)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PSV\n10402", 600, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FV\n10129", 400, -700)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FV\n10106", -500, -250)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "SV\n10107", -400, -250)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10117", -150, 300)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10118", -50, 300)
=======
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "ESV\n10401", -350, -150)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n01", 150, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "P1\n01", 50, -150)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PSV\n10402", 600, 100)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10117", -150, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10118", -50, 200)
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10120", 200, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10121", 300, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "FIC", "10124", 700, 100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "FI", "10124", 800, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10134", 400, -400)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PIC", "10126", 600, -400)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "01", 400, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10122", 550, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10123", 600, -100)
<<<<<<< HEAD
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "FIC", "10106", -550, -250)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10120", -500, 0)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10111", -600, 0)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10115", -550, 150)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10116", -550, 300)

        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 200, 200, "PUMP SPEED", -100, -50)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 180, 180, "HEATER", 360, -50)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 100, 200, "CHILLER\nE-10114", -300, 150)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 60, 30, "E-105", -700, 210)

        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=750, yPos=30, size=20, label="Valve")
        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=-675, yPos=-150, size=20, label="ESV 10401")
        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=-475, yPos=-150, size=20, label="FV 10106")
        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=-375, yPos=-150, size=20, label="SV 10107")
=======

        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 200, 200, "PUMP SPEED", -100, -50)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 180, 180, "HEATER", 360, -50)

        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=750, yPos=30, size=20, label="Valve")
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495

        #Adding lines to scene
        #For Labels the X coordinate of line is Xcoord(Label) + width, Y coord is YCoord(Label) - height/2
        #For circles and tagged circles radius+Xcoord or radius + YCoord is center of circle, edge is diameter + XCoord or diameter + YCoord
<<<<<<< HEAD
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -600, -260, 910, -260, 2) # CONNECTION LINE FROM ESV 10401 to CHEM VENT
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -600, -260, -600, -150, 2)# CONNECTION LINE from CHEM VENT to ESV 10401 and FV branch
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -375, -200, -375, -150, 2)# SV 10107 to ESV 10401 and FV branch
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -475, -200, -475, -150, 2)# FV 10106 to ESV 10401 and FV branch
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -525, -200, -525, -150, 2)# FIC 10106 to ESV 10401 and FV branch
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -675, -200, -675, -150, 2)# ESV 10401 to CHEM VENT and FV branch
=======
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -400, -20, -150, -20, 2)  # NH3 WALL SUPPLY Label to TI 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, -20, -150, -290, 2)  # NH3 WALL SUPPLY Label to PI 10134
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, -20, -150, 200, 2)  # NH3 WALL SUPPLY Label to TI 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, 175,  -25, 175, 2)  # TI 10401 to PT 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -25, 200, -25, 150, 2)    # PT 10401 to Vendor Package
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -325, -100, -325, -20, 2) # ESV to NH3 WALL SUPPLY Label
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, -290, 910, -290, 2) # NH3 WALL SUPPLY Label to PI 10134
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 900, -290, 900, 30, 2)    # CHEM VENT TO CHEM VENT
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 30, 920, 30, 2)      # Vendor Package to Water Drain
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 225, -50, 225, 30, 2)     # PT 10402 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 325, -50, 325, 30, 2)     # TI 10402 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 125, 150, 125, 2)    # Vendor Package to PRV 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 75, -100, 75, -50, 2)     # Vendor Package to P1 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 575, -50, 575, 30, 2)     # TT 10122 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 625, -50, 625, 30, 2)     # PI 10123 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 825, -50, 825, 30, 2)     # FI 10124 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 30, 675, 300, 2)     # Vendor Package and Water Drain Line to PSV 10402
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 300, 920, 300, 2)    # to NH3 CHEM VENT
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 125, 650, 125, 2)    # PSV 10402 to NH3 CHEM VENT
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 700, 30, 700, 100, 2)     # PSV 10402 to TT 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 425, 130, 425, 200, 2)    # Heater to TT 01
<<<<<<< HEAD
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 425, -350, 425, -290, 2)  # PI 10134 to CHEM VENT
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 625, -350, 625, -290, 2)  # PIC 10126 to CHEM VENT
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -200, 250, 0, 250, 2)     # CHILLER E-10114 to TI 10117 and PI 10118
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 0, 250, 0, 150, 2)        # TI 10117 and PI 10118 to PUMP SPEED VENDOR PACKAGE
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -250, 150, -250, 100, 2)  # CHILLER E-10114 to TI 10111 and PI 10120
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -250, 100, -750, 100, 2)  # TI 10111 and PI 10120 to HV123 L119-PID-101
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -475, 50, -475, 100, 2)   # PI 10120 to HV123 L119-PID-101 and CHILLER LINE
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -475, 100, -475, 100, 2)  # PI 10120 to TI 10111 and CHILLER LINE
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -300, 225, -640 , 225, 2) # CHILLER to E-105
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -670, 240, -670, 275, 2)  # E-105 to CHILLER LINE
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -670, 275, -300, 275, 2)  # E-105 LINE to CHILLER
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -525, 225, -525, 200, 2)  # CHILLER LINE to TI 10115
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -525, 275, -525, 300, 2)  # CHILLER LINE to TI 10116
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -575, 50, -575, 100, 2)   # TI 10111 to SV 10107
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -300, 100, -300, -150, 2) # TI 10111 and PI 10120 to SV 10107
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -300, -150, -800, -150, 2)# SV 10107 to N2 CYLINDER
=======
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 425, -350, 425, -290, 2)     # PI 10134 to CHEM VENT
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 625, -350, 625, -290, 2)    # PIC 10126 to CHEM VENT
  
>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
        self.systemControlView.scale(0.9, 0.9)

        #Add Components to Layout
        verticalLayout.addLayout(horizontalButtonLayout)
        verticalLayout.addWidget(self.systemControlView)

        #Set Layout for self
        self.setLayout(verticalLayout)

        #self.ti10117_timer = QTimer(self)

    def toggleGrid(self):
        if self.gridToggle.isChecked():
            SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)
        else :
            SchematicHelperFunctions.RemoveCoordinateGrid(self.systemControlScene)

<<<<<<< HEAD
=======
    """
    UI-slot for the ESV-10401 valve toggle button.

    Delegates to the generic `toggleValve()` helper, which:
        • flips the boolean   self.esv10401ValveState
        • updates the label’s text  (“OPEN” / “CLOSED”)
        • changes the label’s colour (green / red)

    Keeping this wrapper means the button signal can stay
    readable (“clicked → toggleEsv10401Valve”) while the
    common logic lives in one place.
    """
    def toggleEsv10401Valve(self):
        self.toggleValve(self.esv10401Label, 'esv10401ValveState')

    """
    UI-slot for the downstream “blue” valve.

    Behaviour is identical to `toggleEsv10401Valve`, but it
    works on its own label widget and internal state flag
    (`blueValveState`).  All the heavy lifting is still done
    by `toggleValve()`.
    """
    def toggleBlueValve(self):
        self.toggleValve(self.blueValveLabel, 'blueValveState')


>>>>>>> 32954a78b8447ea5c4419a1acc69bcdc1bc05495
    def toggleValve(self, label, current_state_attr):
        current_state = getattr(self, current_state_attr)
        if current_state:
            label.setLabelText("CLOSED")
            label.setLabelColorRed()
        else:
            label.setLabelText("OPEN")
            label.setLabelColorGreen()
        setattr(self, current_state_attr, not current_state)

    # Async function for updating a plot depending on the data type, enumerate sensor names at some point
    async def run_plots(self, value: float, name: str): 
        sp = self.sensors.get(name) 
        if sp: 
            sp._on_new_data(value)
