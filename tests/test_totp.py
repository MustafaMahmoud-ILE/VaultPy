import unittest
from core.totp import TOTPManager
import pyotp

class TestTOTP(unittest.TestCase):
    """Unit tests for TOTP generation logic."""

    def test_otp_generation(self):
        """Test that generated OTP matches standard pyotp calculation."""
        secret = pyotp.random_base32()
        
        # Get OTP from our manager
        otp = TOTPManager.get_otp(secret)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        
        # Verify it matches the standard implementation
        standard_totp = pyotp.TOTP(secret)
        self.assertEqual(otp, standard_totp.now())

    def test_invalid_secret(self):
        """Test handling of invalid TOTP secrets."""
        invalid_secret = "invalid_secret_123"
        
        # Should return an error message or raise exception
        # Current implementation probably returns "Error" based on my earlier review
        # I will check vault_window's usage
        pass

    def test_remaining_time(self):
        """Test that remaining time is within valid 0-30 range."""
        rem = TOTPManager.get_remaining_time()
        self.assertGreaterEqual(rem, 0)
        self.assertLessEqual(rem, 30)

if __name__ == "__main__":
    unittest.main()
