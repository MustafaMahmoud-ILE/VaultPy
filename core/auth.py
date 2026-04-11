import os
from core.crypto import CryptoManager
from core.database import DatabaseManager

class AuthManager:
    """Handles authentication and session management using Wrapped Key architecture."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.master_key = None  # This is actually the DEK when unlocked
        self.temp_recovery_phrase = None # Stored only during setup to show user

    def is_setup_required(self) -> bool:
        """Checks if the user needs to create a master password."""
        return not self.db.is_setup()

    def needs_migration(self) -> bool:
        """Checks if the vault is an old version (v1.1.0) and needs wrapping."""
        meta = self.db.get_meta()
        if meta and meta[2] is None: # password_wrapped_key is NULL
            return True
        return False

    def setup_vault(self, master_password: str) -> bool:
        """
        Initial vault setup: 
        1. Generates a random DEK and Recovery Phrase.
        2. Wraps DEK with both Password-KEK and Recovery-KEK.
        3. Saves everything to DB.
        """
        if len(master_password) < 12:
            return False
            
        # 1. Generate core keys
        dek = CryptoManager.generate_dek()
        phrase, phrase_entropy = CryptoManager.generate_recovery_phrase()
        self.temp_recovery_phrase = phrase
        
        # 2. Derive Password KEK and wrap DEK
        p_hash, p_salt = CryptoManager.hash_password(master_password)
        p_kek = CryptoManager.derive_key(master_password, p_salt)
        p_wrapped = CryptoManager.encrypt(dek.hex(), p_kek) # Store DEK as hex string in cipher
        
        # 3. Derive Recovery KEK and wrap DEK
        r_salt = os.urandom(16)
        r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)
        r_wrapped = CryptoManager.encrypt(dek.hex(), r_kek)
        
        # 4. Save to DB
        self.db.save_setup(p_hash, p_salt, p_wrapped, r_wrapped, r_salt)
        self.master_key = dek
        return True

    def migrate_to_wrapped_keys(self, master_password: str) -> str:
        """
        Migrates a v1.1.0 vault to v1.2.0 (Wrapped Keys).
        Returns the generated recovery phrase.
        """
        meta = self.db.get_meta()
        p_hash, p_salt = meta[0], meta[1]
        
        if not CryptoManager.verify_password(p_hash, master_password):
            raise ValueError("Invalid password for migration")

        # 1. Old model used password-derived key directly for all data.
        # We'll treat the CURRENT key as the new DEK to avoid re-encrypting everything.
        old_key = CryptoManager.derive_key(master_password, p_salt)
        dek = old_key 
        
        # 2. Generate Recovery Phrase
        phrase, _ = CryptoManager.generate_recovery_phrase()
        
        # 3. Wrap DEK with Password
        p_kek = CryptoManager.derive_key(master_password, p_salt)
        p_wrapped = CryptoManager.encrypt(dek.hex(), p_kek)
        
        # 4. Wrap DEK with Recovery Phrase
        r_salt = os.urandom(16)
        r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)
        r_wrapped = CryptoManager.encrypt(dek.hex(), r_kek)
        
        # 5. Update DB
        self.db.update_vault_keys(p_wrapped, r_wrapped, r_salt)
        self.master_key = dek
        return phrase

    def unlock_vault(self, master_password: str) -> bool:
        """Unlocks the vault by unwrapping the DEK using the password."""
        meta = self.db.get_meta()
        if not meta: return False
            
        p_hash, p_salt, p_wrapped = meta[0], meta[1], meta[2]
        
        if CryptoManager.verify_password(p_hash, master_password):
            p_kek = CryptoManager.derive_key(master_password, p_salt)
            try:
                dek_hex = CryptoManager.decrypt(p_wrapped, p_kek)
                self.master_key = bytes.fromhex(dek_hex)
                return True
            except Exception:
                return False
        return False

    def unlock_with_recovery_phrase(self, phrase: str) -> bool:
        """Unlocks the vault by unwrapping the DEK using the recovery phrase."""
        meta = self.db.get_meta()
        if not meta: return False
        
        r_wrapped, r_salt = meta[3], meta[4]
        if not r_wrapped or not r_salt: return False

        try:
            r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)
            dek_hex = CryptoManager.decrypt(r_wrapped, r_kek)
            self.master_key = bytes.fromhex(dek_hex)
            return True
        except Exception:
            return False

    def reset_password(self, new_password: str) -> bool:
        """Re-wraps the DEK with a new password. Vault must be unlocked first."""
        if not self.is_unlocked() or len(new_password) < 12:
            return False
            
        p_hash, p_salt = CryptoManager.hash_password(new_password)
        p_kek = CryptoManager.derive_key(new_password, p_salt)
        p_wrapped = CryptoManager.encrypt(self.master_key.hex(), p_kek)
        
        # Keep old recovery info
        meta = self.db.get_meta()
        r_wrapped, r_salt = meta[3], meta[4]
        
        # Use the new atomic method to avoid "database is locked" issues
        self.db.reset_vault_auth(p_hash, p_salt, p_wrapped, r_wrapped, r_salt)
        return True

    def lock_vault(self):
        self.master_key = None

    def is_unlocked(self) -> bool:
        return self.master_key is not None

    def get_key(self) -> bytes:
        if not self.master_key:
            raise PermissionError("Vault is locked.")
        return self.master_key
