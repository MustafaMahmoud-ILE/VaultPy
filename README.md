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

## 📷 Showcase

> [!TIP]
> **Visual Tour**: Add your application screenshots here to showcase the beautiful UI!

<p align="center">
  <img src="assets/login_preview.png" width="45%" alt="Login Screen Placeholder">
  <img src="assets/vault_preview.png" width="45%" alt="Vault Screen Placeholder">
</p>

---

## ✨ Key Features

- **Pro-Grade UI/UX**: Frameless window architecture with custom title bar, rounded corners, and smooth fade-in animations.
- **Master Password Protection**: Highly secure authentication via **Argon2id** hashing.
- **Strong Encryption**: All secrets (passwords, notes, TOTP) are protected by **AES-256-GCM** authenticated encryption.
- **2FA Support (TOTP)**: Built-in generator with live countdown and high-visibility indicators.
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
2. Run the build automation: `python build.py`
3. Find your app in `dist/VaultPy/VaultPy.exe`.

## 🧪 Testing
We maintain a suite of core logic tests. Run them using:
```bash
python -m unittest discover tests
```

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
