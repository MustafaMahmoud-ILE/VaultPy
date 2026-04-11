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

        # Ensure data directory exists
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
            conn.commit()

    def is_setup(self):
        """Checks if a master password has already been set up."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM meta")
            return cursor.fetchone()[0] > 0

    def save_setup(self, password_hash, salt):
        """Saves the initial master password hash and salt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO meta (password_hash, salt) VALUES (?, ?)",
                (password_hash, salt)
            )
            conn.commit()

    def get_meta(self):
        """Retrieves the password hash and salt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash, salt FROM meta LIMIT 1")
            return cursor.fetchone()

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
