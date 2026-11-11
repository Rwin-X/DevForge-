"""Thin IMAP client built on the standard library (imaplib over TLS).

One MailboxClient is one connection. It is not thread-safe; create one per task.
"""
from __future__ import annotations

import base64
import email.utils
import imaplib
import re
import ssl
from dataclasses import dataclass
from datetime import date

from .errors import MailboxError
from .models import ParsedEmail
from .parser import parse_message

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_LIST_RE = re.compile(rb'\((?P<attrs>[^)]*)\)\s+(?P<delim>"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)', re.S)
_UID_RE = re.compile(rb"UID (\d+)")
_FLAGS_RE = re.compile(rb"FLAGS \(([^)]*)\)")
SCAN_BYTES = 65536
FULL_BYTES = 2_000_000
CHUNK = 50

TRASH_FALLBACKS = (
    "[Gmail]/Trash", "[Google Mail]/Trash", "Trash", "INBOX.Trash",
    "Deleted Items", "Deleted Messages", "Deleted",
)
SENT_FALLBACKS = (
    "[Gmail]/Sent Mail", "[Google Mail]/Sent Mail", "Sent", "Sent Items",
    "Sent Messages", "INBOX.Sent",
)


def imap_date(day: date) -> str:
    """IMAP date literal. Month names are fixed English, never locale based."""
    return f"{day.day:02d}-{_MONTHS[day.month - 1]}-{day.year}"


def quote(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def decode_imap_utf7(name: str) -> str:
    """Decode modified UTF-7 folder names for display only."""

    def repl(match: re.Match) -> str:
        body = match.group(1)
        if not body:
            return "&"
        b64 = body.replace(",", "/")
        b64 += "=" * (-len(b64) % 4)
        try:
            return base64.b64decode(b64).decode("utf-16-be")
        except (ValueError, UnicodeDecodeError):
            return match.group(0)

    return re.sub(r"&([^-]*)-", repl, name)


@dataclass(frozen=True)
class FolderInfo:
    name: str  # raw name exactly as the server expects it
    display: str
    attrs: tuple[str, ...]
    delimiter: str = "/"

    def has_attr(self, attr: str) -> bool:
        return attr.lower() in {a.lower() for a in self.attrs}


def _friendly(exc: Exception) -> str:
    text = str(exc)
    low = text.lower()
    if "authenticationfailed" in low or "invalid credentials" in low or "login failed" in low:
        return (
            "Authentication failed. Use an app password (not your normal password) "
            "and make sure IMAP is enabled for the account."
        )
    if isinstance(exc, ssl.SSLError):
        return f"TLS error: {text}"
    if isinstance(exc, OSError):
        return f"Could not reach the IMAP server: {text}"
    return f"IMAP error: {text}"


def _text(value) -> str:
    return value.decode("utf-8", "replace") if isinstance(value, (bytes, bytearray)) else str(value)


class MailboxClient:
    def __init__(
        self, host: str, port: int, username: str, password: str,
        *, timeout: float = 30.0, connection_factory=None,
    ):
        self.host, self.port, self.username = host, port, username
        self._password = password
        self._timeout = timeout
        self._factory = connection_factory
        self._conn = None
        self._caps: set[str] = set()
        self._selected: tuple[str, bool] | None = None
        self._folders: list[FolderInfo] | None = None

    # ---- lifecycle ---------------------------------------------------

    def __enter__(self) -> "MailboxClient":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def connect(self) -> None:
        try:
            if self._factory:
                conn = self._factory(self.host, self.port)
            else:
                conn = imaplib.IMAP4_SSL(
                    self.host, self.port, ssl_context=ssl.create_default_context(),
                    timeout=self._timeout,
                )
            conn.login(self.username, self._password)
            typ, data = conn.capability()
        except (imaplib.IMAP4.error, OSError) as exc:
            raise MailboxError(_friendly(exc)) from exc
        self._conn = conn
        self._caps = set(_text(data[0]).upper().split()) if typ == "OK" and data and data[0] else set()

    def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is None:
            return
        try:
            conn.logout()
        except Exception:
            pass

    @property
    def _has_move(self) -> bool:
        return "MOVE" in self._caps and "MOVE" in imaplib.Commands

    def _need(self):
        if self._conn is None:
            raise MailboxError("Not connected.")
        return self._conn

    @staticmethod
    def _check(result, what: str):
        typ, data = result
        if typ != "OK":
            detail = _text(data[0]) if data and data[0] else "no detail"
            raise MailboxError(f"{what} failed: {detail}")
        return data

    def _run(self, what: str, call):
        try:
            return self._check(call(), what)
        except (imaplib.IMAP4.error, OSError) as exc:
            raise MailboxError(_friendly(exc)) from exc

    # ---- folders -----------------------------------------------------

    def list_folders(self, refresh: bool = False) -> list[FolderInfo]:
        if self._folders is not None and not refresh:
            return self._folders
        data = self._run("LIST", lambda: self._need().list())
        folders: list[FolderInfo] = []
        items = list(data)
        i = 0
        while i < len(items):
            item = items[i]
            i += 1
            if item is None:
                continue
            if isinstance(item, tuple):  # literal folder name
                line, literal = item[0], item[1]
                match = _LIST_RE.match(line.rsplit(b"{", 1)[0].rstrip() + b" x")
                if not match:
                    continue
                name = _text(literal)
            else:
                match = _LIST_RE.match(item)
                if not match:
                    continue
                name = _text(match.group("name")).strip()
                if name.startswith('"') and name.endswith('"') and len(name) >= 2:
                    name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            attrs = tuple(_text(match.group("attrs")).split())
            if any(a.lower() == "\\noselect" for a in attrs):
                continue
            delim = _text(match.group("delim")).strip('"')
            folders.append(FolderInfo(name, decode_imap_utf7(name), attrs, delim if delim != "NIL" else "/"))
        self._folders = folders
        return folders

    def special_folder(self, attr: str) -> str | None:
        for folder in self.list_folders():
            if folder.has_attr(attr):
                return folder.name
        return None

    def trash_folder(self) -> str:
        found = self.special_folder("\\Trash")
        if found:
            return found
        names = {f.name for f in self.list_folders()}
        for candidate in TRASH_FALLBACKS:
            if candidate in names:
                return candidate
        raise MailboxError("Could not find the Trash folder on this account.")

    def sent_folder(self) -> str | None:
        found = self.special_folder("\\Sent")
        if found:
            return found
        names = {f.name for f in self.list_folders()}
        return next((c for c in SENT_FALLBACKS if c in names), None)

    # ---- selection and search ---------------------------------------

    def select_folder(self, folder: str, readonly: bool = False) -> tuple[int, int]:
        data = self._run("SELECT", lambda: self._need().select(quote(folder), readonly))
        self._selected = (folder, readonly)
        try:
            exists = int(data[0])
        except (TypeError, ValueError, IndexError):
            exists = 0
        validity = 0
        try:
            _, vdata = self._need().response("UIDVALIDITY")
            validity = int(vdata[-1])
        except (TypeError, ValueError, IndexError, imaplib.IMAP4.error):
            pass
        return exists, validity

    def _ensure(self, folder: str, readonly: bool = False) -> None:
        current = self._selected
        if current and current[0] == folder and (current[1] == readonly or not current[1]):
            return
        self.select_folder(folder, readonly)

    def search_uids(self, folder: str, *criteria: str, readonly: bool = False) -> list[int]:
        self._ensure(folder, readonly)
        args = criteria or ("ALL",)
        data = self._run("SEARCH", lambda: self._need().uid("SEARCH", None, *args))
        if not data or not data[0]:
            return []
        return sorted(int(tok) for tok in _text(data[0]).split() if tok.isdigit())

    def find_uid_by_message_id(self, folder: str, message_id: str) -> int | None:
        if not message_id:
            return None
        try:
            uids = self.search_uids(folder, "HEADER", "Message-ID", quote(message_id))
        except (MailboxError, UnicodeEncodeError):
            return None
        return uids[-1] if uids else None

    # ---- fetching ----------------------------------------------------

    @staticmethod
    def _iter_fetch(data):
        items = list(data)
        i = 0
        while i < len(items):
            item = items[i]
            i += 1
            if not isinstance(item, tuple):
                continue
            meta, raw = item[0], item[1]
            if i < len(items) and isinstance(items[i], (bytes, bytearray)):
                meta = meta + b" " + bytes(items[i])
                i += 1
            uid_match = _UID_RE.search(meta)
            if not uid_match:
                continue
            flags_match = _FLAGS_RE.search(meta)
            flags = tuple(_text(flags_match.group(1)).split()) if flags_match else ()
            yield int(uid_match.group(1)), flags, bytes(raw)

    def _fetch(self, folder: str, uids: list[int], spec: str) -> list[ParsedEmail]:
        self._ensure(folder, readonly=True)
        results: list[ParsedEmail] = []
        for start in range(0, len(uids), CHUNK):
            chunk = uids[start : start + CHUNK]
            uid_set = ",".join(str(u) for u in chunk)
            data = self._run("FETCH", lambda: self._need().uid("FETCH", uid_set, spec))
            for uid, flags, raw in self._iter_fetch(data):
                results.append(parse_message(raw, uid=uid, folder=folder, flags=flags))
        return results

    def fetch_scan(self, folder: str, uids: list[int]) -> list[ParsedEmail]:
        """Headers plus the first 64 KB of the body, without setting \\Seen."""
        return self._fetch(folder, uids, f"(UID FLAGS BODY.PEEK[]<0.{SCAN_BYTES}>)")

    def fetch_summaries(self, folder: str, uids: list[int]) -> list[ParsedEmail]:
        spec = "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID LIST-UNSUBSCRIBE)])"
        return self._fetch(folder, uids, spec)

    def fetch_full(self, folder: str, uid: int) -> ParsedEmail | None:
        found = self._fetch(folder, [uid], f"(UID FLAGS BODY.PEEK[]<0.{FULL_BYTES}>)")
        return found[0] if found else None

    # ---- changes -----------------------------------------------------

    @staticmethod
    def _uid_set(uids: list[int]) -> str:
        return ",".join(str(u) for u in uids)

    def _expunge(self, uid_set: str) -> None:
        if "UIDPLUS" in self._caps:
            self._run("EXPUNGE", lambda: self._need().uid("EXPUNGE", uid_set))
        else:
            self._run("EXPUNGE", lambda: self._need().expunge())

    def move(self, folder: str, uids: list[int], dest: str) -> None:
        if not uids:
            return
        self._ensure(folder, readonly=False)
        uid_set = self._uid_set(uids)
        if self._has_move:
            self._run("MOVE", lambda: self._need().uid("MOVE", uid_set, quote(dest)))
            return
        self._run("COPY", lambda: self._need().uid("COPY", uid_set, quote(dest)))
        self._run("STORE", lambda: self._need().uid("STORE", uid_set, "+FLAGS.SILENT", r"(\Deleted)"))
        self._expunge(uid_set)

    def trash(self, folder: str, uids: list[int]) -> str:
        dest = self.trash_folder()
        self.move(folder, uids, dest)
        return dest

    def delete_permanently(self, folder: str, uids: list[int]) -> None:
        if not uids:
            return
        self._ensure(folder, readonly=False)
        uid_set = self._uid_set(uids)
        self._run("STORE", lambda: self._need().uid("STORE", uid_set, "+FLAGS.SILENT", r"(\Deleted)"))
        self._expunge(uid_set)

    def set_flag(self, folder: str, uids: list[int], flag: str, on: bool) -> None:
        if not uids:
            return
        self._ensure(folder, readonly=False)
        op = "+FLAGS.SILENT" if on else "-FLAGS.SILENT"
        self._run("STORE", lambda: self._need().uid("STORE", self._uid_set(uids), op, f"({flag})"))

    # ---- correspondents ---------------------------------------------

    def known_correspondents(self, limit: int = 400) -> set[str]:
        """Addresses the user has written to, read from the Sent folder."""
        try:
            sent = self.sent_folder()
            if not sent:
                return set()
            uids = self.search_uids(sent, "ALL", readonly=True)[-limit:]
            addresses: set[str] = set()
            for start in range(0, len(uids), CHUNK):
                chunk = uids[start : start + CHUNK]
                uid_set = ",".join(str(u) for u in chunk)
                data = self._run(
                    "FETCH",
                    lambda: self._need().uid("FETCH", uid_set, "(UID BODY.PEEK[HEADER.FIELDS (TO CC)])"),
                )
                for _uid, _flags, raw in self._iter_fetch(data):
                    text = raw.decode("utf-8", "replace")
                    pairs = email.utils.getaddresses(re.findall(r"(?im)^(?:to|cc):(.*(?:\r?\n[ \t].*)*)", text))
                    addresses.update(addr.lower() for _name, addr in pairs if "@" in addr)
            return addresses
        except MailboxError:
            return set()
