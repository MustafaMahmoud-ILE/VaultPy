from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QColor, QIcon

from ui.theme import MidnightVault
from ui.components.title_bar import CustomTitleBar

class MidnightMessageBox(QDialog):
    """A premium, themed replacement for QMessageBox."""
    
    def __init__(self, title, message, icon_type="info", buttons=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 220)
        self.drag_pos = QPoint()
        self.result_value = None

        if buttons is None:
            buttons = ["OK"]

        self.init_ui(title, message, icon_type, buttons)

    def init_ui(self, title, message, icon_type, buttons):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Main Container
        self.container = QFrame()
        self.container.setObjectName("AlertContainer")
        self.container.setStyleSheet(f"""
            QFrame#AlertContainer {{
                background-color: {MidnightVault.BG_SECONDARY};
                border: 1px solid {MidnightVault.BORDER};
                border-radius: 16px;
            }}
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 1. Custom Title Bar
        self.title_bar = CustomTitleBar(self, title)
        self.title_bar.minimize_btn.hide()
        self.title_bar.close_btn.clicked.connect(self.reject)
        container_layout.addWidget(self.title_bar)

        # 2. Content Area
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(15)

        # Icon
        self.icon_label = QLabel()
        icon_map = {
            "success": ("✅", MidnightVault.SUCCESS),
            "error": ("❌", MidnightVault.DANGER),
            "warn": ("⚠️", MidnightVault.WARNING),
            "info": ("ℹ️", MidnightVault.ACCENT_PRIMARY),
            "question": ("❓", MidnightVault.ACCENT_SECONDARY)
        }
        symbol, color = icon_map.get(icon_type, icon_map["info"])
        
        self.icon_label.setText(symbol)
        self.icon_label.setStyleSheet(f"font-size: 32px; color: {color}; background: transparent;")
        content_layout.addWidget(self.icon_label)

        # Message
        self.msg_label = QLabel(message)
        self.msg_label.setWordWrap(True)
        self.msg_label.setStyleSheet(f"color: {MidnightVault.TEXT_PRIMARY}; font-size: 14px; font-family: 'Inter'; background: transparent;")
        content_layout.addWidget(self.msg_label, 1)

        container_layout.addWidget(content_widget)

        # 3. Action Buttons
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(20, 0, 20, 20)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        for btn_text in buttons:
            btn = QPushButton(btn_text)
            btn.setCursor(Qt.PointingHandCursor)
            
            is_primary = btn_text in ["OK", "Yes", "Confirm", "Finish", "Verify"]
            bg = MidnightVault.ACCENT_PRIMARY if is_primary else MidnightVault.BG_ELEVATED
            color = "#ffffff" if is_primary else MidnightVault.TEXT_PRIMARY
            border = "none" if is_primary else f"1px solid {MidnightVault.BORDER}"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {color};
                    border: {border};
                    border-radius: 8px;
                    padding: 8px 22px;
                    font-weight: 600;
                    min-width: 90px;
                }}
                QPushButton:hover {{
                    background-color: {MidnightVault.ACCENT_SECONDARY if is_primary else MidnightVault.BORDER};
                }}
            """)
            # Using a more robust connection
            btn.clicked.connect(self.make_callback(btn_text))
            btn_layout.addWidget(btn)

        container_layout.addWidget(btn_container)
        self.main_layout.addWidget(self.container)

    def make_callback(self, text):
        return lambda: self.on_button_clicked(text)

    def on_button_clicked(self, text):
        # DEBUG PRINT to terminal
        print(f"[DEBUG] MidnightMessageBox: User clicked '{text}'")
        self.result_value = text
        if text in ["Yes", "OK", "Confirm", "Finish", "Verify"]:
            self.done(1) # Accepted
        else:
            self.done(0) # Rejected

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

class MidnightInputDialog(QDialog):
    """A premium, themed replacement for QInputDialog."""
    
    def __init__(self, title, message, placeholder="", is_password=False, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 280)
        self.drag_pos = QPoint()
        self.text_value = ""
        self.confirmed = False

        self.init_ui(title, message, placeholder, is_password)

    def init_ui(self, title, message, placeholder, is_password):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        self.container.setObjectName("InputContainer")
        self.container.setStyleSheet(f"""
            QFrame#InputContainer {{
                background-color: {MidnightVault.BG_SECONDARY};
                border: 1px solid {MidnightVault.BORDER};
                border-radius: 16px;
            }}
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, title)
        self.title_bar.minimize_btn.hide()
        self.title_bar.close_btn.clicked.connect(self.reject)
        container_layout.addWidget(self.title_bar)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(15)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {MidnightVault.TEXT_PRIMARY}; font-size: 14px; background: transparent;")
        content_layout.addWidget(msg_label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(placeholder)
        if is_password:
            self.input_field.setEchoMode(QLineEdit.Password)
        
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {MidnightVault.BG_PRIMARY};
                border: 1.5px solid {MidnightVault.BORDER};
                border-radius: 8px;
                padding: 12px;
                color: {MidnightVault.TEXT_PRIMARY};
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {MidnightVault.ACCENT_PRIMARY}; }}
        """)
        self.input_field.returnPressed.connect(self.on_confirm)
        content_layout.addWidget(self.input_field)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"background: {MidnightVault.BG_ELEVATED}; color: {MidnightVault.TEXT_PRIMARY}; border: 1px solid {MidnightVault.BORDER}; border-radius: 8px; padding: 10px 20px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"background: {MidnightVault.ACCENT_PRIMARY}; color: #ffffff; border: none; border-radius: 8px; padding: 10px 25px; font-weight: bold;")
        confirm_btn.clicked.connect(self.on_confirm)
        btn_layout.addWidget(confirm_btn)
        
        content_layout.addLayout(btn_layout)
        container_layout.addWidget(content_widget)
        self.main_layout.addWidget(self.container)

    def on_confirm(self):
        self.text_value = self.input_field.text().strip()
        print(f"[DEBUG] MidnightInputDialog: User confirmed with text: '{self.text_value}'")
        self.confirmed = True
        self.done(1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

class Alert:
    """Helper class for easy static calls like QMessageBox."""
    
    @staticmethod
    def info(parent, title, message):
        return MidnightMessageBox(title, message, "info", ["OK"], parent).exec()

    @staticmethod
    def success(parent, title, message):
        return MidnightMessageBox(title, message, "success", ["OK"], parent).exec()

    @staticmethod
    def error(parent, title, message, details=None):
        if details: message = f"{message}\n\n{details}"
        return MidnightMessageBox(title, message, "error", ["OK"], parent).exec()

    @staticmethod
    def warn(parent, title, message):
        return MidnightMessageBox(title, message, "warn", ["OK"], parent).exec()

    @staticmethod
    def question(parent, title, message):
        dlg = MidnightMessageBox(title, message, "question", ["Yes", "No"], parent)
        res = dlg.exec()
        print(f"[DEBUG] Alert.question finished. Result Code: {res}, Value: {dlg.result_value}")
        return res == 1 or dlg.result_value == "Yes"

    @staticmethod
    def input(parent, title, message, placeholder="", is_password=False):
        dlg = MidnightInputDialog(title, message, placeholder, is_password, parent)
        res = dlg.exec()
        print(f"[DEBUG] Alert.input finished. Result Code: {res}, Text: {dlg.text_value}")
        if res == 1:
            return dlg.text_value, True
        return "", False
