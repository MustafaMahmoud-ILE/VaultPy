import os
import hmac
import hashlib
import winreg
import ctypes
from ctypes import wintypes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher, Type
from argon2.low_level import hash_secret_raw

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

class CryptoManager:
    """Handles encryption, decryption, and key derivation."""

    ITERATIONS = 3
    MEMORY_COST = 65536
    PARALLELISM = 4
    TAG_SIZE = 16  # bytes
    NONCE_SIZE = 12  # bytes
    KEY_SIZE = 32  # bytes

    @staticmethod
    def derive_key(master_password: str, salt: bytes) -> bytes:
        """Derives a 256-bit key from the master password using Argon2id."""
        return hash_secret_raw(
            secret=master_password.encode(),
            salt=salt,
            time_cost=CryptoManager.ITERATIONS,
            memory_cost=CryptoManager.MEMORY_COST,
            parallelism=CryptoManager.PARALLELISM,
            hash_len=CryptoManager.KEY_SIZE,
            type=Type.ID
        )

    @staticmethod
    def encrypt(data: str, key: bytes) -> bytes:
        """Encrypts data using AES-256-GCM. Returns nonce + ciphertext."""
        aesgcm = AESGCM(key)
        nonce = os.urandom(CryptoManager.NONCE_SIZE)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
        return nonce + ciphertext

    @staticmethod
    def decrypt(encrypted_data: bytes, key: bytes) -> str:
        """Decrypts data using AES-256-GCM. Expects nonce + ciphertext."""
        aesgcm = AESGCM(key)
        nonce = encrypted_data[:CryptoManager.NONCE_SIZE]
        ciphertext = encrypted_data[CryptoManager.NONCE_SIZE:]
        try:
            decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError("Decryption failed. Invalid key or corrupted data.") from e

    @staticmethod
    def generate_dek() -> bytes:
        """Generates a random 256-bit Data Encryption Key."""
        return os.urandom(CryptoManager.KEY_SIZE)

    @staticmethod
    def generate_recovery_phrase() -> tuple[str, bytes]:
        """
        Generates a 24-word recovery phrase and its derived entropy.
        Returns (phrase_string, entropy_bytes).
        """
        from core.wordlist import WORDS
        entropy = os.urandom(32)  # 256 bits
        
        # Convert entropy to a mnemonic (Simplified BIP39-style)
        # 256 bits / 11 bits per word = 23.27 words. 
        # We'll use 24 words for simplicity and extra entropy.
        indices = []
        temp_entropy = int.from_bytes(entropy, 'big')
        for _ in range(24):
            indices.append(temp_entropy % 2048)
            temp_entropy //= 2048
            
        phrase = " ".join([WORDS[i % len(WORDS)] for i in indices])
        return phrase, entropy

    @staticmethod
    def derive_key_from_phrase(phrase: str, salt: bytes) -> bytes:
        """Derives a key from a recovery phrase using Argon2id."""
        return hash_secret_raw(
            secret=phrase.strip().lower().encode(),
            salt=salt,
            time_cost=CryptoManager.ITERATIONS,
            memory_cost=CryptoManager.MEMORY_COST,
            parallelism=CryptoManager.PARALLELISM,
            hash_len=CryptoManager.KEY_SIZE,
            type=Type.ID
        )

    @staticmethod
    def hash_password(password: str) -> tuple[str, bytes]:
        """Hashes a password for storage using Argon2id. Returns (hash, salt)."""
        salt = os.urandom(16)
        ph = PasswordHasher(
            time_cost=CryptoManager.ITERATIONS,
            memory_cost=CryptoManager.MEMORY_COST,
            parallelism=CryptoManager.PARALLELISM,
            type=Type.ID
        )
        password_hash = ph.hash(password, salt=salt)
        return password_hash, salt

    @staticmethod
    def verify_password(password_hash: str, password: str) -> bool:
        """Verifies a password against an Argon2id hash."""
        ph = PasswordHasher()
        try:
            ph.verify(password_hash, password)
            return True
        except Exception:
            return False

    @staticmethod
    def get_hardware_id() -> str:
        """Retrieves the unique Windows MachineGuid for hardware binding."""
        try:
            registry_key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, 
                r"SOFTWARE\Microsoft\Cryptography", 
                0, 
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            )
            value, _ = winreg.QueryValueEx(registry_key, "MachineGuid")
            winreg.CloseKey(registry_key)
            return str(value)
        except Exception:
            # Fallback to a stable ID if registry access fails
            return "VaultPy_Default_HWID_7788"

    @staticmethod
    def get_hmac_signature(data: str, key: str) -> bytes:
        """Generates an HMAC-SHA256 signature for data integrity."""
        return hmac.new(key.encode(), data.encode(), hashlib.sha256).digest()

    @staticmethod
    def verify_hmac_signature(data: str, signature: bytes, key: str) -> bool:
        """Verifies an HMAC-SHA256 signature."""
        expected = CryptoManager.get_hmac_signature(data, key)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def encrypt_dpapi(data: bytes, entropy: bytes = None) -> bytes:
        """Encrypts data using Windows DPAPI with optional secondary entropy."""
        data_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data))
        data_out = DATA_BLOB()
        
        ent_blob = None
        if entropy:
            ent_blob = DATA_BLOB(len(entropy), ctypes.create_string_buffer(entropy))
        
        if ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(data_in), None, 
            ctypes.byref(ent_blob) if ent_blob else None, 
            None, None, 0, ctypes.byref(data_out)
        ):
            res = ctypes.string_at(data_out.pbData, data_out.cbData)
            ctypes.windll.kernel32.LocalFree(data_out.pbData)
            return res
        return b""

    @staticmethod
    def decrypt_dpapi(data: bytes, entropy: bytes = None) -> bytes:
        """Decrypts data using Windows DPAPI with the same secondary entropy used during encryption."""
        data_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data))
        data_out = DATA_BLOB()
        
        ent_blob = None
        if entropy:
            ent_blob = DATA_BLOB(len(entropy), ctypes.create_string_buffer(entropy))
            
        if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(data_in), None, 
            ctypes.byref(ent_blob) if ent_blob else None, 
            None, None, 0, ctypes.byref(data_out)
        ):
            res = ctypes.string_at(data_out.pbData, data_out.cbData)
            ctypes.windll.kernel32.LocalFree(data_out.pbData)
            return res
        return b""
