import sqlite3
import os
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
                
            conn.commit()

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
            conn.commit()

    def get_meta(self):
        """Retrieves all vault metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash, salt, password_wrapped_key, recovery_wrapped_key, recovery_salt, totp_secret, totp_wrapped_key, failed_attempts FROM meta LIMIT 1")
            return cursor.fetchone()

    def get_failed_attempts(self) -> int:
        """Returns the current number of failed master password attempts."""
        meta = self.get_meta()
        return meta[7] if meta else 0

    def increment_failed_attempts(self):
        """Increments the failed attempts counter in the DB."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE meta SET failed_attempts = failed_attempts + 1 WHERE id = (SELECT id FROM meta LIMIT 1)")
            conn.commit()

    def reset_failed_attempts(self):
        """Resets the failed attempts counter to zero."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE meta SET failed_attempts = 0 WHERE id = (SELECT id FROM meta LIMIT 1)")
            conn.commit()

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
            conn.commit()
