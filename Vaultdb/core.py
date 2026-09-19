"""
VaultDB core: encrypted SQLite storage layer.

Container formats
-----------------
v2 (written by this version)
    MAGIC2(6) | N_LOG2(1) | R(1) | P(1) | SALT(16) | NONCE(12) | CIPHERTEXT+TAG
    - KDF:    scrypt (memory-hard), parameters stored in the header
    - Cipher: AES-256-GCM
    - The entire header (magic, params, salt) is bound to the ciphertext as
      associated data, so tampering with any header byte fails authentication.
    - A fresh random nonce is generated for every save.

v1 (read-only, for files made by earlier versions)
    MAGIC1(6) | SALT(16) | ITERATIONS(4) | FERNET_TOKEN
    - PBKDF2-HMAC-SHA256 + Fernet. Files are upgraded to v2 on the next save.

While a database is open, the plaintext SQLite image lives in memory only.
Plain (unencrypted) SQLite files are also supported.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import sqlite3
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC_V1 = b"VDB1\x00\x01"
MAGIC_V2 = b"VDB2\x00\x02"
SALT_LEN = 16
NONCE_LEN = 12

# scrypt defaults: N=2^17, r=8, p=1  ->  ~128 MiB memory, ~0.3 s on a modern CPU.
SCRYPT_N_LOG2 = 17
SCRYPT_R = 8
SCRYPT_P = 1
# Refuse absurd parameters from a hostile file (prevents memory-exhaustion DoS).
MAX_N_LOG2 = 20
MAX_R = 16
MAX_P = 4

SCHEMA = """
CREATE TABLE IF NOT EXISTS text_entries (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT NOT NULL,
    body      TEXT NOT NULL DEFAULT '',
    tags      TEXT NOT NULL DEFAULT '',
    created   REAL NOT NULL,
    modified  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS file_entries (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    mime      TEXT NOT NULL DEFAULT '',
    size      INTEGER NOT NULL,
    data      BLOB NOT NULL,
    tags      TEXT NOT NULL DEFAULT '',
    created   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS kv_entries (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    key       TEXT NOT NULL UNIQUE,
    value     TEXT NOT NULL DEFAULT '',
    created   REAL NOT NULL,
    modified  REAL NOT NULL
);
"""


class VaultError(Exception):
    """Base error for VaultDB."""


class WrongPasswordError(VaultError):
    """Raised when the password is wrong or the container is corrupted."""


class NotAVaultError(VaultError):
    """Raised when a file is not a VaultDB container."""


@dataclass
class KdfParams:
    n_log2: int = SCRYPT_N_LOG2
    r: int = SCRYPT_R
    p: int = SCRYPT_P


# ------------------------------------------------------------------ crypto
def _scrypt_key(password: str, salt: bytes, params: KdfParams) -> bytes:
    if not (10 <= params.n_log2 <= MAX_N_LOG2 and 1 <= params.r <= MAX_R
            and 1 <= params.p <= MAX_P):
        raise NotAVaultError("Unsupported or corrupted encryption parameters.")
    return Scrypt(salt=salt, length=32, n=1 << params.n_log2,
                  r=params.r, p=params.p).derive(password.encode("utf-8"))


def _v1_key(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=iterations)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _header_v2(params: KdfParams, salt: bytes) -> bytes:
    return MAGIC_V2 + bytes([params.n_log2, params.r, params.p]) + salt


def is_encrypted_container(path: str | Path) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(6)
        return head in (MAGIC_V1, MAGIC_V2)
    except OSError:
        return False


@dataclass
class Stats:
    texts: int
    files: int
    kvs: int
    total_file_bytes: int


class Vault:
    """An open database. Lives in memory; persisted via save()."""

    def __init__(self, path: Path, conn: sqlite3.Connection,
                 password: Optional[str], key: Optional[bytes],
                 salt: Optional[bytes], params: KdfParams):
        self.path = Path(path)
        self._conn = conn
        self._password = password
        self._key = key          # cached derived key: avoids re-running scrypt on every autosave
        self._salt = salt
        self._params = params
        self.upgraded_from_v1 = False  # set True by open() for legacy files

    # ------------------------------------------------------------ lifecycle
    @classmethod
    def create(cls, path: str | Path, password: Optional[str] = None,
               params: Optional[KdfParams] = None) -> "Vault":
        path = Path(path)
        if path.exists():
            raise VaultError(f"File already exists: {path}")
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA)
        conn.commit()
        params = params or KdfParams()
        salt = key = None
        if password:
            salt = os.urandom(SALT_LEN)
            key = _scrypt_key(password, salt, params)
        vault = cls(path, conn, password or None, key, salt, params)
        vault.save(backup=False)
        return vault

    @classmethod
    def open(cls, path: str | Path, password: Optional[str] = None) -> "Vault":
        path = Path(path)
        raw = path.read_bytes()

        if raw.startswith(MAGIC_V2):
            if not password:
                raise WrongPasswordError("Password required.")
            if len(raw) < 6 + 3 + SALT_LEN + NONCE_LEN + 16:
                raise NotAVaultError("File is truncated.")
            params = KdfParams(raw[6], raw[7], raw[8])
            salt = raw[9:9 + SALT_LEN]
            header_len = 9 + SALT_LEN
            header = raw[:header_len]
            nonce = raw[header_len:header_len + NONCE_LEN]
            body = raw[header_len + NONCE_LEN:]
            key = _scrypt_key(password, salt, params)
            try:
                plain = AESGCM(key).decrypt(nonce, body, header)
            except InvalidTag as exc:
                raise WrongPasswordError("Wrong password or corrupted file.") from exc
            conn = sqlite3.connect(":memory:")
            conn.deserialize(plain)
            return cls(path, conn, password, key, salt, params)

        if raw.startswith(MAGIC_V1):
            if not password:
                raise WrongPasswordError("Password required.")
            off = len(MAGIC_V1)
            salt1 = raw[off:off + SALT_LEN]
            off += SALT_LEN
            (iterations,) = struct.unpack(">I", raw[off:off + 4])
            off += 4
            if not (1000 <= iterations <= 10_000_000):
                raise NotAVaultError("Unsupported or corrupted encryption parameters.")
            try:
                plain = Fernet(_v1_key(password, salt1, iterations)).decrypt(raw[off:])
            except InvalidToken as exc:
                raise WrongPasswordError("Wrong password or corrupted file.") from exc
            conn = sqlite3.connect(":memory:")
            conn.deserialize(plain)
            # Upgrade: derive a fresh v2 key + salt now; the next save() writes v2.
            params = KdfParams()
            salt = os.urandom(SALT_LEN)
            v = cls(path, conn, password, _scrypt_key(password, salt, params), salt, params)
            v.upgraded_from_v1 = True
            return v

        if raw.startswith(b"SQLite format 3\x00"):
            conn = sqlite3.connect(":memory:")
            conn.deserialize(raw)
            conn.executescript(SCHEMA)
            return cls(path, conn, None, None, None, KdfParams())

        raise NotAVaultError("Not a VaultDB container or SQLite database.")

    @property
    def encrypted(self) -> bool:
        return self._password is not None

    def save(self, backup: bool = True) -> None:
        """Atomically write the database. The previous good copy is kept as <name>.bak."""
        self._conn.commit()
        plain = self._conn.serialize()
        if self._key is not None:
            header = _header_v2(self._params, self._salt)
            nonce = os.urandom(NONCE_LEN)            # never reuse a nonce with the same key
            blob = header + nonce + AESGCM(self._key).encrypt(nonce, plain, header)
        else:
            blob = plain

        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "wb") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())                     # ensure bytes hit the disk before the rename
        if backup and self.path.exists():
            try:
                shutil.copy2(self.path, self.path.with_name(self.path.name + ".bak"))
            except OSError:
                pass                                 # a failed backup must not block saving
        os.replace(tmp, self.path)

    def close(self) -> None:
        self._conn.close()
        self._key = None
        self._password = None

    # ------------------------------------------------------------ security
    def set_password(self, new_password: str,
                     params: Optional[KdfParams] = None) -> None:
        """Encrypt, or re-key with a fresh salt."""
        if not new_password:
            raise VaultError("Password must not be empty.")
        self._params = params or KdfParams()
        self._salt = os.urandom(SALT_LEN)
        self._key = _scrypt_key(new_password, self._salt, self._params)
        self._password = new_password
        self.save()

    def remove_password(self) -> None:
        self._password = self._key = self._salt = None
        self.save()

    def verify_password(self, password: str) -> bool:
        if self._password is None:
            return False
        import hmac
        return hmac.compare_digest(password.encode("utf-8"), self._password.encode("utf-8"))

    # ------------------------------------------------------------ text CRUD
    def add_text(self, title: str, body: str, tags: str = "") -> int:
        now = time.time()
        cur = self._conn.execute(
            "INSERT INTO text_entries(title, body, tags, created, modified) "
            "VALUES (?,?,?,?,?)", (title, body, tags, now, now))
        self._conn.commit()
        return cur.lastrowid

    def update_text(self, entry_id: int, title: str, body: str, tags: str) -> None:
        self._conn.execute(
            "UPDATE text_entries SET title=?, body=?, tags=?, modified=? WHERE id=?",
            (title, body, tags, time.time(), entry_id))
        self._conn.commit()

    def delete_text(self, entry_id: int) -> None:
        self._conn.execute("DELETE FROM text_entries WHERE id=?", (entry_id,))
        self._conn.commit()

    def get_text(self, entry_id: int):
        return self._conn.execute(
            "SELECT id,title,body,tags,created,modified FROM text_entries WHERE id=?",
            (entry_id,)).fetchone()

    @staticmethod
    def _like(query: str) -> str:
        """Escape LIKE wildcards so searching for '%' or '_' matches literally."""
        q = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return f"%{q}%"

    def list_texts(self, query: str = ""):
        like = self._like(query)
        return self._conn.execute(
            "SELECT id,title,tags,modified FROM text_entries "
            "WHERE title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\' "
            "ORDER BY modified DESC", (like, like, like)).fetchall()

    # ------------------------------------------------------------ file CRUD
    def add_file(self, filepath: str | Path, tags: str = "") -> int:
        import mimetypes
        p = Path(filepath)
        data = p.read_bytes()
        mime = mimetypes.guess_type(p.name)[0] or ""
        cur = self._conn.execute(
            "INSERT INTO file_entries(name, mime, size, data, tags, created) "
            "VALUES (?,?,?,?,?,?)",
            (p.name, mime, len(data), data, tags, time.time()))
        self._conn.commit()
        return cur.lastrowid

    def export_file(self, entry_id: int, dest: str | Path) -> None:
        row = self._conn.execute(
            "SELECT data FROM file_entries WHERE id=?", (entry_id,)).fetchone()
        if row is None:
            raise VaultError("File entry not found.")
        Path(dest).write_bytes(row[0])

    def delete_file(self, entry_id: int) -> None:
        self._conn.execute("DELETE FROM file_entries WHERE id=?", (entry_id,))
        self._conn.commit()

    def list_files(self, query: str = ""):
        like = self._like(query)
        return self._conn.execute(
            "SELECT id,name,mime,size,tags,created FROM file_entries "
            "WHERE name LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\' ORDER BY created DESC",
            (like, like)).fetchall()

    # ------------------------------------------------------------ key/value
    def set_kv(self, key: str, value: str) -> None:
        now = time.time()
        self._conn.execute(
            "INSERT INTO kv_entries(key,value,created,modified) VALUES (?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, modified=excluded.modified",
            (key, value, now, now))
        self._conn.commit()

    def delete_kv(self, key: str) -> None:
        self._conn.execute("DELETE FROM kv_entries WHERE key=?", (key,))
        self._conn.commit()

    def list_kv(self, query: str = ""):
        like = self._like(query)
        return self._conn.execute(
            "SELECT key,value,modified FROM kv_entries "
            "WHERE key LIKE ? ESCAPE '\\' OR value LIKE ? ESCAPE '\\' ORDER BY key",
            (like, like)).fetchall()

    # ------------------------------------------------------------ JSON export / import
    def export_json(self, dest: str | Path, include_files: bool = True) -> None:
        """Write a readable, UNENCRYPTED JSON backup. The caller must warn the user."""
        c = self._conn
        data = {
            "format": "vaultdb-export",
            "version": 1,
            "exported": time.time(),
            "notes": [
                {"title": t, "body": b, "tags": g, "created": cr, "modified": m}
                for t, b, g, cr, m in c.execute(
                    "SELECT title,body,tags,created,modified FROM text_entries ORDER BY id")],
            "data": [
                {"name": k, "value": v, "modified": m}
                for k, v, m in c.execute("SELECT key,value,modified FROM kv_entries ORDER BY key")],
            "files": [],
        }
        if include_files:
            for n, mime, size, blob, tags, cr in c.execute(
                    "SELECT name,mime,size,data,tags,created FROM file_entries ORDER BY id"):
                data["files"].append({
                    "name": n, "mime": mime, "size": size, "tags": tags, "created": cr,
                    "data_base64": base64.b64encode(blob).decode("ascii")})
        Path(dest).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_json(self, src: str | Path) -> dict:
        """Merge a VaultDB JSON export into this database. Returns counts added."""
        try:
            data = json.loads(Path(src).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise VaultError(f"Could not read the file: {exc}") from exc
        if not isinstance(data, dict) or data.get("format") != "vaultdb-export":
            raise VaultError("This is not a VaultDB export file.")

        counts = {"notes": 0, "data": 0, "files": 0}
        now = time.time()
        try:
            for n in data.get("notes", []):
                self._conn.execute(
                    "INSERT INTO text_entries(title,body,tags,created,modified) VALUES (?,?,?,?,?)",
                    (str(n.get("title", "")), str(n.get("body", "")), str(n.get("tags", "")),
                     float(n.get("created", now)), float(n.get("modified", now))))
                counts["notes"] += 1
            for d in data.get("data", []):
                k = str(d.get("name", "")).strip()
                if k:
                    self.set_kv(k, str(d.get("value", "")))
                    counts["data"] += 1
            for f in data.get("files", []):
                blob = base64.b64decode(f.get("data_base64", ""), validate=True)
                self._conn.execute(
                    "INSERT INTO file_entries(name,mime,size,data,tags,created) VALUES (?,?,?,?,?,?)",
                    (str(f.get("name", "file")), str(f.get("mime", "")), len(blob), blob,
                     str(f.get("tags", "")), float(f.get("created", now))))
                counts["files"] += 1
            self._conn.commit()
        except (ValueError, TypeError) as exc:
            self._conn.rollback()
            raise VaultError(f"The export file is damaged: {exc}") from exc
        return counts

    # ------------------------------------------------------------ misc
    def stats(self) -> Stats:
        c = self._conn
        return Stats(
            texts=c.execute("SELECT COUNT(*) FROM text_entries").fetchone()[0],
            files=c.execute("SELECT COUNT(*) FROM file_entries").fetchone()[0],
            kvs=c.execute("SELECT COUNT(*) FROM kv_entries").fetchone()[0],
            total_file_bytes=c.execute(
                "SELECT COALESCE(SUM(size),0) FROM file_entries").fetchone()[0],
        )
