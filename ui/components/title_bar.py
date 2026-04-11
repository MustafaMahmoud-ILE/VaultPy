from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QIcon, QPixmap
import os

class CustomTitleBar(QWidget):
    """A custom title bar for frameless windows."""
    
    close_clicked = Signal()
    minimize_clicked = Signal()

    def __init__(self, parent=None, title="VaultPy"):
        super().__init__(parent)
        self.parent = parent
        self.drag_pos = QPoint()
        self.init_ui(title)

    def init_ui(self, title):
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }
            QLabel#Title {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                margin-left: 10px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                width: 35px;
                height: 35px;
            }
            QPushButton#MinimizeBtn:hover {
                background-color: #313244;
                color: #89b4fa;
            }
            QPushButton#MinimizeBtn:pressed {
                background-color: #45475a;
            }
            QPushButton#CloseBtn:hover {
                background-color: #f38ba8;
                color: #11111b;
            }
            QPushButton#CloseBtn:pressed {
                background-color: #e64553;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)

        # Icon
        self.icon_label = QLabel()
        icon_path = os.path.join(os.getcwd(), "assets", "icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        layout.addWidget(self.icon_label)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("Title")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Minimize Button
        self.minimize_btn = QPushButton()
        self.minimize_btn.setObjectName("MinimizeBtn")
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.setText("—")
        self.minimize_btn.setCursor(Qt.PointingHandCursor)
        self.minimize_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.minimize_btn)

        # Close Button
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setToolTip("Close")
        self.close_btn.setText("✕")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.parent.move(event.globalPos() - self.drag_pos)
            event.accept()
