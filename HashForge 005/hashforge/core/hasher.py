"""
HashForge Core - Cryptographic hashing engine
Supports MD5, SHA1, SHA256, SHA512 with streaming for large files.
"""

import hashlib
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from PySide6.QtCore import QThread, Signal


CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB chunks for large file support

ALGORITHMS = {
    "MD5":    "md5",
    "SHA1":   "sha1",
    "SHA256": "sha256",
    "SHA512": "sha512",
}


@dataclass
class FileInfo:
    path: str
    name: str
    size: int
    size_human: str

    @classmethod
    def from_path(cls, file_path: str) -> "FileInfo":
        p = Path(file_path)
        size = p.stat().st_size
        return cls(
            path=str(p.resolve()),
            name=p.name,
            size=size,
            size_human=_human_size(size),
        )


@dataclass
class HashResult:
    file_info: FileInfo
    hashes: Dict[str, str] = field(default_factory=dict)
    elapsed: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "file": {
                "name": self.file_info.name,
                "path": self.file_info.path,
                "size": self.file_info.size,
                "size_human": self.file_info.size_human,
            },
            "hashes": self.hashes,
            "elapsed_seconds": round(self.elapsed, 4),
        }

    def to_text(self) -> str:
        lines = [
            "=" * 60,
            "HashForge — Hash Report",
            "=" * 60,
            f"File    : {self.file_info.name}",
            f"Path    : {self.file_info.path}",
            f"Size    : {self.file_info.size_human} ({self.file_info.size:,} bytes)",
            f"Time    : {self.timestamp}",
            f"Elapsed : {self.elapsed:.4f}s",
            "-" * 60,
        ]
        for algo, digest in self.hashes.items():
            lines.append(f"{algo:<8}: {digest}")
        lines.append("=" * 60)
        return "\n".join(lines)


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.2f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024
    return f"{size:.2f} PB"


def compute_hashes(
    file_path: str,
    algorithms: Optional[list] = None,
    progress_cb: Optional[Callable[[int], None]] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> HashResult:
    """
    Compute hashes for a file using streaming chunks.
    progress_cb receives 0-100 progress percent.
    cancel_flag returns True if the operation should abort.
    """
    if algorithms is None:
        algorithms = list(ALGORITHMS.keys())

    file_info = FileInfo.from_path(file_path)
    hashers = {algo: hashlib.new(ALGORITHMS[algo]) for algo in algorithms}

    start = time.perf_counter()
    bytes_read = 0

    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            if cancel_flag and cancel_flag():
                break
            for h in hashers.values():
                h.update(chunk)
            bytes_read += len(chunk)
            if progress_cb and file_info.size > 0:
                progress_cb(int(bytes_read * 100 / file_info.size))

    elapsed = time.perf_counter() - start

    if progress_cb:
        progress_cb(100)

    return HashResult(
        file_info=file_info,
        hashes={algo: hashers[algo].hexdigest() for algo in algorithms},
        elapsed=elapsed,
    )


class HashWorker(QThread):
    """Qt worker thread for non-blocking hash computation."""

    progress = Signal(int)
    finished = Signal(object)   # HashResult
    error = Signal(str)

    def __init__(self, file_path: str, algorithms: list, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.algorithms = algorithms
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            result = compute_hashes(
                self.file_path,
                self.algorithms,
                progress_cb=self.progress.emit,
                cancel_flag=lambda: self._cancel,
            )
            if not self._cancel:
                self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
