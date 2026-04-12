import sqlite3
import os
import json
import time
import winreg
from core.crypto import CryptoManager

class DatabaseManager:
    """Handles all database interactions for VaultPy with strict machine-tethering."""

    ENCRYPTED_HEADER = b"VPYX\x00"  # Magic header for encrypted-at-rest DB files

    @staticmethod
    def resolve_default_path():
        """Resolves the default database file path."""
        app_data = os.getenv('APPDATA')
        if app_data:
            return os.path.join(app_data, "VaultPy", "vault.db")
        return os.path.join(os.path.expanduser("~"), ".vaultpy", "vault.db")

    @staticmethod
    def encrypt_file(db_path):
        """Encrypts the database file with DPAPI for at-rest protection."""
        if not db_path or db_path == ":memory:" or not os.path.exists(db_path):
            return
        try:
            with open(db_path, 'rb') as f:
                header = f.read(5)
            if header == DatabaseManager.ENCRYPTED_HEADER:
                return  # Already encrypted
            with open(db_path, 'rb') as f:
                data = f.read()
            if not data:
                return
            entropy = CryptoManager.get_hardware_id().encode()
            encrypted = CryptoManager.encrypt_dpapi(data, entropy=entropy)
            if encrypted:
                with open(db_path, 'wb') as f:
                    f.write(DatabaseManager.ENCRYPTED_HEADER + encrypted)
                print("[SECURITY] Database encrypted at rest.")
        except Exception as e:
            print(f"[WARNING] Failed to encrypt database at rest: {e}")

    @staticmethod
    def decrypt_file_if_needed(db_path):
        """Decrypts the database file if it's DPAPI-encrypted."""
        if not db_path or db_path == ":memory:" or not os.path.exists(db_path):
            return
        try:
            with open(db_path, 'rb') as f:
                header = f.read(5)
            if header != DatabaseManager.ENCRYPTED_HEADER:
                return  # Not encrypted, nothing to do
            with open(db_path, 'rb') as f:
                f.seek(5)  # Skip header
                encrypted = f.read()
            entropy = CryptoManager.get_hardware_id().encode()
            decrypted = CryptoManager.decrypt_dpapi(encrypted, entropy=entropy)
            if decrypted:
                with open(db_path, 'wb') as f:
                    f.write(decrypted)
                print("[SECURITY] Database decrypted for session.")
            else:
                raise PermissionError("Failed to decrypt database. DPAPI key may have changed.")
        except PermissionError:
            raise
        except Exception as e:
            print(f"[WARNING] Database decryption check failed: {e}")

    def __init__(self, db_path=None):
        if db_path is None:
            # Default to User AppData for persistence across updates
            app_data = os.getenv('APPDATA')
            if app_data:
                db_path = os.path.join(app_data, "VaultPy", "vault.db")
            else:
                db_path = os.path.join(os.path.expanduser("~"), ".vaultpy", "vault.db")

        # Ensure data directory exists
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
        self.db_path = db_path
        self._file_existed_at_start = os.path.exists(db_path) and os.path.getsize(db_path) > 0 if db_path != ":memory:" else False
        
        # --- TETHERING VERIFICATION (Registry & Hardware Sync) ---
        if db_path != ":memory:" and self._file_existed_at_start:
            # Database file exists. We MUST have a valid Registry Anchor.
            try:
                self._verify_machine_tether_at_boot()
            except (PermissionError, FileNotFoundError, OSError):
                # If Registry is missing or AnchorUUID is gone -> LOG SECURITY EVENT
                raise PermissionError("CRITICAL: Vault Identity Missing or Tampered (Registry Mismatch). Access Denied.")
        
        self._initialize_db()

    def _verify_machine_tether_at_boot(self):
        """Strictly verifies that this DB belongs to this machine's Registry."""
        key_path = r"Software\VaultPy\SecurityState"
        
        # Check if DB has an anchor first
        db_anchor = None
        try:
            with sqlite3.connect(self.db_path) as temp_conn:
                cursor = temp_conn.cursor()
                cursor.execute("SELECT registry_uid FROM meta LIMIT 1")
                row = cursor.fetchone()
                db_anchor = row[0] if row else None
        except sqlite3.OperationalError:
            # Table or column doesn't exist -> Migration case, allow.
            return

        if not db_anchor:
            # DB has never been tethered (Old version or fresh file) -> Allow to initialize.
            return

        # DB has an anchor! We MUST match it with the Registry.
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            reg_uid_enc, _ = winreg.QueryValueEx(key, "AnchorUUID")
            winreg.CloseKey(key)
            
            entropy = CryptoManager.get_hardware_id().encode()
            reg_uid = CryptoManager.decrypt_dpapi(reg_uid_enc, entropy=entropy).decode()
            
            if db_anchor != reg_uid:
                raise PermissionError("Identity Mismatch")
        except (FileNotFoundError, OSError, sqlite3.Error):
            # DB expects an anchor, but Registry is empty/missing -> TAMPER DETECTED!
            raise PermissionError("Identity Missing")

    def close(self):
        """No-op. Connections are managed per-call via _get_connection()."""
        pass

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _initialize_db(self):
        """Creates the necessary tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Metadata table for security state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    password_hash TEXT NOT NULL,
                    salt BLOB NOT NULL,
                    password_wrapped_key BLOB,
                    recovery_wrapped_key BLOB,
                    recovery_salt BLOB,
                    totp_secret TEXT,
                    totp_wrapped_key BLOB,
                    failed_attempts INTEGER DEFAULT 0,
                    registry_uid TEXT,
                    integrity_signature BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_encrypted BLOB NOT NULL,
                    totp_secret_encrypted BLOB,
                    notes_encrypted BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migration check
            cursor.execute("PRAGMA table_info(meta)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'registry_uid' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN registry_uid TEXT")
            if 'failed_attempts' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN failed_attempts INTEGER DEFAULT 0")
            if 'integrity_signature' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN integrity_signature BLOB")
                
            self._ensure_integrity(cursor)
            conn.commit()

    def _get_integrity_data(self, cursor):
        """Collects critical metadata for integrity hashing."""
        try:
            cursor.execute("SELECT id, password_hash, failed_attempts FROM meta LIMIT 1")
            row = cursor.fetchone()
            if not row: return None
            return f"{row[0]}|{row[1]}|{row[2]}"
        except Exception as e:
            print(f"[SECURITY] Integrity data read error: {type(e).__name__}")
            return None

    def _ensure_integrity(self, cursor):
        self._update_integrity_signature(cursor)

    def _get_system_integrity_key(self, cursor=None) -> str:
        """Retrieves or generates the HMAC key. No logic branches here, just IO."""
        from core.crypto import CryptoManager
        key_path = r"Software\VaultPy\SecurityState"
        seal_name = "SystemSeal"
        entropy = CryptoManager.get_hardware_id().encode()
        
        try:
            # Read Existing
            key_reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            encrypted_key, _ = winreg.QueryValueEx(key_reg, seal_name)
            
            # Also ensure registry_uid is populated in DB (prevents integrity bypass)
            if cursor:
                cursor.execute("SELECT registry_uid FROM meta LIMIT 1")
                uid_row = cursor.fetchone()
                if uid_row and not uid_row[0]:
                    try:
                        enc_uid, _ = winreg.QueryValueEx(key_reg, "AnchorUUID")
                        uid = CryptoManager.decrypt_dpapi(enc_uid, entropy=entropy).decode()
                        cursor.execute("UPDATE meta SET registry_uid = ? WHERE id = (SELECT id FROM meta LIMIT 1)", (uid,))
                    except (FileNotFoundError, OSError):
                        pass
            
            winreg.CloseKey(key_reg)
            return CryptoManager.decrypt_dpapi(encrypted_key, entropy=entropy).decode()
        except (FileNotFoundError, OSError):
            # Generate New
            new_key = os.urandom(32).hex()
            new_uid = os.urandom(16).hex()
            
            enc_key = CryptoManager.encrypt_dpapi(new_key.encode(), entropy=entropy)
            enc_uid = CryptoManager.encrypt_dpapi(new_uid.encode(), entropy=entropy)
            
            reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(reg_key, seal_name, 0, winreg.REG_BINARY, enc_key)
            winreg.SetValueEx(reg_key, "AnchorUUID", 0, winreg.REG_BINARY, enc_uid)
            winreg.CloseKey(reg_key)
            
            # Push UID to DB
            if cursor:
                cursor.execute("UPDATE meta SET registry_uid = ? WHERE id = (SELECT id FROM meta LIMIT 1)", (new_uid,))
            return new_key

    def _update_integrity_signature(self, cursor):
        from core.crypto import CryptoManager
        data = self._get_integrity_data(cursor)
        if not data: return
        
        dynamic_key = self._get_system_integrity_key(cursor)
        hmac_key = CryptoManager.get_hardware_id() + dynamic_key
        signature = CryptoManager.get_hmac_signature(data, hmac_key)
        cursor.execute("UPDATE meta SET integrity_signature = ? WHERE id = (SELECT id FROM meta LIMIT 1)", (signature,))

    def verify_integrity(self) -> bool:
        from core.crypto import CryptoManager
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Check if DB has an anchor yet
            cursor.execute("SELECT registry_uid, integrity_signature FROM meta LIMIT 1")
            row = cursor.fetchone()
            if not row or not row[0]: 
                # UNTETHERED: Allow access for migration/setup
                return True
                
            data = self._get_integrity_data(cursor)
            if not data or not row[1]: 
                # No data to check or signature missing but anchor exists? Suspect.
                return False
            
            dynamic_key = self._get_system_integrity_key(cursor)
            hmac_key = CryptoManager.get_hardware_id() + dynamic_key
            return CryptoManager.verify_hmac_signature(data, row[1], hmac_key)

    def is_setup(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM meta")
            return cursor.fetchone()[0] > 0

    def save_setup(self, password_hash, salt, p_wrapped=None, r_wrapped=None, r_salt=None, t_secret=None, t_wrapped=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO meta (password_hash, salt, password_wrapped_key, recovery_wrapped_key, recovery_salt, totp_secret, totp_wrapped_key) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (password_hash, salt, p_wrapped, r_wrapped, r_salt, t_secret, t_wrapped)
            )
            self._update_integrity_signature(cursor)
            conn.commit()

    def get_meta(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash, salt, password_wrapped_key, recovery_wrapped_key, recovery_salt, totp_secret, totp_wrapped_key, failed_attempts FROM meta LIMIT 1")
            return cursor.fetchone()

    def get_failed_attempts(self) -> int:
        if not self.verify_integrity(): return 999
        meta = self.get_meta()
        return meta[7] if meta else 0

    def increment_failed_attempts(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE meta SET failed_attempts = failed_attempts + 1 WHERE id = (SELECT id FROM meta LIMIT 1)")
            self._update_integrity_signature(cursor)
            conn.commit()
            
            cursor.execute("SELECT failed_attempts FROM meta LIMIT 1")
            row = cursor.fetchone()
            if row: self._sync_to_registry(row[0])

    def reset_failed_attempts(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE meta SET failed_attempts = 0 WHERE id = (SELECT id FROM meta LIMIT 1)")
            self._update_integrity_signature(cursor)
            conn.commit()
            self._sync_to_registry(0)

    def _sync_to_registry(self, count):
        key_path = r"Software\VaultPy\SecurityState"
        try:
            data = json.dumps({"AuditCount": count, "LastMTime": time.time()}).encode()
            entropy = CryptoManager.get_hardware_id().encode()
            encrypted_data = CryptoManager.encrypt_dpapi(data, entropy=entropy)
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "StateSeal", 0, winreg.REG_BINARY, encrypted_data)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[SECURITY] Registry sync failed: {type(e).__name__}: {e}")

    def get_registry_state(self) -> dict:
        key_path = r"Software\VaultPy\SecurityState"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            encrypted_data, _ = winreg.QueryValueEx(key, "StateSeal")
            winreg.CloseKey(key)
        except (FileNotFoundError, OSError):
            # Registry key doesn't exist yet (first run) — safe default
            return {"AuditCount": 0, "LastMTime": 0.0}
        
        try:
            entropy = CryptoManager.get_hardware_id().encode()
            decrypted_data = CryptoManager.decrypt_dpapi(encrypted_data, entropy=entropy)
            if not decrypted_data:
                print("[SECURITY] Registry state DPAPI decryption failed — treating as tampered")
                return {"AuditCount": 999, "LastMTime": 0.0}
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"[SECURITY] Registry state corrupted or tampered: {type(e).__name__}")
            return {"AuditCount": 999, "LastMTime": 0.0}

    def add_account(self, service, username, password_enc, totp_enc=None, notes_enc=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO accounts (service, username, password_encrypted, totp_secret_encrypted, notes_encrypted) VALUES (?, ?, ?, ?, ?)",
                (service, username, password_enc, totp_enc, notes_enc)
            )
            conn.commit()

    def get_accounts(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, service, username, password_encrypted, totp_secret_encrypted, notes_encrypted FROM accounts")
            return cursor.fetchall()

    def delete_account(self, account_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            conn.commit()

    def reset_vault_auth(self, p_hash, p_salt, p_wrapped, r_wrapped, r_salt, t_secret, t_wrapped):
        """Atomically resets all authentication data in the meta table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE meta SET password_hash = ?, salt = ?, password_wrapped_key = ?,
                   recovery_wrapped_key = ?, recovery_salt = ?, totp_secret = ?, totp_wrapped_key = ?,
                   failed_attempts = 0
                   WHERE id = (SELECT id FROM meta LIMIT 1)""",
                (p_hash, p_salt, p_wrapped, r_wrapped, r_salt, t_secret, t_wrapped)
            )
            self._update_integrity_signature(cursor)
            conn.commit()

    def get_all_accounts(self):
        """Returns all accounts as Account objects."""
        from models.account import Account
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, service, username, password_encrypted, totp_secret_encrypted, notes_encrypted, created_at FROM accounts")
            return [Account(*row) for row in cursor.fetchall()]

    def search_accounts(self, query):
        """Searches accounts by service or username (case-insensitive)."""
        from models.account import Account
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, service, username, password_encrypted, totp_secret_encrypted, notes_encrypted, created_at FROM accounts WHERE service LIKE ? OR username LIKE ?",
                (f"%{query}%", f"%{query}%")
            )
            return [Account(*row) for row in cursor.fetchall()]

    def update_account(self, account_id, service, username, password_enc, totp_enc=None, notes_enc=None):
        """Updates an existing account entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET service = ?, username = ?, password_encrypted = ?, totp_secret_encrypted = ?, notes_encrypted = ? WHERE id = ?",
                (service, username, password_enc, totp_enc, notes_enc, account_id)
            )
            conn.commit()

    def factory_reset(self):
        """Permanently wipes all vault data and resets security state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounts")
            cursor.execute("DELETE FROM meta")
            conn.commit()
        # Clean up Windows Registry security state
        key_path = r"Software\VaultPy\SecurityState"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            for name in ["StateSeal", "SystemSeal", "AnchorUUID"]:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass
