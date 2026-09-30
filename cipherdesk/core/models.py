"""Plain data models shared across the app.

No PyQt widget imports here, ever. QObject/pyqtSignal are acceptable
when a class needs to emit data-flow events, but nothing in this file
should know that a GUI exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional


class Direction(Enum):
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"


class KeyKind(Enum):
    """How a key field's value should be edited and displayed."""

    TEXT = "text"          # single-line, maskable (passphrase, word key)
    INTEGER = "integer"     # single-line, numeric (Caesar shift, rail count)
    PEM = "pem"             # multi-line PEM block (RSA public/private key)


@dataclass(frozen=True)
class KeyFieldSpec:
    """Describes one key input a cipher needs (there can be up to two)."""

    label: str
    hint: str = ""
    placeholder: str = ""
    kind: KeyKind = KeyKind.TEXT


@dataclass(frozen=True)
class CipherSpec:
    """Describes one algorithm: its identity, key requirements, and the
    functions that actually perform encryption/decryption.

    encrypt_fn / decrypt_fn operate on text (str -> str).
    file_encrypt_fn / file_decrypt_fn operate on raw bytes (bytes -> bytes)
    and are only present for byte-safe algorithms.
    """

    id: str
    name: str
    group: str
    description: str
    key1: Optional[KeyFieldSpec] = None
    key2: Optional[KeyFieldSpec] = None
    one_way: bool = False           # hashes: no decrypt direction
    is_asymmetric: bool = False     # RSA: key1 = public, key2 = private
    byte_safe: bool = False         # can operate on raw binary files

    encrypt_fn: Optional[Callable[..., str]] = None
    decrypt_fn: Optional[Callable[..., str]] = None
    file_encrypt_fn: Optional[Callable[..., bytes]] = None
    file_decrypt_fn: Optional[Callable[..., bytes]] = None


@dataclass
class ConversionResult:
    """Outcome of running one cipher operation, text or file."""

    ok: bool
    text_output: str = ""
    file_output: Optional[bytes] = None
    error: str = ""
    input_size: int = 0
    output_size: int = 0


@dataclass
class VaultEntry:
    """One saved conversion in the session vault."""

    uid: str
    timestamp: datetime
    algorithm_id: str
    algorithm_name: str
    direction: Direction
    input_preview: str
    output_preview: str
    key1: str = ""
    key2: str = ""
    is_asymmetric: bool = False

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "timestamp": self.timestamp.isoformat(),
            "algorithm_id": self.algorithm_id,
            "algorithm_name": self.algorithm_name,
            "direction": self.direction.value,
            "input_preview": self.input_preview,
            "output_preview": self.output_preview,
            "key1": self.key1,
            "key2": self.key2,
            "is_asymmetric": self.is_asymmetric,
        }

    @staticmethod
    def from_dict(data: dict) -> "VaultEntry":
        return VaultEntry(
            uid=data["uid"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            algorithm_id=data["algorithm_id"],
            algorithm_name=data["algorithm_name"],
            direction=Direction(data["direction"]),
            input_preview=data["input_preview"],
            output_preview=data["output_preview"],
            key1=data.get("key1", ""),
            key2=data.get("key2", ""),
            is_asymmetric=data.get("is_asymmetric", False),
        )


@dataclass
class PipelineStage:
    """One step in a chained pipeline: an algorithm id plus its keys."""

    algorithm_id: str
    key1: str = ""
    key2: str = ""


@dataclass
class FrequencyReport:
    """Result of a letter-frequency / index-of-coincidence analysis."""

    letter_counts: dict = field(default_factory=dict)
    total_letters: int = 0
    index_of_coincidence: float = 0.0
    caesar_candidates: list = field(default_factory=list)   # list[(shift, plaintext, score)]
    kasiski_candidates: list = field(default_factory=list)  # list[(key_length, score)]
