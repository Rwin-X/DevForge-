"""
HashForge — Local history manager (JSON-backed, no external DB).
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from hashforge.core.hasher import HashResult, FileInfo


HISTORY_FILE = Path.home() / ".hashforge" / "history.json"
MAX_ENTRIES = 500


class HistoryManager:
    def __init__(self, path: Path = HISTORY_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[dict] = self._load()

    # ------------------------------------------------------------------ IO --
    def _load(self) -> List[dict]:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._entries[-MAX_ENTRIES:], f, indent=2, ensure_ascii=False)

    # --------------------------------------------------------------- Public --
    def add(self, result: HashResult):
        entry = result.to_dict()
        self._entries.append(entry)
        self._save()

    def all(self) -> List[dict]:
        return list(reversed(self._entries))

    def search(self, query: str) -> List[dict]:
        q = query.lower()
        return [
            e for e in reversed(self._entries)
            if q in e["file"]["name"].lower()
            or q in e["file"]["path"].lower()
            or any(q in v.lower() for v in e["hashes"].values())
        ]

    def clear(self):
        self._entries.clear()
        self._save()

    def remove(self, index: int):
        """Remove by reverse index (0 = newest)."""
        real = len(self._entries) - 1 - index
        if 0 <= real < len(self._entries):
            self._entries.pop(real)
            self._save()

    def count(self) -> int:
        return len(self._entries)
