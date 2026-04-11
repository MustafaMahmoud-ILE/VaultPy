# VaultPy 🔐

<p align="center">
  <img src="assets/hero.png" width="100%" alt="VaultPy Hero Image">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/UI-PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="UI Framework">
  <img src="https://img.shields.io/badge/License-MIT-F5D76E?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Security-AES--256--GCM-blueviolet?style=for-the-badge" alt="Security Standard">
</p>

VaultPy is a professional-grade, local-first password manager built with Python and PySide6. It features a modern, frameless UI designed for high-contrast visibility and maximum security.

---

## 📷 Visual Journey

VaultPy is designed with a premium, frameless aesthetic. Explore the interface below:

### 🏙️ Secure Access (Login)
*The first line of defense. A minimalist, high-contrast entry point that welcomes you to your vault.*

<p align="center">
  <img src="assets/login_preview.png" width="80%" alt="Login Screen">
</p>

---

### 🗃️ Vault Management (Main View)
*Your secure repository. Clean organization with real-time TOTP generation and searchable accounts.*

<p align="center">
  <img src="assets/vault_preview.png" width="90%" alt="Vault Screen">
</p>

---

### 🛡️ Password Intelligence (Strength Meter)
*Real-time security feedback. Visual indicators help you choose strong, entropy-rich passwords for every account.*

<p align="center">
  <img src="assets/strength_meter_preview.png" width="70%" alt="Strength Meter Screen">
</p>

---

## ✨ Key Features (v1.1.0)

- **Seamless Self-Updates**: Built-in background auto-updater instantly modernizes your app to the latest GitHub release.
- **Persistent Data Safety**: Vaults are securely stored in `%APPDATA%`, saving your passwords safely across app updates.
- **Pro-Grade UI/UX**: Frameless window architecture with custom title bar, rounded corners, and smooth fade-in animations.
- **Master Password Protection**: Highly secure authentication via **Argon2id** hashing.
- **Strong Encryption**: All secrets (passwords, notes, TOTP) are protected by **AES-256-GCM** authenticated encryption.
- **2FA Support (TOTP)**: Built-in generator with live countdown, format sanitization, and high-visibility indicators.
- **Smart Analytics**: Real-time **Auto-lock** countdown timer that monitors user activity.
- **Security Hardening**:
    *   **Single Instance Lock**: Prevents database corruption.
    *   **Automatic Clipboard Clearing**: Clears sensitive data after 20 seconds.
    *   **Safe Recovery**: "Factory Reset" mechanism with keyword confirmation.

## 🛡️ Security Architecture

VaultPy prioritizes security through modern cryptographic standards:

1. **Password Hashing**: We use **Argon2id** (via `argon2-cffi`) for master password verification.
2. **Key Derivation**: A 256-bit encryption key is derived using **Argon2id** with a unique salt.
3. **Data Encryption**: All database secrets are encrypted using **AES-256-GCM** (authenticated encryption).

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher

### Developer Setup
```bash
git clone https://github.com/MustafaMahmoud-ILE/VaultPy.git
cd VaultPy
pip install -r requirements.txt
python main.py
```

### Building for Production (EXE)
To generate a standalone Windows executable:
1. Ensure `pyinstaller` is installed: `pip install pyinstaller`
2. Run the build automation: `python scripts/build.py`
3. Find your app in `dist/VaultPy/VaultPy.exe`.

## 📷 Developer Tools
We provide automated scripts for maintenance:
- **Take Screenshots**: `python scripts/capture.py` (Perfect for README updates)
- **Deep Cleanup**: `python scripts/cleanup.py` (Removes build/test artifacts)

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
