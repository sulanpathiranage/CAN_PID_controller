
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QFormLayout, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsLineItem, QDialog, QGraphicsProxyWidget)

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPolygonF, QFont, QColor, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsTextItem
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QFont
from PySide6.QtCore import QLineF

from app_stylesheets import Stylesheets
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

from datetime import datetime

import time
import random
import pyqtgraph as pg
import asyncio

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class SchematicHelperFunctions:

    def Zoom_In(scene):
        scene.scale(1.1, 1.1)

    def Zoom_Out(scene):
        scene.scale(0.9, 0.9)

    def DrawConnectionLine(scene, x1, y1, x2, y2, thickness=2):
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
        scene.addItem(line_item)

    #height must be double the indent for this to work properly
    def CreateInputOutputLabel(scene, height, width, indent, text, xPos, yPos):
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
        scene.addItem(polygon_item)

    def CreateCircleLabel(scene, radius, text, xPos, yPos):
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
        scene.addItem(circle_item)

    def CreateTaggedCircleBox(scene, radius, top_text, bottom_text, xPos, yPos):
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
        scene.addItem(box_item)

    def CreateLabeledBox(scene, width, height, label, xPos, yPos):
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
        scene.addItem(box_item)
    
    def AddCoordinateGrid(scene, spacing=50, grid_size=1000):
        """
        Adds a coordinate grid to the scene, tagged for later removal.
        """
        GRID_TAG = "grid"

        pen = QPen(QColor(200, 200, 200))
        pen.setStyle(Qt.DotLine)
        pen.setWidth(1)

        # Vertical lines
        for x in range(-grid_size, grid_size + spacing, spacing):
            line = scene.addLine(x, -grid_size, x, grid_size, pen)
            line.setZValue(-1)
            line.setData(0, GRID_TAG)

        # Horizontal lines
        for y in range(-grid_size, grid_size + spacing, spacing):
            line = scene.addLine(-grid_size, y, grid_size, y, pen)
            line.setZValue(-1)
            line.setData(0, GRID_TAG)

        # Origin marker (thicker red lines)
        origin_pen = QPen(Qt.red)
        origin_pen.setWidth(2)
        line_x = scene.addLine(-10, 0, 10, 0, origin_pen)
        line_x.setZValue(-1)
        line_x.setData(0, GRID_TAG)

        line_y = scene.addLine(0, -10, 0, 10, origin_pen)
        line_y.setZValue(-1)
        line_y.setData(0, GRID_TAG)

        # Axis labels
        font = QFont("Arial", 10)
        for x in range(-grid_size, grid_size + spacing, spacing):
            if x == 0:
                continue
            label = QGraphicsTextItem(f"{x}")
            label.setFont(font)
            label.setDefaultTextColor(Qt.darkGray)
            label.setPos(x + 2, 2)
            label.setZValue(-1)
            label.setData(0, GRID_TAG)
            scene.addItem(label)

        for y in range(-grid_size, grid_size + spacing, spacing):
            if y == 0:
                continue
            label = QGraphicsTextItem(f"{y}")
            label.setFont(font)
            label.setDefaultTextColor(Qt.darkGray)
            label.setPos(2, y + 2)
            label.setZValue(-1)
            label.setData(0, GRID_TAG)
            scene.addItem(label)

    def RemoveCoordinateGrid(scene):
        """
        Removes all items previously added by AddCoordinateGrid using the 'grid' tag.
        """
        GRID_TAG = "grid"
        for item in scene.items():
            if item.data(0) == GRID_TAG:
                scene.removeItem(item)

class RoundedProxy(QGraphicsProxyWidget):
    def paint(self, painter, option, widget):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 3, 3)
        painter.setClipPath(path)
        super().paint(painter, option, widget)

class CreatePlotButton():

    def __init__(self, scene, func, buttonName="Plot", xCoord=0, yCoord=0):
        super().__init__()
        
        self.pushButton = QPushButton(buttonName)
        self.pushButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.pushButton.setFixedSize(80, 30)
        self.pushButton.clicked.connect(func)
        self.pushButtonProxy = RoundedProxy()
        self.pushButtonProxy.setWidget(self.pushButton)
        scene.addItem(self.pushButtonProxy)
        self.pushButtonProxy.setPos(xCoord, yCoord)

class CreatePlotLabel():

    def __init__(self, scene, xCoord=0, yCoord=0):
        super().__init__()

        self.label = QLabel("000")
        self.label.setStyleSheet(Stylesheets.PlotLabelStyle())
        self.label.setFixedSize(80, 30)
        self.label.setAlignment(Qt.AlignCenter)
        self.labelProxy = RoundedProxy()
        self.labelProxy.setWidget(self.label)
        scene.addItem(self.labelProxy)
        self.labelProxy.setPos(xCoord, yCoord)
    
    def setLabelText(self, text="---"):
        self.label.setText(text)

    def setLabelColorGreen(self):
        self.label.setStyleSheet(Stylesheets.LabelStyleGreen())

    def setLabelColorRed(self):
        self.label.setStyleSheet(Stylesheets.LabelStyleRed())


class CreatePlotWindow(QDialog):

    update_plot_signal = Signal(list)

    def __init__(self, data_func, title="Sample Plot", poll_rate=1.0, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(200,200)
        
        self.poll_rate = poll_rate
        self.data_func = data_func
        self.data = [] # Data stored here, as part of the class

        self.label = QLabel("Starting...")
        self.plot_widget = pg.PlotWidget()
        layout = QVBoxLayout()

        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time (Index)')
        self.plot_widget.showGrid(x=True, y=True)
        self.curve = self.plot_widget.plot([], [], pen='g', symbol='o')

        layout.addWidget(self.label)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # Connect signal to slot
        self.update_plot_signal.connect(self.update_plot)

        # Start collecting data in an async thread
        self.dataCollectionTask = asyncio.create_task(self.run())

    async def run(self):
        while True:
            await asyncio.sleep(self.poll_rate)
            value = await self.data_func()
            self.data.append(value)

            x = list(range(len(self.data)))
            self.update_plot_signal.emit(x)
            

    @Slot(list)
    def update_plot(self, x):
        self.curve.setData(x, self.data)
        print(f"Plotting {len(self.data)} points")
            
