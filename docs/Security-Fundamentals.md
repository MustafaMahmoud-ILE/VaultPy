# 🛡️ Security Fundamentals

VaultPy is built on the principle of **"Inherent Security"**. We use industry-standard primitives that are resilient to modern brute-force and side-channel attacks.

## 🔑 Key Derivation (Argon2id)

We use **Argon2id**, the winner of the Password Hashing Competition (PHC), for all key derivation tasks. 

### Why Argon2id?
- **Resistant to GPU/ASIC Cracking**: It is memory-hard, making it extremely expensive for attackers to build custom hardware to crack your password.
- **Combined Hybrid**: Argon2id combines Argon2i (resistant to side-channel attacks) and Argon2d (resistant to GPU cracking).
- **Iteration Count**: VaultPy uses a high iteration count and memory cost (64MB) to ensure that even a 10-character password requires significant compute to guess.

---

## 🔒 Data Encryption (AES-256-GCM)

All local storage is encrypted using **Advanced Encryption Standard (AES)** with a 256-bit key in **Galois/Counter Mode (GCM)**.

### Why GCM Mode?
- **Authenticated Encryption**: Unlike older modes (like CBC), GCM provides **Integrity**. If an attacker tries to modify even 1 bit of your database, the decryption will fail.
- **Hardware Acceleration**: Modern CPUs have built-in instructions (AES-NI) that make this encryption nearly instant without compromising safety.

---

## 📦 Zero-Knowledge Persistence

VaultPy is a zero-knowledge application. 
- **No Cloud**: Your data never leaves your machine.
- **No Backdoors**: There is no "Master Key" held by the developers. The only way to unlock the vault is via your password or your recovery phrase.
- **Memory Safety**: Decrypted keys exist only in volatile memory (RAM) and are wiped the moment the application locks or closes.

---

## 🚨 Best Practices for You

Security is a partnership between the software and the user.

1. **The 24-Word Rule**: Your recovery phrase is more powerful than your password. Store it on a physical piece of paper in a fireproof safe. Never store it in a cloud-synced notes app.
2. **Device Security**: Since VaultPy is local-first, the security of your OS matters. Keep your Windows/Linux system updated and use a strong login password for your device.
3. **Backup Often**: Use the `.pyvault` export feature once a month or after adding significant new accounts.
