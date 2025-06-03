
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

        #Create Zoom Buttons
        self.zoomInButton = QPushButton("Zoom In")
        self.zoomOutButton = QPushButton("Zoom Out")
        self.zoomInButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.zoomOutButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        horizontalButtonLayout.addWidget(self.nh3_pump_label)
        horizontalButtonLayout.addItem(self.horizontalSpacer)
        horizontalButtonLayout.addWidget(self.zoomInButton)
        horizontalButtonLayout.addWidget(self.zoomOutButton)
        
        self.zoomInButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_In, self.systemControlView))
        self.zoomOutButton.clicked.connect(partial(SchematicHelperFunctions.Zoom_Out, self.systemControlView))

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

        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10401", -300, 550)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PT", "10401", -200, 550)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "PT", "10402", 250, 50)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "10402", 350, 50)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TI", "01", -150, -100) #change inside of this to a triangle
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TAHH", "01", -150, 50)
        SchematicHelperFunctions.CreateTaggedCircleBox(self.systemControlScene, 25, "TIC", "02", 0, 100)


        SchematicHelperFunctions.CreateLabeledBox(self.systemControlScene, 300, 300, "VENDOR\nPACKAGE", -200, 200)

        self.systemControlView.scale(0.9, 0.9)

        #Add Components to Layout
        verticalLayout.addLayout(horizontalButtonLayout)
        verticalLayout.addWidget(self.systemControlView)

        #Set Layout for self
        self.setLayout(verticalLayout)


    #Define functions for drawing individual components for the NH3 Pump, buttons and logic should also be part of this class 
    
