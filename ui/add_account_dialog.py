from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QLabel, QTextEdit, QFormLayout, QGroupBox, QCheckBox, QSpinBox,
    QFrame, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import os
from utils.password_generator import PasswordGenerator

class AddAccountDialog(QDialog):
    """Dialog for adding or editing an account entry."""

    def __init__(self, parent=None, account_data=None):
        super().__init__(parent)
        self.account_data = account_data
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Add New Account" if not self.account_data else "Edit Account Details")
        self.setFixedWidth(550)
        
        # Set Window Icon
        icon_path = os.path.join(os.getcwd(), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #11111b;
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                font-weight: bold;
                color: #a6adc8;
                font-size: 13px;
            }
            QLineEdit, QTextEdit, QSpinBox {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px;
                color: #cdd6f4;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #89b4fa;
            }
            QPushButton#Primary {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #89b4fa, stop:1 #cba6f7);
                color: #11111b;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
                min-width: 120px;
            }
            QPushButton#Secondary {
                background-color: #313244;
                color: #cdd6f4;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton#Secondary:hover {
                background-color: #45475a;
            }
            QPushButton#Tertiary {
                background-color: transparent;
                border: 1px solid #45475a;
                color: #89b4fa;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#Tertiary:hover {
                background-color: #313244;
                border-color: #89b4fa;
            }
            QGroupBox {
                border: 1px solid #313244;
                border-radius: 10px;
                margin-top: 20px;
                padding-top: 20px;
                color: #89b4fa;
                font-weight: bold;
            }
            QCheckBox {
                spacing: 10px;
                color: #cdd6f4;
            }
            QProgressBar {
                background-color: #313244;
                border-radius: 4px;
                text-align: center;
                height: 6px;
                border: none;
            }
            QProgressBar::chunk {
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        form = QFormLayout()
        form.setVerticalSpacing(15)
        form.setLabelAlignment(Qt.AlignRight)
        
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText("e.g., GitHub, Google, Amazon")
        form.addRow("🏢 Service Name:", self.service_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Email or Username")
        form.addRow("👤 User / Email:", self.username_input)

        # Password with Generator
        pass_wrapper = QVBoxLayout()
        pass_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Account Password")
        pass_layout.addWidget(self.password_input)
        
        self.gen_toggle_btn = QPushButton("✨ Generate")
        self.gen_toggle_btn.setObjectName("Tertiary")
        self.gen_toggle_btn.setFixedWidth(100)
        self.gen_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.gen_toggle_btn.clicked.connect(self.show_generator_options)
        pass_layout.addWidget(self.gen_toggle_btn)
        
        # Strength Meter Layout
        self.strength_label = QLabel("Strength: ---")
        self.strength_label.setStyleSheet("font-size: 11px; color: #6e6a86;")
        
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(False)
        self.strength_bar.setMaximumHeight(6)
        
        pass_wrapper.addLayout(pass_layout)
        pass_wrapper.addWidget(self.strength_bar)
        pass_wrapper.addWidget(self.strength_label)
        
        form.addRow("🔑 Password:", pass_wrapper)
        
        # Connect real-time update
        self.password_input.textChanged.connect(self.update_strength)

        # Generator Options
        self.gen_group = QGroupBox("Password Requirements")
        self.gen_group.setVisible(False)
        gen_form = QFormLayout(self.gen_group)
        gen_form.setContentsMargins(20, 15, 20, 15)
        
        self.len_spin = QSpinBox()
        self.len_spin.setRange(8, 128)
        self.len_spin.setValue(20)
        gen_form.addRow("Length:", self.len_spin)
        
        self.use_upper = QCheckBox("Include Uppercase (A-Z)")
        self.use_upper.setChecked(True)
        gen_form.addRow(self.use_upper)
        
        self.use_digits = QCheckBox("Include Digits (0-9)")
        self.use_digits.setChecked(True)
        gen_form.addRow(self.use_digits)
        
        self.use_sym = QCheckBox("Include Symbols (!@#$%^*)")
        self.use_sym.setChecked(True)
        gen_form.addRow(self.use_sym)
        
        do_gen_btn = QPushButton("Generate & Use")
        do_gen_btn.setObjectName("Secondary")
        do_gen_btn.setCursor(Qt.PointingHandCursor)
        do_gen_btn.clicked.connect(self.apply_generated)
        gen_form.addRow(do_gen_btn)
        
        layout.addLayout(form)
        layout.addWidget(self.gen_group)

        self.totp_input = QLineEdit()
        self.totp_input.setPlaceholderText("Base32 Key (optional)")
        form.addRow("🔢 2FA Secret:", self.totp_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional encrypted notes...")
        self.notes_input.setMaximumHeight(80)
        form.addRow("📝 Notes:", self.notes_input)

        layout.addSpacing(10)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        save_btn = QPushButton("💾 Save Entry")
        save_btn.setObjectName("Primary")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("Secondary")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def show_generator_options(self):
        visible = self.gen_group.isVisible()
        self.gen_group.setVisible(not visible)
        self.gen_toggle_btn.setText("✨ Generate" if visible else "🔼 Hide")

    def apply_generated(self):
        pwd = PasswordGenerator.generate(
            length=self.len_spin.value(),
            use_upper=self.use_upper.isChecked(),
            use_digits=self.use_digits.isChecked(),
            use_symbols=self.use_sym.isChecked()
        )
        self.password_input.setText(pwd)

    def update_strength(self, password):
        """Calculates password entropy and updates the UI meter."""
        if not password:
            self.strength_bar.setValue(0)
            self.strength_label.setText("Strength: ---")
            return

        score = 0
        length = len(password)
        
        # 1. Length Points
        if length >= 8: score += 1
        if length >= 12: score += 1
        if length >= 16: score += 1
        
        # 2. Diversity Points
        import re
        if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password): score += 1
        if re.search(r"\d", password): score += 1
        if re.search(r"[!@#$%^&*(),.?\":{}|<>_]", password): score += 1

        # Map score (max ~6) to scale 0-100
        # Percentage = (score / 6) * 100
        percent = min(100, int((score / 6) * 100))
        self.strength_bar.setValue(percent)

        # Color and Text mapping
        if length < 8:
            color = "#f38ba8" # Maroon/Red
            text = "Too Short"
            self.strength_bar.setValue(15) # Show some red even if score is low
        elif score <= 2:
            color = "#fab387" # Peach/Orange
            text = "Weak"
        elif score <= 3:
            color = "#f9e2af" # Yellow
            text = "Fair"
        elif score <= 5:
            color = "#a6e3a1" # Green
            text = "Good"
        else:
            color = "#94e2d5" # Teal/Cyan
            text = "Strong"

        self.strength_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
        self.strength_label.setText(f"Strength: {text}")

    def get_data(self):
        """Returns the form data, with sanitized TOTP secret."""
        # Sanitize TOTP: Remove spaces/dashes and uppercase
        totp_raw = self.totp_input.text()
        totp_clean = totp_raw.replace(" ", "").replace("-", "").upper() if totp_raw else ""
        
        return {
            "service": self.service_input.text(),
            "username": self.username_input.text(),
            "password": self.password_input.text(),
            "totp": totp_clean,
            "notes": self.notes_input.toPlainText()
        }
