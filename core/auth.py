import os
import pyotp
from contextlib import contextmanager
from core.crypto import CryptoManager
from core.database import DatabaseManager

class AuthManager:
    """Handles authentication and session management using Wrapped Key architecture."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._protected_dek = None # Encrypted/Cloaked container for DEK in RAM
        self._session_key = None # Transient key for RAM cloaking
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
        
        # Guard: In-memory databases have no filesystem metadata
        if self.db.db_path == ":memory:":
            return max(db_count, reg_count) >= 5
        
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

    def setup_vault(self, master_password: str):
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
        
        # Cloak DEK in RAM using DPAPI (hardware-bound encryption)
        self._session_key = os.urandom(32)
        protected = CryptoManager.encrypt_dpapi(dek, entropy=self._session_key)
        if not protected:
            raise RuntimeError("DPAPI encryption failed — cannot protect DEK in RAM")
        self._protected_dek = protected
        
        return phrase, self.get_totp_uri(), totp_secret

    def _obfuscate_secret(self, secret: str) -> str:
        """DPAPI-based encryption bound to this machine's user session."""
        entropy = CryptoManager.get_hardware_id().encode()
        encrypted = CryptoManager.encrypt_dpapi(secret.encode(), entropy=entropy)
        if encrypted:
            return "DPAPI:" + encrypted.hex()
        # Fallback to legacy XOR if DPAPI fails (should not happen)
        key = CryptoManager.get_hardware_id() + "_VaultPy_Security_v1.2.4"
        return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(secret))

    def _deobfuscate_secret(self, obf: str) -> str:
        """Decrypts TOTP secret, supporting both DPAPI and legacy XOR formats."""
        if isinstance(obf, str) and obf.startswith("DPAPI:"):
            encrypted = bytes.fromhex(obf[6:])
            entropy = CryptoManager.get_hardware_id().encode()
            result = CryptoManager.decrypt_dpapi(encrypted, entropy=entropy)
            if not result:
                raise ValueError("DPAPI decryption of TOTP secret failed — possible profile corruption")
            return result.decode()
        # Legacy XOR fallback for pre-upgrade vaults
        key = CryptoManager.get_hardware_id() + "_VaultPy_Security_v1.2.4"
        return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(obf))

    def _migrate_totp_secret_if_needed(self):
        """Auto-migrates TOTP secret from legacy XOR to DPAPI encryption."""
        meta = self.db.get_meta()
        if not meta or not meta[5]:
            return
        t_secret_obf = meta[5]
        if isinstance(t_secret_obf, str) and t_secret_obf.startswith("DPAPI:"):
            return  # Already using DPAPI
        try:
            # Decode with legacy XOR
            old_key = CryptoManager.get_hardware_id() + "_VaultPy_Security_v1.2.4"
            totp_secret = "".join(chr(ord(c) ^ ord(old_key[i % len(old_key)])) for i, c in enumerate(t_secret_obf))
            # Validate it looks like Base32
            if not all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in totp_secret.upper()):
                return  # Not a valid secret, skip migration
            # Re-encrypt with DPAPI
            new_obf = self._obfuscate_secret(totp_secret)
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE meta SET totp_secret = ? WHERE id = (SELECT id FROM meta LIMIT 1)", (new_obf,))
                self.db._update_integrity_signature(cursor)
                conn.commit()
            print("[SECURITY] TOTP secret migrated from XOR to DPAPI encryption.")
        except Exception as e:
            print(f"[SECURITY] TOTP migration skipped: {type(e).__name__}")

    def migrate_to_wrapped_keys(self, master_password: str) -> tuple[str, str, str]:
        """
        Migrates a vault to v1.2.1 (Triple-Wrapped Keys).
        Vault must already be unlocked via unlock_vault().
        Returns (recovery_phrase, totp_uri, totp_secret).
        """
        meta = self.db.get_meta()
        if not meta: raise ValueError("No vault data found")
        
        p_hash, p_salt = meta[0], meta[1]
        
        # Use the already-unlocked DEK if available (avoids redundant Argon2 derivation)
        with self._get_plaintext_dek() as dek_raw:
            if dek_raw:
                dek = bytes(dek_raw)
            else:
                # v1.1.0 fallback: vault has no wrapped key, DEK = KEK (direct derivation)
                if not CryptoManager.verify_password(p_hash, master_password):
                    raise ValueError("Invalid password for migration")
                try:
                    dek = CryptoManager.derive_key(master_password, p_salt)
                except Exception:
                    dek = CryptoManager.derive_key_compat(master_password, p_salt, p_hash)
                
                # Cloak DEK in RAM for v1.1.0 migration
                self._session_key = os.urandom(32)
                protected = CryptoManager.encrypt_dpapi(dek, entropy=self._session_key)
                if not protected:
                    raise RuntimeError("DPAPI encryption failed — cannot protect DEK in RAM during migration")
                self._protected_dek = protected
        
        # Derive p_kek for wrapping (single derivation, skips redundant verify_password)
        try:
            p_kek = CryptoManager.derive_key(master_password, p_salt)
        except Exception:
            p_kek = CryptoManager.derive_key_compat(master_password, p_salt, p_hash)
        
        # Generate Recovery Phrase and TOTP
        phrase, _ = CryptoManager.generate_recovery_phrase()
        totp_secret = pyotp.random_base32()
        self.temp_recovery_phrase = phrase
        self.temp_totp_secret = totp_secret
        
        # New Wraps
        p_wrapped = CryptoManager.encrypt(dek.hex(), p_kek)
        
        r_salt = os.urandom(16)
        r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)
        r_wrapped = CryptoManager.encrypt(dek.hex(), r_kek)
        
        t_kek = CryptoManager.derive_key(totp_secret, p_salt)
        t_wrapped = CryptoManager.encrypt(dek.hex(), t_kek)
        
        # Update DB
        t_secret_obf = self._obfuscate_secret(totp_secret)
        self.db.reset_vault_auth(p_hash, p_salt, p_wrapped, r_wrapped, r_salt, t_secret_obf, t_wrapped)
        
        # DEK is already protected in _protected_dek from the unlock call
        return phrase, self.get_totp_uri(), totp_secret

    def unlock_vault(self, master_password: str) -> bool:
        """Unlocks the vault by unwrapping the DEK using the password."""
        # 1. Immediate Lockout Check
        if self.is_locked_out():
            print("[!] Security Lockout Active: Access Denied.")
            return False
            
        # 2. PRE-VERIFICATION AUDIT: Increment before verifying
        # This prevents bypassing the counter by killing the app during Argon2 window.
        self.db.increment_failed_attempts()
            
        meta = self.db.get_meta()
        if not meta: return False
            
        p_hash, p_salt, p_wrapped = meta[0], meta[1], meta[2]
        
        # 3. Verify Password (Argon2 with high cost and mandatory delay)
        if CryptoManager.verify_password(p_hash, master_password):
            # Try current constants first, fallback to compat for old vaults
            dek_raw = None
            try:
                p_kek = CryptoManager.derive_key(master_password, p_salt)
                dek_hex = CryptoManager.decrypt(p_wrapped, p_kek)
                dek_raw = bytes.fromhex(dek_hex)
            except Exception:
                try:
                    p_kek = CryptoManager.derive_key_compat(master_password, p_salt, p_hash)
                    dek_hex = CryptoManager.decrypt(p_wrapped, p_kek)
                    dek_raw = bytes.fromhex(dek_hex)
                except Exception:
                    return False
            
            # Cloak DEK in RAM using DPAPI
            self._session_key = os.urandom(32)
            protected = CryptoManager.encrypt_dpapi(dek_raw, entropy=self._session_key)
            if not protected:
                raise RuntimeError("DPAPI encryption failed — cannot protect DEK in RAM")
            self._protected_dek = protected
            
            # 4. RESET on success
            self.db.reset_failed_attempts()
            self._migrate_totp_secret_if_needed()
            return True
        
        return False

    def unlock_with_recovery_phrase(self, phrase: str) -> bool:
        """Unlocks the vault by unwrapping the DEK using the recovery phrase."""
        if self.is_locked_out():
            print("[!] Security Lockout Active: Access Denied.")
            return False
            
        # PRE-VERIFICATION AUDIT
        self.db.increment_failed_attempts()
        
        meta = self.db.get_meta()
        if not meta: return False
        
        r_wrapped, r_salt = meta[3], meta[4]
        if not r_wrapped or not r_salt: return False

        try:
            # Try current derive_key_from_phrase first (ITERATIONS * 2)
            r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)
            dek_hex = CryptoManager.decrypt(r_wrapped, r_kek)
            dek_raw = bytes.fromhex(dek_hex)
        except Exception:
            try:
                # Fallback: v1.2.4 used ITERATIONS directly (no doubling)
                r_kek = CryptoManager.derive_key_from_phrase_compat(phrase, r_salt, meta[0])
                dek_hex = CryptoManager.decrypt(r_wrapped, r_kek)
                dek_raw = bytes.fromhex(dek_hex)
            except Exception:
                return False
        
        try:
            # Cloak DEK in RAM using DPAPI
            self._session_key = os.urandom(32)
            protected = CryptoManager.encrypt_dpapi(dek_raw, entropy=self._session_key)
            if not protected:
                raise RuntimeError("DPAPI encryption failed — cannot protect DEK in RAM")
            self._protected_dek = protected
            self.db.reset_failed_attempts()
            self._migrate_totp_secret_if_needed()
            return True
        except Exception:
            return False

    def unlock_with_totp(self, otp_code: str) -> bool:
        """Unlocks the vault using a TOTP code and the stored secret."""
        if self.is_locked_out():
            print("[!] Security Lockout Active: Access Denied.")
            return False
            
        # PRE-VERIFICATION AUDIT
        self.db.increment_failed_attempts()
        
        meta = self.db.get_meta()
        if not meta or not meta[5] or not meta[6]: 
            return False
        
        p_salt, t_secret_obf, t_wrapped = meta[1], meta[5], meta[6]
        
        import time
        try:
            totp_secret = self._deobfuscate_secret(t_secret_obf)
            
            # 1. Verify OTP first
            if not pyotp.TOTP(totp_secret).verify(otp_code):
                time.sleep(0.5) # Mandatory Brute-Force Penalty
                return False
                
            # 2. Derive KEK and unwrap — try current constants, fallback to compat
            dek_raw = None
            try:
                t_kek = CryptoManager.derive_key(totp_secret, p_salt)
                dek_hex = CryptoManager.decrypt(t_wrapped, t_kek)
                dek_raw = bytes.fromhex(dek_hex)
            except Exception:
                t_kek = CryptoManager.derive_key_compat(totp_secret, p_salt, meta[0])
                dek_hex = CryptoManager.decrypt(t_wrapped, t_kek)
                dek_raw = bytes.fromhex(dek_hex)
            
            # Cloak DEK in RAM using DPAPI
            self._session_key = os.urandom(32)
            protected = CryptoManager.encrypt_dpapi(dek_raw, entropy=self._session_key)
            if not protected:
                raise RuntimeError("DPAPI encryption failed — cannot protect DEK in RAM")
            self._protected_dek = protected
            
            self.db.reset_failed_attempts()
            self._migrate_totp_secret_if_needed()
            return True
        except Exception:
            time.sleep(0.5)
            return False

    @contextmanager
    def _get_plaintext_dek(self):
        """Just-In-Time (JIT) materialization of the Master Key via DPAPI decryption."""
        if not self._protected_dek or not self._session_key:
            yield None
            return

        try:
            dek = CryptoManager.decrypt_dpapi(self._protected_dek, entropy=self._session_key)
            yield dek
        finally:
            pass  # dek goes out of scope; DPAPI blob remains encrypted in _protected_dek

    def decrypt_account(self, ciphertext: str) -> str:
        """Decrypts account data using the transient uncloaked Master Key."""
        with self._get_plaintext_dek() as dek:
            if not dek: return ""
            return CryptoManager.decrypt(ciphertext, bytes(dek))

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
        """Re-wraps the DEK with a new password using secure JIT uncloaking."""
        if not self._protected_dek or not self._session_key or len(new_password) < 12:
            return False

        with self._get_plaintext_dek() as dek:
            if not dek: return False
            dek_hex = bytes(dek).hex()

            # 1. New Password KEK
            p_hash, p_salt = CryptoManager.hash_password(new_password)
            p_kek = CryptoManager.derive_key(new_password, p_salt)
            p_wrapped = CryptoManager.encrypt(dek_hex, p_kek)

            # 2. Keep existing Recovery setup (has its own r_salt, unaffected)
            meta = self.db.get_meta()
            if not meta: return False

            r_wrapped, r_salt = meta[3], meta[4]
            t_secret_obf = meta[5]

            # 3. Re-wrap TOTP key with the NEW p_salt
            # (t_wrapped was keyed to the OLD p_salt — must re-derive with the new one)
            t_wrapped = meta[6]
            if t_secret_obf and t_wrapped:
                try:
                    totp_secret = self._deobfuscate_secret(t_secret_obf)
                    t_kek = CryptoManager.derive_key(totp_secret, p_salt)
                    t_wrapped = CryptoManager.encrypt(dek_hex, t_kek)
                except Exception as e:
                    print(f"[SECURITY] TOTP re-wrap failed during password reset: {type(e).__name__}")
                    return False  # Abort reset to prevent orphaning TOTP unlock path

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
        """Securely discards the DPAPI-encrypted DEK and session key from memory."""
        self._protected_dek = None
        self._session_key = None



    def is_unlocked(self) -> bool:
        return self._protected_dek is not None and self._session_key is not None

    def get_key(self) -> bytes:
        """Returns the uncloaked DEK via DPAPI decryption. Caller must not persist the reference."""
        if not self._protected_dek or not self._session_key:
            raise PermissionError("Vault is locked.")
        return CryptoManager.decrypt_dpapi(self._protected_dek, entropy=self._session_key)
