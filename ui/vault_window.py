import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFrame, 
    QSplitter, QScrollArea, QMessageBox, QSpacerItem, QSizePolicy,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QIcon, QFont, QPixmap, QColor
from core.database import DatabaseManager
from core.auth import AuthManager
from core.crypto import CryptoManager
from core.totp import TOTPManager
from utils.clipboard import ClipboardManager
from ui.add_account_dialog import AddAccountDialog
from ui.components.title_bar import CustomTitleBar

class VaultWindow(QWidget):
    """Main application window displaying the password vault (Frameless)."""
    
    lock_requested = Signal()

    def __init__(self, auth_manager: AuthManager, db_manager: DatabaseManager, idle_filter=None):
        super().__init__()
        self.auth = auth_manager
        self.db = db_manager
        self.idle_filter = idle_filter
        self.selected_account = None
        self.totp_val_label = None
        
        # Frameless & Translucent State
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1100, 800)
        
        self.init_ui()
        self.refresh_accounts()
        self.apply_fade_in()

        # Timer for TOTP and live updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_live_elements)
        self.timer.start(1000)
        
        # Connect Idle Timer
        if self.idle_filter:
            self.idle_filter.second_passed.connect(self.update_idle_label)

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }
            QFrame#MainContainer {
                background-color: #0b0b10;
                border-radius: 15px;
                border: 2px solid #45475a;
            }
            QLineEdit#SearchInput {
                background-color: #11111b;
                border: 1.5px solid #45475a;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                margin: 15px;
                color: #ffffff;
            }
            QLineEdit#SearchInput:focus {
                border-color: #89b4fa;
            }
            QListWidget {
                border: none;
                background-color: #0b0b10;
                outline: none;
                padding: 10px;
                color: #ffffff;
            }
            QListWidget::item {
                background-color: #11111b;
                border-radius: 12px;
                padding: 18px;
                margin-bottom: 10px;
                border: 1px solid #313244;
            }
            QListWidget::item:hover {
                background-color: #181825;
                border: 1px solid #45475a;
            }
            QListWidget::item:selected {
                background-color: #1e1e2e;
                border: 2px solid #89b4fa;
                color: #89b4fa;
            }
            QPushButton#ActionBtn {
                background-color: #181825;
                color: #ffffff;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                border: 1.5px solid #45475a;
            }
            QPushButton#ActionBtn:hover {
                background-color: #313244;
                border-color: #89b4fa;
            }
            QPushButton#AccentBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #89b4fa, stop:1 #cba6f7);
                color: #000000;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton#DangerBtn {
                background-color: transparent;
                color: #f38ba8;
                border: 2px solid #f38ba8;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
            }
            QPushButton#DangerBtn:hover {
                background-color: #f38ba8;
                color: #000000;
            }
            QFrame#DetailsPanel {
                background-color: #11111b;
                border-left: 2px solid #313244;
                border-bottom-right-radius: 15px;
            }
            QLabel#DetailHeader {
                font-size: 28px;
                font-weight: bold;
                color: #89b4fa;
                margin-bottom: 25px;
            }
            QLabel#DetailLabel {
                color: #bac2de;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QLabel#DetailValue {
                font-size: 17px;
                margin-bottom: 20px;
                padding: 5px 0;
                color: #ffffff;
            }
        """)

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # 1. Custom Title Bar
        self.title_bar = CustomTitleBar(self, "VaultPy - Secure Dashboard")
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.container_layout.addWidget(self.title_bar)

        # 2. Body Content
        self.body_widget = QWidget()
        self.body_layout = QHBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)

        # Left Column: List and Search
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("🔍 Search your vault...")
        self.search_input.textChanged.connect(self.refresh_accounts)
        search_layout.addWidget(self.search_input)
        
        self.add_btn = QPushButton("+ New Account")
        self.add_btn.setObjectName("AccentBtn")
        self.add_btn.setMinimumHeight(45)
        self.add_btn.clicked.connect(self.show_add_dialog)
        
        add_container = QVBoxLayout()
        add_container.setContentsMargins(0, 15, 15, 15)
        add_container.addWidget(self.add_btn)
        search_layout.addLayout(add_container)
        
        left_layout.addLayout(search_layout)

        self.account_list = QListWidget()
        self.account_list.itemSelectionChanged.connect(self.on_account_selected)
        left_layout.addWidget(self.account_list)

        # Right Column: Details Panel
        self.details_panel = QFrame()
        self.details_panel.setObjectName("DetailsPanel")
        self.details_panel.setMinimumWidth(450)
        
        # Add Scroll Area to Details Panel
        self.details_scroll = QScrollArea()
        self.details_scroll.setWidgetResizable(True)
        self.details_scroll.setFrameShape(QFrame.NoFrame)
        self.details_scroll.setStyleSheet("background: transparent;")
        
        self.details_container = QWidget()
        self.details_container.setStyleSheet("background: transparent;")
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setContentsMargins(40, 40, 40, 40)
        self.details_layout.setAlignment(Qt.AlignTop)
        
        self.details_scroll.setWidget(self.details_container)
        
        # Main layout for the panel to hold the scroll area
        panel_layout = QVBoxLayout(self.details_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self.details_scroll)

        self.setup_details_placeholder()

        # Add to Body
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.details_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStyleSheet("QSplitter::handle { background: #313244; width: 2px; }")
        self.body_layout.addWidget(splitter)

        self.container_layout.addWidget(self.body_widget)

        # 3. Footer Status Bar
        self.status_widget = QWidget()
        self.status_widget.setFixedHeight(50)
        self.status_widget.setStyleSheet("""
            QWidget { 
                background-color: #09090e; 
                border-bottom-left-radius: 15px; 
                border-bottom-right-radius: 15px; 
                border-top: 1px solid #313244;
            }
        """)
        status_layout = QHBoxLayout(self.status_widget)
        status_layout.setContentsMargins(20, 0, 20, 0)
        
        self.status_label = QLabel("🛡️ Vault is Secured and Active")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 13px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # Idle Label
        self.idle_label = QLabel("Auto-locks in 120s")
        self.idle_label.setStyleSheet("color: #fab387; font-family: 'Consolas', monospace; font-size: 13px; margin-right: 15px;")
        status_layout.addWidget(self.idle_label)
        
        lock_btn = QPushButton("🔒 Lock Session")
        lock_btn.setStyleSheet("color: #f38ba8; font-weight: bold; background: transparent; border: none;")
        lock_btn.setCursor(Qt.PointingHandCursor)
        lock_btn.clicked.connect(self.lock_requested.emit)
        status_layout.addWidget(lock_btn)
        
        self.container_layout.addWidget(self.status_widget)
        self.layout.addWidget(self.container)

    def update_idle_label(self, seconds):
        self.idle_label.setText(f"Auto-locks in {seconds}s")
        if seconds < 10:
            self.idle_label.setStyleSheet("color: #f38ba8; font-family: 'Consolas', monospace; font-size: 13px; margin-right: 15px; font-weight: bold;")
        else:
            self.idle_label.setStyleSheet("color: #fab387; font-family: 'Consolas', monospace; font-size: 13px; margin-right: 15px;")

    def apply_fade_in(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.container.setGraphicsEffect(self.opacity_effect)
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(600)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.start()

    def setup_details_placeholder(self):
        self.clear_layout(self.details_layout)
        placeholder_container = QVBoxLayout()
        placeholder_container.setAlignment(Qt.AlignCenter)
        
        placeholder = QLabel("Select an entry to view decrypted details")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #585b70; font-size: 16px; margin-top: 20px;")
        
        placeholder_container.addWidget(placeholder)
        self.details_layout.addStretch()
        self.details_layout.addLayout(placeholder_container)
        self.details_layout.addStretch()
        self.selected_account = None
        self.totp_val_label = None

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())

    def refresh_accounts(self):
        query = self.search_input.text()
        if query.startswith("🔍 "): query = query[2:]
        accounts = self.db.search_accounts(query) if query else self.db.get_all_accounts()
        self.account_list.clear()
        for acc in accounts:
            item = QListWidgetItem(f"{acc.service} | {acc.username}")
            item.setData(Qt.UserRole, acc)
            self.account_list.addItem(item)

    def on_account_selected(self):
        selected_items = self.account_list.selectedItems()
        if not selected_items:
            self.setup_details_placeholder()
            return
        acc_data = selected_items[0].data(Qt.UserRole)
        self.selected_account = acc_data
        self.show_account_details(acc_data)

    def show_account_details(self, acc):
        self.clear_layout(self.details_layout)
        self.totp_val_label = None
        service, username = acc.service, acc.username
        header = QLabel(service)
        header.setObjectName("DetailHeader")
        self.details_layout.addWidget(header)
        self.add_detail_to_layout("👤 Username", username, copy_text=username)
        try:
            password = CryptoManager.decrypt(acc.password_encrypted, self.auth.get_key())
            self.add_detail_to_layout("🔑 Password", "••••••••••••", copy_text=password)
        except Exception:
            self.add_detail_to_layout("🔑 Password", "Error Decrypting")
        if acc.totp_secret_encrypted:
            self.add_detail_to_layout("🔢 One-Time Password", "------", copy_btn=True)
            self.update_live_elements()
        if acc.notes_encrypted:
            try:
                notes = CryptoManager.decrypt(acc.notes_encrypted, self.auth.get_key())
                self.add_detail_to_layout("📝 Notes", notes)
            except Exception:
                self.add_detail_to_layout("📝 Notes", "Error Decrypting")
        self.details_layout.addStretch()
        actions_layout = QHBoxLayout()
        edit_btn = QPushButton("✏️ Edit Entry")
        edit_btn.setObjectName("ActionBtn")
        edit_btn.setMinimumHeight(45)
        edit_btn.clicked.connect(lambda: self.show_edit_dialog(acc))
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setObjectName("DangerBtn")
        delete_btn.setMinimumHeight(45)
        delete_btn.clicked.connect(lambda: self.delete_account(acc[0]))
        actions_layout.addWidget(edit_btn, 1)
        actions_layout.addWidget(delete_btn, 1)
        self.details_layout.addLayout(actions_layout)

    def add_detail_to_layout(self, label_text, value_text, copy_text=None, copy_btn=False):
        lbl = QLabel(label_text)
        lbl.setObjectName("DetailLabel")
        self.details_layout.addWidget(lbl)
        val_layout = QHBoxLayout()
        val = QLabel(value_text)
        val.setObjectName("DetailValue")
        val.setWordWrap(True)
        if "One-Time Password" in label_text:
            self.totp_val_label = val
            val.setStyleSheet("font-size: 26px; color: #fab387; font-weight: bold; font-family: 'Consolas', monospace;")
        val_layout.addWidget(val)
        if copy_text or copy_btn:
            btn = QPushButton("📋 Copy")
            btn.setObjectName("ActionBtn")
            btn.setFixedWidth(80)
            btn.setStyleSheet("font-size: 11px; padding: 6px; border-radius: 6px;")
            btn.setCursor(Qt.PointingHandCursor)
            def do_copy():
                txt = copy_text or (self.totp_val_label.text().split(" ")[0] if self.totp_val_label else "")
                if txt:
                    ClipboardManager.copy(txt)
                    btn.setText("✅ Copied")
                    QTimer.singleShot(2000, lambda: btn.setText("📋 Copy"))
            btn.clicked.connect(do_copy)
            val_layout.addWidget(btn)
        self.details_layout.addLayout(val_layout)
        return val_layout

    def update_live_elements(self):
        if not self.selected_account or not self.selected_account.totp_secret_encrypted or not self.totp_val_label: return
        try:
            totp_secret = CryptoManager.decrypt(self.selected_account.totp_secret_encrypted, self.auth.get_key())
            code = TOTPManager.get_otp(totp_secret)
            remaining = TOTPManager.get_remaining_time()
            self.totp_val_label.setText(f"{code}  ({remaining}s)")
            if remaining < 5: self.totp_val_label.setStyleSheet("font-size: 26px; color: #f38ba8; font-weight: bold; font-family: 'Consolas', monospace;")
            else: self.totp_val_label.setStyleSheet("font-size: 26px; color: #fab387; font-weight: bold; font-family: 'Consolas', monospace;")
        except Exception: pass

    def show_add_dialog(self):
        dialog = AddAccountDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                key = self.auth.get_key()
                self.db.add_account(data['service'], data['username'], CryptoManager.encrypt(data['password'], key), CryptoManager.encrypt(data['totp'], key) if data['totp'] else None, CryptoManager.encrypt(data['notes'], key) if data['notes'] else None)
                self.refresh_accounts()
            except Exception as e: QMessageBox.critical(self, "Error", f"Failed to save account: {e}")

    def show_edit_dialog(self, acc):
        try:
            key = self.auth.get_key()
            dialog = AddAccountDialog(self, account_data=acc)
            dialog.service_input.setText(acc.service)
            dialog.username_input.setText(acc.username)
            dialog.password_input.setText(CryptoManager.decrypt(acc.password_encrypted, key))
            dialog.totp_input.setText(CryptoManager.decrypt(acc.totp_secret_encrypted, key) if acc.totp_secret_encrypted else "")
            dialog.notes_input.setText(CryptoManager.decrypt(acc.notes_encrypted, key) if acc.notes_encrypted else "")
            if dialog.exec():
                new_data = dialog.get_data()
                self.db.update_account(acc.id, new_data['service'], new_data['username'], CryptoManager.encrypt(new_data['password'], key), CryptoManager.encrypt(new_data['totp'], key) if new_data['totp'] else None, CryptoManager.encrypt(new_data['notes'], key) if new_data['notes'] else None)
                self.refresh_accounts()
                self.on_account_selected()
        except Exception as e: QMessageBox.critical(self, "Error", f"Failed to edit account: {e}")

    def delete_account(self, acc_id):
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this account?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_account(acc_id)
            self.refresh_accounts()
            self.setup_details_placeholder()
