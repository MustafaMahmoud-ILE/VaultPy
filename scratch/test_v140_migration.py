import sys
import os
import sqlite3

# Add project root to path
sys.path.append(os.getcwd())

from core.database import DatabaseManager
from models.account import Account

def test_migration():
    db_path = "scratch/test_migrate.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print("--- Testing Database Migration ---")
    
    # 1. Create a "Legacy" database (v1.3.0 style without folder column)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            username TEXT NOT NULL,
            password_encrypted BLOB NOT NULL,
            totp_secret_encrypted BLOB,
            notes_encrypted BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("INSERT INTO accounts (service, username, password_encrypted) VALUES ('LegacySite', 'user1', 'enc_pass')")
    conn.commit()
    conn.close()
    
    print("[INIT] Legacy database created with 1 entry.")
    
    # 2. Open with new DatabaseManager
    db = DatabaseManager(db_path=db_path)
    
    # 3. Check if 'folder' column exists now
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(accounts)")
    columns = [info[1] for info in cursor.fetchall()]
    conn.close()
    
    if 'folder' in columns:
        print("[SUCCESS] 'folder' column added automatically via migration.")
    else:
        print("[FAILURE] 'folder' column missing after migration!")
        return

    # 4. Test CRUD with folder
    print("--- Testing CRUD with Folders ---")
    db.add_account("WorkSite", "work_user", b"enc_pass_2", folder="Work")
    db.add_account("PersonalSite", "pers_user", b"enc_pass_3", folder="Personal")
    
    accounts = db.get_all_accounts()
    print(f"[DATA] Total accounts: {len(accounts)}")
    
    # Verify Account objects
    for acc in accounts:
        print(f" - {acc.service}: Folder={acc.folder}")
        
    # Check folder list
    folders = db.get_all_folders()
    print(f"[FOLDERS] Unique folders: {folders}")
    
    if "Work" in folders and "Personal" in folders and len(folders) == 2:
        print("[SUCCESS] Folder extraction works.")
    else:
        print("[FAILURE] Folder list incorrect.")

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    test_migration()
