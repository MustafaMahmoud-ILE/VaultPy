import os
import pyotp
import ctypes
from core.crypto import CryptoManager
from core.database import DatabaseManager

class AuthManager:
    """Handles authentication and session management using Wrapped Key architecture."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.master_key = None  # This is actually the DEK when unlocked
        self.temp_recovery_phrase = None 
        self.temp_totp_secret = None # Stored only during setup to show user

    def is_setup_required(self) -> bool:
        """Checks if the user needs to create a master password."""
        return not self.db.is_setup()

    def needs_migration(self) -> bool:
        """Checks if the vault needs wrapping (v1.1.0) or TOTP setup (v1.2.0)."""
        meta = self.db.get_meta()
        if not meta: return False
        
        # v1.1.0 -> v1.2.0 (Wrapped Keys)
        if meta[2] is None: 
            return True
        
        # v1.2.0 -> v1.2.1 (Mandatory TOTP)
        if meta[5] is None: # totp_secret is NULL
            return True
            
        return False

    def is_locked_out(self) -> bool:
        """Checks if the account is locked after 5 failed attempts (Secure Dual-Check)."""
        db_count = self.db.get_failed_attempts()
        reg_state = self.db.get_registry_state()
        reg_count = reg_state.get("AuditCount", 0)
        reg_mtime = reg_state.get("LastMTime", 0.0)
        
        current_mtime = os.path.getmtime(self.db.db_path)
        
        # 1. Detection of 'Time Travel' (Database rollback)
        # If the file on disk is older than our last recorded modification, it was swapped.
        # We allow a small 2-second grace for precision issues.
        if reg_mtime > 0 and (current_mtime + 2.0) < reg_mtime:
             # TRIGGER PERMANENT LOCK on tampering
             return True

        # 2. Detection of Count Rollback (Registry shadow check)
        if reg_count > db_count and reg_count < 999: # 999 is local lockout signal
             # Force DB to catch up to Registry state
             with self.db._get_connection() as conn:
                 cursor = conn.cursor()
                 cursor.execute("UPDATE meta SET failed_attempts = ? WHERE id = (SELECT id FROM meta LIMIT 1)", (reg_count,))
                 self.db._update_integrity_signature(cursor)
                 conn.commit()
             db_count = reg_count

        return max(db_count, reg_count) >= 5

    def setup_vault(self, master_password: str) -> bool:
        """
        Initial vault setup: 
        1. Generates random DEK, Recovery Phrase, and TOTP Secret.
        2. Wraps DEK with Password-KEK, Recovery-KEK, and TOTP-KEK.
        3. Saves everything to DB.
        """
        if len(master_password) < 12:
            return False
            
        # 1. Generate core keys
        dek = CryptoManager.generate_dek()
        phrase, _ = CryptoManager.generate_recovery_phrase()
        self.temp_recovery_phrase = phrase
        
        # TOTP Secret (Base32)
        totp_secret = pyotp.random_base32()
        self.temp_totp_secret = totp_secret
        
        # 2. Derive Password KEK and wrap DEK
        p_hash, p_salt = CryptoManager.hash_password(master_password)
        p_kek = CryptoManager.derive_key(master_password, p_salt)
        p_wrapped = CryptoManager.encrypt(dek.hex(), p_kek)
        
        # 3. Derive Recovery KEK and wrap DEK
        r_salt = os.urandom(16)
        r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)
        r_wrapped = CryptoManager.encrypt(dek.hex(), r_kek)
        
        # 4. Derive TOTP KEK and wrap DEK
        # Note: We use the TOTP Secret itself as the entropy source for this KEK
        t_kek = CryptoManager.derive_key(totp_secret, p_salt) # Reuse p_salt for simplicity
        t_wrapped = CryptoManager.encrypt(dek.hex(), t_kek)
        
        # 5. Save to DB
        # To allow recovery WITHOUT password, we must NOT encrypt secret with p_kek.
        # We use a simple XOR obfuscation with a constant to hide it from plain-text scanners.
        t_secret_obf = self._obfuscate_secret(totp_secret)
        
        self.db.save_setup(p_hash, p_salt, p_wrapped, r_wrapped, r_salt, t_secret_obf, t_wrapped)
        self.master_key = bytearray(dek)
        return True

    def _obfuscate_secret(self, secret: str) -> str:
        """Hardware-linked XOR obfuscation to bind recovery data to this machine."""
        key = CryptoManager.get_hardware_id() + "_VaultPy_Security_v1.2.4"
        return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(secret))

    def _deobfuscate_secret(self, obf: str) -> str:
        return self._obfuscate_secret(obf) # XOR is reversible

    def migrate_to_wrapped_keys(self, master_password: str) -> tuple[str, str, str]:
        """
        Migrates a vault to v1.2.1 (Triple-Wrapped Keys).
        Returns (recovery_phrase, totp_uri, totp_secret).
        """
        meta = self.db.get_meta()
        if not meta: raise ValueError("No vault data found")
        
        p_hash, p_salt = meta[0], meta[1]
        
        if not CryptoManager.verify_password(p_hash, master_password):
            raise ValueError("Invalid password for migration")

        # 1. Un-wrap current DEK
        p_kek = CryptoManager.derive_key(master_password, p_salt)
        if meta[2]: # Already v1.2.0
            dek_hex = CryptoManager.decrypt(meta[2], p_kek)
            dek = bytes.fromhex(dek_hex)
        else: # v1.1.0
            dek = p_kek 
        
        # 2. Generate Recovery Phrase and TOTP
        phrase, _ = CryptoManager.generate_recovery_phrase()
        totp_secret = pyotp.random_base32()
        self.temp_recovery_phrase = phrase
        self.temp_totp_secret = totp_secret
        
        # 3. New Wraps
        p_wrapped = CryptoManager.encrypt(dek.hex(), p_kek)
        
        r_salt = os.urandom(16)
        r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)
        r_wrapped = CryptoManager.encrypt(dek.hex(), r_kek)
        
        t_kek = CryptoManager.derive_key(totp_secret, p_salt)
        t_wrapped = CryptoManager.encrypt(dek.hex(), t_kek)
        
        # 4. Update DB
        t_secret_obf = self._obfuscate_secret(totp_secret)
        self.db.reset_vault_auth(p_hash, p_salt, p_wrapped, r_wrapped, r_salt, t_secret_obf, t_wrapped)
        
        self.master_key = bytearray(dek)
        return phrase, self.get_totp_uri(), totp_secret

    def unlock_vault(self, master_password: str) -> bool:
        """Unlocks the vault by unwrapping the DEK using the password."""
        if self.is_locked_out():
            return False
            
        meta = self.db.get_meta()
        if not meta: return False
            
        p_hash, p_salt, p_wrapped = meta[0], meta[1], meta[2]
        
        if CryptoManager.verify_password(p_hash, master_password):
            p_kek = CryptoManager.derive_key(master_password, p_salt)
            try:
                dek_hex = CryptoManager.decrypt(p_wrapped, p_kek)
                self.master_key = bytearray(bytes.fromhex(dek_hex))
                self.db.reset_failed_attempts()
                return True
            except Exception:
                self.db.increment_failed_attempts()
                return False
        
        self.db.increment_failed_attempts()
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
            self.master_key = bytearray(bytes.fromhex(dek_hex))
            return True
        except Exception:
            return False

    def unlock_with_totp(self, otp_code: str) -> bool:
        """Unlocks the vault using a TOTP code and the stored secret."""
        meta = self.db.get_meta()
        if not meta or not meta[5] or not meta[6]: 
            return False
        
        # meta format: p_hash, p_salt, p_wrapped, r_wrapped, r_salt, t_secret_obf, t_wrapped
        p_salt, t_secret_obf, t_wrapped = meta[1], meta[5], meta[6]
        
        try:
            totp_secret = self._deobfuscate_secret(t_secret_obf)
            
            # 1. Verify OTP first
            if not pyotp.TOTP(totp_secret).verify(otp_code):
                return False
                
            # 2. Derive KEK from secret and unwrap DEK
            t_kek = CryptoManager.derive_key(totp_secret, p_salt)
            dek_hex = CryptoManager.decrypt(t_wrapped, t_kek)
            self.master_key = bytearray(bytes.fromhex(dek_hex))
            return True
        except Exception:
            return False

    def get_totp_uri(self) -> str:
        """Returns the provisioning URI for the QR code."""
        if not self.temp_totp_secret:
            return ""
        return pyotp.totp.TOTP(self.temp_totp_secret).provisioning_uri(
            name="User", 
            issuer_name="VaultPy"
        )

    def verify_otp(self, code: str, secret: str = None) -> bool:
        """Verifies a 6-digit TOTP code against a secret."""
        target_secret = secret if secret else self.temp_totp_secret
        if not target_secret:
            meta = self.db.get_meta()
            if meta and meta[5]:
                target_secret = self._deobfuscate_secret(meta[5])
            else:
                return False
        
        totp = pyotp.TOTP(target_secret)
        return totp.verify(code)

    def reset_password(self, new_password: str) -> bool:
        """Re-wraps the DEK with a new password and updates TOTP wrap too."""
        if not self.is_unlocked() or len(new_password) < 12:
            return False
            
        # 1. New Password KEK
        p_hash, p_salt = CryptoManager.hash_password(new_password)
        p_kek = CryptoManager.derive_key(new_password, p_salt)
        p_wrapped = CryptoManager.encrypt(self.master_key.hex(), p_kek)
        
        # 2. Keep existing Recovery and TOTP setups
        meta = self.db.get_meta()
        if not meta: return False
        
        r_wrapped, r_salt = meta[3], meta[4]
        t_secret_obf, t_wrapped = meta[5], meta[6]
        
        # Update DB atomically
        try:
            self.db.reset_vault_auth(
                p_hash, p_salt, p_wrapped, 
                r_wrapped, r_salt, 
                t_secret_obf, t_wrapped
            )
            self.db.reset_failed_attempts()
            return True
        except Exception:
            return False

    def lock_vault(self):
        """Securely wipes the master key from memory before locking."""
        if self.master_key:
            self._scrub_memory(self.master_key)
        self.master_key = None

    def _scrub_memory(self, buffer):
        """Hard-wipes a bytearray by filling it with zeros using C-level access."""
        try:
            # Get the pointer to the buffer and its size
            size = len(buffer)
            addr = (ctypes.c_char * size).from_buffer(buffer)
            ctypes.memset(addr, 0, size)
        except Exception:
            # Fallback for immutable-like behavior (less secure but non-crashing)
            for i in range(len(buffer)):
                buffer[i] = 0

    def is_unlocked(self) -> bool:
        return self.master_key is not None

    def get_key(self) -> bytes:
        if not self.master_key:
            raise PermissionError("Vault is locked.")
        return self.master_key
