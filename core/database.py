import sqlite3
import os
import winreg
import json
from datetime import datetime

class DatabaseManager:
    """Handles all database interactions for VaultPy."""

    def __init__(self, db_path=None):
        if db_path is None:
            # Default to User AppData for persistence across updates
            app_data = os.getenv('APPDATA')
            if app_data:
                db_path = os.path.join(app_data, "VaultPy", "vault.db")
            else:
                # Fallback for non-Windows or if APPDATA is missing
                db_path = os.path.join(os.path.expanduser("~"), ".vaultpy", "vault.db")

        # Ensure data directory exists (unless using in-memory DB for tests)
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._initialize_db()

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
                    integrity_signature BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Accounts table for stored secrets
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
            
            # Migration: Add columns if they don't exist (for existing v1.1.0 databases)
            cursor.execute("PRAGMA table_info(meta)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'password_wrapped_key' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN password_wrapped_key BLOB")
            if 'recovery_wrapped_key' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN recovery_wrapped_key BLOB")
            if 'recovery_salt' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN recovery_salt BLOB")
            if 'totp_secret' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN totp_secret TEXT")
            if 'totp_wrapped_key' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN totp_wrapped_key BLOB")
            if 'failed_attempts' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN failed_attempts INTEGER DEFAULT 0")
            if 'integrity_signature' not in columns:
                cursor.execute("ALTER TABLE meta ADD COLUMN integrity_signature BLOB")
                
            # Auto-sign if migration occurred or if signature is missing
            self._ensure_integrity(cursor)
                
            conn.commit()

    def _get_integrity_data(self, cursor):
        """Collects critical metadata for integrity hashing."""
        cursor.execute("SELECT id, password_hash, failed_attempts FROM meta LIMIT 1")
        row = cursor.fetchone()
        if not row: return None
        return f"{row[0]}|{row[1]}|{row[2]}"

    def _ensure_integrity(self, cursor):
        """Verifies or initializes the integrity signature."""
        cursor.execute("SELECT integrity_signature FROM meta LIMIT 1")
        sig = cursor.fetchone()
        if sig and sig[0]:
            return # Already has a signature
            
        # Initialize signature for existing data
        self._update_integrity_signature(cursor)

    def _get_system_integrity_key(self) -> str:
        """Retrieves or generates a unique, machine-bound HMAC key for database integrity."""
        from core.crypto import CryptoManager
        key_path = r"Software\VaultPy\SecurityState"
        seal_name = "SystemSeal"
        
        try:
            # 1. Try to fetch existing sealed key
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            encrypted_key, _ = winreg.QueryValueEx(key, seal_name)
            winreg.CloseKey(key)
            
            # Use HWID as secondary entropy
            entropy = CryptoManager.get_hardware_id().encode()
            decrypted_key = CryptoManager.decrypt_dpapi(encrypted_key, entropy=entropy)
            if not decrypted_key:
                raise ValueError("DPAPI Decryption Failed")
            return decrypted_key.decode()
            
        except (FileNotFoundError, OSError, ValueError):
            # 2. Key doesn't exist or is corrupted - generate new one
            new_key = os.urandom(32).hex()
            entropy = CryptoManager.get_hardware_id().encode()
            encrypted_new_key = CryptoManager.encrypt_dpapi(new_key.encode(), entropy=entropy)
            
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, seal_name, 0, winreg.REG_BINARY, encrypted_new_key)
            winreg.CloseKey(key)
            return new_key

    def _update_integrity_signature(self, cursor):
        """Calculates and saves HMAC of current metadata using a dynamic System Key."""
        from core.crypto import CryptoManager
        data = self._get_integrity_data(cursor)
        if not data: return
        
        # Key = HardwareID + Registry-Sealed System Key (Non-static)
        dynamic_key = self._get_system_integrity_key()
        hmac_key = CryptoManager.get_hardware_id() + dynamic_key
        signature = CryptoManager.get_hmac_signature(data, hmac_key)
        
        cursor.execute("UPDATE meta SET integrity_signature = ? WHERE id = (SELECT id FROM meta LIMIT 1)", (signature,))

    def verify_integrity(self) -> bool:
        """Checks if metadata has been tampered with using the Dynamic Integrity Seal."""
        from core.crypto import CryptoManager
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = self._get_integrity_data(cursor)
            cursor.execute("SELECT integrity_signature FROM meta LIMIT 1")
            row = cursor.fetchone()
            
            if not data or not row or not row[0]:
                return True # Nothing to verify yet
            
            dynamic_key = self._get_system_integrity_key()
            hmac_key = CryptoManager.get_hardware_id() + dynamic_key
            return CryptoManager.verify_hmac_signature(data, row[0], hmac_key)

    def is_setup(self):
        """Checks if a master password has already been set up."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM meta")
            return cursor.fetchone()[0] > 0

    def save_setup(self, password_hash, salt, p_wrapped=None, r_wrapped=None, r_salt=None, t_secret=None, t_wrapped=None):
        """Saves the initial setup data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO meta 
                   (password_hash, salt, password_wrapped_key, recovery_wrapped_key, recovery_salt, totp_secret, totp_wrapped_key) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (password_hash, salt, p_wrapped, r_wrapped, r_salt, t_secret, t_wrapped)
            )
            self._update_integrity_signature(cursor)
            conn.commit()

    def update_vault_keys(self, p_wrapped, r_wrapped, r_salt, t_secret=None, t_wrapped=None):
        """Updates the wrapped keys in the meta table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE meta SET 
                   password_wrapped_key = ?, 
                   recovery_wrapped_key = ?, 
                   recovery_salt = ?,
                   totp_secret = ?,
                   totp_wrapped_key = ?
                   WHERE id = (SELECT id FROM meta LIMIT 1)""",
                (p_wrapped, r_wrapped, r_salt, t_secret, t_wrapped)
            )
            self._update_integrity_signature(cursor)
            conn.commit()

    def get_meta(self):
        """Retrieves all vault metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash, salt, password_wrapped_key, recovery_wrapped_key, recovery_salt, totp_secret, totp_wrapped_key, failed_attempts FROM meta LIMIT 1")
            return cursor.fetchone()

    def get_failed_attempts(self) -> int:
        """Returns the current number of failed master password attempts with integrity check."""
        if not self.verify_integrity():
            return 999 # Emergency lockout if tampering detected
        meta = self.get_meta()
        return meta[7] if meta else 0

    def increment_failed_attempts(self):
        """Increments the failed attempts counter in DB and Registry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE meta SET failed_attempts = failed_attempts + 1 WHERE id = (SELECT id FROM meta LIMIT 1)")
            self._update_integrity_signature(cursor)
            conn.commit()
            
            # Sync to registry
            cursor.execute("SELECT failed_attempts FROM meta LIMIT 1")
            row = cursor.fetchone()
            if row:
                self._sync_to_registry(row[0])

    def reset_failed_attempts(self):
        """Resets the failed attempts counter to zero in DB and Registry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE meta SET failed_attempts = 0 WHERE id = (SELECT id FROM meta LIMIT 1)")
            self._update_integrity_signature(cursor)
            conn.commit()
            self._sync_to_registry(0)

    def _sync_to_registry(self, count):
        """Hidden synchronization of failed attempts and mtime to Windows Registry (DPAPI Encrypted)."""
        from core.crypto import CryptoManager
        try:
            mtime = os.path.getmtime(self.db_path)
            state = {
                "AuditCount": count,
                "LastMTime": mtime
            }
            raw_data = json.dumps(state).encode()
            
            # Use HWID as secondary entropy
            entropy = CryptoManager.get_hardware_id().encode()
            encrypted_data = CryptoManager.encrypt_dpapi(raw_data, entropy=entropy)
            
            key_path = r"Software\VaultPy\SecurityState"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "StateSeal", 0, winreg.REG_BINARY, encrypted_data)
            winreg.CloseKey(key)
        except Exception:
            pass

    def get_registry_state(self) -> dict:
        """Retrieves the sealed security state (count, mtime) from the Registry."""
        from core.crypto import CryptoManager
        try:
            key_path = r"Software\VaultPy\SecurityState"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            encrypted_data, _ = winreg.QueryValueEx(key, "StateSeal")
            winreg.CloseKey(key)
            
            # Use HWID as secondary entropy
            entropy = CryptoManager.get_hardware_id().encode()
            decrypted_data = CryptoManager.decrypt_dpapi(encrypted_data, entropy=entropy)
            return json.loads(decrypted_data.decode())
        except Exception:
            return {"AuditCount": 0, "LastMTime": 0.0}

    def add_account(self, service, username, password_enc, totp_enc=None, notes_enc=None):
        """Adds a new account entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO accounts 
                   (service, username, password_encrypted, totp_secret_encrypted, notes_encrypted) 
                   VALUES (?, ?, ?, ?, ?)""",
                (service, username, password_enc, totp_enc, notes_enc)
            )
            conn.commit()

    def update_account(self, account_id, service, username, password_enc, totp_enc=None, notes_enc=None):
        """Updates an existing account entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE accounts 
                   SET service = ?, username = ?, password_encrypted = ?, 
                       totp_secret_encrypted = ?, notes_encrypted = ?
                   WHERE id = ?""",
                (service, username, password_enc, totp_enc, notes_enc, account_id)
            )
            conn.commit()

    def delete_account(self, account_id):
        """Deletes an account entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            conn.commit()

    def get_all_accounts(self):
        """Retrieves all account entries as Account objects."""
        from models.account import Account
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY service ASC")
            rows = cursor.fetchall()
            return [Account(*row) for row in rows]

    def search_accounts(self, query):
        """Searches accounts by service or username, returns Account objects."""
        from models.account import Account
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM accounts WHERE service LIKE ? OR username LIKE ? ORDER BY service ASC",
                (f"%{query}%", f"%{query}%")
            )
            rows = cursor.fetchall()
            return [Account(*row) for row in rows]

    def factory_reset(self):
        """Wipes the entire database to allow a fresh start."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS accounts")
            cursor.execute("DROP TABLE IF EXISTS meta")
            conn.commit()
        # Re-initialize the tables
        self._initialize_db()

    def reset_vault_auth(self, password_hash, salt, p_wrapped, r_wrapped, r_salt, t_secret=None, t_wrapped=None):
        """Atomically wipes and re-initializes vault authentication metadata. Fixes locking issues."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM meta")
            cursor.execute(
                """INSERT INTO meta 
                   (password_hash, salt, password_wrapped_key, recovery_wrapped_key, recovery_salt, totp_secret, totp_wrapped_key) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (password_hash, salt, p_wrapped, r_wrapped, r_salt, t_secret, t_wrapped)
            )
            self._update_integrity_signature(cursor)
            conn.commit()
