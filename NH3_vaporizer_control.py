
import random
import asyncio

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QGraphicsScene, QGraphicsView,
    QGraphicsProxyWidget, QGraphicsTextItem, QVBoxLayout,
    QLabel, QDoubleSpinBox, QCheckBox, QSpacerItem, QSizePolicy,
    QHBoxLayout
)
from PyQt6.QtCore import (
    Qt, QLineF, QPointF, QRectF
)
from PyQt6.QtGui import (
    QFont, QColor, QPen, QPainter, QPolygonF
)

from app_stylesheets import Stylesheets
from SchematicHelper import (
    CreatePlotButton, SchematicHelperFunctions, CreatePlotLabel,
    CreatePlotWindow
)
from functools import partial

class NH3VaporizerControlScene(QWidget):
    def __init__(self):
        super().__init__()

        #Create Layout
        verticalLayout = QVBoxLayout()
        horizontalButtonLayout = QHBoxLayout()
        self.nh3_pump_label = QLabel("NH3 VAPORIZER TEST-1")

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

        #Create Spacer Item
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        horizontalButtonLayout.addWidget(self.nh3_pump_label)
        horizontalButtonLayout.addItem(self.horizontalSpacer)
        horizontalButtonLayout.addWidget(self.zoomInButton)
        horizontalButtonLayout.addWidget(self.zoomOutButton)
        horizontalButtonLayout.addWidget(self.gridToggle)
        
        #Connect Buttons
        self.zoomInButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_In, self.systemControlView))
        self.zoomOutButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_Out, self.systemControlView))
        self.gridToggle.stateChanged.connect(self.toggleGrid)

        self.ti10401Button = CreatePlotButton(self.systemControlScene, self.ti10401ShowPlot, "Plot", -390, 600)
        self.ti10401Label = CreatePlotLabel(self.systemControlScene, -390, 560)

        self.pt10401Button = CreatePlotButton(self.systemControlScene, self.pt10401ShowPlot, "Plot", -140, 600)
        self.pt10401Label = CreatePlotLabel(self.systemControlScene, -140, 560)

        self.esv10401Button = CreatePlotButton(self.systemControlScene, self.esv10401ShowPlot, "Toggle", -540, 250) # hook up button to turn valve on and off here
        self.esv10401Label = CreatePlotLabel(self.systemControlScene, -540, 210)
        self.esv10401Label.setLabelText("CLOSED") # Determine what the default state is for the valve

        self.ti01Button = CreatePlotButton(self.systemControlScene, self.ti01ShowPlot, "Plot", -290, -50)
        self.ti01Label = CreatePlotLabel(self.systemControlScene, -290, -90)

        self.tahh01Button = CreatePlotButton(self.systemControlScene, self.tahh01ShowPlot, "Plot", -290, 100)
        self.tahh01Label = CreatePlotLabel(self.systemControlScene, -290, 60)

        self.tic02Button = CreatePlotButton(self.systemControlScene, self.tic02ShowPlot, "Plot", 60, 150)
        self.tic02Label = CreatePlotLabel(self.systemControlScene, 60, 110)

        self.pt10402Button = CreatePlotButton(self.systemControlScene, self.pt10402ShowPlot, "Plot", 210, -40)
        self.pt10402Label = CreatePlotLabel(self.systemControlScene, 210, 0)

        self.ti10402Button = CreatePlotButton(self.systemControlScene, self.ti10402ShowPlot, "Plot", 360, -40)
        self.ti10402Label = CreatePlotLabel(self.systemControlScene, 360, 0)

        #Store all labels in a plot and in an normal synchronous continously running process update all of them with whatever latest information
        #Can also update all the labels async if the process takes too long

        #Add Coordinate grid
        SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)

        #Add Components to scene
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "City\nwater", -820, 350)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "N2/AIR", -400, -180)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "VENT", 650, -180)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "Water\nDrain", 700, 200)

        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "10501", 250, -300)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n10501", 350, -300)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PT\n10501", 500, -300)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FE\n01", 500, 50)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "ESV\n10401", -600, 200)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10401", -300, 550)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PT", "10401", -200, 550)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PT", "10402", 250, 50)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10402", 350, 50)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "01", -150, -100) #change inside of this to a triangle
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TAHH", "01", -150, 50)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TIC", "02", 0, 100)


        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 300, 300, "VENDOR\nPACKAGE", -200, 200)

        #Adding lines to scene
        #For Labels the X coordinate of line is Xcoord(Label) + width, Y coord is YCoord(Label) - height/2
        #For circles and tagged circles radius+Xcoord or radius + YCoord is center of circle, edge is diameter + XCoord or diameter + YCoord

        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -280, -190, 660, -190, 2) # N2/AIR to vent line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -700, 330, -275, 330, 2)  # City Water to TI10401 (horizontal)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -275, 330, -275, 525, 2)  # City Water to TI10401 (vertical)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -575, 250, -575, 330, 2)  # City Water to ESV       
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -275, 525, -175, 525, 2)  # TI10401 to PT10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -175, 550, -175, 500, 2)  # Vendor Package to PT10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -175, 200, -175, -75, 2)  # Vendor Package to TI01 and TAHH01 (main line)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -175, 75, -150, 75, 2)    # Vendor Package to TAHH01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -175, -75, -150, -75, 2)  # Vendor Package to TI01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -25, 200, -25, 125, 2)    # Vendor Package to TIC02 (main line)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -25, 125, 0, 125, 2)      # Vendor Package to TIC02

        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 275, -250, 275, -190, 2)  # 10501 to N2/AIR and Vent line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 375, -250, 375, -190, 2)  # PRV 10501 to N2/AIR and Vent Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 525, -250, 525, -190, 2)  # PT10501 to N2/AIR and Vent Line

        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 350, 200, 350, 2)    # Vendor package to water drain
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 200, 350, 200, 180, 2)    # Vendor package to water drain
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 200, 180, 720, 180, 2)    # Vendor package to water drain

        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 275, 100, 275, 180, 2)    # PT10402 to vendor package and water drain line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 375, 100, 375, 180, 2)    # TI10402 to vendor package and water drain line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 525, 100, 525, 180, 2)    # FE01 to vendor package and water drain line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 475, -190, 475, 180, 2)   # N2/AIR to vent line to water drain line

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

    def ti10401ShowPlot(self):
        self.ti10401 = CreatePlotWindow()
        self.ti10401.show()
        self.ti10401.run_loop()

    def pt10401ShowPlot(self):
        self.pt10401 = CreatePlotWindow()
        self.pt10401.show()
        self.pt10401.run_loop()

    def esv10401ShowPlot(self):
        self.esv10401 = CreatePlotWindow()
        self.esv10401.show()
        self.esv10401.run_loop()

    def ti01ShowPlot(self):
        self.ti01 = CreatePlotWindow()
        self.ti01.show()
        self.ti01.run_loop()

    def tahh01ShowPlot(self):
        self.tahh01 = CreatePlotWindow()
        self.tahh01.show()
        self.tahh01.run_loop()

    def tic02ShowPlot(self):
        self.tic02 = CreatePlotWindow()
        self.tic02.show()
        self.tic02.run_loop()

    def pt10402ShowPlot(self):
        self.pt10402 = CreatePlotWindow()
        self.pt10402.show()
        self.pt10402.run_loop()
    
    def ti10402ShowPlot(self):
        self.ti10402 = CreatePlotWindow()
        self.ti10402.show()
        self.ti10402.run_loop()


    
