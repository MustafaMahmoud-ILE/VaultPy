"""Test v1.2.4 backward compatibility — simulates ALL unlock paths with old constants."""
import os, sys
sys.path.insert(0, os.getcwd())
from core.crypto import CryptoManager
from argon2.low_level import hash_secret_raw
from argon2 import Type

# v1.2.4 constants
OLD_ITERATIONS = 3
OLD_MEMORY = 65536
OLD_PARALLELISM = 4

password = "TestPassword123!"
salt = os.urandom(16)
dek = os.urandom(32)

# === Simulate v1.2.4 vault creation ===
# 1. Password wrap (t=3)
old_p_kek = hash_secret_raw(secret=password.encode(), salt=salt, time_cost=OLD_ITERATIONS, 
                             memory_cost=OLD_MEMORY, parallelism=OLD_PARALLELISM, hash_len=32, type=Type.ID)
p_wrapped = CryptoManager.encrypt(dek.hex(), old_p_kek)

# 2. Recovery phrase wrap (t=3, no doubling in v1.2.4)
phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
r_salt = os.urandom(16)
old_r_kek = hash_secret_raw(secret=phrase.strip().lower().encode(), salt=r_salt, time_cost=OLD_ITERATIONS, 
                             memory_cost=OLD_MEMORY, parallelism=OLD_PARALLELISM, hash_len=32, type=Type.ID)
r_wrapped = CryptoManager.encrypt(dek.hex(), old_r_kek)

# 3. TOTP wrap (t=3)
totp_secret = "JBSWY3DPEHPK3PXP"
old_t_kek = hash_secret_raw(secret=totp_secret.encode(), salt=salt, time_cost=OLD_ITERATIONS, 
                             memory_cost=OLD_MEMORY, parallelism=OLD_PARALLELISM, hash_len=32, type=Type.ID)
t_wrapped = CryptoManager.encrypt(dek.hex(), old_t_kek)

# Old password hash (has t=3 in it)
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=OLD_ITERATIONS, memory_cost=OLD_MEMORY, parallelism=OLD_PARALLELISM, type=Type.ID)
old_hash = ph.hash(password, salt=salt)
print(f"Old hash params: {old_hash.split(chr(36))[3]}")

# === Test v1.3.0 unlock paths with old data ===

# TEST 1: Password unlock (try current → fallback compat)
print("\n--- TEST 1: Password Unlock ---")
try:
    p_kek = CryptoManager.derive_key(password, salt)
    result = CryptoManager.decrypt(p_wrapped, p_kek)
    print(f"  Current constants: OK (DEK match: {bytes.fromhex(result) == dek})")
except:
    try:
        p_kek = CryptoManager.derive_key_compat(password, salt, old_hash)
        result = CryptoManager.decrypt(p_wrapped, p_kek)
        print(f"  Compat fallback: OK (DEK match: {bytes.fromhex(result) == dek})")
    except Exception as e:
        print(f"  FAILED: {e}")

# TEST 2: Recovery Phrase unlock
print("\n--- TEST 2: Recovery Phrase Unlock ---")
try:
    r_kek = CryptoManager.derive_key_from_phrase(phrase, r_salt)  # t=20
    result = CryptoManager.decrypt(r_wrapped, r_kek)
    print(f"  Current constants (t*2): OK (DEK match: {bytes.fromhex(result) == dek})")
except:
    try:
        r_kek = CryptoManager.derive_key_from_phrase_compat(phrase, r_salt, old_hash)  # t=3
        result = CryptoManager.decrypt(r_wrapped, r_kek)
        print(f"  Compat fallback (t=3): OK (DEK match: {bytes.fromhex(result) == dek})")
    except Exception as e:
        print(f"  FAILED: {e}")

# TEST 3: TOTP unlock
print("\n--- TEST 3: TOTP Unlock ---")
try:
    t_kek = CryptoManager.derive_key(totp_secret, salt)  # t=10
    result = CryptoManager.decrypt(t_wrapped, t_kek)
    print(f"  Current constants: OK (DEK match: {bytes.fromhex(result) == dek})")
except:
    try:
        t_kek = CryptoManager.derive_key_compat(totp_secret, salt, old_hash)  # t=3
        result = CryptoManager.decrypt(t_wrapped, t_kek)
        print(f"  Compat fallback: OK (DEK match: {bytes.fromhex(result) == dek})")
    except Exception as e:
        print(f"  FAILED: {e}")

print("\n=== ALL TESTS COMPLETE ===")
