import sys
import os

# Add parent directory to sys.path so it can find project modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from ui.vault_window import VaultWindow
from models.account import Account
from core.auth import AuthManager
from core.database import DatabaseManager

def capture_screenshot():
    """Launches the app, captures screenshots, and exits."""
    app = QApplication(sys.argv)
    
    # Initialize Core (Assume DB is in project root)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(project_root, "data", "vault.db")
    db = DatabaseManager(db_path)
    auth = AuthManager(db)
    
    # 1. Capture Login Screenshot
    login_win = LoginWindow(auth)
    login_win.show()
    QApplication.processEvents()
    
    # Create assets directory in project root
    assets_dir = os.path.join(project_root, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    
    from PySide6.QtCore import QTimer
    
    def step_2_capture_vault():
        # Hide login
        login_win.hide()
        
        # 2. Capture Vault Screenshot (with Mock Data)
        auth.master_key = b"dummy_key_for_snap" 
        
        # Pass db to VaultWindow
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
            screenshot.save(os.path.join(assets_dir, "vault_preview.png"))
            print("Success: Captured vault_preview.png in assets folder!")
            app.quit()
            
        QTimer.singleShot(800, finalize)

    def step_1_capture_login():
        screenshot = login_win.grab()
        screenshot.save(os.path.join(assets_dir, "login_preview.png"))
        print("Success: Captured login_preview.png")
        QTimer.singleShot(100, step_2_capture_vault)
        
    # Wait 800ms for Login fade-in
    QTimer.singleShot(800, step_1_capture_login)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    capture_screenshot()
