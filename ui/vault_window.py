import os
import shutil
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFrame, 
    QSplitter, QScrollArea, QMessageBox, QSpacerItem, QSizePolicy,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QProgressBar,
    QFileDialog
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
from ui.components.message_box import Alert
from ui.theme import MidnightVault

class VaultWindow(QWidget):
    """Main application window displaying the password vault (Midnight Vault Edition)."""
    
    lock_requested = Signal()
    update_check_requested = Signal()
    install_update_requested = Signal(str) # url

    def __init__(self, auth_manager: AuthManager, db_manager: DatabaseManager, idle_filter=None):
        super().__init__()
        self.auth = auth_manager
        self.db = db_manager
        self.idle_filter = idle_filter
        self.selected_account = None
        self.totp_val_label = None
        self.active_dialog = None
        
        # Frameless & Translucent State
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1100, 800)
        
        self.init_ui()
        self.refresh_folders()
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
        self.setStyleSheet(f"""
            QWidget {{
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }}
            QFrame#MainContainer {{
                background-color: {MidnightVault.BG_PRIMARY};
                border-radius: 16px;
                border: 1px solid {MidnightVault.BORDER};
            }}
            QLineEdit#SearchInput {{
                background-color: {MidnightVault.BG_ELEVATED};
                border: 1.5px solid {MidnightVault.BORDER};
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 14px;
                margin: 15px;
                color: {MidnightVault.TEXT_PRIMARY};
            }}
            QLineEdit#SearchInput:focus {{
                border-color: {MidnightVault.ACCENT_PRIMARY};
            }}
            QListWidget {{
                border: none;
                background-color: transparent;
                outline: none;
                padding: 5px;
            }}
            QListWidget#AccountList::item {{
                background-color: {MidnightVault.BG_SECONDARY};
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 8px;
                border: 1px solid {MidnightVault.BORDER};
                color: {MidnightVault.TEXT_PRIMARY};
                min-height: 72px;
            }}
            QListWidget#AccountList::item:hover {{
                background-color: {MidnightVault.BG_ELEVATED};
                border: 1px solid {MidnightVault.BORDER};
            }}
            QListWidget#AccountList::item:selected {{
                background-color: {MidnightVault.BG_ELEVATED};
                border: 2px solid {MidnightVault.ACCENT_PRIMARY};
                color: {MidnightVault.ACCENT_PRIMARY};
            }}
            QPushButton#ActionBtn {{
                background-color: {MidnightVault.BG_ELEVATED};
                color: {MidnightVault.TEXT_PRIMARY};
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: 600;
                border: 1px solid {MidnightVault.BORDER};
            }}
            QPushButton#ActionBtn:hover {{
                background-color: {MidnightVault.BORDER};
                border-color: {MidnightVault.ACCENT_PRIMARY};
            }}
            QPushButton#AccentBtn {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {MidnightVault.ACCENT_PRIMARY}, stop:1 {MidnightVault.ACCENT_SECONDARY});
                color: #ffffff;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton#DangerBtn {{
                background-color: rgba(247, 118, 142, 0.1);
                color: {MidnightVault.DANGER};
                border: 1px solid {MidnightVault.DANGER};
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: 600;
            }}
            QPushButton#DangerBtn:hover {{
                background-color: {MidnightVault.DANGER};
                color: #ffffff;
            }}
            QFrame#DetailsPanel {{
                background-color: {MidnightVault.BG_SECONDARY};
                border-left: 1px solid {MidnightVault.BORDER};
            }}
            QLabel#DetailHeader {{
                font-size: 32px;
                font-weight: 700;
                color: {MidnightVault.ACCENT_PRIMARY};
                margin-bottom: 25px;
                letter-spacing: -0.5px;
            }}
            QLabel#DetailLabel {{
                color: {MidnightVault.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            QLabel#DetailValue {{
                font-size: 17px;
                padding: 5px 0;
                color: {MidnightVault.TEXT_PRIMARY};
            }}
            QListWidget#FolderSidebar {{
                background-color: {MidnightVault.BG_PRIMARY};
                border-right: 1px solid {MidnightVault.BORDER};
                padding: 10px;
                color: {MidnightVault.TEXT_SECONDARY};
            }}
            QListWidget#FolderSidebar::item {{
                border-radius: 8px;
                padding: 10px 12px;
                margin-bottom: 4px;
                font-size: 13px;
                font-weight: 600;
            }}
            QListWidget#FolderSidebar::item:hover {{
                background-color: {MidnightVault.BG_ELEVATED};
                color: {MidnightVault.TEXT_PRIMARY};
            }}
            QListWidget#FolderSidebar::item:selected {{
                background-color: rgba(122, 162, 247, 0.15);
                color: {MidnightVault.ACCENT_PRIMARY};
                border-left: 3px solid {MidnightVault.ACCENT_PRIMARY};
            }}
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

        # 0. Folders Sidebar (Leftmost)
        self.folder_sidebar = QListWidget()
        self.folder_sidebar.setObjectName("FolderSidebar")
        self.folder_sidebar.setFixedWidth(200)
        self.folder_sidebar.itemSelectionChanged.connect(self.refresh_accounts)
        self.body_layout.addWidget(self.folder_sidebar)
        
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
        self.account_list.setObjectName("AccountList")
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
        # Check for Updates Button
        status_layout.addSpacing(15)
        self.update_btn = QPushButton("🔄 Check for Updates")
        self.update_btn.setStyleSheet("color: #89b4fa; font-size: 11px; background: transparent; border: none;")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.clicked.connect(self.request_update_check)
        status_layout.addWidget(self.update_btn)

        # Backup Button
        status_layout.addSpacing(15)
        self.backup_btn = QPushButton("💾 Backup Vault (.pyvault)")
        self.backup_btn.setStyleSheet("color: #a6e3a1; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        self.backup_btn.setCursor(Qt.PointingHandCursor)
        self.backup_btn.clicked.connect(self.handle_backup)
        status_layout.addWidget(self.backup_btn)
        
        # Download Progress (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e2e;
                border-radius: 5px;
                text-align: center;
                color: transparent;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 5px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        self.container_layout.addWidget(self.status_widget)
        self.layout.addWidget(self.container)

    def request_update_check(self):
        self.update_btn.setText("⏳ Checking...")
        self.update_btn.setEnabled(False)
        self.update_check_requested.emit()
        # Reset text after a timeout if no signal comes back
        QTimer.singleShot(10000, lambda: self.update_btn.setText("🔄 Check for Updates"))
        QTimer.singleShot(10000, lambda: self.update_btn.setEnabled(True))

    def show_update_available(self, version, url, notes):
        """Shows an update notification dialog with a download option."""
        self.update_btn.setText("✨ Update Available!")
        self.update_btn.setStyleSheet("color: #a6e3a1; font-weight: bold; background: transparent; border: none;")
        self.update_btn.setEnabled(True)
        
        full_msg = (
            f"A new version ({version}) is available!\n\n"
            "Would you like to download and install it automatically?\n\n"
            f"Release Notes:\n{notes}"
        )
        
        if Alert.question(self, "VaultPy Update", full_msg):
            self.update_btn.setVisible(False)
            self.progress_bar.setVisible(True)
            self.status_label.setText("⏬ Downloading Update...")
            self.install_update_requested.emit(url)

    def update_download_progress(self, percent):
        if percent == -1:
            # Unknown size, set to Marquee (pulse) mode
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)
            
        if percent >= 100:
            self.progress_bar.setRange(0, 100) # Reset to normal
            self.progress_bar.setValue(100)
            self.status_label.setText("📦 Preparing Installation...")

    def update_idle_label(self, seconds):
        self.idle_label.setText(f"Auto-locks in {seconds}s")
        if seconds < 10:
            self.idle_label.setStyleSheet("color: #f38ba8; font-family: 'Consolas', monospace; font-size: 13px; margin-right: 15px; font-weight: bold;")
        else:
            self.idle_label.setStyleSheet("color: #fab387; font-family: 'Consolas', monospace; font-size: 13px; margin-right: 15px;")

    def closeEvent(self, event):
        """Ensures all modal children are dismissed when the vault locks."""
        if self.active_dialog:
            try:
                self.active_dialog.reject()
            except Exception:
                pass
        event.accept()

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

    def refresh_folders(self):
        """Populates the sidebar with unique folders from the database."""
        current_selection = self.folder_sidebar.currentItem().text() if self.folder_sidebar.currentItem() else "📁 All Accounts"
        self.folder_sidebar.clear()
        
        folders = self.db.get_all_folders()
        all_item = QListWidgetItem("📁 All Accounts")
        self.folder_sidebar.addItem(all_item)
        
        has_uncategorized = False
        for folder in folders:
            if not folder:
                has_uncategorized = True
                continue
            item = QListWidgetItem(f"📁 {folder}")
            self.folder_sidebar.addItem(item)
            if f"📁 {folder}" == current_selection:
                self.folder_sidebar.setCurrentItem(item)
                
        if has_uncategorized:
            item = QListWidgetItem("📁 Uncategorized")
            self.folder_sidebar.addItem(item)
            if "📁 Uncategorized" == current_selection:
                self.folder_sidebar.setCurrentItem(item)

        if not self.folder_sidebar.currentItem():
            self.folder_sidebar.setCurrentItem(all_item)

    def refresh_accounts(self):
        query = self.search_input.text()
        if query.startswith("🔍 "): query = query[2:]
        
        # Folder Filtering
        selected_folder_item = self.folder_sidebar.currentItem()
        folder_filter = selected_folder_item.text() if selected_folder_item else "📁 All Accounts"
        
        accounts = self.db.search_accounts(query) if query else self.db.get_all_accounts()
        
        if folder_filter == "📁 Uncategorized":
            accounts = [acc for acc in accounts if not acc.folder]
        elif folder_filter != "📁 All Accounts":
            folder_name = folder_filter[2:]
            accounts = [acc for acc in accounts if acc.folder == folder_name]

        self.account_list.clear()
        for acc in accounts:
            # Multi-line item text
            display_text = f"{acc.service}\n{acc.username}"
            item = QListWidgetItem(display_text)
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
        
        if acc.folder:
            self.add_detail_to_layout("📁 Folder", acc.folder)
            
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
        delete_btn.clicked.connect(lambda: self.delete_account(acc.id))
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
                    btn.setText("✓ Copied!")
                    btn.setStyleSheet(f"background-color: {MidnightVault.SUCCESS}; color: #ffffff; font-size: 11px; padding: 6px; border-radius: 6px;")
                    QTimer.singleShot(2000, lambda: btn.setText("📋 Copy"))
                    QTimer.singleShot(2000, lambda: btn.setStyleSheet("font-size: 11px; padding: 6px; border-radius: 6px;"))
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
            
            base_style = f"font-size: 32px; font-weight: 700; font-family: 'JetBrains Mono', 'Consolas', monospace; padding: 10px;"
            if remaining < 5: 
                self.totp_val_label.setStyleSheet(f"{base_style} color: {MidnightVault.DANGER};")
            else: 
                self.totp_val_label.setStyleSheet(f"{base_style} color: {MidnightVault.INFO};")
        except Exception: pass

    def show_add_dialog(self):
        self.active_dialog = AddAccountDialog(self)
        if self.active_dialog.exec():
            data = self.active_dialog.get_data()
            try:
                key = self.auth.get_key()
                self.db.add_account(
                    data['service'], 
                    data['username'], 
                    CryptoManager.encrypt(data['password'], key), 
                    CryptoManager.encrypt(data['totp'], key) if data['totp'] else None, 
                    CryptoManager.encrypt(data['notes'], key) if data['notes'] else None,
                    data['folder']
                )
                self.refresh_folders()
                self.refresh_accounts()
            except Exception as e: Alert.error(self, "Error", f"Failed to save account: {e}")
        self.active_dialog = None

    def show_edit_dialog(self, acc):
        try:
            key = self.auth.get_key()
            self.active_dialog = AddAccountDialog(self, account_data=acc)
            dialog = self.active_dialog
            dialog.service_input.setText(acc.service)
            dialog.username_input.setText(acc.username)
            dialog.password_input.setText(CryptoManager.decrypt(acc.password_encrypted, key))
            dialog.totp_input.setText(CryptoManager.decrypt(acc.totp_secret_encrypted, key) if acc.totp_secret_encrypted else "")
            dialog.notes_input.setText(CryptoManager.decrypt(acc.notes_encrypted, key) if acc.notes_encrypted else "")
            dialog.folder_input.setText(acc.folder if acc.folder else "")
            if dialog.exec():
                new_data = dialog.get_data()
                self.db.update_account(
                    acc.id, 
                    new_data['service'], 
                    new_data['username'], 
                    CryptoManager.encrypt(new_data['password'], key), 
                    CryptoManager.encrypt(new_data['totp'], key) if new_data['totp'] else None, 
                    CryptoManager.encrypt(new_data['notes'], key) if new_data['notes'] else None,
                    new_data['folder']
                )
                self.refresh_folders()
                self.refresh_accounts()
                self.on_account_selected()
        except Exception as e: Alert.error(self, "Error", f"Failed to edit account: {e}")
        self.active_dialog = None

    def delete_account(self, acc_id):
        if Alert.question(self, "Confirm Delete", "Are you sure you want to delete this account?"):
            self.db.delete_account(acc_id)
            self.refresh_folders()
            self.refresh_accounts()
            self.setup_details_placeholder()

    def handle_backup(self):
        """Exports the current database as an encrypted .pyvault file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Vault", "", "VaultPy Backup (*.pyvault)"
        )
        if file_path:
            if not file_path.endswith(".pyvault"):
                file_path += ".pyvault"
            try:
                shutil.copy(self.db.db_path, file_path)
                Alert.success(self, "Success", f"Vault backup created successfully at:\n{file_path}")
            except Exception as e:
                Alert.error(self, "Error", f"Failed to create backup: {e}")
