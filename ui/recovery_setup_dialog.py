import qrcode
import os
import sys
from io import BytesIO
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, 
    QPushButton, QHBoxLayout, QFrame, QMessageBox,
    QStackedWidget, QWidget, QLineEdit
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPixmap

from ui.theme import MidnightVault
from ui.components.title_bar import TitleBar

class RecoverySetupDialog(QDialog):
    """Wizard to guide the user through Phrase and TOTP setup (Midnight Vault Edition)."""
    
    def __init__(self, phrase, totp_uri, totp_secret, parent=None, is_migration=False):
        super().__init__(parent)
        self.phrase = phrase
        self.totp_uri = totp_uri
        self.totp_secret = totp_secret
        self.is_migration = is_migration
        self.drag_pos = QPoint()
        
        self.setWindowTitle("Security Setup")
        self.setFixedSize(500, 620)
        
        # Frameless logic for a consistent feel
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()

    def init_ui(self):
        # Create a main_container to hold everything and provide the background
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_container = QFrame()
        self.main_container.setObjectName("MainContainer")
        self.main_container.setStyleSheet(f"""
            QFrame#MainContainer {{
                background-color: {MidnightVault.BG_SECONDARY};
                border: 1px solid {MidnightVault.BORDER};
                border-radius: 20px;
            }}
        """)
        
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 1. Custom Title Bar
        self.title_bar = TitleBar("🔐 Security Setup", parent=self)
        self.title_bar.close_btn.clicked.connect(self.reject)
        container_layout.addWidget(self.title_bar)

        # Content Widget
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(20, 10, 20, 20)
        self.content_layout.setSpacing(15)
        
        self.setStyleSheet(f"""
            QLabel {{ color: {MidnightVault.TEXT_PRIMARY}; font-family: 'Inter', sans-serif; }}
            QTextEdit {{
                background-color: {MidnightVault.BG_PRIMARY};
                border: 1.5px solid {MidnightVault.WARNING};
                border-radius: 12px;
                color: {MidnightVault.WARNING};
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 14px;
                padding: 15px;
            }}
            QPushButton {{
                background-color: {MidnightVault.ACCENT_PRIMARY};
                color: #ffffff;
                border-radius: 10px;
                padding: 12px;
                font-weight: 600;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {MidnightVault.ACCENT_SECONDARY}; }}
            QPushButton#Secondary {{
                background-color: {MidnightVault.BG_ELEVATED};
                color: {MidnightVault.TEXT_PRIMARY};
                border: 1px solid {MidnightVault.BORDER};
            }}
        """)

        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)

        # Step 1: 24-Word Phrase
        self.setup_phrase_step()
        
        # Step 2: TOTP QR Code
        self.setup_totp_step()
        
        container_layout.addWidget(content_widget)
        self.main_layout.addWidget(self.main_container)

    def setup_phrase_step(self):
        step1 = QWidget()
        step1_layout = QVBoxLayout(step1)
        step1_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Step 1: 🛡️ Recovery Seed Phrase")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {MidnightVault.WARNING};")
        step1_layout.addWidget(title)

        desc = QLabel(
            "This phrase is the ONLY way to recover your vault if you forget your password. "
            "Write it down and store it in a physical, secure location."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {MidnightVault.TEXT_SECONDARY}; margin-bottom: 10px;")
        step1_layout.addWidget(desc)

        self.phrase_display = QTextEdit()
        self.phrase_display.setReadOnly(True)
        self.phrase_display.setText(self.phrase)
        step1_layout.addWidget(self.phrase_display)

        warning = QLabel("⚠️ Warning: Never share this phrase. It grants full access to your vault.")
        warning.setStyleSheet(f"color: {MidnightVault.DANGER}; font-size: 11px; margin-top: 5px;")
        step1_layout.addWidget(warning)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.next_btn = QPushButton("I have saved the phrase →")
        self.next_btn.clicked.connect(self.go_to_totp)
        btn_layout.addWidget(self.next_btn)
        step1_layout.addLayout(btn_layout)

        self.stack.addWidget(step1)

    def setup_totp_step(self):
        step2 = QWidget()
        step2_layout = QVBoxLayout(step2)
        step2_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Step 2: 📱 Authenticator App (TOTP)")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {MidnightVault.ACCENT_PRIMARY};")
        step2_layout.addWidget(title)

        desc = QLabel(
            "Scan this QR code with Google Authenticator, Authy, or any TOTP app. "
            "This allows you to reset your password using your phone."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {MidnightVault.TEXT_SECONDARY}; margin-bottom: 10px;")
        step2_layout.addWidget(desc)

        # QR Code Display
        qr_container = QLabel()
        qr_container.setAlignment(Qt.AlignCenter)
        qr_container.setStyleSheet("background-color: white; padding: 10px; border-radius: 10px;")
        
        pixmap = self.generate_qr_pixmap(self.totp_uri)
        qr_container.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio))
        step2_layout.addWidget(qr_container)

        # Manual Code
        secret_label = QLabel(f"Manual Secret Key: <br/><b style='color:{MidnightVault.ACCENT_PRIMARY};'>{self.totp_secret}</b>")
        secret_label.setAlignment(Qt.AlignCenter)
        secret_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        step2_layout.addWidget(secret_label)

        # Verification Field
        v_title = QLabel("Verify Sync:")
        v_title.setStyleSheet(f"font-weight: bold; color: {MidnightVault.TEXT_SECONDARY};")
        step2_layout.addWidget(v_title)

        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter 6-digit code from app")
        self.otp_input.setAlignment(Qt.AlignCenter)
        self.otp_input.setMaxLength(6)
        self.otp_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {MidnightVault.BG_PRIMARY};
                border: 2px solid {MidnightVault.BORDER};
                border-radius: 8px;
                padding: 10px;
                font-size: 18px;
                color: {MidnightVault.ACCENT_PRIMARY};
                font-weight: bold;
            }}
            QLineEdit:focus {{ border: 2px solid {MidnightVault.ACCENT_PRIMARY}; }}
        """)
        step2_layout.addWidget(self.otp_input)

        btn_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_layout.addWidget(back_btn)

        btn_layout.addStretch()

        self.finish_btn = QPushButton("✅ Verify & Finish")
        self.finish_btn.clicked.connect(self.on_verify_and_finish)
        btn_layout.addWidget(self.finish_btn)
        step2_layout.addLayout(btn_layout)

        self.stack.addWidget(step2)

    def generate_qr_pixmap(self, uri):
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qimg = QImage.fromData(buffer.getvalue())
        return QPixmap.fromImage(qimg)

    def go_to_totp(self):
        reply = QMessageBox.question(
            self, "Confirm Phrase", 
            "Are you sure you've saved the 24 words? You cannot go back to see them easily later.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.stack.setCurrentIndex(1)

    def on_verify_and_finish(self):
        code = self.otp_input.text().strip()
        if not code or len(code) != 6:
            QMessageBox.warning(self, "Invalid Input", "Please enter the 6-digit code from your app.")
            return

        import pyotp
        totp = pyotp.TOTP(self.totp_secret)
        if totp.verify(code):
            QMessageBox.information(self, "Success", "Phone recovery linked successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Verification Failed", "The code you entered is incorrect. Please check your app and try again.")
            self.otp_input.clear()

    # Drag functionality
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()
