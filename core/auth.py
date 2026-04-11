from core.crypto import CryptoManager
from core.database import DatabaseManager

class AuthManager:
    """Handles authentication and session management."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.master_key = None  # Derived key in memory (None if locked)

    def is_setup_required(self) -> bool:
        """Checks if the user needs to create a master password."""
        return not self.db.is_setup()

    def setup_vault(self, master_password: str) -> bool:
        """Initial vault setup: hashes master password and derives initial key."""
        if len(master_password) < 12:
            return False
            
        password_hash, salt = CryptoManager.hash_password(master_password)
        self.db.save_setup(password_hash, salt)
        
        # Immediately derive the key to "log in"
        self.master_key = CryptoManager.derive_key(master_password, salt)
        return True

    def unlock_vault(self, master_password: str) -> bool:
        """Verifies master password and derives the encryption key."""
        meta = self.db.get_meta()
        if not meta:
            return False
            
        password_hash, salt = meta
        if CryptoManager.verify_password(password_hash, master_password):
            self.master_key = CryptoManager.derive_key(master_password, salt)
            return True
        return False

    def lock_vault(self):
        """Clears the master key from memory."""
        # Security: overwriting memory is tricky in Python, 
        # but setting to None removes the reference.
        self.master_key = None

    def is_unlocked(self) -> bool:
        """Checks if the vault is currently unlocked."""
        return self.master_key is not None

    def get_key(self) -> bytes:
        """Returns the derived key for encryption/decryption."""
        if not self.master_key:
            raise PermissionError("Vault is locked.")
        return self.master_key
