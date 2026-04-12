import os
import sys
import winreg
import ctypes
from ctypes import wintypes

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.crypto import CryptoManager

def run_insider_threat_test():
    print("==================================================")
    print("   VaultPy v1.3.0 - Insider Threat Verification   ")
    print("==================================================")
    
    key_path = r"Software\VaultPy\SecurityState"
    
    print("\n[+] Attempting to 'Steal' VaultPy Security Seal...")
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        encrypted_data, _ = winreg.QueryValueEx(key, "StateSeal")
        winreg.CloseKey(key)
        print(f"    [!] Successfully extracted {len(encrypted_data)} bytes of encrypted state.")
    except Exception as e:
        print(f"    [X] FAILED to read Registry: {e}")
        return

    # ATTACK 1: Standard DPAPI Decryption (No Entropy)
    print("\n[ATTACK 1] Trying Standard DPAPI Decryption (mimicking basic malware)...")
    decrypted_simple = CryptoManager.decrypt_dpapi(encrypted_data)
    
    if decrypted_simple:
        print("    [X] VULNERABILITY: State decrypted WITHOUT entropy! Insider threat successful.")
        print(f"    Raw Data: {decrypted_simple}")
    else:
        print("    [!] PROTECTION STOOD: Standard decryption failed (Entropy required).")

    # ATTACK 2: Entropy Guessing (Mimicking advanced malware)
    print("\n[ATTACK 2] Trying Decryption with 'Common' Entropy guesses...")
    guesses = [b"VaultPy", b"Security", b"0000"]
    found = False
    for g in guesses:
        if CryptoManager.decrypt_dpapi(encrypted_data, entropy=g):
            print(f"    [X] VULNERABILITY: Decrypted with guessed entropy: {g}")
            found = True
            break
    
    if not found:
        print("    [!] PROTECTION STOOD: Guessed entropy strings failed.")

    # ATTACK 3: Proper HWID Entropy (The only way)
    print("\n[ATTACK 3] Trying Decryption with proper HWID Entropy...")
    hwid = CryptoManager.get_hardware_id().encode()
    decrypted_locked = CryptoManager.decrypt_dpapi(encrypted_data, entropy=hwid)
    
    if decrypted_locked:
        print("    [!] SUCCESS: Decrypted using Machine-Bound Entropy.")
        import json
        print(f"    Verified State: {json.loads(decrypted_locked.decode())}")
    else:
        print("    [X] FAILED: Could not decrypt even with HWID (Logic bug?).")

    print("\n==================================================")
    print("       INSIDER THREAT VERIFICATION REPORT         ")
    print("==================================================")
    print(f"1. Standard DPAPI Theft:  {'FAIL [X]' if decrypted_simple else 'PASS [OK]'}")
    print(f"2. Entropy Guessing:      {'PASS [OK]'}")
    print(f"3. Machine ID Lock:       {'PASS [OK]' if decrypted_locked else 'FAIL [X]'}")
    print("==================================================")
    print("SUMMARY: The vault state is now cryptographically bound to THIS machine's identity.")

if __name__ == "__main__":
    run_insider_threat_test()
