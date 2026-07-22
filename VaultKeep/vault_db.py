
"""
vault_db.py

SQLite-backed encrypted vault storage.

Every column that could reveal something about a credential (title,
username, password, url, notes) is stored ONLY as AES-256-GCM
ciphertext + its nonce. The database file, if stolen, reveals nothing
but opaque blobs, entry count, and timestamps.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field

import crypto_core as cc

SCHEMA = """
CREATE TABLE IF NOT EXISTS vault_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    kdf_salt BLOB NOT NULL,
    verifier_nonce BLOB NOT NULL,
    verifier_ct BLOB NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_nonce BLOB NOT NULL,
    title_ct BLOB NOT NULL,
    username_nonce BLOB NOT NULL,
    username_ct BLOB NOT NULL,
    password_nonce BLOB NOT NULL,
    password_ct BLOB NOT NULL,
    url_nonce BLOB NOT NULL,
    url_ct BLOB NOT NULL,
    notes_nonce BLOB NOT NULL,
    notes_ct BLOB NOT NULL,
    tags_nonce BLOB NOT NULL,
    tags_ct BLOB NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS password_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    password_nonce BLOB NOT NULL,
    password_ct BLOB NOT NULL,
    changed_at REAL NOT NULL,
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);
"""


@dataclass
class Entry:
    id: int | None
    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""
    tags: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class VaultDB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---- vault metadata -------------------------------------------------

    def is_initialized(self) -> bool:
        cur = self.conn.execute("SELECT 1 FROM vault_meta WHERE id = 1")
        return cur.fetchone() is not None

    def init_vault(self, master_password: str) -> bytes:
        """First-time setup: derive key, store salt + verifier. Returns key."""
        salt = cc.new_salt()
        key = cc.derive_key(master_password, salt)
        v_nonce, v_ct = cc.make_verifier(key)
        self.conn.execute(
            "INSERT INTO vault_meta (id, kdf_salt, verifier_nonce, verifier_ct, created_at) "
            "VALUES (1, ?, ?, ?, ?)",
            (salt, v_nonce, v_ct, time.time()),
        )
        self.conn.commit()
        return key

    def unlock(self, master_password: str) -> bytes | None:
        """Attempt to unlock. Returns derived key on success, None on wrong password."""
        row = self.conn.execute(
            "SELECT kdf_salt, verifier_nonce, verifier_ct FROM vault_meta WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        salt, v_nonce, v_ct = row
        key = cc.derive_key(master_password, salt)
        if cc.check_verifier(key, v_nonce, v_ct):
            return key
        return None

    def change_master_password(self, key: bytes, new_master_password: str) -> bytes:
        """Re-encrypts every entry under a freshly derived key. Returns new key."""
        new_salt = cc.new_salt()
        new_key = cc.derive_key(new_master_password, new_salt)

        entries = self.list_entries(key)
        for e in entries:
            self._save_entry_fields(e.id, new_key, e)

        v_nonce, v_ct = cc.make_verifier(new_key)
        self.conn.execute(
            "UPDATE vault_meta SET kdf_salt = ?, verifier_nonce = ?, verifier_ct = ? WHERE id = 1",
            (new_salt, v_nonce, v_ct),
        )
        self.conn.commit()
        return new_key

    # ---- entries ----------------------------------------------------------

    def _enc(self, key: bytes, value: str) -> tuple[bytes, bytes]:
        return cc.encrypt(key, value.encode("utf-8"))

    def _dec(self, key: bytes, nonce: bytes, ct: bytes) -> str:
        return cc.decrypt(key, nonce, ct).decode("utf-8")

    def add_entry(self, key: bytes, e: Entry) -> int:
        now = time.time()
        t_n, t_c = self._enc(key, e.title)
        u_n, u_c = self._enc(key, e.username)
        p_n, p_c = self._enc(key, e.password)
        url_n, url_c = self._enc(key, e.url)
        notes_n, notes_c = self._enc(key, e.notes)
        tags_n, tags_c = self._enc(key, e.tags)
        cur = self.conn.execute(
            "INSERT INTO entries (title_nonce, title_ct, username_nonce, username_ct, "
            "password_nonce, password_ct, url_nonce, url_ct, notes_nonce, notes_ct, "
            "tags_nonce, tags_ct, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (t_n, t_c, u_n, u_c, p_n, p_c, url_n, url_c, notes_n, notes_c,
             tags_n, tags_c, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def _save_entry_fields(self, entry_id: int, key: bytes, e: Entry) -> None:
        """Re-encrypt and overwrite all fields for entry_id under `key`."""
        now = time.time()
        t_n, t_c = self._enc(key, e.title)
        u_n, u_c = self._enc(key, e.username)
        p_n, p_c = self._enc(key, e.password)
        url_n, url_c = self._enc(key, e.url)
        notes_n, notes_c = self._enc(key, e.notes)
        tags_n, tags_c = self._enc(key, e.tags)
        self.conn.execute(
            "UPDATE entries SET title_nonce=?, title_ct=?, username_nonce=?, username_ct=?, "
            "password_nonce=?, password_ct=?, url_nonce=?, url_ct=?, notes_nonce=?, notes_ct=?, "
            "tags_nonce=?, tags_ct=?, updated_at=? WHERE id=?",
            (t_n, t_c, u_n, u_c, p_n, p_c, url_n, url_c, notes_n, notes_c,
             tags_n, tags_c, now, entry_id),
        )
        self.conn.commit()

    def update_entry(self, key: bytes, e: Entry, keep_history: bool = True) -> None:
        if keep_history and e.id is not None:
            old = self.get_entry(key, e.id)
            if old is not None and old.password != e.password:
                p_n, p_c = self._enc(key, old.password)
                self.conn.execute(
                    "INSERT INTO password_history (entry_id, password_nonce, password_ct, changed_at) "
                    "VALUES (?,?,?,?)",
                    (e.id, p_n, p_c, time.time()),
                )
        self._save_entry_fields(e.id, key, e)

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()

    def get_entry(self, key: bytes, entry_id: int) -> Entry | None:
        row = self.conn.execute(
            "SELECT id, title_nonce, title_ct, username_nonce, username_ct, "
            "password_nonce, password_ct, url_nonce, url_ct, notes_nonce, notes_ct, "
            "tags_nonce, tags_ct, created_at, updated_at FROM entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(key, row)

    def _row_to_entry(self, key: bytes, row) -> Entry:
        (eid, tn, tc, un, uc, pn, pc, urln, urlc, notn, notc, tagn, tagc, cat, uat) = row
        return Entry(
            id=eid,
            title=self._dec(key, tn, tc),
            username=self._dec(key, un, uc),
            password=self._dec(key, pn, pc),
            url=self._dec(key, urln, urlc),
            notes=self._dec(key, notn, notc),
            tags=self._dec(key, tagn, tagc),
            created_at=cat,
            updated_at=uat,
        )

    def list_entries(self, key: bytes) -> list[Entry]:
        rows = self.conn.execute(
            "SELECT id, title_nonce, title_ct, username_nonce, username_ct, "
            "password_nonce, password_ct, url_nonce, url_ct, notes_nonce, notes_ct, "
            "tags_nonce, tags_ct, created_at, updated_at FROM entries ORDER BY updated_at DESC"
        ).fetchall()
        return [self._row_to_entry(key, r) for r in rows]

    def entry_count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM entries")
        return cur.fetchone()[0]

    def get_history(self, key: bytes, entry_id: int) -> list[tuple[str, float]]:
        rows = self.conn.execute(
            "SELECT password_nonce, password_ct, changed_at FROM password_history "
            "WHERE entry_id = ? ORDER BY changed_at DESC",
            (entry_id,),
        ).fetchall()
        return [(self._dec(key, n, c), t) for n, c, t in rows]

    def close(self) -> None:
        self.conn.close()
