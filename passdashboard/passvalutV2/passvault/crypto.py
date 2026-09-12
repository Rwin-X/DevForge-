"""
crypto.py — Key derivation and encryption primitives for PassVault.

Security design:
- The master password is never stored anywhere, in any form.
- A random 16-byte salt is generated once per vault and saved alongside
  the encrypted data (the salt itself is not secret).
- The master password + salt are run through PBKDF2-HMAC-SHA256 with a
  high iteration count to derive a symmetric encryption key.
- All vault contents are encrypted with Fernet (AES-128-CBC + HMAC-SHA256
  for authenticity) using the derived key.

If the master password is lost, the vault cannot be recovered. There is
no backdoor and no reset mechanism — this is intentional.
"""

from __future__ import annotations

import base64
import secrets

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Iteration count for PBKDF2. Higher = slower to brute-force, slower to unlock.
# 390,000 is in line with current (2024+) OWASP guidance for PBKDF2-SHA256.
KDF_ITERATIONS = 390_000
SALT_SIZE_BYTES = 16


class WrongPasswordError(Exception):
    """Raised when a master password fails to decrypt the vault."""


def generate_salt() -> bytes:
    """Generate a new cryptographically secure random salt."""
    return secrets.token_bytes(SALT_SIZE_BYTES)


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a URL-safe base64-encoded key suitable for Fernet."""
    if not master_password:
        raise ValueError("Master password must not be empty.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    raw_key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


def make_fernet(master_password: str, salt: bytes) -> Fernet:
    """Convenience: derive a key and wrap it in a Fernet instance."""
    return Fernet(derive_key(master_password, salt))


def encrypt_bytes(fernet: Fernet, data: bytes) -> bytes:
    return fernet.encrypt(data)


def decrypt_bytes(fernet: Fernet, token: bytes) -> bytes:
    """Decrypt data, raising WrongPasswordError on failure."""
    try:
        return fernet.decrypt(token)
    except InvalidToken as exc:
        raise WrongPasswordError("Incorrect master password.") from exc
