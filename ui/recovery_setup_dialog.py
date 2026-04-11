import qrcode
from io import BytesIO
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, 
    QPushButton, QHBoxLayout, QFrame, QMessageBox,
    QStackedWidget, QWidget, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

class RecoverySetupDialog(QDialog):
    """Wizard to guide the user through Phrase and TOTP setup."""
    
    def __init__(self, phrase, totp_uri, totp_secret, parent=None, is_migration=False):
        super().__init__(parent)
        self.phrase = phrase
        self.totp_uri = totp_uri
        self.totp_secret = totp_secret
        self.is_migration = is_migration
        
        self.setWindowTitle("Security Setup: 2-Step Recovery")
        self.setFixedSize(500, 550)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QDialog { background-color: #0b0b10; }
            QLabel { color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
            QTextEdit {
                background-color: #11111b;
                border: 2px solid #fab387;
                border-radius: 10px;
                color: #fab387;
                font-family: 'Consolas', monospace;
                font-size: 15px;
                padding: 10px;
            }
            QPushButton {
                background-color: #fab387;
                color: #11111b;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #f9e2af; }
            QPushButton#Secondary {
                background-color: #313244;
                color: #cdd6f4;
            }
        """)

        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Step 1: 24-Word Phrase
        self.setup_phrase_step()
        
        # Step 2: TOTP QR Code
        self.setup_totp_step()

    def setup_phrase_step(self):
        step1 = QWidget()
        step1_layout = QVBoxLayout(step1)
        
        title = QLabel("Step 1: 🛡️ Recovery Seed Phrase")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #fab387;")
        step1_layout.addWidget(title)

        desc = QLabel(
            "This phrase is the ONLY way to recover your vault if you forget your password. "
            "Write it down and store it in a physical, secure location."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; margin-bottom: 10px;")
        step1_layout.addWidget(desc)

        self.phrase_display = QTextEdit()
        self.phrase_display.setReadOnly(True)
        self.phrase_display.setText(self.phrase)
        step1_layout.addWidget(self.phrase_display)

        warning = QLabel("⚠️ Warning: Never share this phrase. It grants full access to your vault.")
        warning.setStyleSheet("color: #f38ba8; font-size: 11px; margin-top: 5px;")
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

        title = QLabel("Step 2: 📱 Authenticator App (TOTP)")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #89b4fa;")
        step2_layout.addWidget(title)

        desc = QLabel(
            "Scan this QR code with Google Authenticator, Authy, or any TOTP app. "
            "This allows you to reset your password using your phone."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; margin-bottom: 10px;")
        step2_layout.addWidget(desc)

        # QR Code Display
        qr_container = QLabel()
        qr_container.setAlignment(Qt.AlignCenter)
        qr_container.setStyleSheet("background-color: white; padding: 10px; border-radius: 10px;")
        
        pixmap = self.generate_qr_pixmap(self.totp_uri)
        qr_container.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
        step2_layout.addWidget(qr_container)

        # Manual Code
        secret_label = QLabel(f"Manual Secret Key: <b>{self.totp_secret}</b>")
        secret_label.setAlignment(Qt.AlignCenter)
        secret_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        step2_layout.addWidget(secret_label)

        step2_layout.addSpacing(10)

        # Verification Field
        v_title = QLabel("Verify Sync:")
        v_title.setStyleSheet("font-weight: bold; color: #a6adc8;")
        step2_layout.addWidget(v_title)

        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter 6-digit code from app")
        self.otp_input.setAlignment(Qt.AlignCenter)
        self.otp_input.setMaxLength(6)
        self.otp_input.setStyleSheet("""
            QLineEdit {
                background-color: #181825;
                border: 2px solid #313244;
                border-radius: 8px;
                padding: 10px;
                font-size: 18px;
                color: #89b4fa;
                font-weight: bold;
            }
            QLineEdit:focus { border: 2px solid #89b4fa; }
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

        # Verification Logic
        import pyotp
        totp = pyotp.TOTP(self.totp_secret)
        if totp.verify(code):
            QMessageBox.information(self, "Success", "Phone recovery linked successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Verification Failed", "The code you entered is incorrect. Please check your app and try again.")
            self.otp_input.clear()
