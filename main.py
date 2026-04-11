import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject, QEvent, Signal
from core.database import DatabaseManager
from core.auth import AuthManager
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

class VaultApp:
    """Main application controller."""

    IDLE_TIMEOUT = 2 * 60 * 1000  # 2 minutes in ms

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("VaultPy")
        
        # Global Icon
        import os
        from PySide6.QtGui import QIcon
        icon_path = os.path.join(os.getcwd(), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))
            
        self.db = DatabaseManager()
        self.auth = AuthManager(self.db)
        
        self.login_window = None
        self.vault_window = None
        self.idle_filter = None
        
        # Single Instance Lock
        from PySide6.QtCore import QLockFile, QDir
        self.lock_file = QLockFile(QDir.tempPath() + "/vaultpy.lock")
        if not self.lock_file.tryLock(100):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", "VaultPy is already running.")
            sys.exit(1)

        self.show_login()

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

    def show_vault(self):
        if self.login_window:
            self.login_window.close()
            self.login_window = None
            
        # 1. Setup Idle Filter first so we can pass it to VaultWindow
        self.idle_filter = IdleFilter(self.IDLE_TIMEOUT)
        self.idle_filter.timeout_signal.connect(self.show_login)
        self.app.installEventFilter(self.idle_filter)
            
        self.vault_window = VaultWindow(self.auth, self.db, self.idle_filter)
        self.vault_window.lock_requested.connect(self.show_login)
        self.vault_window.show()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = VaultApp()
    app.run()
