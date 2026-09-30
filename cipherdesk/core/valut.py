"""Session vault: saved conversions persisted to a small JSON file in
the user's config directory. No PyQt imports.
"""
from __future__ import annotations
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from core.models import Direction, VaultEntry
_APP_DIR_NAME = "cipherdesk"
_VAULT_FILE_NAME = "vault.json"
_MAX_ENTRIES = 200
def _config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home()))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    path = Path(base) / _APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
def _vault_path() -> Path:
    return _config_dir() / _VAULT_FILE_NAME
def load_vault() -> List[VaultEntry]:
    path = _vault_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [VaultEntry.from_dict(item) for item in raw]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []
def save_vault(entries: List[VaultEntry]) -> None:
    trimmed = entries[-_MAX_ENTRIES:]
    data = [e.to_dict() for e in trimmed]
    _vault_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
def make_entry(
    algorithm_id: str,
    algorithm_name: str,
    direction: Direction,
    input_text: str,
    output_text: str,
    key1: str = "",
    key2: str = "",
    is_asymmetric: bool = False,
    preview_len: int = 90,
) -> VaultEntry:
    def preview(s: str) -> str:
        return s if len(s) <= preview_len else s[:preview_len] + "..."
    return VaultEntry(
        uid=str(uuid.uuid4()),
        timestamp=datetime.now(),
        algorithm_id=algorithm_id,
        algorithm_name=algorithm_name,
        direction=direction,
        input_preview=preview(input_text),
        output_preview=preview(output_text),
        key1=key1 if not is_asymmetric else "",
        key2=key2 if not is_asymmetric else "",
        is_asymmetric=is_asymmetric,
    )
