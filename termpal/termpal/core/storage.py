"""Save/load the creature's state to disk.

Zero curses/UI imports - only filesystem and JSON. Keeps the creature
alive between separate runs of the program, which is the entire point
of a persistent terminal pet.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from termpal.core.creature import Creature

APP_DIR_ENV_VAR = "TERMPAL_HOME"
DEFAULT_DIR_NAME = "termpal"
SAVE_FILE_NAME = "creature.json"


def get_data_dir() -> Path:
    """Return the directory TERMPAL stores its save file in.

    Honors XDG_DATA_HOME when set, falls back to ~/.local/share, and
    can be overridden entirely with the TERMPAL_HOME environment
    variable (used by the test suite to avoid touching a real home
    directory).
    """
    override = os.environ.get(APP_DIR_ENV_VAR)
    if override:
        return Path(override)

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base / DEFAULT_DIR_NAME


def get_save_path() -> Path:
    return get_data_dir() / SAVE_FILE_NAME


def save_creature(creature: Creature, path: Path | None = None) -> Path:
    path = path or get_save_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(creature.to_dict(), f, indent=2)
    tmp_path.replace(path)
    return path


def load_creature(path: Path | None = None) -> Creature | None:
    path = path or get_save_path()
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Creature.from_dict(data)


def delete_save(path: Path | None = None) -> bool:
    path = path or get_save_path()
    if path.exists():
        path.unlink()
        return True
    return False
