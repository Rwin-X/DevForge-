"""Plain data classes shared across the core layer. No GUI imports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedEmail:
    uid: int = 0
    folder: str = ""
    message_id: str = ""
    sender_name: str = ""
    sender_address: str = ""
    recipients: str = ""
    subject: str = ""
    date: datetime | None = None
    flags: tuple[str, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""
    has_html: bool = False
    link_count: int = 0
    image_count: int = 0
    tracking_pixels: int = 0

    @property
    def is_unread(self) -> bool:
        return "\\seen" not in {flag.lower() for flag in self.flags}

    @property
    def sender_display(self) -> str:
        if self.sender_name and self.sender_address:
            return f"{self.sender_name} <{self.sender_address}>"
        return self.sender_address or self.sender_name or "(unknown sender)"


@dataclass
class ClassifierResult:
    ad_score: float = 0.0
    ai_score: float = 0.0
    ad_reasons: list[str] = field(default_factory=list)
    ai_reasons: list[str] = field(default_factory=list)


@dataclass
class Decision:
    action: str = "keep"  # keep | trash | review
    category: str = ""  # ad | ai | empty
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
