"""
storage.py — Reading, writing, and exporting the vault.

The vault on disk is always encrypted (vault.dat + vault.salt).
Export supports two modes:
  - Encrypted export (.pvexport): a portable, still-encrypted copy of
    the vault, re-encryptable with a password you choose at export
    time (so you can share/back it up without reusing your main
    master password).
  - Plaintext export (.json / .csv): explicit, opt-in, clearly a
    security tradeoff — used for migrating to another tool. The UI
    warns loudly before doing this.
"""

from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from cryptography.fernet import Fernet

from .crypto import derive_key, generate_salt, make_fernet, decrypt_bytes, encrypt_bytes
from .models import normalize_entry

VAULT_FILENAME = "vault.dat"
SALT_FILENAME = "vault.salt"

EXPORT_FORMAT_VERSION = 1


@dataclass
class VaultPaths:
    directory: str

    @property
    def vault_file(self) -> str:
        return os.path.join(self.directory, VAULT_FILENAME)

    @property
    def salt_file(self) -> str:
        return os.path.join(self.directory, SALT_FILENAME)

    def exists(self) -> bool:
        return os.path.exists(self.vault_file)


def load_or_create_salt(paths: VaultPaths) -> bytes:
    if os.path.exists(paths.salt_file):
        with open(paths.salt_file, "rb") as f:
            return f.read()
    salt = generate_salt()
    with open(paths.salt_file, "wb") as f:
        f.write(salt)
    return salt


def load_vault(fernet: Fernet, paths: VaultPaths) -> list[dict[str, Any]]:
    """Load, decrypt, and normalize vault entries. Empty list if none yet."""
    if not paths.exists():
        return []
    with open(paths.vault_file, "rb") as f:
        encrypted = f.read()
    if not encrypted:
        return []
    decrypted = decrypt_bytes(fernet, encrypted)
    raw_entries = json.loads(decrypted.decode("utf-8"))
    return [normalize_entry(e) for e in raw_entries]


def save_vault(fernet: Fernet, paths: VaultPaths, entries: list[dict[str, Any]]) -> None:
    data = json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
    encrypted = encrypt_bytes(fernet, data)
    # Write atomically: write to a temp file then replace, so a crash
    # mid-write can never corrupt the real vault file.
    tmp_path = paths.vault_file + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(encrypted)
    os.replace(tmp_path, paths.vault_file)


# --------------------------------------------------------------------------
# Encrypted export / import (.pvexport)
# --------------------------------------------------------------------------

def export_encrypted(entries: list[dict[str, Any]], export_password: str, out_path: str) -> None:
    """
    Write a self-contained encrypted export file. It carries its own
    salt and can be decrypted with `export_password` alone (does not
    require the vault's own master password or salt file).
    """
    salt = generate_salt()
    fernet = make_fernet(export_password, salt)
    payload = {
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": time.time(),
        "entries": entries,
    }
    encrypted = encrypt_bytes(fernet, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    container = {
        "salt": salt.hex(),
        "data": encrypted.decode("ascii"),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(container, f, indent=2)


def import_encrypted(import_password: str, in_path: str) -> list[dict[str, Any]]:
    """Read back a file written by export_encrypted(). Raises WrongPasswordError on bad password."""
    with open(in_path, "r", encoding="utf-8") as f:
        container = json.load(f)

    salt = bytes.fromhex(container["salt"])
    fernet = make_fernet(import_password, salt)
    decrypted = decrypt_bytes(fernet, container["data"].encode("ascii"))
    payload = json.loads(decrypted.decode("utf-8"))
    return [normalize_entry(e) for e in payload.get("entries", [])]


# --------------------------------------------------------------------------
# Plaintext export / import (explicit opt-in, for migration only)
# --------------------------------------------------------------------------

PLAINTEXT_FIELDS = ["name", "username", "password", "url", "category", "tags", "notes"]


def export_plaintext_json(entries: list[dict[str, Any]], out_path: str) -> None:
    slim = [{k: e.get(k, "") for k in PLAINTEXT_FIELDS} for e in entries]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=2)


def export_plaintext_csv(entries: list[dict[str, Any]], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PLAINTEXT_FIELDS)
        writer.writeheader()
        for e in entries:
            row = {k: e.get(k, "") for k in PLAINTEXT_FIELDS}
            if isinstance(row.get("tags"), list):
                row["tags"] = ",".join(row["tags"])
            writer.writerow(row)


def import_plaintext_json(in_path: str) -> list[dict[str, Any]]:
    with open(in_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    result = []
    for item in raw:
        entry = normalize_entry({
            "name": item.get("name", "Untitled"),
            "username": item.get("username", ""),
            "password": item.get("password", ""),
            "url": item.get("url", ""),
            "category": item.get("category", "General"),
            "tags": item.get("tags", []) if isinstance(item.get("tags"), list) else [],
            "notes": item.get("notes", ""),
        })
        result.append(entry)
    return result


def import_plaintext_csv(in_path: str) -> list[dict[str, Any]]:
    result = []
    with open(in_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tags_raw = row.get("tags", "") or ""
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            entry = normalize_entry({
                "name": row.get("name") or "Untitled",
                "username": row.get("username", ""),
                "password": row.get("password", ""),
                "url": row.get("url", ""),
                "category": row.get("category") or "General",
                "tags": tags,
                "notes": row.get("notes", ""),
            })
            result.append(entry)
    return result
