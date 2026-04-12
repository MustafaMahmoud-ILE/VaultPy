"""Diagnostic script to identify v1.2.4 → current version compatibility issues."""
import os
import sys
import sqlite3
import winreg

sys.path.insert(0, os.getcwd())
from core.crypto import CryptoManager

db_path = os.path.join(os.getenv('APPDATA'), 'VaultPy', 'vault.db')
print(f"DB Path: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")
print("=" * 60)

# 1. Check DB Anchor
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check schema
cursor.execute("PRAGMA table_info(meta)")
columns = [info[1] for info in cursor.fetchall()]
print(f"Meta columns: {columns}")

has_registry_uid = 'registry_uid' in columns
print(f"Has registry_uid: {has_registry_uid}")

if has_registry_uid:
    cursor.execute("SELECT registry_uid FROM meta LIMIT 1")
    row = cursor.fetchone()
    db_anchor = row[0] if row else None
    print(f"DB Anchor: {repr(db_anchor)}")
else:
    db_anchor = None
    print("DB Anchor: N/A (column missing)")

# 2. Check Failed Attempts
if 'failed_attempts' in columns:
    cursor.execute("SELECT failed_attempts FROM meta LIMIT 1")
    fa = cursor.fetchone()
    print(f"Failed Attempts: {fa[0] if fa else 'N/A'}")

# 3. Check Registry
print("\n" + "=" * 60)
key_path = r"Software\VaultPy\SecurityState"
entropy = CryptoManager.get_hardware_id().encode()
print(f"Hardware ID: {CryptoManager.get_hardware_id()[:8]}...")

try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
    
    # Check AnchorUUID
    try:
        reg_uid_enc, reg_type = winreg.QueryValueEx(key, "AnchorUUID")
        print(f"\nAnchorUUID Registry Type: {reg_type} (1=REG_SZ, 3=REG_BINARY)")
        
        if reg_type == 1:  # REG_SZ - plain text
            print(f"AnchorUUID (plain): {repr(reg_uid_enc)}")
            reg_uid = reg_uid_enc
        else:  # REG_BINARY - DPAPI encrypted
            # Try with entropy
            decrypted = CryptoManager.decrypt_dpapi(reg_uid_enc, entropy=entropy)
            print(f"AnchorUUID DPAPI+entropy: {repr(decrypted)}")
            
            # Try without entropy
            decrypted_no_ent = CryptoManager.decrypt_dpapi(reg_uid_enc)
            print(f"AnchorUUID DPAPI no entropy: {repr(decrypted_no_ent)}")
            
            if decrypted:
                reg_uid = decrypted.decode()
            elif decrypted_no_ent:
                reg_uid = decrypted_no_ent.decode()
            else:
                reg_uid = None
                
        if db_anchor and reg_uid:
            match = db_anchor == reg_uid
            print(f"\n>>> ANCHOR MATCH: {match}")
            if not match:
                print(f"    DB:  {repr(db_anchor)}")
                print(f"    REG: {repr(reg_uid)}")
    except FileNotFoundError:
        print("AnchorUUID: NOT FOUND in registry")

    # Check SystemSeal
    try:
        sys_seal_enc, seal_type = winreg.QueryValueEx(key, "SystemSeal")
        print(f"\nSystemSeal Registry Type: {seal_type}")
        
        decrypted = CryptoManager.decrypt_dpapi(sys_seal_enc, entropy=entropy)
        print(f"SystemSeal DPAPI+entropy: {repr(decrypted[:20])}..." if decrypted else "SystemSeal DPAPI+entropy: FAILED")
        
        decrypted_no_ent = CryptoManager.decrypt_dpapi(sys_seal_enc)
        print(f"SystemSeal DPAPI no entropy: {repr(decrypted_no_ent[:20])}..." if decrypted_no_ent else "SystemSeal DPAPI no entropy: FAILED")
    except FileNotFoundError:
        print("SystemSeal: NOT FOUND in registry")
    
    winreg.CloseKey(key)
except FileNotFoundError:
    print("Registry key Software\\VaultPy\\SecurityState: NOT FOUND")

# 4. Test password verification  
print("\n" + "=" * 60)
cursor.execute("SELECT password_hash FROM meta LIMIT 1")
row = cursor.fetchone()
if row:
    p_hash = row[0]
    print(f"Password hash: {p_hash[:30]}...")
    print(f"Hash type: {type(p_hash).__name__}")
    
conn.close()
print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
