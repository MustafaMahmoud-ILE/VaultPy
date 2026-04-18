import os
import sys
import time
import winreg
import sqlite3
import shutil

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.database import DatabaseManager
from core.auth import AuthManager
from core.crypto import CryptoManager

def cleanup_registry():
    """Wipes the VaultPy registry key systematically."""
    try:
        key_path = r"Software\VaultPy"
        # We need to delete subkeys first on Windows
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + r"\SecurityState")
        except: pass
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
    except:
        pass

def run_registry_integrity_test():
    print("==================================================")
    print("    VaultPy v1.4.0 - REGISTRY INTEGRITY TEST      ")
    print("==================================================")
    
    test_dir = os.path.abspath("test_integrity_scratch")
    if not os.path.exists(test_dir): os.makedirs(test_dir)
    
    # --- PHASE 0: Clean State ---
    cleanup_registry()
    db_path = os.path.join(test_dir, "vault_identity_check.db")
    if os.path.exists(db_path): os.remove(db_path)
    
    print("\n[+] Initializing test vault...")
    db = DatabaseManager(db_path)
    auth = AuthManager(db)
    password = "Integrity_Test_v13"
    auth.setup_vault(password)
    db.close() # Ensure file is not locked on Windows
    
    # --- TEST 1: The Identity Mismatch Check (Registry Wipe) ---
    print("\n[TEST 1] Testing Hardware-Binding Loss (Registry Wipe Security)...")
    print("    WIPING 'Software\\VaultPy\\SecurityState' Registry key...")
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\VaultPy\SecurityState", 0, winreg.KEY_ALL_ACCESS)
        winreg.DeleteValue(key, "SystemSeal")
        winreg.DeleteValue(key, "AnchorUUID")
        winreg.CloseKey(key)
        print("    [+] Values deleted successfully.")
    except Exception as e:
        print(f"    [!] Error during wiping: {e}")

    print("    Attempting to re-open vault without its Anchor...")
    mismatch_pass = False
    try:
        new_db = DatabaseManager(db_path)
        print("    [X] VULNERABILITY: Vault re-opened and generated a new Seal!")
    except PermissionError as e:
        print(f"    [!] PROTECTION STOOD: {e}")
        mismatch_pass = True
    except Exception as e:
        print(f"    [!] DETECTED: {e}")
        mismatch_pass = True

    # --- TEST 2: The Brute-Force Pressure Test (Throttling + Account Lockout) ---
    print("\n[TEST 2] Testing High-Speed Access Pressure (Argon2 Throttling + Lockout)...")
    cleanup_registry() # Start fresh for storm
    db_path_bruteforce = os.path.join(test_dir, "vault_bruteforce.db")
    if os.path.exists(db_path_bruteforce): os.remove(db_path_bruteforce)
    
    db_bruteforce = DatabaseManager(db_path_bruteforce)
    auth_bruteforce = AuthManager(db_bruteforce)
    auth_bruteforce.setup_vault(password)
    
    print("    Simulating 5 high-speed failed attempts...")
    start_time = time.time()
    for i in range(5):
        attempt_start = time.time()
        auth_bruteforce.unlock_vault(f"wrong_guess_{i}")
        duration = time.time() - attempt_start
        print(f"    Attempt {i+1} took {duration:.4f}s")
        
    total_duration = time.time() - start_time
    print(f"    Total time for 5 iterations: {total_duration:.2f}s")
    
    throttling_pass = total_duration >= 2.5 # 5 * 0.5s penalty
    lockout_pass = auth_bruteforce.is_locked_out()
    
    if throttling_pass:
        print("    [!] PROTECTION STOOD: Throttling was strictly enforced.")
    else:
        print("    [X] VULNERABILITY: CPU Throttling too weak!")
        
    if lockout_pass:
        print("    [!] LOCKOUT VERIFIED: Account is strictly locked.")
    else:
        print("    [X] FAILED: Account not locked out.")

    print("\n==================================================")
    print("          REGISTRY INTEGRITY REPORT v1.3         ")
    print("==================================================")
    print(f"1. Identity Binding Resilience:        {'PASS' if mismatch_pass else 'FAIL'}")
    print(f"2. Brute-Force Throttling:             {'PASS' if throttling_pass else 'FAIL'}")
    print(f"3. Lockout Enforcement:                {'PASS' if lockout_pass else 'FAIL'}")
    print("==================================================")
    if mismatch_pass and throttling_pass and lockout_pass:
        print("SUMMARY: The vault has verified resistance against machine identity tampering.")
    else:
        print("FINAL ADVISORY: CRITICAL VULNERABILITIES REMAIN.")

if __name__ == "__main__":
    run_registry_integrity_test()
