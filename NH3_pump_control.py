
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QFormLayout, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsLineItem)

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPolygonF, QFont, QColor, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsTextItem
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QFont
from PySide6.QtCore import QLineF

from app_stylesheets import Stylesheets

class NH3PumpControlScene(QWidget):

    def __init__(self):
        super().__init__()

        #Create Layout
        verticalLayout = QVBoxLayout()
        horizontalButtonLayout = QHBoxLayout()

        #Create Buttons
        self.zoomInButton = QPushButton("Zoom In")
        self.zoomOutButton = QPushButton("Zoom Out")
        self.zoomInButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.zoomOutButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        horizontalButtonLayout.addWidget(self.zoomInButton)
        horizontalButtonLayout.addWidget(self.zoomOutButton)

        self.zoomInButton.clicked.connect(self.Zoom_In)
        self.zoomOutButton.clicked.connect(self.Zoom_Out)

        #Create Graphics Scene, add to Graphics View Widget
        self.systemControlScene = QGraphicsScene()
        self.systemControlView = QGraphicsView(self.systemControlScene)
        self.systemControlView.setStyleSheet(Stylesheets.GraphicsViewStyleSheet())

        #view_size = self.systemControlView.viewport().size()
        #self.systemControlScene.setSceneRect(0, 0, view_size.width(), view_size.height())

        #Add Coordinate grid
        self.AddCoordinateGrid()

        #Add Components to scene
        self.CreateInputOutputLabel(40, 120, 20, "City\nwater", -520, 0)
        self.CreateInputOutputLabel(20, 120, 10, "N2/AIR", -250, -180)
        self.CreateInputOutputLabel(20, 120, 10, "VENT", 650, -180)
        self.CreateInputOutputLabel(40, 120, 20, "Water\nDrain", 700, 50)
        self.CreateInputOutputLabel(40, 120, 20, "Weighed\nBucket", 700, 150)

        self.CreateCircleLabel(25, "PG\n10501", 200, -300)
        self.CreateCircleLabel(25, "PRV\n10501", 300, -300)
        self.CreateCircleLabel(25, "PT\n10501", 400, -300)
        self.CreateCircleLabel(25, "ESV\n10401", -350, -100)
        self.CreateCircleLabel(25, "FE\n01", 500, -100)

        self.CreateTaggedCircleBox(25, "TI", "10401", -175, 200)
        self.CreateTaggedCircleBox(25, "PT", "10401", -75, 200)
        self.CreateTaggedCircleBox(25, "PT", "10402", 200, -100)
        self.CreateTaggedCircleBox(25, "TI", "10402", 300, -100)

        self.CreateLabeledBox(200, 200, "VENDOR\nPACKAGE", -100, -50)

        #Adding lines to scene
        #For Labels the X coordinate of line is Xcoord(Label) + width, Y coord is YCoord(Label) - height/2
        #For circles and tagged circles radius+Xcoord or radius + YCoord is center of circle, edge is diameter + XCoord or diameter + YCoord

        self.DrawConnectionLine(-400, -20, -150, -20, 2)  # City Water Label to TI 10401
        self.DrawConnectionLine(-150, -20, -150, 175, 2)  # City Water Label to TI 10401
        self.DrawConnectionLine(-150, 175,  -50, 175, 2)  # TI 10401 to PT 10401
        self.DrawConnectionLine(-50, 200, -50, 150, 2)    # PT 10401 to Vendor Package
        self.DrawConnectionLine(-325, -50, -325, -20, 2)  # ESV to City Water Label
        self.DrawConnectionLine(-130, -190, 660, -190, 2) # N2/AIR to Vent

        self.DrawConnectionLine(225, -250, 225, -190, 2)  # PG 10501 to N2/AIR and Vent Line
        self.DrawConnectionLine(325, -250, 325, -190, 2)  # PRV 10501 to N2/AIR and Vent Line
        self.DrawConnectionLine(425, -250, 425, -190, 2)  # PT 10501 to N2/AIR and Vent Line

        self.DrawConnectionLine(100, 30, 720, 30, 2)      # Vendor Package to Water Drain

        self.DrawConnectionLine(225, -50, 225, 30, 2)     # PT 10402 to Vendor Package and Water Drain Line
        self.DrawConnectionLine(325, -50, 325, 30, 2)     # TI 10402 to Vendor Package and Water Drain Line
        self.DrawConnectionLine(525, -50, 525, 30, 2)     # FE 01 to Vendor Package and Water Drain Line


        self.systemControlView.scale(0.9, 0.9)
        #self.systemControlView.translate()


        #Add Components to Layout
        verticalLayout.addLayout(horizontalButtonLayout)
        verticalLayout.addWidget(self.systemControlView)

        #Set Layout for self
        self.setLayout(verticalLayout)


    #Define functions for drawing individual components for the NH3 Pump, buttons and logic should also be part of this class

    def Zoom_In(self):
        self.systemControlView.scale(1.1, 1.1)

    def Zoom_Out(self):
        self.systemControlView.scale(0.9, 0.9)

    def DrawConnectionLine(self, x1, y1, x2, y2, thickness=2):
        """
        Draws a straight black line between two points in the scene.

        Parameters:
            x1, y1 (float): Starting point of the line
            x2, y2 (float): Ending point of the line
            thickness (float): Thickness of the line
        """
        line = QLineF(x1, y1, x2, y2)
        line_item = QGraphicsLineItem(line)
        pen = QPen(QColor("black"))
        pen.setWidthF(thickness)
        line_item.setPen(pen)
        self.systemControlScene.addItem(line_item)

    #height must be double the indent for this to work properly
    def CreateInputOutputLabel(self, height, width, indent, text, xPos, yPos):
        # height = 40
        # width = 120
        # indent = 20

        points = [
            # (x,y)
            QPointF(0, 0),
            QPointF(width - indent, 0),
            QPointF(width, -indent),
            QPointF(width - indent, -height),
            QPointF(0, -height),
            QPointF(indent, -indent)
        ]
        polygon = QPolygonF(points)
        polygon_item = QGraphicsPolygonItem(polygon)
        text_item = QGraphicsTextItem(text)
        text_item.setFont(QFont("Arial", 10, QFont.Bold))
        text_item.setParentItem(polygon_item)
        text_item.setPos(width/3, -height)
        polygon_item.setPos(xPos, yPos)
        self.systemControlScene.addItem(polygon_item)

    def CreateCircleLabel(self, radius, text, xPos, yPos):
        """
        Draws a circle with centered text and adds it to the scene.

        Parameters:
            radius (float): Radius of the circle
            text (str): Text to be centered inside the circle
            xPos (float): X position of the circle's top-left corner in the scene
            yPos (float): Y position of the circle's top-left corner in the scene
        """
        rect = QRectF(0, 0, radius * 2, radius * 2)
        circle_item = QGraphicsEllipseItem(rect)
        text_item = QGraphicsTextItem(text)
        text_item.setFont(QFont("Arial", 10, QFont.Bold))
        text_item.setParentItem(circle_item)
        text_rect = text_item.boundingRect()
        text_item.setPos(
            radius - text_rect.width() / 2,
            radius - text_rect.height() / 2
        )

        circle_item.setPos(xPos, yPos)
        self.systemControlScene.addItem(circle_item)

    def CreateTaggedCircleBox(self, radius, top_text, bottom_text, xPos, yPos):
        """
        Creates a circle inside a square box with a center line and two text labels (top and bottom).

        Parameters:
            radius (float): Radius of the circle
            top_text (str): Text to display above the center line
            bottom_text (str): Text to display below the center line
            xPos (float): X position for the group
            yPos (float): Y position for the group
        """
        size = radius * 2
        box_rect = QRectF(0, 0, size, size)
        center_y = size / 2

        # Create the box
        box_item = QGraphicsRectItem(box_rect)

        # Create the circle inside the box
        circle_item = QGraphicsEllipseItem(box_rect)
        circle_item.setParentItem(box_item)

        # Horizontal line through center
        center_line = QGraphicsLineItem(0, center_y, size, center_y)
        center_line.setParentItem(box_item)

        # Top text
        top_text_item = QGraphicsTextItem(top_text)
        top_text_item.setFont(QFont("Arial", 8, QFont.Bold))
        top_text_rect = top_text_item.boundingRect()
        top_text_item.setPos((size - top_text_rect.width()) / 2, center_y - top_text_rect.height())
        top_text_item.setParentItem(box_item)

        # Bottom text
        bottom_text_item = QGraphicsTextItem(bottom_text)
        bottom_text_item.setFont(QFont("Arial", 8, QFont.Bold))
        bottom_text_rect = bottom_text_item.boundingRect()
        bottom_text_item.setPos((size - bottom_text_rect.width()) / 2, center_y)
        bottom_text_item.setParentItem(box_item)

        # Position the whole structure
        box_item.setPos(xPos, yPos)

        # Add to scene
        self.systemControlScene.addItem(box_item)

    def CreateLabeledBox(self, width, height, label, xPos, yPos):
        """
        Draws a rectangular box with a centered label and adds it to the scene.

        Parameters:
            width (float): Width of the box
            height (float): Height of the box
            label (str): Text to center inside the box
            xPos (float): X position of the box in the scene
            yPos (float): Y position of the box in the scene
        """
        # Create rectangle item
        rect = QRectF(0, 0, width, height)
        box_item = QGraphicsRectItem(rect)

        # Create text item
        text_item = QGraphicsTextItem(label)
        text_item.setFont(QFont("Arial", 10, QFont.Bold))
        text_item.setParentItem(box_item)

        # Center text inside the box
        text_rect = text_item.boundingRect()
        text_item.setPos(
            (width - text_rect.width()) / 2,
            (height - text_rect.height()) / 2
        )

        # Position the whole item in the scene
        box_item.setPos(xPos, yPos)

        # Add to the scene
        self.systemControlScene.addItem(box_item)
    
    def AddCoordinateGrid(self, spacing=50, grid_size=1000):
        """
        Adds a coordinate grid to the scene to help with layout reference.
        
        Parameters:
            spacing (int): Distance between grid lines in scene units
            grid_size (int): Half-width/height of the grid extent (positive and negative)
        """
        pen = QPen(QColor(200, 200, 200))
        pen.setStyle(Qt.DotLine)
        pen.setWidth(1)

        # Vertical lines
        for x in range(-grid_size, grid_size + spacing, spacing):
            line = self.systemControlScene.addLine(x, -grid_size, x, grid_size, pen)
            line.setZValue(-1)

        # Horizontal lines
        for y in range(-grid_size, grid_size + spacing, spacing):
            line = self.systemControlScene.addLine(-grid_size, y, grid_size, y, pen)
            line.setZValue(-1)

        # Draw origin marker
        origin_pen = QPen(Qt.red)
        origin_pen.setWidth(2)
        self.systemControlScene.addLine(-10, 0, 10, 0, origin_pen)  # X axis at origin
        self.systemControlScene.addLine(0, -10, 0, 10, origin_pen)  # Y axis at origin

        # Optionally add labels at major points
        font = QFont("Arial", 10)
        for x in range(-grid_size, grid_size + spacing, spacing):
            if x == 0:
                continue
            label = QGraphicsTextItem(f"{x}")
            label.setFont(font)
            label.setDefaultTextColor(Qt.darkGray)
            label.setPos(x + 2, 2)
            label.setZValue(-1)
            self.systemControlScene.addItem(label)

        for y in range(-grid_size, grid_size + spacing, spacing):
            if y == 0:
                continue
            label = QGraphicsTextItem(f"{y}")
            label.setFont(font)
            label.setDefaultTextColor(Qt.darkGray)
            label.setPos(2, y + 2)
            label.setZValue(-1)
            self.systemControlScene.addItem(label)

