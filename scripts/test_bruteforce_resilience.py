import os
import sys
import time
import pyotp

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.database import DatabaseManager
from core.auth import AuthManager

def run_bruteforce_resilience_test():
    print("==================================================")
    print("    VaultPy v1.3.0 - BRUTE-FORCE RESILIENCE TEST  ")
    print("==================================================")
    
    test_dir = os.path.abspath("test_bruteforce_scratch")
    if not os.path.exists(test_dir): os.makedirs(test_dir)
    db_path = os.path.join(test_dir, "test_recovery_hardening.db")
    if os.path.exists(db_path): 
        try: os.remove(db_path)
        except: pass
    
    print("\n[+] Initializing vulnerable vault for testing...")
    db = DatabaseManager(db_path)
    auth = AuthManager(db)
    password = "Safe_Password_123"
    _, _, totp_secret = auth.setup_vault(password)
    
    # 1. TOTP Brute Force Test
    print("\n[TEST 1] TOTP Brute-Force Storm...")
    print(f"    Target TOTP Secret: {totp_secret}")
    
    valid_code = pyotp.TOTP(totp_secret).now()
    print(f"    Current Valid Code: {valid_code}")
    print("    Simulating a 'Storm' of 100 random guesses...")
    
    start_time = time.time()
    success_found = False
    attempts = 0
    
    for i in range(100):
        code = f"{i:06d}" # Trying 000000 to 000099
        attempts += 1
        if auth.unlock_with_totp(code):
            success_found = True
            break
            
    duration = time.time() - start_time
    print(f"    - Attempted {attempts} codes in {duration:.4f}s")
    
    totp_pass = (attempts <= 6) or (duration > 2.0) # Should be slow due to sleep or blocked due to lockout
    lockout_pass = auth.is_locked_out()
    
    if lockout_pass:
        print("    [!] PROTECTION: Account locked after failed recovery attempts.")
    else:
        print("    [X] VULNERABILITY: Recovery attempts do not trigger Lockout.")

    # Reset for next test
    db.reset_failed_attempts()

    # 2. Recovery Phrase Throttling Test
    print("\n[TEST 2] Recovery Phrase Brute-Force Speed...")
    start_time = time.time()
    fake_phrase = "apple banana " * 12
    auth.unlock_with_recovery_phrase(fake_phrase)
    duration = time.time() - start_time
    
    phrase_pass = duration >= 0.4
    print(f"    - One Recovery Phrase attempt took {duration:.4f}s")
    if not phrase_pass:
        print("    [X] VULNERABILITY: Recovery Phrase check is too fast.")
    else:
        print("    [!] PROTECTION: Argon2 is correctly throttling the phrase check.")

    print("\n==================================================")
    print("        BRUTE-FORCE RESILIENCE REPORT v1.0        ")
    print("==================================================")
    print(f"1. TOTP Brute-Force Protection:        {'PASS' if totp_pass else 'FAIL'}")
    print(f"2. Recovery Lockout Participation:     {'PASS' if lockout_pass else 'FAIL'}")
    print(f"3. Phrase Check Throttling:            {'PASS' if phrase_pass else 'FAIL'}")
    print("==================================================")
    if totp_pass and lockout_pass and phrase_pass:
        print("FINAL ADVISORY: Recovery entry points are now SECURE.")
    else:
        print("ADVISORY: Recovery entry points are still VULNERABLE.")

if __name__ == "__main__":
    run_bruteforce_resilience_test()
