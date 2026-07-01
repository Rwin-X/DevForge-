# 🔐 Secure Password Hashing Utility

> A lightweight Python utility demonstrating secure password hashing, verification, and storage using modern cryptographic techniques.

This project showcases how passwords should be securely processed using **PBKDF2-HMAC-SHA256**, random salts, and constant-time comparison. It also includes a simple SHA-256 demonstration function for educational purposes.

---

## 📖 Overview

Instead of storing plaintext passwords, this program converts each password into a secure cryptographic hash using:

- PBKDF2-HMAC-SHA256
- Random cryptographic salt
- Configurable iteration count
- Constant-time verification

The generated records can later be used to verify whether an entered password matches a previously stored one without ever revealing the original password.

---

## ✨ Features

- 🔒 Secure password hashing with PBKDF2-HMAC-SHA256
- 🧂 Cryptographically secure random salt generation
- ⚙️ Configurable iteration count
- ✔️ Password verification against stored hashes
- 📁 Automatic storage of hash records
- 🛡 Constant-time hash comparison to reduce timing attacks
- 📄 Simple file-based storage
- 🧪 Educational SHA-256 demonstration function

---

## 🔑 Password Storage Format

Each stored password record follows the format:

```
salt:iterations:hash
```

Example:

```
5d7d3f6b9b8b0d...:200000:8e2af7b3...
```

This format allows each password to have its own unique salt while preserving the iteration count used during hashing.

---

## ⚙️ How It Works

The program performs the following steps:

1. Accepts user input.
2. Loads previously stored password records.
3. Compares the input against existing hashes.
4. If a match is found, verification succeeds.
5. Otherwise, a new salted hash is generated and saved.

---

## 🧪 Demonstration Function

In addition to secure password hashing, the project contains a small demonstration utility that:

- Inserts a random character into a string.
- Computes its SHA-256 hash.

This function is intended **only for educational purposes** and is **not suitable for password security**.

---

## 🛠 Technologies

- Python 3
- hashlib
- hmac
- secrets
- os

Uses only the Python Standard Library.

---

## 🎯 Educational Goals

This project demonstrates important security concepts including:

- Password hashing
- Salt generation
- Key derivation functions (KDFs)
- PBKDF2
- SHA-256
- Secure password verification
- Constant-time comparison
- Secure credential storage

---

## 🚀 Possible Future Improvements

Potential enhancements include:

- User account management
- SQLite database support
- Argon2 implementation
- bcrypt support
- Password strength checking
- Command-line arguments
- Encrypted password storage
- JSON export/import
- Logging system
- Unit tests

---

## 📄 License

This project is intended for educational purposes and learning modern password security practices.
