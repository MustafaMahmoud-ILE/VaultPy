# 📖 User Guide

This guide will help you master VaultPy and ensure your digital life remains secure and accessible.

## 🚀 Initial Setup

1. **First Launch**: When you run VaultPy for the first time, you will be asked to set a **Master Password**.
2. **Strength Meter**: Pay attention to the visual feedback. Ensure your password is "Strong" or "Very Strong".
3. **Seed Generation**: After setting your password, VaultPy will display your **24-word Recovery Seed**.
   - **Crucial**: Verify and write these words down on paper. 
   - **Warning**: Do not take a screenshot or store them in a plaintext file on your computer.

---

## 🔐 Managing Your Vault

### Adding Accounts
- Click **+ New Account**.
- Enter the service name, username, and password.
- **TOTP (optional)**: Paste the 2FA secret from your service provider (e.g., Google, GitHub). VaultPy will automatically generate 6-digit codes every 30 seconds.

### Searching
- Use the 🔍 search bar to instantly filter your accounts. VaultPy decrypts details only when an account is selected.

### Copying to Clipboard
- Use the **📋 Copy** buttons. VaultPy will automatically clear your clipboard after 20 seconds for your safety.

---

## 💾 Backups and Protection

VaultPy provides two layers of disaster recovery:

### layer 1: Manual Backups (.pyvault)
- In the dashboard, click **💾 Backup Vault**.
- Save the file to a secure location (External Drive, Private NAS).
- To restore, use the **📥 Import Vault** option on the login screen.

### Layer 2: Master Password Recovery
- If you lose your password, click **Lost password? Use Recovery Phrase** on the login screen.
- Enter your 24 words.
- VaultPy will grant you access and prompt you to set a **new master password**.

---

## 🔒 Session Security

- **Auto-Lock**: VaultPy monitors your inactivity. The app will automatically lock and clear all keys from memory after 2 minutes of inactivity.
- **Manual Lock**: Click the **🔒 Lock Session** button in the status bar to lock instantly.
- **Single Instance**: VaultPy prevents multiple copies from running at once to ensure your database remains uncorrupted.
