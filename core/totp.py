import pyotp
import time

class TOTPManager:
    """Handles TOTP code generation and time tracking."""

    @staticmethod
    def get_otp(secret: str) -> str:
        """Generates a 6-digit TOTP code from a secret."""
        if not secret:
            return ""
        try:
            # Sanitize: Remove spaces, dashes, and ensure uppercase
            clean_secret = str(secret).replace(" ", "").replace("-", "").upper()
            totp = pyotp.TOTP(clean_secret)
            return totp.now()
        except Exception:
            return "ERROR"

    @staticmethod
    def get_remaining_time() -> int:
        """Returns the seconds remaining until the next OTP refresh."""
        return 30 - (int(time.time()) % 30)
