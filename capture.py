import sys
import os
from PySide6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from core.auth import AuthManager
from core.database import DatabaseManager

from ui.vault_window import VaultWindow
from models.account import Account

def capture_screenshot():
    """Launches the app, captures screenshots, and exits."""
    app = QApplication(sys.argv)
    
    # Initialize Core
    db = DatabaseManager()
    auth = AuthManager(db)
    
    # 1. Capture Login Screenshot
    login_win = LoginWindow(auth)
    login_win.show()
    QApplication.processEvents()
    
    # Create assets directory
    os.makedirs('assets', exist_ok=True)
    
    from PySide6.QtCore import QTimer
    
    def step_2_capture_vault():
        # Hide login
        login_win.hide()
        
        # 2. Capture Vault Screenshot (with Mock Data)
        # We manually inject a fake key to bypass auth for screenshot
        auth.master_key = b"dummy_key_for_snap" 
        
        vault_win = VaultWindow(auth, db)
        
        # Add some mock items for the list
        mock_accounts = [
            Account(1, "Google", "mustafa@gmail.com", b"enc", b"enc", b"enc"),
            Account(2, "GitHub", "MustafaMahmoud", b"enc", b"enc", b"enc"),
            Account(3, "Facebook", "mustafa_dev", b"enc", b"enc", b"enc")
        ]
        
        # Populate the list widget directly for the shot
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        for acc in mock_accounts:
            item = QListWidgetItem(f"{acc.service} | {acc.username}")
            item.setData(Qt.UserRole, acc)
            vault_win.account_list.addItem(item)
            
        vault_win.show()
        QApplication.processEvents()
        
        def finalize():
            screenshot = vault_win.grab()
            screenshot.save("assets/vault_preview.png")
            print("Success: Captured vault_preview.png in assets folder!")
            app.quit()
            
        QTimer.singleShot(800, finalize)

    def step_1_capture_login():
        screenshot = login_win.grab()
        screenshot.save("assets/login_preview.png")
        print("Success: Captured login_preview.png")
        QTimer.singleShot(100, step_2_capture_vault)
        
    # Wait 800ms for Login fade-in
    QTimer.singleShot(800, step_1_capture_login)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    capture_screenshot()
