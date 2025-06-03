
class Stylesheets:

    def GenericPushButtonStyleSheet():
        pushButtonStyle = """
            QWidget {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 4px 10px;
                border: none;
            }

            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 4px 10px;
                border: none;
                min-height: 20px;
            }

            QPushButton:hover {
                background-color: #0099FF;
            }

            QPushButton:pressed {
                background-color: #005599;
            }
        """
        return pushButtonStyle
    
    def EStopPushButtonStyleSheet():
        eStopPushButtonSyle = """
        QPushButton {
            background-color: #c94444;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 14px;
        }
        
        QPushButton:hover {
            background-color: #d65555;
            transform: translateY(-1px);
        }
        
        QPushButton:pressed {
            background-color: #b33838;
            transform: translateY(1px);
        }
        
        QPushButton:disabled {
            background-color: #888888;
            color: #cccccc;
        }
        """
        return eStopPushButtonSyle
    
    def LabelStlyeSheet():
        labelStyleSheet = """
        QLabel {
            color: #2c3e50;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 12px;
            font-weight: 500;
            padding: 2px 4px;
            background-color: transparent;
            border: none;
        }

        QLabel[class="header"] {
            font-size: 16px;
            font-weight: bold;
            color: #34495e;
            padding: 8px 4px;
        }

        QLabel[class="subtitle"] {
            font-size: 10px;
            color: #7f8c8d;
            font-weight: normal;
        }"""
    
    def LineEditStyleSheet():
        lineEditStyle = ""
        return lineEditStyle
    
    def TabWidgetStyleSheet():
        tabWidgetStyle = """
            QTabWidget::pane {
                border: 1px solid #444444;
                background: #2e2e2e;
                padding: 5px;
            }

            QTabBar::tab {
                background: #3a3a3a;
                border: 1px solid #555555;
                border-bottom-color: #2e2e2e;  /* blend with pane */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                color: #CCCCCC;
            }

            QTabBar::tab:selected {
                background: #2e2e2e;
                border-color: #888888;
                border-bottom-color: #2e2e2e;
                color: #FFFFFF;
            }

            QTabBar::tab:hover {
                background: #505050;
                color: #FFFFFF;
            }
            """
        return tabWidgetStyle
    
    def CheckBoxStyleSheet():
        checkBoxStyle = ""
        return checkBoxStyle
    
    def WidgetStyleSheet():
        widgetStyle = ""
        return widgetStyle
    
    def GraphicsViewStyleSheet():
        graphicsViewStyle = """
            /* QGraphicsView background optional */
            QGraphicsView {
                background-color: #f9f9f9;
            }

            /* Common scrollbar settings */
            QScrollBar:horizontal,
            QScrollBar:vertical {
                border: none;
                background: #f9f9f9; /* removes scroll area background */
                margin: 0px;
            }

            /* Scrollbar handle (the draggable part) */
            QScrollBar::handle:horizontal,
            QScrollBar::handle:vertical {
                background: #444444; /* dark, modern look */
                border-radius: 4px;
            }

            /* Hover effect */
            QScrollBar::handle:horizontal:hover,
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }

            /* Remove the top/bottom or left/right buttons */
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                background: none;
                border: none;
                width: 0px;
                height: 0px;
            }

            /* Remove the track area between the handle and the buttons */
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }

            /* Optional: control size */
            QScrollBar:vertical {
                width: 8px;
            }

            QScrollBar:horizontal {
                height: 8px;
            }
        """
        return graphicsViewStyle