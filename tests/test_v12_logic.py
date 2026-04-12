import unittest
import os
import sqlite3
import tempfile
from core.crypto import CryptoManager
from core.database import DatabaseManager
from core.auth import AuthManager

class TestV12Logic(unittest.TestCase):
    """Tests for the new Wrapped Key and Recovery Seed architecture in v1.2.0."""

    def setUp(self):
        # Use a temporary file for the database to ensure persistent connections for testing
        self.fd, self.db_path = tempfile.mkstemp()
        self.db = DatabaseManager(self.db_path)
        self.auth = AuthManager(self.db)

    def tearDown(self):
        # Clear references to close potential sqlite connections
        self.auth = None
        self.db = None
        
        # Try to cleanup the temporary file, but don't fail the test if Windows holds a lock
        os.close(self.fd)
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass

    def test_dek_wrapping_and_unwrapping(self):
        """Test the pure crypto flow for key wrapping."""
        # 1. Generate DEK (32 bytes)
        dek = CryptoManager.generate_dek()
        self.assertEqual(len(dek), 32)

        # 2. Derive KEK from a password
        password = "TestingPassword123"
        salt = os.urandom(16)
        kek = CryptoManager.derive_key(password, salt)

        # 3. Wrap DEK (encrypt it using KEK)
        wrapped_dek = CryptoManager.encrypt(dek.hex(), kek)
        self.assertIsInstance(wrapped_dek, bytes)

        # 4. Unwrap DEK (decrypt it using KEK)
        unwrapped_hex = CryptoManager.decrypt(wrapped_dek, kek)
        unwrapped_dek = bytes.fromhex(unwrapped_hex)
        
        self.assertEqual(unwrapped_dek, dek)

    def test_mnemonic_entropy_and_derivation(self):
        """Test that the 24-word phrase correctly derives a key."""
        phrase, _ = CryptoManager.generate_recovery_phrase()
        words = phrase.split(" ")
        self.assertEqual(len(words), 24)

        salt = os.urandom(16)
        key1 = CryptoManager.derive_key_from_phrase(phrase, salt)
        key2 = CryptoManager.derive_key_from_phrase(phrase, salt)
        
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)

    def test_full_setup_and_unlock(self):
        """Test the complete AuthManager flow from setup to unlock."""
        password = "SecureMasterPassword123"
        
        # Setup
        success = self.auth.setup_vault(password)
        self.assertTrue(success)
        self.assertIsNotNone(self.auth.temp_recovery_phrase)
        self.assertTrue(self.auth.is_unlocked())
        
        dek = self.auth.get_key()
        self.assertEqual(len(dek), 32)

        # Lock and Unlock via Password
        self.auth.lock_vault()
        self.assertFalse(self.auth.is_unlocked())
        
        unlock_success = self.auth.unlock_vault(password)
        self.assertTrue(unlock_success)
        self.assertEqual(self.auth.get_key(), dek)

    def test_recovery_unlock(self):
        """Test unlocking the vault using ONLY the recovery phrase."""
        password = "InitialPassword123"
        self.auth.setup_vault(password)
        phrase = self.auth.temp_recovery_phrase
        original_dek = self.auth.get_key()

        # Try to unlock with phrase
        self.auth.lock_vault()
        success = self.auth.unlock_with_recovery_phrase(phrase)
        
        self.assertTrue(success)
        self.assertEqual(self.auth.get_key(), original_dek)

    def test_migration_from_v11(self):
        """Test that a v1.1.0 database can be upgraded to v1.2.1 Triple-Wrap."""
        password = "LegacyPassword123"
        
        # 1. Simulate a v1.1.0 DB state (direct password derivation)
        p_hash, p_salt = CryptoManager.hash_password(password)
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO meta (password_hash, salt) VALUES (?, ?)",
                (p_hash, p_salt)
            )
        
        # 2. Check if migration is required
        self.assertTrue(self.auth.needs_migration())

        # 3. Perform Migration (v1.1.0 has no wrapped key, handled internally)
        phrase, uri, secret = self.auth.migrate_to_wrapped_keys(password)
        self.assertIsNotNone(phrase)
        self.assertEqual(len(phrase.split(" ")), 24)
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertEqual(len(secret), 32) # Base32 secret length

        # 4. Verify migrated state
        self.assertFalse(self.auth.needs_migration())
        self.assertTrue(self.auth.is_unlocked())
        
        # Verify phrase actually works to unlock after locking
        self.auth.lock_vault()
        self.assertTrue(self.auth.unlock_with_recovery_phrase(phrase))

    def test_totp_unlock(self):
        """Test unlocking the vault using ONLY a TOTP code."""
        import pyotp
        password = "MasterPassword123"
        self.auth.setup_vault(password)
        
        # Get the secret from the database (obfuscated)
        meta = self.db.get_meta()
        secret_obf = meta[5]
        secret = self.auth._deobfuscate_secret(secret_obf)
        
        # Generate valid OTP
        totp = pyotp.TOTP(secret)
        otp = totp.now()
        
        # Clear DEK
        self.auth.lock_vault()
        self.assertFalse(self.auth.is_unlocked())
        
        # Unlock via OTP
        success = self.auth.unlock_with_totp(otp)
        self.assertTrue(success)
        self.assertTrue(self.auth.is_unlocked())

if __name__ == "__main__":
    unittest.main()
