"""Password storage in the operating system keyring.

The password is never written to the JSON config file. For headless servers
without a keyring backend, the INBOXGUARD_PASSWORD environment variable is
used instead.
"""
from __future__ import annotations

import os

from .errors import SecretError

SERVICE_NAME = "inboxguard"
ENV_VAR = "INBOXGUARD_PASSWORD"


def _keyring():
    try:
        import keyring  # noqa: PLC0415 - imported lazily so tests run without it
    except ImportError as exc:
        raise SecretError("The 'keyring' package is not installed.") from exc
    return keyring


def get_password(username: str) -> str:
    env = os.environ.get(ENV_VAR)
    if env:
        return env
    kr = _keyring()
    try:
        value = kr.get_password(SERVICE_NAME, username)
    except Exception as exc:  # keyring raises backend-specific errors
        raise SecretError(
            f"Keyring unavailable ({exc}). Set the {ENV_VAR} environment variable instead."
        ) from exc
    if not value:
        raise SecretError("No password stored for this account. Open Settings and save it.")
    return value


def set_password(username: str, password: str) -> None:
    kr = _keyring()
    try:
        kr.set_password(SERVICE_NAME, username, password)
    except Exception as exc:
        raise SecretError(f"Could not store the password in the keyring: {exc}") from exc


def has_password(username: str) -> bool:
    if os.environ.get(ENV_VAR):
        return True
    try:
        return bool(_keyring().get_password(SERVICE_NAME, username))
    except Exception:
        return False
