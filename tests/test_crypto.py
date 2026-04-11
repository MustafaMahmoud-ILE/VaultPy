import unittest
import os
from core.crypto import CryptoManager

class TestCrypto(unittest.TestCase):
    """Unit tests for encryption and hashing logic."""

    def test_aes_encrypt_decrypt(self):
        """Test that data encrypted can be correctly decrypted."""
        key = os.urandom(32)
        plaintext = "SecretPassword123"
        
        encrypted = CryptoManager.encrypt(plaintext, key)
        self.assertIsInstance(encrypted, bytes)
        self.assertNotEqual(encrypted.decode(errors='ignore'), plaintext)
        
        decrypted = CryptoManager.decrypt(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_argon2_hashing(self):
        """Test password hashing and verification."""
        password = "MasterPassword"
        
        hashed, salt = CryptoManager.hash_password(password)
        self.assertIn("$argon2id$", hashed)
        
        # Verify success
        self.assertTrue(CryptoManager.verify_password(hashed, password))
        
        # Verify failure
        self.assertFalse(CryptoManager.verify_password(hashed, "WrongPassword"))

    def test_wrong_key_decryption(self):
        """Test that decryption fails with wrong key."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = "SecretData"
        
        encrypted = CryptoManager.encrypt(plaintext, key1)
        
        with self.assertRaises(Exception):
            CryptoManager.decrypt(encrypted, key2)

if __name__ == "__main__":
    unittest.main()
