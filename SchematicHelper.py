import sys
from datetime import datetime
import time
import random
import asyncio

import pyqtgraph as pg

from app_stylesheets import Stylesheets

from PySide6.QtCore import (
    Qt,
    QPointF,
    QRectF,
    QLineF,
    Signal,
    QTimer
)

from PySide6.QtGui import (
    QPolygonF,
    QFont,
    QColor,
    QPen,
    QPainterPath
)

from PySide6.QtWidgets import (
    QApplication,
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
import pyqtgraph as pg
from collections import deque
from typing import List, Dict, Any, Union, Tuple

from data_manager import SystemDataManager
from typing import Callable


class SchematicHelperFunctions:
    """
    Collection of **static** helper routines for drawing P&ID primitives.

    All methods operate purely on a provided :class:`~PySide6.QtWidgets.QGraphicsScene`
    instance and therefore have no hidden side effects or shared state.
    The methods are designed to be stateless and reusable, allowing for easy
    integration into any PySide6 application that requires P&ID schematic
    rendering capabilities.

    The methods include zooming functionality, drawing connection lines,
    creating input/output labels, circles, tagged boxes, and coordinate grids,
    and more. They are intended to be used in a graphical context where
    graphical items need to be added to a scene for visualization.

    The methods are designed to be flexible and customizable, allowing for
    various parameters to control the appearance and behavior of the drawn
    elements.
    """
    @staticmethod
    def zoom_in(view: QGraphicsView) -> None:        
        """
        Zoom *in* the supplied graphics view by 10 %.

        Parameters
        -------
        view
            The view that should be scaled.

        Returns
        -------
        None

        Notes
        -------
        This method scales the view by a factor of 1.1, effectively zooming in
        on the content displayed in the view.

        This method modifies the view's scale directly, so it should be called
        when the view is already set up and ready to display content.
        The zoom factor of 1.1 means that each time this method is called,
        the content will appear 10% larger than before.
        """
        view.scale(1.1, 1.1)

    @staticmethod
    def zoom_out(view: QGraphicsView) -> None:
        """
        Zoom *out* the supplied graphics view by 10 %.

        Parameters
        -------
        view
            The view that should be scaled.

        Returns
        -------
        None

        Notes
        -------
        This method scales the view by a factor of 0.9, effectively zooming out
        on the content displayed in the view.

        This method modifies the view's scale directly, so it should be called
        when the view is already set up and ready to display content.
        The zoom factor of 0.9 means that each time this method is called,
        the content will appear 10% smaller than before.
        """
        view.scale(0.9, 0.9)

    @staticmethod
    def DrawConnectionLine(
        scene: QGraphicsScene,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        thickness: int | float = 2,
        ) -> None:
        """
        Draw a straight connection line on *scene*.

        Parameters
        -------
        scene
            Target scene.
        x1, y1, x2, y2
            End-point coordinates (scene−space).
        thickness
            Pen width in device-independent pixels.  Defaults to *2*.

        Returns
        -------
        None

        -------
        This method creates a line item in the scene that connects the two
        specified points (*x1*, *y1*) and (*x2*, *y2*). The line is drawn with
        the specified thickness, which defaults to 2 device-independent pixels.
        """
        line = QLineF(x1, y1, x2, y2)
        line_item = QGraphicsLineItem(line)
        pen = QPen(QColor("black"))
        pen.setWidthF(thickness)
        line_item.setPen(pen)
        scene.addItem(line_item)

    @staticmethod
    def CreateInputOutputLabel(
        scene: QGraphicsScene,
        height: float,
        width: float,
        indent: float,
        text: str,
        xPos: float,
        yPos: float,
    ) -> None:
        """
        Add a six‑sided I/O label (often used for PLC *tags*).
        
        Parameters
        -------
        scene
            Target scene.
        height
            Height of the label in scene units.
        width
            Width of the label in scene units.
        indent
            Indentation of the arrow notch in scene units.
        text
            Text to display inside the label.
        xPos, yPos
            Position of the label in scene units (top-left corner).

        Returns
        -------
        None

        Notes
        -------
        The method draws an arrow‑notched hexagon and centres *text* inside.
        Coordinates are relative to the top‑left corner of the shape.
        Parameters

        This method creates a polygon item representing a six-sided label with
        an arrow notch and adds it to the specified scene. The text is centered 
        inside the polygon. The label is positioned at the specified coordinates
        (*xPos*, *yPos*), and the polygon is defined by the given *height*,
        *width*, and *indent* parameters. 

        The label is drawn as a hexagon with an arrow notch on the right side.
        The text is set in a bold Arial font and colored black. The label can
        be used to represent input/output tags in a P&ID schematic.
        """
        points = [
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
        text_item.setDefaultTextColor(Qt.black) # Set text color to BLACK
        text_item.setParentItem(polygon_item)
        text_item.setPos(width/3, -height)
        polygon_item.setPos(xPos, yPos)
        scene.addItem(polygon_item)

    @staticmethod
    def CreateCircleLabel(
        scene: QGraphicsScene,
        radius: float,
        text: str,
        xPos: float,
        yPos: float,
    ) -> None:
        """
        Draw a circular tag with centred *text*.
        The circle is centred at (*xPos*, *yPos*) and has a diameter of *radius*.

        Parameters
        -------
        scene
            Target scene.
        radius
            Radius of the circle in scene units.
        text
            Text to display inside the circle.
        xPos, yPos
            Position of the circle in scene units (top-left corner).

        Returns
        -------
        None

        Notes
        -------
        This method creates a circular item in the scene with the specified
        radius and positions it at the specified coordinates (*xPos*, *yPos*).
        The text is centered inside the circle. The circle is drawn as a filled
        ellipse, and the text is set in a bold Arial font and colored black.
        The circle can be used to represent tags or labels in a P&ID schematic.
        """
        rect = QRectF(0, 0, radius * 2, radius * 2)
        circle_item = QGraphicsEllipseItem(rect)
        text_item = QGraphicsTextItem(text)
        text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text_item.setDefaultTextColor(Qt.black) # Set text color to BLACK
        text_item.setParentItem(circle_item)
        text_rect = text_item.boundingRect()
        text_item.setPos(
            radius - text_rect.width() / 2,
            radius - text_rect.height() / 2
        )
        circle_item.setPos(xPos, yPos)
        scene.addItem(circle_item)

    @staticmethod
    def CreateTaggedCircleBox(
        scene: QGraphicsScene,
        radius: float,
        top_text: str,
        bottom_text: str,
        xPos: float,
        yPos: float,
        ) -> None:
        """
        Draw a square bounding box that contains a bisected circle.

        The upper and lower halves are annotated with *top_text* and
        *bottom_text* respectively—useful e.g. for pump IDs “P–101 A/B”.    
        """
        size = radius * 2
        box_rect = QRectF(0, 0, size, size)
        center_y = size / 2

        box_item = QGraphicsRectItem(box_rect)
        circle_item = QGraphicsEllipseItem(box_rect)
        circle_item.setParentItem(box_item)

        center_line = QGraphicsLineItem(0, center_y, size, center_y)
        center_line.setParentItem(box_item)

        top_text_item = QGraphicsTextItem(top_text)
        top_text_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        top_text_item.setDefaultTextColor(Qt.black) # Set text color to BLACK
        top_text_rect = top_text_item.boundingRect()
        top_text_item.setPos((size - top_text_rect.width()) / 2, center_y - top_text_rect.height())
        top_text_item.setParentItem(box_item)

        bottom_text_item = QGraphicsTextItem(bottom_text)
        bottom_text_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        bottom_text_item.setDefaultTextColor(Qt.black) # Set text color to BLACK
        bottom_text_rect = bottom_text_item.boundingRect()
        bottom_text_item.setPos((size - bottom_text_rect.width()) / 2, center_y)
        bottom_text_item.setParentItem(box_item)

        box_item.setPos(xPos, yPos)
        scene.addItem(box_item)

    @staticmethod
    def CreateLabeledBox(
        scene: QGraphicsScene,
        width: float,
        height: float,
        label: str,
        xPos: float,
        yPos: float,
    ) -> None:
        """
        Draw a plain rectangle with *label* centred inside. 
        The rectangle is positioned at (*xPos*, *yPos*) and has the specified
        *width* and *height*.
        """
        rect = QRectF(0, 0, width, height)
        box_item = QGraphicsRectItem(rect)
        text_item = QGraphicsTextItem(label)
        text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text_item.setDefaultTextColor(Qt.black) # Set text color to BLACK
        text_item.setParentItem(box_item)
        text_rect = text_item.boundingRect()
        text_item.setPos(
            (width - text_rect.width()) / 2,
            (height - text_rect.height()) / 2
        )
        box_item.setPos(xPos, yPos)
        scene.addItem(box_item)
    
    @staticmethod
    def AddCoordinateGrid(
        scene: QGraphicsScene,
        *,
        spacing: int = 50,
        grid_size: int = 1000,
    ) -> None:
        """
        Super‑impose a dotted coordinate grid on *scene*.

        Parameters
        -------
        spacing
            Major grid spacing (both axes) in scene units.
        grid_size
            Grid half‑width/height.  A value of *1000* draws from −1000 to +1000.
        """
        GRID_TAG = "grid"
        pen = QPen(QColor(200, 200, 200))
        pen.setStyle(Qt.PenStyle.DotLine)
        pen.setWidth(1)

        for x in range(-grid_size, grid_size + spacing, spacing):
            line = scene.addLine(x, -grid_size, x, grid_size, pen)
            line.setZValue(-1)
            line.setData(0, GRID_TAG)

        for y in range(-grid_size, grid_size + spacing, spacing):
            line = scene.addLine(-grid_size, y, grid_size, y, pen)
            line.setZValue(-1)
            line.setData(0, GRID_TAG)

        # origin cross-hairs
        origin_pen = QPen(Qt.GlobalColor.red)
        origin_pen.setWidth(2)
        line_x = scene.addLine(-10, 0, 10, 0, origin_pen)
        line_x.setZValue(-1)
        line_x.setData(0, GRID_TAG)

        line_y = scene.addLine(0, -10, 0, 10, origin_pen)
        line_y.setZValue(-1)
        line_y.setData(0, GRID_TAG)

        # labels for grid lines
        font = QFont("Arial", 10)
        for x in range(-grid_size, grid_size + spacing, spacing):
            if x == 0:
                continue
            label = QGraphicsTextItem(f"{x}")
            label.setFont(font)
            label.setDefaultTextColor(Qt.darkGray) # Set grid labels to dark gray
            label.setPos(x + 2, 2)
            label.setZValue(-1)
            label.setData(0, GRID_TAG)
            scene.addItem(label)

        for y in range(-grid_size, grid_size + spacing, spacing):
            if y == 0:
                continue
            label = QGraphicsTextItem(f"{y}")
            label.setFont(font)
            label.setDefaultTextColor(Qt.darkGray) # Set grid labels to dark gray
            label.setPos(2, y + 2)
            label.setZValue(-1)
            label.setData(0, GRID_TAG)
            scene.addItem(label)

    @staticmethod
    def RemoveCoordinateGrid(scene: QGraphicsScene) -> None:
        """
        Remove all grid items previously added via :py:meth:`AddCoordinateGrid`.
        This method searches for items tagged with "grid" and removes them
        from the scene.
        """
        GRID_TAG = "grid"
        for item in scene.items():
            if item.data(0) == GRID_TAG:
                scene.removeItem(item)

    @staticmethod
    def CreateDoubleTriangleValve(
        scene: QGraphicsScene,
        xPos: float,
        yPos: float,
        size: float,
        label: str,
    ) -> None:
        """
        Draw an ANSI/ISA style double‑triangle valve symbol.
        This method creates two triangles and a horizontal line between them,
        representing a double triangle valve. The triangles are positioned
        at (*xPos*, *yPos*) and have a base width of *size*. The label is
        positioned below the triangles.
        """
        tri1 = QPolygonF([
            QPointF(xPos, yPos),
            QPointF(xPos + size, yPos - size/2),
            QPointF(xPos + size, yPos + size/2)
        ])
        tri1_item = QGraphicsPolygonItem(tri1)
        tri1_item.setPen(QPen(Qt.black, 2))
        scene.addItem(tri1_item)

        tri2 = QPolygonF([
            QPointF(xPos + size * 2, yPos),
            QPointF(xPos + size, yPos - size/2),
            QPointF(xPos + size, yPos + size/2)
        ])
        tri2_item = QGraphicsPolygonItem(tri2)
        tri2_item.setPen(QPen(Qt.black, 2))
        scene.addItem(tri2_item)

        line = QLineF(xPos, yPos, xPos + size * 2, yPos)
        line_item = QGraphicsLineItem(line)
        line_item.setPen(QPen(Qt.black, 2))
        scene.addItem(line_item)

        text_item = QGraphicsTextItem(label)
        font = QFont("Arial", 8, QFont.Weight.Bold)
        text_item.setFont(font)
        text_item.setDefaultTextColor(Qt.black) # Set text color to BLACK
        text_item.setPos(xPos + size / 2, yPos + size / 2 + 5)
        scene.addItem(text_item)
    

    @staticmethod
    def CreateSetpointInput(
        scene: QGraphicsScene,
        xPos: float,
        yPos: float,
        min_val: float,
        max_val: float,
        step: float,
        initial_val: float,
        *,
        units: str = "",
        label_text: str = "",
    ) -> QDoubleSpinBox:
        """
        Factory helper that drops a labelled :class:`QDoubleSpinBox`.
        Returns the spin box so that the caller can wire up its *valueChanged*
        signal.

        Parameters
        -------
        scene
            The scene to which the spin box should be added.
        xPos, yPos
            The position where the spin box should be placed.
        min_val, max_val
            The minimum and maximum values for the spin box.
        step
            The step size for the spin box.
        initial_val
            The initial value to set in the spin box.
        units
            Optional units to display as a suffix in the spin box.
        label_text
            Optional label text to display above the spin box.

        Returns
        -------
        QDoubleSpinBox
            The created spin box widget. This widget is styled, positioned, and optionally labeled.
        """
        # Create a text label above the spin box if label_text is provided
        if label_text:
            label_item = QGraphicsTextItem(label_text)
            label_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            label_item.setDefaultTextColor(Qt.black) # Match other icon text
            # Position the label text above the spin box. Adjust yPos for the spin box itself.
            label_item.setPos(xPos, yPos - label_item.boundingRect().height() - 5) # 5 pixels above input
            scene.addItem(label_item)
            # Adjust yPos for the spin box to be below its label
            input_y_pos = yPos - label_item.boundingRect().height() - 5 # Start input from top of label text
        else:
            input_y_pos = yPos # No label, just use given yPos

        spin_box = QDoubleSpinBox()
        spin_box.setRange(min_val, max_val)
        spin_box.setSingleStep(step)
        spin_box.setValue(initial_val)
        spin_box.setSuffix(f" {units}") # Add units as suffix
        spin_box.setFixedSize(80, 25) # Standard size for input boxes
        spin_box.setStyleSheet(Stylesheets.DoubleSpinBoxStyleSheet()) # Assuming this stylesheet exists

        proxy_widget = QGraphicsProxyWidget()
        proxy_widget.setWidget(spin_box)
        proxy_widget.setPos(xPos, input_y_pos) # Use the adjusted yPos for the input box
        scene.addItem(proxy_widget)

        return spin_box # Return the spin box so its signal can be connected

class RoundedProxy(QGraphicsProxyWidget):
    """
    Proxy widget with rounded‑corner clipping.
    """
    def paint(self, painter, option, widget):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 3, 3)
        painter.setClipPath(path)
        super().paint(painter, option, widget)

class CreatePlotButton():
    """
    Push‑button factory used by :class:`SensorPlot`.
    """
    def __init__(self, scene: QGraphicsScene, func: Callable[[], None], buttonName="Plot", xCoord=0, yCoord=0):
        self.pushButton = QPushButton(buttonName)
        self.pushButton.setStyleSheet(Stylesheets.GenericPushButtonStyleSheet())
        self.pushButton.setFixedSize(80, 30)
        self.pushButton.clicked.connect(func)
        
        self.pushButtonProxy = QGraphicsProxyWidget()
        self.pushButtonProxy.setWidget(self.pushButton)
        
        scene.addItem(self.pushButtonProxy)
        self.pushButtonProxy.setPos(xCoord, yCoord)

class CreatePlotLabel():
    """
    Tiny QLabel wrapped in a rounded proxy used to display sensor value.
    """
    def __init__(self, scene: QGraphicsScene, xCoord=0, yCoord=0):
        super().__init__()
        self.label = QLabel("---")
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

    def setLabelColorDefault(self):
        self.label.setStyleSheet(Stylesheets.PlotLabelStyle())


class CreatePlotWindow(QDialog):
    """
    Popup window that streams live deque‑buffered sensor data.

    Signals
    -------
    update_plot_signal : Signal(list)
        Emitted to update the plot with new data in the GUI thread.
    update_label_signal : Signal(float)
        Emitted to update the label with the current value.
    """
    update_plot_signal = Signal(list)
    update_label_signal = Signal(float)

    def __init__(self, designator: str, data_manager: SystemDataManager, title: str = "Sensor Plot", units: str = "", y_range: Tuple[float, float] = (0, 100), history_len: int = 100, parent=None):
        super().__init__(parent)

        self.designator = designator
        self.data_manager = data_manager
        self.setWindowTitle(f"{title} - {designator}")
        self.resize(500, 400)
        
        self.units = units
        self.history_len = history_len

        self.sensor_deque = self.data_manager.get_sensor_deque(self.designator)
        """
        Notes
        -----
        If the sensor designator is unknown, the window will display a placeholder deque.
        """
        if self.sensor_deque is None:
            print(f"Warning: {designator} does not have a historical deque. Plot will be empty initially.")
            self.sensor_deque = deque([0.0] * self.history_len, maxlen=self.history_len)


        # Label in plot window should show Designator and Value (as previously specified for plot window)
        self.current_value_label = QLabel(f"{self.designator}: --- {self.units}")
        self.current_value_label.setStyleSheet(Stylesheets.PlotLabelStyle())
        self.current_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', title, units=self.units)
        self.plot_widget.setLabel('bottom', "Time", units='s')
        self.plot_widget.setYRange(y_range[0], y_range[1])
        self.plot_widget.setXRange(0, self.history_len * 0.1)
        self.plot_widget.showGrid(x=True, y=True)
        axis_left = self.plot_widget.getAxis("left")
        axis_bottom = self.plot_widget.getAxis("bottom")

        axis_left.setStyle(tickFont=pg.Qt.QtGui.QFont("Arial", 10))
        axis_bottom.setStyle(tickFont=pg.Qt.QtGui.QFont("Arial", 10))

        axis_left.setTextPen('w')   # Set tick labels to white
        axis_bottom.setTextPen('w')

        axis_left.setPen('w')       # Set axis line to white
        axis_bottom.setPen('w')
        self.plot_widget.getPlotItem().setTitle(f'<span style="color:white;font-size:12pt;">{title} - {designator}</span>') # Set plot title to white, include designator
        self.curve = self.plot_widget.plot(pen=pg.mkPen('r', width=2), name=designator)

        layout.addWidget(self.current_value_label)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        self.update_plot_signal.connect(self.update_plot)
        self.update_label_signal.connect(self.update_label)

    async def _on_new_data_for_plot(self, value: float):
        """
        Queued‑update entry point called from outside GUI thread.
        """
        actual_deque = self.data_manager.get_sensor_deque(self.designator)
        if actual_deque:
            self.update_plot_signal.emit(list(actual_deque))
        else:
            self.update_plot_signal.emit([value])
            
        self.update_label_signal.emit(value)

    def update_plot(self, data: List[float]):
        """
        Re‑plot new *data* (executed in GUI thread).
        """
        time_axis = [i * 0.1 for i in range(len(data))]
        self.curve.setData(time_axis, data)

    def update_label(self, data_val: float):
        """
        Refresh numeric readout above the graph.
        """
        self.current_value_label.setText(f"{self.designator}: {data_val:.1f} {self.units}")


class SensorPlot:
    """
    Aggregates all GUI elements for a single sensor on the P&ID diagram.

    This class creates a labeled display for a sensor's latest reading,
    along with a button that opens a real-time plot window for historical data.
    It connects to signals from the SystemDataManager to update the label and plot
    as new values arrive. Used for rendering pressure, temperature, flow, or
    pump feedback data in a schematic-style view.

    Parameters
    -------
    scene : QGraphicsScene
        The target scene to which the sensor components are added.
    designator : str
        The unique name of the sensor (e.g., "PT101", "TT102").
    data_manager : SystemDataManager
        Shared data manager instance that emits sensor update signals.
    data_type_category : str
        One of "pressure", "temperature", "flow_feedback", or "pump_feedback".
    position : Tuple[int, int]
        (x, y) coordinates to place the sensor label in the scene.
    units : str
        Units of the sensor value (e.g., "psi", "°C").
    live_plot_enabled : bool
        Whether the live plot should stream values automatically.

    Attributes
    -------
    schematic_label : CreatePlotLabel
        Label widget used to display the current sensor value in the scene.
    plot_button : CreatePlotButton
        Button widget that opens a popup with a historical sensor plot.
    plot_window : CreatePlotWindow or None
        The popup window that plots live sensor history.
    """
    def __init__(self, scene: QGraphicsScene, designator: str, data_manager: SystemDataManager, 
                 data_type_category: str, position: Tuple[int, int], units: str, live_plot_enabled: bool):
        
        self.designator = designator
        self.data_manager = data_manager
        self.data_type_category = data_type_category
        self.units = units
        self.live_plot_enabled = live_plot_enabled
        self.plot_window: Union[CreatePlotWindow, None] = None
        
        # Create graphical label on the schematic
        self.schematic_label = CreatePlotLabel(scene, position[0], position[1])
        initial_value = self.data_manager.get_latest_sensor_value(self.designator)
        if self.data_type_category == "temperature" and initial_value == self.data_manager.INVALID_TEMP_MARKER:
             self.schematic_label.setLabelText("INVALID")
             self.schematic_label.setLabelColorRed()
        else:
            self.schematic_label.setLabelText(f"{initial_value:.1f} {self.units}") # Just the value and units

        # Create plot button on the schematic
        button_x_offset = position[0]
        button_y_offset = position[1] + self.schematic_label.labelProxy.size().height() + 5
        self.plot_button = CreatePlotButton(scene, self._open_plot_window, "Plot", button_x_offset, button_y_offset)

        self.plot_window_title = f"{self.designator} Plot"
        self.plot_window_y_range = self._get_default_y_range(data_type_category)

        if data_type_category == "pressure":
            self.data_manager.pressure_updated.connect(self._on_pressure_data_update_for_label_and_plot)
        elif data_type_category == "temperature":
            self.data_manager.temperature_updated.connect(self._on_temperature_data_update_for_label_and_plot)
        elif data_type_category in ["flow_feedback", "pump_feedback"]:
            self.data_manager.pump_feedback_updated.connect(self._on_pump_feedback_data_update_for_label_and_plot)
        
    def _get_default_y_range(self, data_type: str) -> Tuple[float, float]:
        """
        Return default Y-axis range for the plot based on the sensor type.

        Parameters
        -------
        data_type : str
            Sensor data type (e.g., "pressure", "temperature", "flow_feedback").

        Returns
        -------
        Tuple[float, float]
            A 2-tuple specifying the Y-axis lower and upper bounds.
        """
        if data_type == "pressure": return (0, 100)
        if data_type == "temperature": return (0, 100)
        if data_type == "flow_feedback": return (0, 1000)
        if data_type == "pump_feedback": return (0, 100)
        return (0, 100)


    def _open_plot_window(self):
        """
        Open or raise the real-time plot window for this sensor.

        If the window does not exist, a new instance is created. If it already
        exists, the window is brought to the front.
        """
        if self.plot_window is None or not self.plot_window.isVisible():
            self.plot_window = CreatePlotWindow(
                designator=self.designator,
                data_manager=self.data_manager,
                title=self.plot_window_title,
                units=self.units,
                y_range=self.plot_window_y_range,
                history_len=self.data_manager.history_len
            )
            self.plot_window.show()
        else:
            self.plot_window.activateWindow()
            self.plot_window.raise_()

    def update_value(self, new_value: float):
        """
        Updates the displayed sensor value on the schematic label and optionally
        sends data to the pop-up plot window.
        This method is called by the _on_..._data_update_for_label_and_plot methods.
        """
        # Format value for display on the schematic label
        if self.data_type_category == "temperature" and new_value == self.data_manager.INVALID_TEMP_MARKER:
            display_text = "INVALID"
            self.schematic_label.setLabelColorRed()
        else:
            display_text = f"{new_value:.1f}"
            self.schematic_label.setLabelColorDefault() # Ensure it reverts to default if OK

        # Update the text on the schematic label
        self.schematic_label.setLabelText(f"{display_text} {self.units}")

        # If a plot window is open and enabled, send data to it
        if self.live_plot_enabled and self.plot_window and self.plot_window.isVisible():
            # Call the async method in CreatePlotWindow to append and plot new data
            # This is wrapped in asyncio.create_task because _on_new_data_for_plot is async
            asyncio.create_task(self.plot_window._on_new_data_for_plot(new_value))

    # --- Modify these existing methods to call the new update_value method ---
    # These methods are primarily responsible for receiving the signal and
    # extracting the correct 'value' for this specific SensorPlot instance.
    def _on_pressure_data_update_for_label_and_plot(self, pressures: List[float]):
        """
        Receives pressure_updated signal and calls update_value for this sensor.
        """
        if self.designator in self.data_manager.pressure_sensor_names:
            value = self.data_manager.get_latest_sensor_value(self.designator)
            self.update_value(value) 

    def _on_temperature_data_update_for_label_and_plot(self, temperatures: List[float]):
        """
        Receives temperature_updated signal and calls update_value for this sensor.
        """
        if self.designator in self.data_manager.temperature_sensor_names:
            value = self.data_manager.get_latest_sensor_value(self.designator)
            self.update_value(value)

    def _on_pump_feedback_data_update_for_label_and_plot(self, pump_percent: float, flow1_kg_per_h: float, flow2_kg_per_h: float):
        """
        Receives pump_feedback_updated signal and calls update_value for pump or flow sensors.
        Note: The signal emits three values, so the method signature must match.
        """
        value_to_update = None
        if self.designator == "PumpFeedback":
            value_to_update = pump_percent
        elif self.designator == "FT1024":
            value_to_update = flow1_kg_per_h # Assuming FT1024 corresponds to the second argument
        elif self.designator == "FT10106":
            value_to_update = flow2_kg_per_h # Assuming FT10106 corresponds to the third argument

        if value_to_update is not None:
            self.update_value(value_to_update)