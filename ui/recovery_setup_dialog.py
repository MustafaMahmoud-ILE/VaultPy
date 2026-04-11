from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, 
    QPushButton, QHBoxLayout, QFrame, QMessageBox
)
from PySide6.QtCore import Qt

class RecoverySetupDialog(QDialog):
    """Dialog to show the 24-word recovery phrase to the user."""
    
    def __init__(self, phrase, parent=None, is_migration=False):
        super().__init__(parent)
        self.phrase = phrase
        self.is_migration = is_migration
        self.setWindowTitle("Critical: Save Your Recovery Phrase")
        self.setFixedSize(500, 450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0b10;
            }
            QLabel {
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
            }
            QTextEdit {
                background-color: #11111b;
                border: 2px solid #fab387;
                border-radius: 10px;
                color: #fab387;
                font-family: 'Consolas', monospace;
                font-size: 16px;
                padding: 15px;
            }
            QPushButton {
                background-color: #fab387;
                color: #11111b;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f9e2af;
            }
        """)

        # Header
        title = QLabel("🛡️ Your Recovery Seed Phrase")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #fab387;")
        layout.addWidget(title)

        msg_text = (
            "This phrase is the ONLY way to recover your vault if you forget your master password. "
            "Write it down and store it in a physical, secure location."
        )
        if self.is_migration:
            msg_text = "VaultPy has been upgraded to a more secure architecture. " + msg_text

        msg = QLabel(msg_text)
        msg.setWordWrap(True)
        msg.setStyleSheet("margin-top: 5px; margin-bottom: 15px; color: #a6adc8;")
        layout.addWidget(msg)

        # Phrase Display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setText(self.phrase)
        layout.addWidget(self.text_display)

        warning = QLabel("⚠️ Warning: Never share this phrase. Anyone with these 24 words can unlock your vault.")
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #f38ba8; font-size: 11px; margin-top: 10px;")
        layout.addWidget(warning)

        # Confirm Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.confirm_btn = QPushButton("I have saved this phrase securely")
        self.confirm_btn.clicked.connect(self.on_confirm)
        btn_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(btn_layout)

    def on_confirm(self):
        reply = QMessageBox.question(
            self, "Confirm Safety", 
            "Are you absolutely sure you have written down or saved this phrase? "
            "You will NOT be able to see it again easily.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.accept()
