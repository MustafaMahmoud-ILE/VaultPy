from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QIcon, QPixmap
import os

from ui.theme import MidnightVault

class CustomTitleBar(QWidget):
    """A custom title bar for frameless windows (Midnight Vault Edition)."""
    
    close_clicked = Signal()
    minimize_clicked = Signal()

    def __init__(self, parent=None, title="VaultPy"):
        super().__init__(parent)
        self.parent = parent
        self.drag_pos = QPoint()
        self.init_ui(title)

    def init_ui(self, title):
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {MidnightVault.BG_SECONDARY}, stop:1 {MidnightVault.BG_PRIMARY});
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
            QLabel#Title {{
                color: {MidnightVault.TEXT_PRIMARY};
                font-weight: 600;
                font-size: 12px;
                margin-left: 5px;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 16px;
                font-size: 14px;
                color: {MidnightVault.TEXT_SECONDARY};
                width: 32px;
                height: 32px;
            }}
            QPushButton#MinimizeBtn:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: {MidnightVault.ACCENT_PRIMARY};
            }}
            QPushButton#CloseBtn:hover {{
                background-color: {MidnightVault.DANGER};
                color: #ffffff;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(5)

        # Icon
        self.icon_label = QLabel()
        icon_path = os.path.join(os.getcwd(), "assets", "icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        layout.addWidget(self.icon_label)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("Title")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Minimize Button
        self.minimize_btn = QPushButton("—")
        self.minimize_btn.setObjectName("MinimizeBtn")
        self.minimize_btn.setCursor(Qt.PointingHandCursor)
        self.minimize_btn.setFixedSize(32, 32)
        self.minimize_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.minimize_btn)

        # Close Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setFixedSize(32, 32)
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
