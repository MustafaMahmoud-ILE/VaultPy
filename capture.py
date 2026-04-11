import sys
import os
from PySide6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from core.auth import AuthManager
from core.database import DatabaseManager

def capture_screenshot():
    """Launches the app, captures a pixel-perfect screenshot, and exits."""
    app = QApplication(sys.argv)
    
    # Initialize Core
    db = DatabaseManager()
    auth = AuthManager(db)
    
    # Create Widow
    window = LoginWindow(auth)
    window.show()
    
    # Process events to render the window
    QApplication.processEvents()
    
    # Ensure assets directory exists
    os.makedirs('assets', exist_ok=True)
    
    # Grab the screenshot from the widget (including transparency)
    # Give it a tiny sleep to let fade-in finish (or just capture immediate)
    from PySide6.QtCore import QTimer
    
    def on_capture():
        screenshot = window.grab()
        screenshot.save("assets/login_preview.png")
        print("Success: Captured login_preview.png in assets folder!")
        app.quit()
        
    # Wait 800ms for the fade-in animation to finish
    QTimer.singleShot(800, on_capture)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    capture_screenshot()
