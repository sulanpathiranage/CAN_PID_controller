
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QSlider, QLineEdit, QGroupBox,
    QFormLayout, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QDoubleSpinBox, QScrollArea, QTabWidget,
    QGraphicsView, QGraphicsScene
)

class NH3VaporizerControlWidget(QWidget):
    def __init__(self):
        super().__init__()

        #Create Layout
        horizontalLayout = QHBoxLayout()

        #Create Components
        self.systemControlScene = QGraphicsScene()
        self.systemControlView = QGraphicsView(self.systemControlScene)

        #Add Components to Layout
        horizontalLayout.addWidget(self.systemControlView)

        #Set Layout for self
        self.setLayout(horizontalLayout)


    #Define functions for drawing individual components for the NH3 Pump, buttons and logic should also be part of this class 
    
