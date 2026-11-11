"""SQLite persistence: scanned messages and a reversible action log."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    account TEXT NOT NULL,
    folder TEXT NOT NULL,
    uidvalidity INTEGER NOT NULL,
    uid INTEGER NOT NULL,
    message_id TEXT NOT NULL DEFAULT '',
    sender TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    date_utc TEXT NOT NULL DEFAULT '',
    ad_score REAL NOT NULL DEFAULT 0,
    ai_score REAL NOT NULL DEFAULT 0,
    category TEXT NOT NULL DEFAULT '',
    score REAL NOT NULL DEFAULT 0,
    reasons TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    scanned_at TEXT NOT NULL,
    PRIMARY KEY (account, folder, uidvalidity, uid)
);
CREATE INDEX IF NOT EXISTS items_status ON items (account, status);
CREATE INDEX IF NOT EXISTS items_msgid ON items (account, message_id);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    account TEXT NOT NULL,
    kind TEXT NOT NULL,
    folder TEXT NOT NULL DEFAULT '',
    message_id TEXT NOT NULL DEFAULT '',
    sender TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    score REAL NOT NULL DEFAULT 0,
    undone INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS actions_account ON actions (account, id DESC);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ItemRecord:
    account: str
    folder: str
    uidvalidity: int
    uid: int
    message_id: str
    sender: str
    subject: str
    date_utc: str
    ad_score: float
    ai_score: float
    category: str
    score: float
    reasons: list[str]
    status: str  # kept | review | trashed | restored


class Store:
    """Each call opens its own connection, so it is safe to use from any thread."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            if self.path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- items -------------------------------------------------------

    def processed_uids(self, account: str, folder: str, uidvalidity: int) -> set[int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT uid FROM items WHERE account=? AND folder=? AND uidvalidity=?",
                (account, folder, uidvalidity),
            ).fetchall()
        return {row["uid"] for row in rows}

    def record_item(self, rec: ItemRecord) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO items (account, folder, uidvalidity, uid, message_id, "
                "sender, subject, date_utc, ad_score, ai_score, category, score, reasons, "
                "status, scanned_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rec.account, rec.folder, rec.uidvalidity, rec.uid, rec.message_id,
                    rec.sender, rec.subject, rec.date_utc, rec.ad_score, rec.ai_score,
                    rec.category, rec.score, json.dumps(rec.reasons), rec.status, utc_now(),
                ),
            )

    def set_item_status(self, account: str, folder: str, uidvalidity: int, uid: int, status: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE items SET status=? WHERE account=? AND folder=? AND uidvalidity=? AND uid=?",
                (status, account, folder, uidvalidity, uid),
            )

    def set_status_by_message_id(self, account: str, message_id: str, status: str) -> None:
        if not message_id:
            return
        with self._conn() as conn:
            conn.execute(
                "UPDATE items SET status=? WHERE account=? AND message_id=?",
                (status, account, message_id),
            )

    def review_items(self, account: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM items WHERE account=? AND status='review' ORDER BY date_utc DESC",
                (account,),
            ).fetchall()
        return [self._item_dict(row) for row in rows]

    def recent_items(self, account: str, limit: int = 60) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM items WHERE account=? ORDER BY scanned_at DESC, rowid DESC LIMIT ?",
                (account, limit),
            ).fetchall()
        return [self._item_dict(row) for row in rows]

    def verdicts(self, account: str, folder: str, uidvalidity: int, uids: list[int]) -> dict[int, dict]:
        if not uids:
            return {}
        found: dict[int, dict] = {}
        with self._conn() as conn:
            for start in range(0, len(uids), 500):
                chunk = uids[start : start + 500]
                marks = ",".join("?" * len(chunk))
                rows = conn.execute(
                    f"SELECT * FROM items WHERE account=? AND folder=? AND uidvalidity=? "
                    f"AND uid IN ({marks})",
                    (account, folder, uidvalidity, *chunk),
                ).fetchall()
                for row in rows:
                    found[row["uid"]] = self._item_dict(row)
        return found

    def stats(self, account: str) -> dict[str, int]:
        with self._conn() as conn:
            def count(where: str, *args) -> int:
                row = conn.execute(
                    f"SELECT COUNT(*) AS n FROM items WHERE account=? AND {where}", (account, *args)
                ).fetchone()
                return int(row["n"])

            return {
                "scanned": count("1=1"),
                "ads_trashed": count("status='trashed' AND category='ad'"),
                "ai_trashed": count("status='trashed' AND category='ai'"),
                "review": count("status='review'"),
                "kept": count("status='kept'"),
            }

    @staticmethod
    def _item_dict(row: sqlite3.Row) -> dict:
        data = dict(row)
        try:
            data["reasons"] = json.loads(data.get("reasons") or "[]")
        except ValueError:
            data["reasons"] = []
        return data

    # ---- actions -----------------------------------------------------

    def log_action(
        self, account: str, kind: str, folder: str, message_id: str, sender: str,
        subject: str, category: str = "", score: float = 0.0,
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO actions (ts, account, kind, folder, message_id, sender, subject, "
                "category, score) VALUES (?,?,?,?,?,?,?,?,?)",
                (utc_now(), account, kind, folder, message_id, sender, subject, category, score),
            )
            return int(cur.lastrowid)

    def recent_actions(self, account: str, limit: int = 300) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM actions WHERE account=? ORDER BY id DESC LIMIT ?", (account, limit)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_action(self, action_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
        return dict(row) if row else None

    def mark_undone(self, action_id: int) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE actions SET undone=1 WHERE id=?", (action_id,))
