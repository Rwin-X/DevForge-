"""
HashForge — Export utilities.
"""

import json
import os
from pathlib import Path
from datetime import datetime

from hashforge.core.hasher import HashResult


def export_txt(result: HashResult, dest: str) -> str:
    Path(dest).write_text(result.to_text(), encoding="utf-8")
    return dest


def export_json(result: HashResult, dest: str) -> str:
    Path(dest).write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return dest


def suggest_filename(result: HashResult, ext: str) -> str:
    stem = Path(result.file_info.name).stem
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stem}_hashes_{ts}.{ext}"
