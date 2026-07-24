"""
Chat Personality Analyzer - Parser Module
==========================================
Detects and parses multiple chat export formats:
  • WhatsApp  (.txt  – Android & iOS exports)
  • Telegram  (.txt  or plain log)
  • Discord   (plain log)
  • Raw pasted / generic conversation
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class Message:
    """A single parsed chat message."""
    speaker: str
    text: str
    timestamp: Optional[datetime] = None
    word_count: int = 0
    char_count: int = 0

    def __post_init__(self) -> None:
        self.word_count = len(self.text.split())
        self.char_count = len(self.text)


@dataclass
class ConversationStats:
    """Aggregate statistics for one participant."""
    speaker: str
    message_count: int = 0
    total_words: int = 0
    total_chars: int = 0
    avg_message_length: float = 0.0      # words per message
    avg_char_length: float = 0.0
    question_count: int = 0
    exclamation_count: int = 0
    emoji_count: int = 0
    response_times: list[float] = field(default_factory=list)
    avg_response_time: Optional[float] = None  # seconds
    messages_per_hour: dict[int, int] = field(default_factory=dict)

    def compute(self, messages: list[Message]) -> None:
        """Derive computed fields from raw messages."""
        self.message_count = len(messages)
        if not messages:
            return
        self.total_words = sum(m.word_count for m in messages)
        self.total_chars = sum(m.char_count for m in messages)
        self.avg_message_length = self.total_words / self.message_count
        self.avg_char_length = self.total_chars / self.message_count
        full_text = " ".join(m.text for m in messages)
        self.question_count = full_text.count("?")
        self.exclamation_count = full_text.count("!")
        self.emoji_count = _count_emojis(full_text)

        # Response-time stats (need timestamps)
        timed = [m for m in messages if m.timestamp]
        if len(timed) > 1 and self.avg_response_time is None:
            self.avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else None

        # Hour-of-day distribution
        for m in messages:
            if m.timestamp:
                h = m.timestamp.hour
                self.messages_per_hour[h] = self.messages_per_hour.get(h, 0) + 1


@dataclass
class ParsedConversation:
    """Result of parsing a chat file."""
    format_detected: str
    speakers: list[str]
    messages: list[Message]
    stats: dict[str, ConversationStats]
    target_speaker: str          # The person we are analysing (not "you")
    raw_text: str = ""

    @property
    def total_messages(self) -> int:
        return len(self.messages)


# ─── Emoji helper ─────────────────────────────────────────────────────────────

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"
    "\u3030"
    "]+",
    flags=re.UNICODE,
)

def _count_emojis(text: str) -> int:
    return sum(len(m.group()) for m in _EMOJI_RE.finditer(text))


# ─── Format Detection ─────────────────────────────────────────────────────────

# WhatsApp Android:  "12/31/23, 11:59 PM - Speaker: message"
_WA_ANDROID = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\s+-\s+(.+?):\s+(.+)$",
    re.IGNORECASE,
)
# WhatsApp iOS:  "[31/12/2023, 23:59:00] Speaker: message"
_WA_IOS = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{4}),\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\]\s+(.+?):\s+(.+)$",
    re.IGNORECASE,
)
# Telegram:  "Speaker, [DD.MM.YYYY HH:MM]"  then next line is message
_TG_HEADER = re.compile(r"^(.+),\s+\[(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\]$")
# Telegram plain export:  "HH:MM Speaker"
_TG_PLAIN = re.compile(r"^(\d{2}:\d{2})\s+(.+)$")
# Discord:  "[Today/Yesterday at HH:MM AM/PM] Speaker: message"  or  "Speaker — Today at HH:MM"
_DISCORD = re.compile(
    r"^(.+?)\s*[—–-]\s*(Today|Yesterday|\d{2}/\d{2}/\d{4})\s+at\s+(\d{1,2}:\d{2}\s?[AP]M)$",
    re.IGNORECASE,
)
# Generic "Speaker: message"
_GENERIC = re.compile(r"^([A-Za-z][A-Za-z0-9 _\-]{0,29}):\s+(.+)$")


def _detect_format(lines: list[str]) -> str:
    sample = lines[:min(30, len(lines))]
    wa_android = sum(1 for l in sample if _WA_ANDROID.match(l))
    wa_ios = sum(1 for l in sample if _WA_IOS.match(l))
    tg = sum(1 for l in sample if _TG_HEADER.match(l))
    discord = sum(1 for l in sample if _DISCORD.match(l))
    generic = sum(1 for l in sample if _GENERIC.match(l))

    scores = {
        "WhatsApp (Android)": wa_android,
        "WhatsApp (iOS)": wa_ios,
        "Telegram": tg,
        "Discord": discord,
        "Generic": generic,
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "Unknown/Raw"


# ─── Per-format parsers ────────────────────────────────────────────────────────

def _parse_whatsapp_android(lines: list[str]) -> list[Message]:
    messages: list[Message] = []
    current: Optional[Message] = None
    for line in lines:
        m = _WA_ANDROID.match(line)
        if m:
            date_str, time_str, speaker, text = m.groups()
            try:
                ts = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%y %I:%M %p")
            except ValueError:
                try:
                    ts = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M %p")
                except ValueError:
                    ts = None
            if current:
                messages.append(current)
            current = Message(speaker=speaker.strip(), text=text.strip(), timestamp=ts)
        elif current and line.strip():
            current.text += " " + line.strip()
    if current:
        messages.append(current)
    return messages


def _parse_whatsapp_ios(lines: list[str]) -> list[Message]:
    messages: list[Message] = []
    current: Optional[Message] = None
    for line in lines:
        m = _WA_IOS.match(line)
        if m:
            date_str, time_str, speaker, text = m.groups()
            try:
                ts = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            except ValueError:
                ts = None
            if current:
                messages.append(current)
            current = Message(speaker=speaker.strip(), text=text.strip(), timestamp=ts)
        elif current and line.strip():
            current.text += " " + line.strip()
    if current:
        messages.append(current)
    return messages


def _parse_telegram(lines: list[str]) -> list[Message]:
    """Handles Telegram desktop export TXT format."""
    messages: list[Message] = []
    i = 0
    while i < len(lines):
        header = _TG_HEADER.match(lines[i])
        if header and i + 1 < len(lines):
            speaker = header.group(1).strip()
            try:
                ts = datetime.strptime(header.group(2), "%d.%m.%Y %H:%M")
            except ValueError:
                ts = None
            text_lines = []
            i += 1
            while i < len(lines) and not _TG_HEADER.match(lines[i]):
                if lines[i].strip():
                    text_lines.append(lines[i].strip())
                i += 1
            text = " ".join(text_lines)
            if text:
                messages.append(Message(speaker=speaker, text=text, timestamp=ts))
        else:
            i += 1
    return messages


def _parse_discord(lines: list[str]) -> list[Message]:
    messages: list[Message] = []
    current_speaker: str = ""
    for line in lines:
        m = _DISCORD.match(line)
        if m:
            current_speaker = m.group(1).strip()
        elif current_speaker and line.strip() and not line.startswith("—"):
            messages.append(Message(speaker=current_speaker, text=line.strip()))
    return messages


def _parse_generic(lines: list[str]) -> list[Message]:
    """Fallback: Speaker: message format."""
    messages: list[Message] = []
    current: Optional[Message] = None
    for line in lines:
        m = _GENERIC.match(line)
        if m:
            if current:
                messages.append(current)
            current = Message(speaker=m.group(1).strip(), text=m.group(2).strip())
        elif current and line.strip():
            current.text += " " + line.strip()
    if current:
        messages.append(current)
    return messages


# ─── Speaker resolution ───────────────────────────────────────────────────────

_SELF_ALIASES = {
    "me", "you", "i", "myself", "self", "user", "anon",
}

def _resolve_target(speakers: list[str], messages: list[Message]) -> str:
    """
    Pick the speaker we should analyse.
    Heuristic: the one who is NOT 'Me'/'You'.  If ambiguous, pick the one
    with MORE messages (they've shared more content to analyse).
    """
    if len(speakers) == 1:
        return speakers[0]
    if len(speakers) == 2:
        for sp in speakers:
            if sp.lower() not in _SELF_ALIASES:
                return sp
    # Fall back to most frequent
    counts: dict[str, int] = defaultdict(int)
    for m in messages:
        counts[m.speaker] += 1
    return max(counts, key=lambda k: counts[k])


# ─── Response-time computation ────────────────────────────────────────────────

def _compute_response_times(
    messages: list[Message],
    stats: dict[str, ConversationStats],
) -> None:
    """Annotate stats with per-speaker average response time in seconds."""
    for i in range(1, len(messages)):
        prev, curr = messages[i - 1], messages[i]
        if (
            curr.timestamp
            and prev.timestamp
            and curr.speaker != prev.speaker
        ):
            delta = (curr.timestamp - prev.timestamp).total_seconds()
            if 0 < delta < 86400:  # ignore >24h gaps
                stats[curr.speaker].response_times.append(delta)

    for sp, st in stats.items():
        if st.response_times:
            st.avg_response_time = sum(st.response_times) / len(st.response_times)


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_file(path: str | Path) -> ParsedConversation:
    """Parse a chat file and return a :class:`ParsedConversation`."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_text(text)


def parse_text(raw_text: str) -> ParsedConversation:
    """Parse raw chat text (may come from stdin or paste)."""
    lines = raw_text.splitlines()
    fmt = _detect_format(lines)

    if fmt == "WhatsApp (Android)":
        messages = _parse_whatsapp_android(lines)
    elif fmt == "WhatsApp (iOS)":
        messages = _parse_whatsapp_ios(lines)
    elif fmt == "Telegram":
        messages = _parse_telegram(lines)
    elif fmt == "Discord":
        messages = _parse_discord(lines)
    else:
        messages = _parse_generic(lines)
        if not messages:
            # Last resort: treat every non-blank line as a message alternating between two speakers
            messages = _parse_raw_alternating(lines)
            fmt = "Raw/Unknown"

    if not messages:
        raise ValueError(
            "No parseable messages found. Please check the format of your input file."
        )

    # De-duplicate consecutive same-speaker messages (Telegram multi-line)
    # Already handled in per-parser, but do a final clean pass
    speakers: list[str] = list(dict.fromkeys(m.speaker for m in messages))

    # Build per-speaker stats
    speaker_messages: dict[str, list[Message]] = defaultdict(list)
    for m in messages:
        speaker_messages[m.speaker].append(m)

    stats: dict[str, ConversationStats] = {}
    for sp in speakers:
        st = ConversationStats(speaker=sp)
        st.compute(speaker_messages[sp])
        stats[sp] = st

    _compute_response_times(messages, stats)

    target = _resolve_target(speakers, messages)

    return ParsedConversation(
        format_detected=fmt,
        speakers=speakers,
        messages=messages,
        stats=stats,
        target_speaker=target,
        raw_text=raw_text,
    )


def _parse_raw_alternating(lines: list[str]) -> list[Message]:
    """
    Treat non-blank lines as alternating between Speaker A and Speaker B
    when no recognisable format is found.
    """
    clean = [l.strip() for l in lines if l.strip()]
    speakers = ["Person A", "Person B"]
    return [
        Message(speaker=speakers[i % 2], text=line)
        for i, line in enumerate(clean)
    ]
