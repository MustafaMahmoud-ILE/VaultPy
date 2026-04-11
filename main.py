import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QObject, QEvent, Signal, QThread, QLockFile, QDir
from PySide6.QtGui import QIcon

from core.database import DatabaseManager
from core.auth import AuthManager
from core.updater import Updater
from ui.login_window import LoginWindow
from ui.vault_window import VaultWindow

class IdleFilter(QObject):
    """Event filter to detect user inactivity and broadcast remaining seconds."""
    
    timeout_signal = Signal()
    second_passed = Signal(int)

    def __init__(self, timeout_ms):
        super().__init__()
        self.timeout_ms = timeout_ms
        self.total_seconds = timeout_ms // 1000
        self.remaining_seconds = self.total_seconds

        # Main Timeout Timer
        self.timer = QTimer()
        self.timer.setInterval(timeout_ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timeout_signal.emit)
        
        # Countdown Heartbeat Timer
        self.heartbeat = QTimer()
        self.heartbeat.setInterval(1000)
        self.heartbeat.timeout.connect(self.update_countdown)
        
        self.start_timers()

    def start_timers(self):
        self.remaining_seconds = self.total_seconds
        self.timer.start()
        self.heartbeat.start()
        self.second_passed.emit(self.remaining_seconds)

    def update_countdown(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.second_passed.emit(self.remaining_seconds)

    def eventFilter(self, obj, event):
        if event.type() in [QEvent.MouseMove, QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.Wheel]:
            self.start_timers() # Reset everything
        return super().eventFilter(obj, event)

class DownloadWorker(QThread):
    progress = Signal(int)
    finished = Signal(bool, str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        import os
        from core.updater import Updater
        zip_path = os.path.join(os.environ.get('TEMP', os.getcwd()), "vault_update.zip")
        success = Updater.download_update(self.url, zip_path, self.progress.emit)
        self.finished.emit(success, zip_path)

class VaultApp(QObject):
    IDLE_TIMEOUT = 2 * 60 * 1000  # 2 minutes in ms
    VERSION = "1.1.0"
    update_detected = Signal(str, str, str) # version, url, notes

    def __init__(self):
        super().__init__() # Signal support
        
        # 0. Fix Taskbar Icon for Windows
        try:
            myappid = 'MustafaMahmoud.VaultPy.v1.0' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        self.app = QApplication(sys.argv)
        self.app.setApplicationName("VaultPy")
        
        # Set Global Window Icon
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        icon_path = os.path.join(base_dir, "assets", "icon.png")
            
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Warning: Icon not found at {icon_path}")

        # 0. Migrate data if necessary
        self.migrate_database()
        
        # 1. Global Setup
        self.latest_update_info = None
        
        self.db = DatabaseManager()
        self.auth = AuthManager(self.db)
        
        self.login_window = None
        self.vault_window = None
        self.idle_filter = None
        
        # Single Instance Lock
        self.lock_file = QLockFile(QDir.tempPath() + "/vaultpy.lock")
        if not self.lock_file.tryLock(100):
            QMessageBox.critical(None, "Error", "VaultPy is already running.")
            sys.exit(1)

        # 2. Check for updates on startup (Silent)
        QTimer.singleShot(2000, self.perform_update_check)

        self.show_login()

    def perform_update_check(self):
        """Silently checks for updates in the background."""
        class UpdateWorker(QThread):
            finished = Signal(bool, str, str, str)
            def run(self):
                available, ver, url, notes = Updater.check_for_updates(VaultApp.VERSION)
                self.finished.emit(available, ver, url, notes)

        self.worker = UpdateWorker()
        self.worker.finished.connect(self.on_update_check_finished)
        self.worker.start()

    def on_update_check_finished(self, available, ver, url, notes):
        if available:
            print(f"Update available: {ver}")
            self.latest_update_info = (ver, url, notes)
            self.update_detected.emit(ver, url, notes)
        else:
            print("No updates found.")

    def show_login(self):
        if self.vault_window:
            self.vault_window.close()
            self.vault_window = None
        
        if self.idle_filter:
            self.app.removeEventFilter(self.idle_filter)
            self.idle_filter = None

        self.auth.lock_vault()
        self.login_window = LoginWindow(self.auth)
        self.login_window.login_success.connect(self.show_vault)
        self.login_window.show()

    def initiate_update_download(self, url):
        """Starts the download of the update ZIP in a background thread."""
        self.dl_worker = DownloadWorker(url)
        self.dl_worker.progress.connect(self.vault_window.update_download_progress)
        self.dl_worker.finished.connect(self.handle_update_download_finished)
        self.dl_worker.start()

    def handle_update_download_finished(self, success, zip_path):
        if success:
            print("Download successful. Starting installer...")
            if Updater.run_installer(zip_path):
                # Small delay to ensure command is sent
                QTimer.singleShot(500, self.app.quit)
        else:
            QMessageBox.warning(self.vault_window, "Update Error", "Failed to download the update ZIP.")
            # Restore UI if failed
            self.vault_window.status_label.setText("🛡️ Vault is Secured and Active")
            self.vault_window.update_btn.setVisible(True)
            self.vault_window.progress_bar.setVisible(False)

    def show_vault(self):
        if self.login_window:
            self.login_window.close()
            self.login_window = None
            
        # 1. Setup Idle Filter first so we can pass it to VaultWindow
        self.idle_filter = IdleFilter(self.IDLE_TIMEOUT)
        self.idle_filter.timeout_signal.connect(self.show_login)
        self.app.installEventFilter(self.idle_filter)
            
        self.vault_window = VaultWindow(self.auth, self.db, self.idle_filter)
        
        # Connect Update Signals
        self.vault_window.update_check_requested.connect(self.perform_update_check)
        self.vault_window.install_update_requested.connect(self.initiate_update_download)
        self.update_detected.connect(self.vault_window.show_update_available)
        
        # If an update was already detected during startup, notify immediately
        if self.latest_update_info:
            ver, url, notes = self.latest_update_info
            self.vault_window.show_update_available(ver, url, notes)

        self.vault_window.lock_requested.connect(self.show_login)
        self.vault_window.show()

    def migrate_database(self):
        """Moves the database from the local folder to AppData if it exists."""
        import os
        import shutil
        
        old_path = os.path.join(os.getcwd(), "data", "vault.db")
        
        # Resolve target path (same logic as DatabaseManager)
        app_data = os.getenv('APPDATA')
        if app_data:
            new_dir = os.path.join(app_data, "VaultPy")
        else:
            new_dir = os.path.join(os.path.expanduser("~"), ".vaultpy")
            
        new_path = os.path.join(new_dir, "vault.db")
        
        if os.path.exists(old_path) and not os.path.exists(new_path):
            print(f"Migrating database to: {new_path}")
            os.makedirs(new_dir, exist_ok=True)
            try:
                shutil.move(old_path, new_path)
                print("Migration successful.")
            except Exception as e:
                print(f"Migration failed: {e}")

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = VaultApp()
    app.run()
