# VaultPy 🔐

VaultPy is a professional-grade, local-first password manager built with Python and PySide6. It features a modern, frameless UI designed for high-contrast visibility and maximum security.

## ✨ Key Features

- **Pro-Grade UI/UX**: Frameless window architecture with custom title bar, rounded corners, and smooth fade-in animations.
- **Master Password Protection**: Highly secure authentication via **Argon2id** hashing.
- **Strong Encryption**: All secrets (passwords, notes, TOTP) are protected by **AES-256-GCM** authenticated encryption.
- **2FA Support (TOTP)**: Built-in generator with live countdown and high-visibility indicators.
- **Smart Analytics**: Real-time **Auto-lock** countdown timer that monitors user activity.
- **Data Integrity**: Clean, object-oriented architecture using a structured `models` layer.
- **Security Hardening**:
    *   **Single Instance Lock**: Prevents database corruption by allowing only one running instance.
    *   **Automatic Clipboard Clearing**: Clears sensitive data after 20 seconds.
    *   **Secure Password Policy**: Enforces a 12-character minimum for the master password.
    *   **Safe Recovery**: "Factory Reset" mechanism with keyword confirmation.

## 🛡️ Security Architecture

VaultPy prioritizes security through modern cryptographic standards:

1. **Password Hashing**: We use **Argon2id** (via `argon2-cffi`) for master password verification. We never store the master password in plaintext.
2. **Key Derivation**: A 256-bit encryption key is derived from the master password using **Argon2id** with a unique salt.
3. **Data Encryption**: All database secrets are encrypted using **AES-256-GCM** (via `cryptography`).
4. **Memory Safety**: sensitive data is stored as `bytes` and handled narrowly in the `AuthManager`.

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher

### Developer Setup
1. Clone the repository: `git clone https://github.com/yourusername/vaultpy.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python main.py`

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
