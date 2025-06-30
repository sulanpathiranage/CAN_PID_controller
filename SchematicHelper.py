
import math

from datetime import datetime

import pyqtgraph as pg

from app_stylesheets import Stylesheets

from PySide6.QtCore import (
    Qt,
    QPointF,
    QLineF,
    Signal,
    QTimer
)

from PySide6.QtGui import (
    QPolygonF,
    QFont,
    QColor,
    QPen,
    QPainterPath # Added QPainterPath here
)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QFormLayout, QGridLayout,
    QSizePolicy, QMessageBox,
    QDoubleSpinBox,
    QScrollArea, QTabWidget,
    QGraphicsView, QGraphicsPolygonItem, QGraphicsRectItem,
    QGraphicsLineItem, QGraphicsEllipseItem,
    QDialog
)

from PySide6.QtWidgets import QPushButton, QGraphicsProxyWidget, QGraphicsScene, QGraphicsTextItem
from collections import deque
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from time import sleep
from PySide6.QtCore import Slot
from threading import Thread
from PySide6.QtCore import QRectF

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

    def CreateDoubleTriangleValve(scene, xPos=0, yPos=0, size=20, label=""):
        """
        Draws two equilateral triangles pointing toward each other tip-to-tip (horizontal alignment).

        Parameters:
            scene (QGraphicsScene): The scene to draw into.
            xPos (float): Center X position of the symbol.
            yPos (float): Center Y position of the symbol.
            size (float): Length of each triangle side.
            label (str): Optional label below the symbol.
        """
        from PySide6.QtWidgets import QGraphicsPolygonItem, QGraphicsTextItem
        from PySide6.QtGui import QPolygonF, QPen, QColor, QFont
        from PySide6.QtCore import QPointF, Qt

        pen = QPen(QColor("blue"))
        pen.setWidth(2)

        height = (math.sqrt(3) / 2) * size  # Height of the triangle

        # Left triangle pointing right (→)
        left_points = [
            QPointF(0, 0),
            QPointF(-size, -height / 2),
            QPointF(-size, height / 2)
        ]
        left_triangle = QGraphicsPolygonItem(QPolygonF(left_points))
        left_triangle.setPen(pen)
        left_triangle.setBrush(Qt.GlobalColor.transparent)
        left_triangle.setPos(xPos, yPos)

        # Right triangle pointing left (←)
        right_points = [
            QPointF(0, 0),
            QPointF(size, -height / 2),
            QPointF(size, height / 2)
        ]
        right_triangle = QGraphicsPolygonItem(QPolygonF(right_points))
        right_triangle.setPen(pen)
        right_triangle.setBrush(Qt.GlobalColor.transparent)
        right_triangle.setPos(xPos, yPos)

        # Optional label
        if label:
            text_item = QGraphicsTextItem(label)
            text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            text_item.setDefaultTextColor(Qt.GlobalColor.black)
            text_rect = text_item.boundingRect()
            text_item.setPos(xPos - text_rect.width() / 2, yPos + height + 4)
            scene.addItem(text_item)

        # Add to scene
        scene.addItem(left_triangle)
        scene.addItem(right_triangle)

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
        text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
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
        text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
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
        top_text_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        top_text_rect = top_text_item.boundingRect()
        top_text_item.setPos((size - top_text_rect.width()) / 2, center_y - top_text_rect.height())
        top_text_item.setParentItem(box_item)

        # Bottom text
        bottom_text_item = QGraphicsTextItem(bottom_text)
        bottom_text_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
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
        text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
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
        pen.setStyle(Qt.PenStyle.DotLine)
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
        origin_pen = QPen(Qt.GlobalColor.red)
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
            label.setDefaultTextColor(Qt.GlobalColor.darkGray)
            label.setPos(x + 2, 2)
            label.setZValue(-1)
            label.setData(0, GRID_TAG)
            scene.addItem(label)

        for y in range(-grid_size, grid_size + spacing, spacing):
            if y == 0:
                continue
            label = QGraphicsTextItem(f"{y}")
            label.setFont(font)
            label.setDefaultTextColor(Qt.GlobalColor.darkGray)
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
    def __init__(self, scene: QGraphicsScene, func, buttonName="Plot", xCoord=0, yCoord=0):
        self.pushButton = QPushButton(buttonName)
        self.pushButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.pushButton.setFixedSize(80, 30)
        self.pushButton.clicked.connect(func)
        
        self.pushButtonProxy = QGraphicsProxyWidget()
        self.pushButtonProxy.setWidget(self.pushButton)
        
        scene.addItem(self.pushButtonProxy)
        self.pushButtonProxy.setPos(xCoord, yCoord)

class CreatePlotLabel():

    def __init__(self, scene, xCoord=0, yCoord=0):
        super().__init__()

        self.label = QLabel("000")
        self.label.setStyleSheet(Stylesheets.PlotLabelStyle())
        self.label.setFixedSize(80, 30)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
    update_label_signal = Signal(float)

    def __init__(
        self,
        label_func,
        title="Sample Plot",
        poll_rate=1,
        y_label="Temperature",
        y_unit="°C",
        x_label="Time",
        x_unit="s",
        parent=None
    
    ):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(200, 200)

        self.poll_rate = poll_rate
        self.labelUpdateFunc = label_func

        self.history_len = 100
        self.data = deque([0.0] * self.history_len, maxlen=self.history_len)

        self.label = QLabel("Starting...")
        layout = QVBoxLayout()


        self.plot_widget = LivePlotWidget()
        self.plot_widget.setLabel('left', y_label, units=y_unit)
        self.plot_widget.setLabel('bottom', x_label, units=x_unit)
        self.plot_widget.showGrid(x=True, y=True)

        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='r', width=2), name="Data")
        self.connector = DataConnector(plot=self.curve, max_points=100, update_rate=10, plot_rate=10)

        layout.addWidget(self.label)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        self.update_plot_signal.connect(self.update_plot)
        self.update_label_signal.connect(self.update_label)

        self.connected = False  # Flag: Is data source connected?

    # Start collecting data in an async thread
    #self.dataCollectionTask = asyncio.create_task(self.run()) # Have the same thread call the polling function

    async def run(self, value):
        #while True:
        # await asyncio.sleep(self.poll_rate)
        # value = await self.data_func()
        self.data.append(value)
        #print("Updating plots")
        self.update_plot_signal.emit(list(self.data))
        self.update_label_signal.emit(value)

            
    def update_plot(self, data):
        time_axis = [i * 0.1 for i in range(self.history_len)] # For sliding window of only last 10 seconds, otherwise use line above

        for i in range(len(data)):
            self.connector.add_xy_data_point(time_axis[i], data[i])
    
    def update_label(self, data_val):
        self.labelUpdateFunc(f"{data_val:.3g}"[:4].ljust(4))

class CreateLivePlotWindow(QDialog):
    update_label_signal = Signal(str)
    refresh_plot_signal = Signal()

    def __init__(
        self,
        label_func,
        title="Sample Plot",
        poll_rate=1,
        y_label="Temperature",
        y_unit="°C",
        x_label="Time",
        x_unit="s",
        parent=None
    ):
        super().__init__(parent)

        self._poll_rate = poll_rate
        
        self.refresh_plot_signal.connect(self.update_plot)

        self.labelUpdateFunc = label_func
        self.update_label_signal.connect(self._update_label)

        self.setWindowTitle(title)
        self.resize(700, 400)

        self.poll_rate = poll_rate
        self.labelUpdateFunc = label_func

        self.label = QLabel("Starting...", alignment=Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

        # Setup matplotlib figure
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylabel(f"{y_label} ({y_unit})")
        self.ax.set_xlabel(f"{x_label} ({x_unit})")
        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, 100)
        self.ax.grid(True)

        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.curve, = self.ax.plot([], [], 'r-', linewidth=2)
        self.x_vals = deque(maxlen=100)
        self.y_vals = deque(maxlen=100)
        self.x = 0
 
        # self.update_label_signal.connect(self.labelUpdateFunc)

        # Setup plot refresher
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_plot)
        self.refresh_timer.start(100)  # ~20 FPS

        self.running = False

    def start_data_feed(self):
        self.running = True
        self.thread = Thread(target=self._data_feed_loop, daemon=True)
        self.thread.start()

    def _data_feed_loop(self):
        while self.running:
            self.x += 1
            y = math.sin(self.x * 0.02) * 50 + 50
            self.x_vals.append(self.x)
            self.y_vals.append(y)
            self.update_label_signal.emit(f"{y:.2f}")
            sleep(self._poll_rate)

    def update_plot(self):
        if not self.running:
            return
        self.curve.set_data(self.x_vals, self.y_vals)
        if self.x_vals:
            self.ax.set_xlim(max(0, self.x_vals[0]), self.x_vals[-1])
        self.canvas.draw_idle()


    def stop_data_feed(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()

    def closeEvent(self, event):
        event.ignore()   # hide only
        self.hide()

    @Slot(str)
    def _update_label(self, value: str):
        self.labelUpdateFunc(value)

    def load_initial_data(self, data):
        self.x_vals.clear()
        self.y_vals.clear()
        for i, val in enumerate(data):
            self.x_vals.append(i)
            self.y_vals.append(val)
        self.canvas.draw()

    def start_plotting(self):
        self.running = True
        self.refresh_timer.start(100)

    def stop_plotting(self):
        self.running = False
        self.refresh_timer.stop()

    def set_external_buffer(self, x_vals, y_vals, counter_ref):
        self.x_vals = x_vals
        self.y_vals = y_vals
        self.counter_ref = counter_ref  # a reference to the running counter


# sensor_plot.py  (new file or put at top of SchematicHelper)
class SensorPlot:
    """
    Wraps:  • QLabel on the P&ID   • LivePlotWindow   • feed thread
    Keeps everything for one indicator in one object.
    """

    def __init__(self, scene: QGraphicsScene, name: str,
                 pos: tuple[int, int], units: str,
                 live: bool = True,  # False → simple history plot
                 color: str = 'r'):

        # --- label on the main schematic ---
        self.label = CreatePlotLabel(scene, *pos)
        self.label.setLabelText("--")

        x_btn, y_btn = pos[0], pos[1] + 40
        self.button = CreatePlotButton(scene, self._open_plot, "Plot", x_btn, y_btn)
        self.button.pushButton.setEnabled(False)

        self._x_counter = 0
        self._data_buffer = deque(maxlen=1000)
        self.x_vals = deque(maxlen=1000)
        self.y_vals = deque(maxlen=1000)

        # --- pop-up plot window ---
        if live:
            self.plot = CreateLivePlotWindow(self.label.setLabelText,
                                             f"{name} Plot",
                                             poll_rate=0.1,
                                             y_label=name,
                                             y_unit=units)
        else:
            self.plot = CreatePlotWindow(self.label.setLabelText,
                                         f"{name} Plot",
                                         y_label=name,
                                         y_unit=units)

        # --- internal sine-wave generator (replace with real data) ---
        self._running = False
        self._thread = None

        self.plot.set_external_buffer(self.x_vals, self.y_vals, self._x_counter)
    
    def _open_plot(self):
        self.plot.x_vals.clear()
        self.plot.y_vals.clear()
        self.plot.start_plotting()
        self.plot.show()

    # ---------------- feed control ----------------
    def start(self, poll_rate=0.1, freq=0.02):
        # Starts collecting dummy data, but doesn't open plot
        self._running = True
        self._x_counter = 0
        self._data_buffer = deque(maxlen=500)
        self._thread = Thread(target=self._collect_data_loop, args=(poll_rate, freq), daemon=True)
        self._thread.start()

        # Start a timer to check when data is ready
        self._enable_timer = QTimer()
        self._enable_timer.setInterval(200)  # check every 200ms
        self._enable_timer.timeout.connect(self._check_data_ready)
        self._enable_timer.start()

    def _check_data_ready(self):
        if len(self._data_buffer) > 5:  # Wait until a few values are available
            print("[DEBUG] Buffer filled. Enabling button.")
            self.button.pushButton.setEnabled(True)
            self._enable_timer.stop()

    def stop(self):
        self._running = False
        if hasattr(self.plot, "stop_data_feed"):
            self.plot.stop_data_feed()
        if self._thread:
            self._thread.join()

    def _loop(self, poll_rate, freq):
        x = 0
        while self._running:
            x += 1
            val = math.sin(x * freq) * 50 + 50

            self.plot.x_vals.append(x)
            self.plot.y_vals.append(val)
            self.plot.update_label_signal.emit(f"{val:.2f}")
            self.plot.refresh_plot_signal.emit()

            sleep(poll_rate)

    def _collect_data_loop(self, poll_rate, freq):
        while self._running:
            self._x_counter += 1
            val = math.sin(self._x_counter * freq) * 50 + 50
            self.label.setLabelText(f"{val:.2f}")
            self._data_buffer.append(val)
            self.x_vals.append(self._x_counter)
            self.y_vals.append(val)
            sleep(poll_rate)