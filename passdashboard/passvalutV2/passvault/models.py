"""
models.py — Data model for a single vault entry.

Each entry is a plain dict under the hood (so it stays trivially
JSON-serializable for encryption), but this module centralizes the
shape of that dict and provides small helper functions so the rest of
the codebase doesn't sprinkle raw dict keys everywhere.
"""

from __future__ import annotations

import secrets
import time
from typing import Any, Optional

# Built-in category suggestions. Users can also type a custom category.
DEFAULT_CATEGORIES = [
    "General",
    "Personal",
    "Work",
    "Banking",
    "Social",
    "Shopping",
    "Email",
    "Servers / Dev",
]


def new_entry(
    name: str,
    username: str = "",
    password: str = "",
    url: str = "",
    notes: str = "",
    category: str = "General",
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Build a brand-new entry dict with a fresh id and timestamps."""
    now = time.time()
    return {
        "id": secrets.token_hex(8),
        "name": name,
        "username": username,
        "password": password,
        "url": url,
        "notes": notes,
        "category": category or "General",
        "tags": tags or [],
        "created": now,
        "updated": now,
        "history": [],  # list of {"password": ..., "changed": timestamp}
    }


def update_entry(entry: dict[str, Any], **changes: Any) -> dict[str, Any]:
    """
    Return a new entry dict with the given fields changed.

    If the password is changed, the previous password is pushed onto
    the entry's history so old passwords remain recoverable/visible.
    """
    updated = dict(entry)
    old_password = entry.get("password", "")
    new_password = changes.get("password", old_password)

    if new_password != old_password:
        history = list(entry.get("history", []))
        history.append({"password": old_password, "changed": entry.get("updated", time.time())})
        updated["history"] = history

    updated.update(changes)
    updated["updated"] = time.time()
    # Ensure required fields always exist even for entries created by
    # older versions of the app.
    updated.setdefault("category", "General")
    updated.setdefault("tags", [])
    updated.setdefault("history", [])
    return updated


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Backfill missing fields on entries loaded from older vault versions,
    so the rest of the app can assume every entry has every key.
    """
    entry = dict(entry)
    entry.setdefault("id", secrets.token_hex(8))
    entry.setdefault("username", "")
    entry.setdefault("password", "")
    entry.setdefault("url", "")
    entry.setdefault("notes", "")
    entry.setdefault("category", "General")
    entry.setdefault("tags", [])
    entry.setdefault("created", time.time())
    entry.setdefault("updated", time.time())
    entry.setdefault("history", [])
    return entry


def all_categories(entries: list[dict[str, Any]]) -> list[str]:
    """Return the sorted union of default categories and any in use."""
    used = {e.get("category", "General") for e in entries}
    combined = set(DEFAULT_CATEGORIES) | used
    return sorted(combined)


def all_tags(entries: list[dict[str, Any]]) -> list[str]:
    """Return the sorted union of every tag currently in use."""
    tags: set[str] = set()
    for e in entries:
        tags.update(e.get("tags", []))
    return sorted(tags)
