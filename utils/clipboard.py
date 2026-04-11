import pyperclip
from PySide6.QtCore import QTimer

class ClipboardManager:
    """Handles secure clipboard operations with auto-clearing."""

    _timer = None

    @staticmethod
    def copy(text: str, clear_after=20000):
        """Copies text to clipboard and schedules clearing."""
        pyperclip.copy(text)

        # If a timer is already running, stop it
        if ClipboardManager._timer:
            ClipboardManager._timer.stop()

        # Create a new timer to clear the clipboard
        # Note: We need a QTimer or similar that lives in the main loop
        ClipboardManager._timer = QTimer()
        ClipboardManager._timer.setSingleShot(True)
        ClipboardManager._timer.timeout.connect(ClipboardManager.clear)
        ClipboardManager._timer.start(clear_after)

    @staticmethod
    def clear():
        """Clears the clipboard."""
        # Only clear if it hasn't been changed by the user to something else? 
        # (Simplified: just clear it)
        pyperclip.copy("")
        if ClipboardManager._timer:
            ClipboardManager._timer.stop()
            ClipboardManager._timer = None
