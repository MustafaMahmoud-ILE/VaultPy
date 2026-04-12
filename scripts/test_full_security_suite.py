import os
import sys
import sqlite3
import pyotp
import binascii

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.database import DatabaseManager
from core.auth import AuthManager
from core.crypto import CryptoManager

def run_security_suite():
    print("==================================================")
    print("     VaultPy v1.3.0 Security Verification Suite   ")
    print("==================================================")
    
    test_dir = os.path.join(os.getcwd(), "security_test_scratch")
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
        
    db_path = os.path.join(test_dir, "pentest.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = DatabaseManager(db_path)
    auth = AuthManager(db)
    
    password = "SuperSecretPassword123!"
    
    # SETUP
    print("\n[+] Initializing Security Test Vault (v1.3.0)...")
    auth.setup_vault(password)
    
    # Get DEK via JIT for reference
    with auth._get_plaintext_dek() as dek:
        dek_value = bytes(dek)
    print(f"    Target DEK (Hidden): {dek_value.hex()[:8]}...")
    
    # --- PHASE 1: Memory Forensics (DPAPI Cloaking) ---
    print("\n[PHASE 1] Testing DPAPI RAM Cloaking...")
    
    protected_blob = auth._protected_dek
    plain_visible = (dek_value in protected_blob) if protected_blob else False
    
    if plain_visible:
        print("    [X] VULNERABILITY: Raw DEK found in memory!")
    else:
        print("    [!] SUCCESS: DEK is DPAPI-encrypted in RAM.")
    
    # After locking, both references should be None
    auth.lock_vault()
    
    if auth._protected_dek is None and auth._session_key is None:
        print("    [!] SUCCESS: DPAPI blob discarded on lock (None).")
        memory_pass = True
    else:
        print("    [X] SECURITY FAILURE: Protected DEK not cleared after lock!")
        memory_pass = False

    # --- PHASE 2: Database Integrity (Lockout Bypass) ---
    print("\n[PHASE 2] Testing Database Integrity (Lockout Bypass)...")
    
    # Trigger lockout
    print("    Simulating 5 failed attempts...")
    for _ in range(5):
        auth.unlock_vault("wrong_pass")
    
    if auth.is_locked_out():
        print("    [!] Lockout verified.")
    
    # ATTACK: Modify DB directly (Tampering)
    print("    ATTACK: Manually resetting failed_attempts to 0 in vault.db...")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE meta SET failed_attempts = 0 WHERE id = (SELECT id FROM meta LIMIT 1)")
        conn.commit()
    
    fa = db.get_failed_attempts()
    if fa == 999:
        print("    [!] SUCCESS: Tampering detected! Emergency lockout (999) triggered.")
        integrity_pass = True
    elif fa == 0:
        print("    [X] VULNERABILITY: HMAC check failed to detect tampering!")
        integrity_pass = False
    else:
        print(f"    [?] Unexpected failed_attempts value: {fa}")
        integrity_pass = fa > 0

    # --- PHASE 3: Cryptographic Hardware Binding ---
    print("\n[PHASE 3] Testing Cryptographic Hardware Binding...")
    
    meta = db.get_meta()
    t_secret_obf = meta[5]
    
    if isinstance(t_secret_obf, str) and t_secret_obf.startswith("DPAPI:"):
        print(f"    Secret stored as: DPAPI-encrypted ({len(t_secret_obf)} chars)")
        
        # ATTACK: Try to decrypt without proper entropy
        encrypted_bytes = bytes.fromhex(t_secret_obf[6:])
        decrypted_no_entropy = CryptoManager.decrypt_dpapi(encrypted_bytes)
        
        if decrypted_no_entropy:
            print("    [X] VULNERABILITY: TOTP secret decrypted WITHOUT entropy!")
            binding_pass = False
        else:
            print("    [!] SUCCESS: DPAPI decryption without entropy FAILED (hardware-bound).")
            binding_pass = True
    else:
        print(f"    Captured Obfuscated Secret: {t_secret_obf[:10]}...")
        # ATTACK: Try old static XOR key (without hardware ID)
        old_key = "VaultPy_Security_v1.2.1"
        decrypted_old = "".join(chr(ord(c) ^ ord(old_key[i % len(old_key)])) for i, c in enumerate(t_secret_obf))
        
        if all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567 =" for c in decrypted_old) and len(decrypted_old) >= 16:
             print(f"    [X] VULNERABILITY: Secret DECRYPTED with static key: {decrypted_old}")
             binding_pass = False
        else:
             print("    [!] SUCCESS: Static key failed to reveal secret (Hardware Binding active).")
             binding_pass = True

    print("\n==================================================")
    print("          SECURITY VERIFICATION REPORT v3.0       ")
    print("==================================================")
    print(f"1. Memory Isolation:   {'PASS [OK]' if memory_pass else 'FAIL [X]'}")
    print(f"2. Database Integrity: {'PASS [OK]' if integrity_pass else 'FAIL [X]'}")
    print(f"3. Hardware Binding:   {'PASS [OK]' if binding_pass else 'FAIL [X]'}")
    print("==================================================")
    all_pass = memory_pass and integrity_pass and binding_pass
    print(f"VERDICT: {'ALL TESTS PASSED — Vault is HARDENED.' if all_pass else 'SECURITY WEAKNESS DETECTED!'}")

    # Cleanup
    import shutil
    db.close()
    if os.path.exists(test_dir): shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    run_security_suite()
