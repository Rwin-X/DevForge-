"""Convert raw RFC 5322 bytes into a ParsedEmail. Standard library only."""
from __future__ import annotations

import email
import re
from datetime import datetime, timezone
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser

from .models import ParsedEmail

MAX_TEXT_CHARS = 20000

# Only these headers are kept; they are the ones the classifier looks at.
KEPT_HEADERS = frozenset(
    {
        "list-unsubscribe",
        "list-id",
        "precedence",
        "x-mailer",
        "x-mailchimp-id",
        "x-mc-user",
        "x-campaign",
        "x-campaignid",
        "x-mailgun-sid",
        "x-sg-eid",
        "x-sg-id",
        "x-ses-outgoing",
        "x-mandrill-user",
        "x-mailjet-campaign",
        "x-report-abuse",
        "x-csa-complaints",
        "feedback-id",
        "auto-submitted",
    }
)

_BLOCK_TAGS = {"br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "table"}


class _HtmlStats(HTMLParser):
    """Extract visible text and simple structural counts from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links = 0
        self.images = 0
        self.pixels = 0
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "a":
            if attributes.get("href"):
                self.links += 1
        elif tag == "img":
            self.images += 1
            if _tiny(attributes.get("width")) and _tiny(attributes.get("height")):
                self.pixels += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _tiny(value: str | None) -> bool:
    if not value:
        return False
    digits = re.sub(r"[^0-9]", "", value)
    return bool(digits) and int(digits) <= 2


def _collapse(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _header(msg, name: str) -> str:
    try:
        value = msg.get(name)
    except Exception:
        return ""
    return "" if value is None else " ".join(str(value).split())


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _part_text(part) -> str:
    try:
        content = part.get_content()
        if isinstance(content, str):
            return content
    except Exception:
        pass
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")
    return ""


def parse_message(
    raw: bytes, uid: int = 0, folder: str = "", flags: tuple[str, ...] = ()
) -> ParsedEmail:
    """Parse raw message bytes. Truncated or malformed input never raises."""
    try:
        msg = email.message_from_bytes(raw, policy=policy.default)
    except Exception:
        return ParsedEmail(uid=uid, folder=folder, flags=flags)

    name, address = parseaddr(_header(msg, "From"))
    kept: dict[str, str] = {}
    try:
        for key in msg.keys():
            lowered = key.lower()
            if lowered in KEPT_HEADERS and lowered not in kept:
                kept[lowered] = _header(msg, key)
    except Exception:
        pass

    plain_parts: list[str] = []
    html_parts: list[str] = []
    try:
        for part in msg.walk():
            if part.is_multipart() or part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain":
                plain_parts.append(_part_text(part))
            elif ctype == "text/html":
                html_parts.append(_part_text(part))
    except Exception:
        pass

    stats = _HtmlStats()
    if html_parts:
        try:
            stats.feed("\n".join(html_parts))
        except Exception:
            pass

    text = _collapse("\n".join(plain_parts))
    if not text and html_parts:
        text = _collapse("".join(stats.parts))

    return ParsedEmail(
        uid=uid,
        folder=folder,
        message_id=_header(msg, "Message-ID").strip(),
        sender_name=name.strip(),
        sender_address=address.strip().lower(),
        recipients=_header(msg, "To"),
        subject=_header(msg, "Subject"),
        date=_parse_date(_header(msg, "Date")),
        flags=tuple(flags),
        headers=kept,
        text=text[:MAX_TEXT_CHARS],
        has_html=bool(html_parts),
        link_count=stats.links,
        image_count=stats.images,
        tracking_pixels=stats.pixels,
    )
