"""
note_store.py

Handles all filesystem interaction for Local AI Notes.
Notes are plain .md files living in one folder chosen by the user.
There is no database, no cache file, and no hidden state written to disk
other than the .md files themselves -- the folder is the single source
of truth, exactly like a plain-text notes app should behave.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# A note's "id" is just its filename without the .md extension.
# Wiki links use this same id: [[My Note]] -> My Note.md
NOTE_EXTENSION = ".md"

# Matches [[Note Name]] or [[Note Name|Display Text]]
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]+)?\]\]")


def sanitize_filename(name: str) -> str:
    """Turn a note title into a safe filename (without extension)."""
    name = name.strip()
    # Remove characters that are illegal or awkward in filenames on
    # Windows/macOS/Linux.
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = re.sub(r"\s+", " ", name)
    return name or "Untitled"


@dataclass
class Note:
    """In-memory representation of a single note."""

    note_id: str  # filename without extension, also the wiki-link target
    path: str
    content: str = ""
    modified: float = 0.0
    links_out: list[str] = field(default_factory=list)  # note_ids this note links to
    links_in: list[str] = field(default_factory=list)  # note_ids that link to this note (backlinks)

    @property
    def title(self) -> str:
        return self.note_id


class NoteStore:
    """
    Owns a single folder of .md files.

    Responsibilities:
      - list notes on disk
      - read / write note content
      - parse [[wiki links]] and maintain backlinks
      - create / rename / delete notes
    """

    def __init__(self, folder: str):
        self.folder = folder
        self.notes: dict[str, Note] = {}

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #

    def load_all(self) -> None:
        """Scan the folder and (re)build the in-memory note index."""
        self.notes.clear()
        if not os.path.isdir(self.folder):
            return

        for filename in os.listdir(self.folder):
            if not filename.lower().endswith(NOTE_EXTENSION):
                continue
            path = os.path.join(self.folder, filename)
            if not os.path.isfile(path):
                continue
            note_id = filename[: -len(NOTE_EXTENSION)]
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            mtime = os.path.getmtime(path)
            self.notes[note_id] = Note(
                note_id=note_id, path=path, content=content, modified=mtime
            )

        self._rebuild_links()

    def _rebuild_links(self) -> None:
        """Recompute outbound links and backlinks for every note."""
        for note in self.notes.values():
            note.links_out = self._extract_links(note.content)
            note.links_in = []

        for note in self.notes.values():
            for target_id in note.links_out:
                target = self.notes.get(target_id)
                if target is not None and note.note_id not in target.links_in:
                    target.links_in.append(note.note_id)

    @staticmethod
    def _extract_links(content: str) -> list[str]:
        """Return the list of note_ids referenced via [[Wiki Links]]."""
        seen: list[str] = []
        for match in WIKILINK_PATTERN.finditer(content):
            target = match.group(1).strip()
            if target and target not in seen:
                seen.append(target)
        return seen

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #

    def create_note(self, title: str, content: str = "") -> Note:
        note_id = sanitize_filename(title)
        base_id = note_id
        counter = 2
        while note_id in self.notes:
            note_id = f"{base_id} {counter}"
            counter += 1

        path = os.path.join(self.folder, note_id + NOTE_EXTENSION)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        note = Note(note_id=note_id, path=path, content=content, modified=os.path.getmtime(path))
        self.notes[note_id] = note
        self._rebuild_links()
        return note

    def save_note(self, note_id: str, content: str) -> None:
        """Write content to disk immediately (used for auto-save)."""
        note = self.notes.get(note_id)
        if note is None:
            return
        with open(note.path, "w", encoding="utf-8") as f:
            f.write(content)
        note.content = content
        note.modified = os.path.getmtime(note.path)
        self._rebuild_links()

    def rename_note(self, note_id: str, new_title: str) -> Optional[Note]:
        note = self.notes.get(note_id)
        if note is None:
            return None

        new_id = sanitize_filename(new_title)
        if new_id == note_id:
            return note
        if new_id in self.notes:
            return None  # name collision; caller should show an error

        new_path = os.path.join(self.folder, new_id + NOTE_EXTENSION)
        os.rename(note.path, new_path)

        old_id = note.note_id
        note.note_id = new_id
        note.path = new_path
        del self.notes[old_id]
        self.notes[new_id] = note

        # Update any [[old links]] elsewhere in the vault to point at the new title.
        self._rewrite_links_after_rename(old_id, new_id)
        self._rebuild_links()
        return note

    def _rewrite_links_after_rename(self, old_id: str, new_id: str) -> None:
        pattern = re.compile(
            r"\[\[" + re.escape(old_id) + r"(#[^\]|]*)?(\|[^\]]+)?\]\]"
        )

        def replacement(m: re.Match) -> str:
            anchor = m.group(1) or ""
            alias = m.group(2) or ""
            return f"[[{new_id}{anchor}{alias}]]"

        for note in self.notes.values():
            if pattern.search(note.content):
                new_content = pattern.sub(replacement, note.content)
                note.content = new_content
                with open(note.path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                note.modified = os.path.getmtime(note.path)

    def delete_note(self, note_id: str) -> None:
        note = self.notes.get(note_id)
        if note is None:
            return
        try:
            os.remove(note.path)
        except OSError:
            pass
        del self.notes[note_id]
        self._rebuild_links()

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def get(self, note_id: str) -> Optional[Note]:
        return self.notes.get(note_id)

    def all_notes(self) -> list[Note]:
        return sorted(self.notes.values(), key=lambda n: n.note_id.lower())

    def search(self, query: str) -> list[Note]:
        query = query.strip().lower()
        if not query:
            return self.all_notes()
        results = []
        for note in self.notes.values():
            if query in note.note_id.lower() or query in note.content.lower():
                results.append(note)
        return sorted(results, key=lambda n: n.note_id.lower())

    def note_exists(self, note_id: str) -> bool:
        return note_id in self.notes

    def graph_edges(self) -> list[tuple[str, str]]:
        """Return (source_id, target_id) pairs for every valid wiki link."""
        edges = []
        for note in self.notes.values():
            for target_id in note.links_out:
                if target_id in self.notes:
                    edges.append((note.note_id, target_id))
        return edges
