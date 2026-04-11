import pyotp
import time

class TOTPManager:
    """Handles TOTP code generation and time tracking."""

    @staticmethod
    def get_otp(secret: str) -> str:
        """Generates a 6-digit TOTP code from a secret."""
        try:
            totp = pyotp.TOTP(secret)
            return totp.now()
        except Exception:
            return "ERROR"

    @staticmethod
    def get_remaining_time() -> int:
        """Returns the seconds remaining until the next OTP refresh."""
        return 30 - (int(time.time()) % 30)
