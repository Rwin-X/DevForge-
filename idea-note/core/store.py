"""
store.py — SQLite persistence layer for Idea Book.

Local-only. No cloud, no login, no telemetry. One .db file on disk.
Notes are markdown+. Links between notes are parsed from [[wikilink]]
syntax and cached in a separate table so graph queries stay O(1)
instead of re-parsing every note's body on every graph render.
"""

import sqlite3
import re
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
TAG_RE = re.compile(r"(?<!\w)#([a-zA-Z0-9_\-/]+)")

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL UNIQUE,
    body        TEXT NOT NULL DEFAULT '',
    folder      TEXT NOT NULL DEFAULT '',
    pinned      INTEGER NOT NULL DEFAULT 0,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS links (
    src_id      INTEGER NOT NULL,
    dst_title   TEXT NOT NULL,
    FOREIGN KEY (src_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    note_id     INTEGER NOT NULL,
    tag         TEXT NOT NULL,
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_links_src ON links(src_id);
CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst_title);
CREATE INDEX IF NOT EXISTS idx_tags_note ON tags(note_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""


@dataclass
class Note:
    id: int
    title: str
    body: str
    folder: str
    pinned: bool
    created_at: float
    updated_at: float


class Store:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- CRUD ----------

    def create_note(self, title: str, body: str = "", folder: str = "") -> Note:
        now = time.time()
        cur = self.conn.execute(
            "INSERT INTO notes (title, body, folder, pinned, created_at, updated_at) "
            "VALUES (?, ?, ?, 0, ?, ?)",
            (title, body, folder, now, now),
        )
        self.conn.commit()
        note = self.get_note(cur.lastrowid)
        self._reindex_links(note)
        return note

    def get_note(self, note_id: int) -> Optional[Note]:
        row = self.conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        return self._row_to_note(row) if row else None

    def get_note_by_title(self, title: str) -> Optional[Note]:
        row = self.conn.execute("SELECT * FROM notes WHERE title=?", (title,)).fetchone()
        return self._row_to_note(row) if row else None

    def list_notes(self, folder: Optional[str] = None) -> list[Note]:
        if folder is not None:
            rows = self.conn.execute(
                "SELECT * FROM notes WHERE folder=? ORDER BY pinned DESC, updated_at DESC",
                (folder,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM notes ORDER BY pinned DESC, updated_at DESC"
            ).fetchall()
        return [self._row_to_note(r) for r in rows]

    def search_notes(self, query: str) -> list[Note]:
        q = f"%{query}%"
        rows = self.conn.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR body LIKE ? "
            "ORDER BY pinned DESC, updated_at DESC",
            (q, q),
        ).fetchall()
        return [self._row_to_note(r) for r in rows]

    def update_note(self, note_id: int, title: str = None, body: str = None,
                     folder: str = None, pinned: bool = None) -> Note:
        note = self.get_note(note_id)
        if note is None:
            raise ValueError(f"No note with id {note_id}")
        new_title = title if title is not None else note.title
        new_body = body if body is not None else note.body
        new_folder = folder if folder is not None else note.folder
        new_pinned = int(pinned) if pinned is not None else int(note.pinned)
        self.conn.execute(
            "UPDATE notes SET title=?, body=?, folder=?, pinned=?, updated_at=? WHERE id=?",
            (new_title, new_body, new_folder, new_pinned, time.time(), note_id),
        )
        self.conn.commit()
        updated = self.get_note(note_id)
        self._reindex_links(updated)
        return updated

    def delete_note(self, note_id: int):
        self.conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self.conn.commit()

    def rename_folder(self, old: str, new: str):
        self.conn.execute("UPDATE notes SET folder=? WHERE folder=?", (new, old))
        self.conn.commit()

    def list_folders(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT folder FROM notes WHERE folder != '' ORDER BY folder"
        ).fetchall()
        return [r["folder"] for r in rows]

    # ---------- links / graph ----------

    def _reindex_links(self, note: Note):
        """Re-parse [[links]] and #tags from a note's body and refresh cache tables."""
        self.conn.execute("DELETE FROM links WHERE src_id=?", (note.id,))
        self.conn.execute("DELETE FROM tags WHERE note_id=?", (note.id,))
        for m in WIKILINK_RE.finditer(note.body):
            dst = m.group(1).strip()
            if dst:
                self.conn.execute(
                    "INSERT INTO links (src_id, dst_title) VALUES (?, ?)",
                    (note.id, dst),
                )
        for m in TAG_RE.finditer(note.body):
            self.conn.execute(
                "INSERT INTO tags (note_id, tag) VALUES (?, ?)",
                (note.id, m.group(1)),
            )
        self.conn.commit()

    def backlinks(self, title: str) -> list[Note]:
        rows = self.conn.execute(
            "SELECT n.* FROM notes n JOIN links l ON n.id = l.src_id "
            "WHERE l.dst_title = ? ORDER BY n.title",
            (title,),
        ).fetchall()
        return [self._row_to_note(r) for r in rows]

    def graph_data(self) -> tuple[list[dict], list[dict]]:
        """
        Returns (nodes, edges) for the whole vault.
        nodes: [{id, title, folder, degree, pinned}]
        edges: [{src, dst}]  (both are note ids; dangling links to
                               non-existent notes are dropped from edges
                               but the target still isn't fabricated)
        """
        notes = self.list_notes()
        title_to_id = {n.title: n.id for n in notes}
        degree = {n.id: 0 for n in notes}

        edges = []
        rows = self.conn.execute("SELECT src_id, dst_title FROM links").fetchall()
        for r in rows:
            dst_id = title_to_id.get(r["dst_title"])
            if dst_id is not None and dst_id != r["src_id"]:
                edges.append({"src": r["src_id"], "dst": dst_id})
                degree[r["src_id"]] = degree.get(r["src_id"], 0) + 1
                degree[dst_id] = degree.get(dst_id, 0) + 1

        nodes = [
            {
                "id": n.id,
                "title": n.title,
                "folder": n.folder,
                "degree": degree.get(n.id, 0),
                "pinned": n.pinned,
            }
            for n in notes
        ]
        return nodes, edges

    def all_tags(self) -> list[str]:
        rows = self.conn.execute("SELECT DISTINCT tag FROM tags ORDER BY tag").fetchall()
        return [r["tag"] for r in rows]

    # ---------- helpers ----------

    def _row_to_note(self, row) -> Note:
        return Note(
            id=row["id"],
            title=row["title"],
            body=row["body"],
            folder=row["folder"],
            pinned=bool(row["pinned"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def close(self):
        self.conn.close()
