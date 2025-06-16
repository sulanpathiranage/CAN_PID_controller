import sys
import numpy as np
import PySide6
import pyqtgraph as pg
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QCoreApplication, Qt

# Set application attributes for High DPI scaling.
# These lines ensure that the application scales correctly on high-resolution displays.
# While often handled automatically in newer PySide6, it's good practice to include.
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

# Optional: Improve appearance of PyQtGraph plots.
# useOpenGL=False: Disables OpenGL for plotting, sometimes resolves rendering issues.
# antialias=True: Improves the smoothness of lines and edges in plots.
pg.setConfigOptions(useOpenGL=False)
pg.setConfigOptions(antialias=True)

class MainWindow(QMainWindow):
    """
    Main application window for demonstrating PyQtGraph plotting with PySide6.
    """
    def __init__(self):
        super().__init__()
        # Set the window title
        self.setWindowTitle("Working Plot Test")
        # Set the initial size of the window
        self.resize(600, 400)

        # Create a PlotWidget instance, which is the main plotting canvas.
        self.graphWidget = pg.PlotWidget()
        # Set the PlotWidget as the central widget of the QMainWindow.
        self.setCentralWidget(self.graphWidget)

        # Generate sample data using numpy.
        # x is an array from 0 to 9.
        x = np.arange(10)
        # y is an array of corresponding data points.
        y = np.array([30, 32, 34, 32, 33, 31, 29, 32, 35, 45])

        # Print the data to console for verification.
        print("Plotting data (x):", list(x))
        print("Plotting data (y):", list(y))

        # Plot the data on the graphWidget.
        # 'pen='r'' specifies a red line for the plot.
        curve = self.graphWidget.plot(x, y, pen='r')
        # Print the curve object to console for verification.
        print("Curve object:", curve)

        # --- IMPORTANT: Explicitly set the Y-axis range ---
        # This is often necessary for PyQtGraph to correctly display data,
        # especially if auto-ranging doesn't work as expected.
        # We calculate a range slightly wider than the min/max of the 'y' data
        # to ensure all points are visible and there's some padding.
        if len(y) > 0:
            min_y = np.min(y)
            max_y = np.max(y)
            # Set the Y-range with a buffer (e.g., 5 units below min and above max).
            self.graphWidget.setYRange(min_y - 5, max_y + 5)
        else:
            print("Warning: No data in 'y' array to set Y-range.")

        # You can also set a title for the plot if desired:
        self.graphWidget.setTitle("Sample Data Plot")
        # And labels for the axes:
        self.graphWidget.setLabel('left', 'Value', units='units')
        self.graphWidget.setLabel('bottom', 'Index', units='idx')


# Create the QApplication instance. This is required for any Qt application.
app = QApplication(sys.argv)
# Create an instance of our MainWindow.
window = MainWindow()
# Show the main window.
window.show()
# Start the Qt event loop. This keeps the application running until it's closed.
# sys.exit() ensures a clean exit when the application closes.
sys.exit(app.exec())
