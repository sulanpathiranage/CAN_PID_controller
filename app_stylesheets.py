
class Stylesheets:

    def GenericPushButtonStyleSheet():
        pushButtonStyle = """
            QPushButton {
                background-color: #486a8c;       /* Muted blue-gray */
                color: #ffffff;
                border-radius: 2px;
                padding: 4px 10px;
                font-weight: 500;
            }

            QPushButton:hover {
                background-color: #4c5a6a;
            }

            QPushButton:pressed {
                background-color: #2c3a4a;
            }

            QPushButton:disabled {
                background-color: #2a2f35;
                color: #888888;
            }
        """
        return pushButtonStyle
    
    def EStopPushButtonStyleSheet():
        eStopPushButtonSyle = """
        QPushButton {
            background-color: #c94444;
            color: white;
            border: none;
            border-radius: 2px;
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
            color: #FFFFFF;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 12px;
            font-weight: normal;
            padding: 4px 6px;
            background-color: transparent;
            border: none;
        }

        QLabel[class="header"] {
            font-size: 20px;
            font-weight: bold;
            color: #FFFFFF;
            padding: 8px 6px;
        }

        QLabel[class="subtitle"] {
            font-size: 13px;
            color: #CCCCCC;
            font-weight: normal;
            padding: 2px 6px;
        }

        QLabel[class="warning"] {
            color: #FFA500;
            font-weight: bold;
        }

        QLabel[class="error"] {
            color: #FF5555;
            font-weight: bold;
        }"""
        return labelStyleSheet
    
    def PlotLabelStyle():
        plotLabelStyle = """
        QLabel {
            background-color: #2e2e2e;  /* Dark grey */
            color: white;               /* White text */
            font-size: 18px;            /* Large text */
            border-radius: 10px;        /* Rounded corners */
            padding: 6px
        }
        """
        return plotLabelStyle
    
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
        checkBoxStyle = """
            QCheckBox {
                spacing: 8px;
                color: #dddddd;
                font-size: 13px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #555555;
                background-color: #2e2e2e;
            }

            QCheckBox::indicator:hover {
                border: 2px solid #888888;
            }

            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
            }

            QCheckBox::indicator:disabled {
                background-color: #444444;
                border: 2px solid #333333;
            }
            """
        return checkBoxStyle
    
    def GraphicsViewStyleSheet():
        graphicsViewStyle = """
            QGraphicsView {
                background-color: #f9f9f9;
                border-radius: 4px;
                border: 1px solid #ccc;
            }

            QScrollBar:horizontal {
                background: #f9f9f9;  /* Avoid leaking background */
                margin: 0px;
                border-bottom-left: 2px;
            }

            QScrollBar:vertical {
                background: #f9f9f9;  /* Avoid leaking background */
                margin: 0px;
                border-top-right: 2px;
            }

            QScrollBar::handle:horizontal,
            QScrollBar::handle:vertical {
                background: #444444;
                border-radius: 4px; /* Visual roundness */
                min-height: 20px;
                min-width: 20px;
            }

            QScrollBar::handle:horizontal:hover,
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: none;
                border: none;
                width: 0px;
                height: 0px;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar:vertical {
                width: 8px;
            }

            QScrollBar:horizontal {
                height: 8px;
            }
        """
        return graphicsViewStyle
    
    def GenericScrollAreaStyleSheet():
        genericScrollAreaStyleSheet = """
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 2px 0 2px 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #888;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """
        return genericScrollAreaStyleSheet
    
    def LabelStyleSheet():
        labelStyleSheet = """
            QLabel {
                color: #DDDDDD;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
                padding: 2px 4px;
                background-color: transparent;
                border: none;
            }

            QLabel[class="header"] {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 6px 4px;
            }

            QLabel[class="subtitle"] {
                font-size: 11px;
                color: #AAAAAA;
                font-weight: normal;
                padding: 2px 4px;
            }

            QLabel[class="warning"] {
                color: #FFA500;
                font-weight: bold;
            }

            QLabel[class="error"] {
                color: #FF5555;
                font-weight: bold;
            }
        """
        return labelStyleSheet