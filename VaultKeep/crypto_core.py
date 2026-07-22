"""
crypto_core.py

Cryptographic core for VaultKeep.

Design:
    - The master password is never stored anywhere, in any form.
    - Argon2id derives a 256-bit master key from the master password
      plus a random per-vault salt. Argon2id is memory-hard and is the
      current recommended KDF for password-based key derivation
      (winner of the Password Hashing Competition).
    - The master key never touches disk. It lives only in process
      memory for the duration of the unlocked session and is wiped
      when the vault locks.
    - Each secret (password entry) is encrypted individually with
      AES-256-GCM using a fresh random 96-bit nonce. GCM gives us
      both confidentiality and integrity (authenticated encryption) -
      any tampering with ciphertext is detected on decryption.
    - A separate "verifier" blob (a known plaintext encrypted under
      the derived key) is stored so the app can check whether a
      typed master password is correct WITHOUT ever decrypting real
      entries just to test it, and without storing the master
      password or a fast hash of it (which would be brute-forceable).
"""

from __future__ import annotations

import os
import base64
import secrets
from dataclasses import dataclass

from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Argon2id parameters
#
# These follow OWASP's current guidance for interactive, high-security
# password hashing (as of the 2024/2025 cheat sheet): Argon2id with
# m=19 MiB minimum for low-friction logins, but since this is a LOCAL
# vault unlock (not a web login with thousands of concurrent requests),
# we can afford to be much heavier and make offline brute force of a
# stolen vault file expensive.
# ---------------------------------------------------------------------------
ARGON2_TIME_COST = 4          # iterations
ARGON2_MEMORY_COST = 262144   # KiB = 256 MiB
ARGON2_PARALLELISM = 2
ARGON2_HASH_LEN = 32          # 256-bit key for AES-256
ARGON2_SALT_LEN = 16
GCM_NONCE_LEN = 12             # 96-bit nonce, standard for AES-GCM

VERIFIER_PLAINTEXT = b"VAULTKEEP-OK-v1"


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from the master password using Argon2id."""
    return hash_secret_raw(
        secret=master_password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )


def new_salt() -> bytes:
    return secrets.token_bytes(ARGON2_SALT_LEN)


def encrypt(key: bytes, plaintext: bytes, associated_data: bytes = b"") -> tuple[bytes, bytes]:
    """Encrypt with AES-256-GCM. Returns (nonce, ciphertext_with_tag)."""
    nonce = secrets.token_bytes(GCM_NONCE_LEN)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce, ct


def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes = b"") -> bytes:
    """Decrypt with AES-256-GCM. Raises cryptography.exceptions.InvalidTag on
    tampered/incorrect data."""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


def make_verifier(key: bytes) -> tuple[bytes, bytes]:
    """Create a (nonce, ciphertext) pair proving knowledge of `key`,
    without revealing anything about real vault contents."""
    return encrypt(key, VERIFIER_PLAINTEXT)


def check_verifier(key: bytes, nonce: bytes, ciphertext: bytes) -> bool:
    try:
        pt = decrypt(key, nonce, ciphertext)
        return pt == VERIFIER_PLAINTEXT
    except Exception:
        return False


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def wipe_bytearray(buf: bytearray) -> None:
    """Best-effort zeroing of sensitive buffers held as bytearray."""
    for i in range(len(buf)):
        buf[i] = 0


@dataclass
class UnlockedSession:
    """Holds the derived master key only while the vault is unlocked.
    Call .lock() as soon as the session should end."""
    key: bytes | None

    def lock(self) -> None:
        if self.key is not None:
            # bytes are immutable in Python, so true zeroing isn't
            # possible without ctypes tricks; we drop the reference so
            # it becomes eligible for garbage collection immediately
            # and is no longer reachable from the session.
            self.key = None

    @property
    def is_unlocked(self) -> bool:
        return self.key is not None
