import os
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QLabel, QFrame, QMessageBox, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QFileDialog
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QPixmap, QIcon, QColor
from core.auth import AuthManager
from ui.components.title_bar import CustomTitleBar
from ui.recovery_setup_dialog import RecoverySetupDialog

class LoginWindow(QWidget):
    """Window for master password setup and login (Frameless)."""
    
    login_success = Signal()

    def __init__(self, auth_manager: AuthManager):
        super().__init__()
        self.auth = auth_manager
        
        # Frameless & Translucent State
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(450, 680) # Increased height for recovery link
        
        self.init_ui()
        self.apply_fade_in()

    def init_ui(self):
        # Global Style
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }
            QFrame#MainContainer {
                background-color: #0b0b10;
                border-radius: 15px;
                border: 2px solid #45475a;
            }
            QFrame#LoginCard {
                background-color: #11111b;
                border-radius: 20px;
                border: 1px solid #45475a;
            }
            QLabel#Subtitle {
                font-size: 14px;
                color: #bac2de;
                margin-bottom: 20px;
            }
            QLineEdit {
                background-color: #181825;
                border: 1.5px solid #45475a;
                border-radius: 10px;
                padding: 15px;
                font-size: 15px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1.5px solid #89b4fa;
            }
            QPushButton#PrimaryAction {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #89b4fa, stop:1 #cba6f7);
                color: #000000;
                border-radius: 10px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#PrimaryAction:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b4befe, stop:1 #f5c2e7);
            }
            QPushButton#ResetLink {
                color: #585b70;
                text-decoration: underline;
                background: transparent;
                border: none;
                font-size: 12px;
                margin-top: 5px;
            }
            QPushButton#RecoveryLink {
                color: #fab387;
                text-decoration: underline;
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: bold;
                margin-top: 15px;
            }
            QPushButton#ImportLink {
                color: #89b4fa;
                text-decoration: underline;
                background: transparent;
                border: none;
                font-size: 12px;
                margin-top: 5px;
            }
        """)

        # Main Layout (containing the rounded container)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10) # Space for shadow

        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # 1. Custom Title Bar
        self.title_bar = CustomTitleBar(self, "VaultPy - Secure Access")
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.container_layout.addWidget(self.title_bar)

        # 2. Content Section
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(30, 5, 30, 30)
        self.content_layout.setAlignment(Qt.AlignCenter)

        # Container Card
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(40, 40, 40, 40)
        self.card_layout.setSpacing(15)

        # Logo Section
        self.logo_label = QLabel("VaultPy")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("""
            font-size: 42px; 
            font-weight: 800; 
            color: #89b4fa;
            margin-bottom: 5px;
            letter-spacing: 2px;
        """)
        self.card_layout.addWidget(self.logo_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("Subtitle")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.card_layout.addWidget(self.subtitle_label)

        # Inputs
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Master Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_action)
        self.card_layout.addWidget(self.password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm Master Password")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setVisible(False)
        self.card_layout.addWidget(self.confirm_password_input)

        self.card_layout.addSpacing(10)

        # Setup Info
        self.setup_warning = QLabel("🛡️ Recovery: A 24-word seed phrase will be generated to help you recover your vault if you lose this password.")
        self.setup_warning.setObjectName("SetupWarning")
        self.setup_warning.setWordWrap(True)
        self.setup_warning.setAlignment(Qt.AlignCenter)
        self.setup_warning.setStyleSheet("color: #a6e3a1; font-size: 12px; margin-bottom: 5px;")
        self.setup_warning.setVisible(False)
        self.card_layout.addWidget(self.setup_warning)

        # Action Button
        self.action_button = QPushButton("Unlock Vault")
        self.action_button.setObjectName("PrimaryAction")
        self.action_button.setCursor(Qt.PointingHandCursor)
        self.action_button.clicked.connect(self.handle_action)
        self.card_layout.addWidget(self.action_button)

        # Recovery Links
        self.recovery_phrase_btn = QPushButton("🔑 Recover with Phrase")
        self.recovery_phrase_btn.setObjectName("RecoveryLink")
        self.recovery_phrase_btn.setCursor(Qt.PointingHandCursor)
        self.recovery_phrase_btn.clicked.connect(self.handle_phrase_recovery)
        self.recovery_phrase_btn.setVisible(False)
        self.card_layout.addWidget(self.recovery_phrase_btn)

        self.recovery_otp_btn = QPushButton("📱 Recover with Phone (OTP)")
        self.recovery_otp_btn.setObjectName("RecoveryLink")
        self.recovery_otp_btn.setStyleSheet("color: #89b4fa;")
        self.recovery_otp_btn.setCursor(Qt.PointingHandCursor)
        self.recovery_otp_btn.clicked.connect(self.handle_otp_recovery)
        self.recovery_otp_btn.setVisible(False)
        self.card_layout.addWidget(self.recovery_otp_btn)

        # Import Link
        self.import_btn = QPushButton("📥 Import Vault (.pyvault)")
        self.import_btn.setObjectName("ImportLink")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self.handle_import)
        self.card_layout.addWidget(self.import_btn)

        # Factory Reset Link
        self.reset_btn = QPushButton("Factory Reset (Wipe All Data)")
        self.reset_btn.setObjectName("ResetLink")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.handle_reset)
        self.reset_btn.setVisible(False)
        self.card_layout.addWidget(self.reset_btn)

        self.content_layout.addWidget(self.card)
        self.container_layout.addWidget(self.content_widget)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)

        self.layout.addWidget(self.container)

        if self.auth.is_setup_required():
            self.set_setup_mode()
        else:
            self.set_login_mode()

    def set_setup_mode(self):
        self.is_setup = True
        self.subtitle_label.setText("Create your master password to initialize your personal vault.")
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #bac2de; margin-bottom: 20px;")
        
        self.password_input.setPlaceholderText("Master Password")
        self.password_input.setEnabled(True)
        
        self.action_button.setText("Initialize Vault")
        self.action_button.setEnabled(True)
        self.action_button.setStyleSheet("") 
        
        self.confirm_password_input.setVisible(True)
        self.setup_warning.setVisible(True)
        self.recovery_phrase_btn.setVisible(False)
        self.recovery_otp_btn.setVisible(False)
        self.reset_btn.setVisible(False)

    def set_login_mode(self):
        self.is_setup = False
        
        if self.auth.is_locked_out():
            self.subtitle_label.setText("⚠️ Vault Locked: Too many failed attempts. Use recovery phrase or OTP to reset access.")
            self.subtitle_label.setStyleSheet("font-size: 13px; color: #f38ba8; font-weight: bold; margin-bottom: 20px;")
            self.password_input.setPlaceholderText("LOCKED")
            self.password_input.setEnabled(False)
            self.action_button.setText("Access Denied")
            self.action_button.setEnabled(False)
            self.action_button.setStyleSheet("background: #313244; color: #585b70;")
            
            # Highlight recovery buttons
            self.recovery_phrase_btn.setStyleSheet("color: #fab387; font-weight: 800; font-size: 14px;")
            self.recovery_otp_btn.setStyleSheet("color: #89b4fa; font-weight: 800; font-size: 14px;")
        else:
            self.subtitle_label.setText("Enter password to decrypt your secure repository.")
            self.subtitle_label.setStyleSheet("font-size: 14px; color: #bac2de; margin-bottom: 20px;")
            self.password_input.setPlaceholderText("Master Password")
            self.password_input.setEnabled(True)
            self.action_button.setText("Unlock Vault")
            self.action_button.setEnabled(True)
            self.action_button.setStyleSheet("") # Revert to stylesheet default
            
            self.recovery_phrase_btn.setStyleSheet("")
            self.recovery_otp_btn.setStyleSheet("color: #89b4fa;")

        self.confirm_password_input.setVisible(False)
        self.setup_warning.setVisible(False)
        self.recovery_phrase_btn.setVisible(True)
        self.recovery_otp_btn.setVisible(True)
        self.reset_btn.setVisible(True)

    def handle_import(self):
        """Allows user to restore vault from a .pyvault backup."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Vault", "", "VaultPy Backup (*.pyvault)"
        )
        if file_path:
            confirm = QMessageBox.question(
                self, "Confirm Import",
                "Importing a vault will OVERWRITE your current data. Are you sure you want to proceed?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                try:
                    # Target is the current DB path
                    target_path = self.auth.db.db_path
                    shutil.copy(file_path, target_path)
                    
                    QMessageBox.information(self, "Success", "Vault imported successfully. Please log in.")
                    
                    # Refresh UI mode based on imported DB
                    if self.auth.is_setup_required():
                        self.set_setup_mode()
                    else:
                        self.set_login_mode()
                    
                    self.password_input.clear()
                    self.confirm_password_input.clear()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to import vault: {e}")

    def handle_phrase_recovery(self):
        """Handle access restoration via 24-word phrase."""
        from PySide6.QtWidgets import QInputDialog
        phrase, ok = QInputDialog.getMultiLineText(self, "Vault Recovery", "Enter your 24-word recovery phrase:")
        if ok and phrase:
            if self.auth.unlock_with_recovery_phrase(phrase):
                self._perform_password_reset_flow()
            else:
                QMessageBox.critical(self, "Error", "Invalid Recovery Phrase. Access Denied.")

    def handle_otp_recovery(self):
        """Handle access restoration via TOTP 6-digit code."""
        from PySide6.QtWidgets import QInputDialog
        code, ok = QInputDialog.getText(self, "Phone Recovery", "Enter the 6-digit code from your Authenticator app:")
        if ok and code:
            if self.auth.unlock_with_totp(code):
                self._perform_password_reset_flow()
            else:
                QMessageBox.critical(self, "Error", "Invalid or expired OTP code. Access Denied.")

    def _perform_password_reset_flow(self):
        """Internal helper to prompt for new password after recovery success."""
        from PySide6.QtWidgets import QInputDialog
        new_pass, ok = QInputDialog.getText(
            self, "Reset Password", 
            "Identity Verified! Enter a NEW master password:", 
            QLineEdit.Password
        )
        if ok and len(new_pass) >= 12:
            if self.auth.reset_password(new_pass):
                QMessageBox.information(self, "Success", "Password reset successfully. Access granted.")
                self.login_success.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to update vault keys.")
        elif ok:
            QMessageBox.warning(self, "Security", "New password too short. Reset aborted.")

    def handle_reset(self):
        msg = "Are you sure you want to RESET your vault?\n\nThis will PERMANENTLY DELETE all accounts and passwords. This action is IRREVERSIBLE."
        reply = QMessageBox.question(self, "Factory Reset", msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "Security Confirmation", "To confirm data deletion, please type 'RESET' in uppercase:")
            if ok and text == "RESET":
                self.auth.db.factory_reset()
                QMessageBox.information(self, "Success", "Vault wiped successfully.")
                self.set_setup_mode()
                self.password_input.clear()
            elif ok:
                QMessageBox.critical(self, "Error", "Invalid confirmation code. Reset cancelled.")

    def apply_fade_in(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.container.setGraphicsEffect(self.opacity_effect)
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(600)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self._restore_shadow)
        self.animation.start()

    def _restore_shadow(self):
        """Re-apply shadow effect after fade-in completes (Qt allows only one effect per widget)."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)

    def handle_action(self):
        password = self.password_input.text()
        
        if self.is_setup:
            confirm = self.confirm_password_input.text()
            if len(password) < 12:
                QMessageBox.warning(self, "Security Requirement", "Master password must be at least 12 characters long.")
                return
            if password != confirm:
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return
            
            if self.auth.setup_vault(password):
                # Show recovery wizard (Phrase + TOTP)
                dialog = RecoverySetupDialog(
                    self.auth.temp_recovery_phrase, 
                    self.auth.get_totp_uri(),
                    self.auth.temp_totp_secret,
                    self
                )
                dialog.exec()
                self.login_success.emit()
        else:
            # Check for migration first
            if self.auth.needs_migration():
                if self.auth.unlock_vault(password):
                    # Perform migration to Triple-Wrap (Phrase + TOTP)
                    phrase, uri, secret = self.auth.migrate_to_wrapped_keys(password)
                    dialog = RecoverySetupDialog(phrase, uri, secret, self, is_migration=True)
                    dialog.exec()
                    self.login_success.emit()
                else:
                    QMessageBox.warning(self, "Error", "Invalid Master Password.")
                    self.password_input.clear()
            else:
                if self.auth.unlock_vault(password):
                    self.login_success.emit()
                else:
                    if self.auth.is_locked_out():
                        QMessageBox.critical(self, "Security Lockout", "Too many failed attempts. Your vault has been locked for security.\n\nYou must use your recovery phrase or OTP to reset your password.")
                        self.set_login_mode() # Refresh UI to locked state
                    else:
                        failed_count = self.auth.db.get_failed_attempts()
                        remaining = 5 - failed_count
                        QMessageBox.warning(self, "Error", f"Invalid Master Password.\n\n{remaining} attempts remaining before lockout.")
                    self.password_input.clear()
