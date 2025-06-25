
import random
import asyncio

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
    CreatePlotWindow
)

from functools import partial
from can_open_protocol import CanOpen

class NH3PumpControlScene(QWidget):

    # valveState = True # for testing valve state initially set to true (open) , typically would be set based on actual message

    def __init__(self):
        super().__init__()

        #Assuming valve is closed initially
        self.valveState = False

        #Create Layout
        verticalLayout = QVBoxLayout()
        horizontalButtonLayout = QHBoxLayout()
        self.nh3_pump_label = QLabel("NH3 PUMP TEST-1")

        #Create Graphics Scene, add to Graphics View Widget
        self.systemControlScene = QGraphicsScene()
        self.systemControlView = QGraphicsView(self.systemControlScene)
        self.systemControlView.setStyleSheet(Stylesheets.GraphicsViewStyleSheet())
        self.systemControlView.setRenderHints(self.systemControlView.renderHints() | QPainter.RenderHint.Antialiasing)

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
        self.esv10401Label = CreatePlotLabel(self.systemControlScene, -290, -140)
        self.esv10401Label.setLabelText("CLOSED")
        self.blueValveLabel = CreatePlotLabel(self.systemControlScene, 725, -60)
        self.blueValveLabel.setLabelText("CLOSED")
        self.ti10401Label = CreatePlotLabel(self.systemControlScene, -240, 210)
        self.pt10401Label = CreatePlotLabel(self.systemControlScene, 10, 210)
        self.pi10120Label = CreatePlotLabel(self.systemControlScene, 160, -190)
        self.ti10121Label = CreatePlotLabel(self.systemControlScene, 310, -190)
        self.fi10124Label = CreatePlotLabel(self.systemControlScene, 810, -190)
        self.pumpLabel = CreatePlotLabel(self.systemControlScene, -40, 60)
        self.ti10122Label = CreatePlotLabel(self.systemControlScene, 510, -190)
        self.pi10123Label = CreatePlotLabel(self.systemControlScene, 610, -190)
        self.ti01Label = CreatePlotLabel(self.systemControlScene, 350, 260)
        #self.tic02Label = CreatePlotLabel(self.systemControlScene, 500, 260)
        self.fic10124Label = CreatePlotLabel(self.systemControlScene, 700, 160)

        # Create plots to start data collection
        self.ti10401Plot = CreatePlotWindow(self.ti10401Label.setLabelText, "TI 10401 Plot", "Temperature vs. Time", "Temperature", "C")
        self.pt10401Plot = CreatePlotWindow(self.pt10401Label.setLabelText,"PT 10401 Plot", "Pressure vs. Time", "Pressure", "bar")
        self.pi10120Plot = CreatePlotWindow(self.pi10120Label.setLabelText, "PI 10120 Plot", "Pressure vs. Time", "Pressure", "barg")
        self.ti10121Plot = CreatePlotWindow(self.ti10121Label.setLabelText, "TI 10121 Plot", "Temperature vs. Time", "Temperature", "C")
        self.fi10124Plot = CreatePlotWindow(self.fi10124Label.setLabelText, "FI 10124 Plot", "Flow vs. Time", "Flow", "L/min")
        self.pumpPlot = CreatePlotWindow(self.pumpLabel.setLabelText, "Pump Speed Plot", "Speed vs. Time", "Speed", "RPM")
        self.ti10122Plot = CreatePlotWindow(self.ti10122Label.setLabelText, "TI 10122 Plot", "Temperature vs. Time", "Temperature", "C")
        self.pi10123Plot = CreatePlotWindow(self.pi10123Label.setLabelText, "PI 10123 Plot", "Pressure vs. Time", "Pressure", "bar")
        self.ti01Plot = CreatePlotWindow(self.ti01Label.setLabelText, "TI 01 Plot", "Temperature vs. Time", "Temperature", "C")
        #self.tic02Plot = CreatePlotWindow(self.tic02Label.setLabelText, "TIC 02 Plot", "Temperature vs. Time", "Temperature", "C")
        self.fic10124Plot = CreatePlotWindow(self.fic10124Label.setLabelText, "FIC 10124 Plot", "Flow vs. Time", "Flow", "L/min")

        # Create Plot buttons
        self.esv10401Button = CreatePlotButton(self.systemControlScene, self.toggleEsv10401Valve, "Toggle", -290, -100)
        self.blueValveButton = CreatePlotButton(self.systemControlScene, self.toggleBlueValve, "Toggle", 725, -25)
        self.ti10401Button = CreatePlotButton(self.systemControlScene, self.ti10401Plot.show, "Plot", -240, 250)
        self.pt10401Button = CreatePlotButton(self.systemControlScene, self.pt10401Plot.show, "Plot", 10, 250)
        self.pi10120Button = CreatePlotButton(self.systemControlScene, self.pi10120Plot.show, "Plot", 160, -140)
        self.ti10121Button = CreatePlotButton(self.systemControlScene, self.ti10121Plot.show, "Plot", 310, -140)
        self.fi10124Button = CreatePlotButton(self.systemControlScene, self.fi10124Plot.show, "Plot", 810, -140)
        self.pumpButton = CreatePlotButton(self.systemControlScene, self.pumpPlot.show, "Plot", -40, 100)
        self.ti10122Button = CreatePlotButton(self.systemControlScene, self.ti10122Plot.show, "Plot", 510, -140)
        self.pi10123Button = CreatePlotButton(self.systemControlScene, self.pi10123Plot.show, "Plot", 610, -140)
        self.ti01Button = CreatePlotButton(self.systemControlScene, self.ti01Plot.show, "Plot", 350, 310)
        #self.tic02Button = CreatePlotButton(self.systemControlScene, self.tic02Plot.show, "Plot", 500, 310)
        self.fic10124Button = CreatePlotButton(self.systemControlScene, self.fic10124Plot.show, "Plot", 700, 210)

        #view_size = self.systemControlView.viewport().size()
        #self.systemControlScene.setSceneRect(0, 0, view_size.width(), view_size.height())

        #Add Coordinate grid
        SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)

        #Add Components to scene
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "City\nwater", -520, 0)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "N2/AIR", -250, -280)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "VENT", 650, -280)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "Water\nDrain", 900, 50)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "Weighed\nBucket", 900, 150)

        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PG\n10501", 200, -400)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n10501", 300, -400)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PT\n10501", 450, -400)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "ESV\n10401", -350, -150)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FI\n10124", 800, -100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n01", 150, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "P1\n01", 50, -150)
        #SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FV\n10124", 750, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PSV\n10402", 600, 100)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10401", -150, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PT", "10401", -50, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10120", 200, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10121", 300, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "FIC", "10124", 700, 100)

        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 200, 200, "PUMP SPEED", -100, -50)
        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 100, 100, "HEATER", 400, 0)

        #SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TT", "01", 400, 150)
        #SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TAHH", "01", 400, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "01", 350, 200)
        #SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TT", "02", 450, 150)
        #SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TIC", "02", 500, 200)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10122", 550, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PI", "10123", 600, -100)

        SchematicHelperFunctions.CreateDoubleTriangleValve(self.systemControlScene, xPos=750, yPos=30, size=20, label="Valve")

        #Adding lines to scene
        #For Labels the X coordinate of line is Xcoord(Label) + width, Y coord is YCoord(Label) - height/2
        #For circles and tagged circles radius+Xcoord or radius + YCoord is center of circle, edge is diameter + XCoord or diameter + YCoord

        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -400, -20, -150, -20, 2)  # City Water Label to TI 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, -20, -150, 175, 2)  # City Water Label to TI 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, 175,  -25, 175, 2)  # TI 10401 to PT 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -25, 200, -25, 150, 2)    # PT 10401 to Vendor Package
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -325, -100, -325, -20, 2) # ESV to City Water Label
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -130, -290, 660, -290, 2) # N2/AIR to Vent
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 225, -350, 225, -290, 2)  # PG 10501 to N2/AIR and Vent Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 325, -350, 325, -290, 2)  # PRV 10501 to N2/AIR and Vent Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 475, -350, 475, -290, 2)  # PT 10501 to N2/AIR and Vent Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 30, 920, 30, 2)      # Vendor Package to Water Drain
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 225, -50, 225, 30, 2)     # PT 10402 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 325, -50, 325, 30, 2)     # TI 10402 to Vendor Package and Water Drain Line
        #SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 525, -50, 525, 30, 2)     # FE 01 to Vendor Package and Water Drain Line
        #SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 450, -290, 450, 30, 2)    # N2AIR to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 800, 30, 800, 130, 2)     # Vendor Package and Water Drain Line to Weighed Bucket
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 800, 130, 920, 130, 2)    # Vendor Package and Water Drain Line to Weighed Bucket (horizontal portion)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 125, 150, 125, 2)    # Vendor Package to PRV 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 75, -100, 75, -50, 2)     # Vendor Package to P1 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 575, -50, 575, 30, 2)     # TT 10122 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 625, -50, 625, 30, 2)     # PI 10123 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 825, -50, 825, 30, 2)     # FI 10124 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 30, 675, 250, 2)     # Vendor Package and Water Drain Line to PSV 10402
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 675, 125, 650, 125, 2)    # PSV 10402 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 700, 30, 700, 100, 2)     # PSV 10402 to TT 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 400, 100, 400, 200, 2)    # Heater to TT 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 500, 100, 500, 200, 2)    # Heater to TT 01

        self.systemControlView.scale(0.9, 0.9)

        #Add Components to Layout
        verticalLayout.addLayout(horizontalButtonLayout)
        verticalLayout.addWidget(self.systemControlView)

        #Set Layout for self
        self.setLayout(verticalLayout)

    def toggleGrid(self):
        if self.gridToggle.isChecked():
            SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)
        else :
            SchematicHelperFunctions.RemoveCoordinateGrid(self.systemControlScene)

    def toggleEsv10401Valve(self):

        # True denotes open valve
        # False denotes closed valve

        if (self.valveState == True):
            # # Send signal to close valve
            # try:
            #     await CanOpen.send_can_message(self.bus, 0x600, data, eStopValue, False, testingFlag)
            # except Exception as e:
            #         self.status_bar.setText(f"CAN Send Error: {str(e)}")

            # Update text
            self.esv10401Label.setLabelText("CLOSED")
            self.esv10401Label.setLabelColorRed()

            #Update valve state
            self.valveState = False

        else :
            # Send signal to open valve

            # Update text
            self.esv10401Label.setLabelText("OPEN")
            self.esv10401Label.setLabelColorGreen()

            #Update valve state
            self.valveState = True
   
    def toggleBlueValve(self):

        # True denotes open valve
        # False denotes closed valve

        if (self.valveState == True):
            # # Send signal to close valve
            # try:
            #     await CanOpen.send_can_message(self.bus, 0x600, data, eStopValue, False, testingFlag)
            # except Exception as e:
            #         self.status_bar.setText(f"CAN Send Error: {str(e)}")

            # Update text
            self.blueValveLabel.setLabelText("CLOSED")
            self.blueValveLabel.setLabelColorRed()

            #Update valve state
            self.valveState = False

        else :
            # Send signal to open valve

            # Update text
            self.blueValveLabel.setLabelText("OPEN")
            self.blueValveLabel.setLabelColorGreen()

            #Update valve state
            self.valveState = True

    # Async function for updating a plot depending on the data type, enumerate sensor names at some point
    async def run_plots(self, data, sensorName):
        if sensorName == "TI10401" :
            await self.ti10401Plot.run(data)
        elif sensorName == "TI10402" :
            await self.ti10402Plot.run(data)
        elif sensorName == "PT10401" :
            await self.pt10401Plot.run(data)
        elif sensorName == "PT10402" :
            await self.pt10402Plot.run(data)
        elif sensorName == "PUMP" :
            await self.pumpPlot.run(data)
        elif sensorName == "FE01" :
            await self.fe01Plot.run(data)
