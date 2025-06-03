
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QFormLayout, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsProxyWidget, QSpacerItem)

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPolygonF, QFont, QColor, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsTextItem
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QFont
from PySide6.QtCore import QLineF

from app_stylesheets import Stylesheets
from SchematicHelper import SchematicHelperFunctions
from SchematicHelper import CreatePlotWindow
from functools import partial

class NH3PumpControlScene(QWidget):

    def __init__(self):
        super().__init__()

        #Create Layout
        verticalLayout = QVBoxLayout()
        horizontalButtonLayout = QHBoxLayout()
        self.nh3_pump_label = QLabel("NH3 PUMP TEST-1")

        #Create Graphics Scene, add to Graphics View Widget
        self.systemControlScene = QGraphicsScene()
        self.systemControlView = QGraphicsView(self.systemControlScene)
        self.systemControlView.setStyleSheet(Stylesheets.GraphicsViewStyleSheet())

        #Create Zoom Buttons
        self.zoomInButton = QPushButton("Zoom In")
        self.zoomOutButton = QPushButton("Zoom Out")
        self.zoomInButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.zoomOutButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())

        #Create Spacer
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        #Add Zoom buttons and spacer to horizontal layout
        horizontalButtonLayout.addWidget(self.nh3_pump_label)
        horizontalButtonLayout.addItem(self.horizontalSpacer)
        horizontalButtonLayout.addWidget(self.zoomInButton)
        horizontalButtonLayout.addWidget(self.zoomOutButton)
        
        self.zoomInButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_In, self.systemControlView))
        self.zoomOutButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_Out, self.systemControlView))

        #Create View Data Buttons 
        # ESV10401 Button
        self.esv10401Button = QPushButton("Plot")
        self.esv10401Button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.esv10401Proxy = QGraphicsProxyWidget()
        self.esv10401Proxy.setWidget(self.esv10401Button)
        self.systemControlScene.addItem(self.esv10401Proxy)
        self.esv10401Proxy.setPos(-350, -140)

        # TI10401 Button
        self.ti10401Button = QPushButton("Plot")
        self.ti10401Button.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.ti10401Proxy = QGraphicsProxyWidget()
        self.ti10401Proxy.setWidget(self.ti10401Button)
        self.systemControlScene.addItem(self.ti10401Proxy)
        self.ti10401Button.clicked.connect(self.ti10401ShowPlot)
        self.ti10401Proxy.setPos(-175, 260)

        # PT10401 Button
        self.pt10401 = QPushButton("Plot")
        self.pt10401.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.pt10401Proxy = QGraphicsProxyWidget()
        self.pt10401Proxy.setWidget(self.pt10401)
        self.systemControlScene.addItem(self.pt10401Proxy)
        self.pt10401Proxy.setPos(-75, 260)

        # PRV01 Button
        self.prv01 = QPushButton("Plot")
        self.prv01.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.prv01Proxy = QGraphicsProxyWidget()
        self.prv01Proxy.setWidget(self.prv01)
        self.systemControlScene.addItem(self.prv01Proxy)
        self.prv01Proxy.setPos(150, 160)

        # P101 Button
        self.p101 = QPushButton("Plot")
        self.p101.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.p101Proxy = QGraphicsProxyWidget()
        self.p101Proxy.setWidget(self.p101)
        self.systemControlScene.addItem(self.p101Proxy)
        self.p101Proxy.setPos(50, -180)

        # PG10501 Button
        self.pg10501 = QPushButton("Plot")
        self.pg10501.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.pg10501Proxy = QGraphicsProxyWidget()
        self.pg10501Proxy.setWidget(self.pg10501)
        self.systemControlScene.addItem(self.pg10501Proxy)
        self.pg10501Proxy.setPos(200, -340)

        # PRV10501 Button
        self.prv10501 = QPushButton("Plot")
        self.prv10501.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.prv10501Proxy = QGraphicsProxyWidget()
        self.prv10501Proxy.setWidget(self.prv10501)
        self.systemControlScene.addItem(self.prv10501Proxy)
        self.prv10501Proxy.setPos(300, -340)

        # PT10501 Button
        self.pt10501 = QPushButton("Plot")
        self.pt10501.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.pt10501Proxy = QGraphicsProxyWidget()
        self.pt10501Proxy.setWidget(self.pt10501)
        self.systemControlScene.addItem(self.pt10501Proxy)
        self.pt10501Proxy.setPos(400, -340)

        # PT10402 Button
        self.pt10402 = QPushButton("Plot")
        self.pt10402.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.pt10402Proxy = QGraphicsProxyWidget()
        self.pt10402Proxy.setWidget(self.pt10402)
        self.systemControlScene.addItem(self.pt10402Proxy)
        self.pt10402Proxy.setPos(200, -140)

        # TI10402 Button
        self.ti10402 = QPushButton("Plot")
        self.ti10402.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.ti10402Proxy = QGraphicsProxyWidget()
        self.ti10402Proxy.setWidget(self.ti10402)
        self.systemControlScene.addItem(self.ti10402Proxy)
        self.ti10402Proxy.setPos(300, -140)

        # FE01 Button
        self.fe01 = QPushButton("Plot")
        self.fe01.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.fe01Proxy = QGraphicsProxyWidget()
        self.fe01Proxy.setWidget(self.fe01)
        self.systemControlScene.addItem(self.fe01Proxy)
        self.fe01Proxy.setPos(500, -140)

        #view_size = self.systemControlView.viewport().size()
        #self.systemControlScene.setSceneRect(0, 0, view_size.width(), view_size.height())

        #Add Coordinate grid
        SchematicHelperFunctions.AddCoordinateGrid(self.systemControlScene)

        #Add Components to scene
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "City\nwater", -520, 0)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "N2/AIR", -250, -180)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 20, 120, 10, "VENT", 650, -180)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "Water\nDrain", 700, 50)
        SchematicHelperFunctions.CreateInputOutputLabel(self.systemControlScene, 40, 120, 20, "Weighed\nBucket", 700, 150)

        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PG\n10501", 200, -300)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n10501", 300, -300)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PT\n10501", 400, -300)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "ESV\n10401", -350, -100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "FE\n01", 500, -100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "PRV\n01", 150, 100)
        SchematicHelperFunctions.CreateCircleLabel(self.systemControlScene, 25, "P1\n01", 50, -150)

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10401", -175, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PT", "10401", -75, 200)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PT", "10402", 200, -100)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10402", 300, -100)

        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 200, 200, "VENDOR\nPACKAGE", -100, -50)

        #Adding lines to scene
        #For Labels the X coordinate of line is Xcoord(Label) + width, Y coord is YCoord(Label) - height/2
        #For circles and tagged circles radius+Xcoord or radius + YCoord is center of circle, edge is diameter + XCoord or diameter + YCoord

        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -400, -20, -150, -20, 2)  # City Water Label to TI 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, -20, -150, 175, 2)  # City Water Label to TI 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -150, 175,  -50, 175, 2)  # TI 10401 to PT 10401
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -50, 200, -50, 150, 2)    # PT 10401 to Vendor Package
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -325, -50, -325, -20, 2)  # ESV to City Water Label
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, -130, -190, 660, -190, 2) # N2/AIR to Vent
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 225, -250, 225, -190, 2)  # PG 10501 to N2/AIR and Vent Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 325, -250, 325, -190, 2)  # PRV 10501 to N2/AIR and Vent Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 425, -250, 425, -190, 2)  # PT 10501 to N2/AIR and Vent Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 30, 720, 30, 2)      # Vendor Package to Water Drain
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 225, -50, 225, 30, 2)     # PT 10402 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 325, -50, 325, 30, 2)     # TI 10402 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 525, -50, 525, 30, 2)     # FE 01 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 400, -190, 400, 30, 2)    # PT 10501 to Vendor Package and Water Drain Line
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 600, 30, 600, 130, 2)     # Vendor Package and Water Drain Line to Weighed Bucket
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 600, 130, 720, 130, 2)    # Vendor Package and Water Drain Line to Weighed Bucket (horizontal portion)
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 100, 125, 150, 125, 2)    # Vendor Package to PRV 01
        SchematicHelperFunctions.DrawConnectionLine(self.systemControlScene, 75, -100, 75, -50, 2)     # Vendor Package to P1 01

        self.systemControlView.scale(0.9, 0.9)

        #Add Components to Layout
        verticalLayout.addLayout(horizontalButtonLayout)
        verticalLayout.addWidget(self.systemControlView)

        #Set Layout for self
        self.setLayout(verticalLayout)

    def ti10401ShowPlot(self):

        self.ti10401 = CreatePlotWindow()
        #self.ti10401.setParent(QApplication.activeWindow())
        self.ti10401.show()
        self.ti10401.run_loop()

    

