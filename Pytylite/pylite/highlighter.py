"""Python syntax highlighting (VS Code Dark+ style).

Strategy: regex rules paint identifiers, keywords, numbers, calls, etc.
Afterwards a small hand-written scanner finds strings and comments (including
multi-line triple-quoted strings, tracked through the block state) and paints
over them, so a ``#`` inside a string is never treated as a comment.
"""

import builtins
import keyword
import re
from typing import List, Optional, Tuple

from PyQt6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat

from .theme import SYNTAX

# Block states carried between lines.
NORMAL, IN_TRIPLE_SINGLE, IN_TRIPLE_DOUBLE = 0, 1, 2
_TRIPLE = {IN_TRIPLE_SINGLE: "'''", IN_TRIPLE_DOUBLE: '"""'}

Span = Tuple[int, int, str]  # (start, end, "string" | "comment")


def _find_close(text: str, start: int, quote: str) -> int:
    """Index of the closing ``quote`` at/after ``start`` (backslash-aware), or -1."""
    i, n = start, len(text)
    while i < n:
        if text[i] == "\\":
            i += 2
            continue
        if text.startswith(quote, i):
            return i
        i += 1
    return -1


def scan_strings(text: str, state: int = NORMAL) -> Tuple[List[Span], int]:
    """Find string and comment spans in one line. Returns (spans, next_state)."""
    spans: List[Span] = []
    n = len(text)
    i = 0

    if state in _TRIPLE:
        close = _find_close(text, 0, _TRIPLE[state])
        if close == -1:
            return [(0, n, "string")], state
        spans.append((0, close + 3, "string"))
        i = close + 3

    while i < n:
        c = text[i]
        if c == "#":
            spans.append((i, n, "comment"))
            break
        if c in "\"'":
            # Include a string prefix such as r, b, f, rb, Rb ... in the span.
            start = i
            while start > 0 and i - start < 2 and text[start - 1] in "rRbBfFuU":
                start -= 1
            if start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
                start = i
            triple = c * 3
            if text.startswith(triple, i):
                close = _find_close(text, i + 3, triple)
                if close == -1:
                    spans.append((start, n, "string"))
                    return spans, IN_TRIPLE_SINGLE if c == "'" else IN_TRIPLE_DOUBLE
                spans.append((start, close + 3, "string"))
                i = close + 3
            else:
                close = _find_close(text, i + 1, c)
                if close == -1:  # unterminated: colour to end of line
                    spans.append((start, n, "string"))
                    break
                spans.append((start, close + 1, "string"))
                i = close + 1
            continue
        i += 1
    return spans, NORMAL


def _utf16_offsets(text: str) -> Optional[List[int]]:
    """Qt counts UTF-16 units, Python counts code points; map only when they differ."""
    if text.isascii() or max(text) <= "\uffff":
        return None
    offsets = [0]
    for ch in text:
        offsets.append(offsets[-1] + (2 if ord(ch) > 0xFFFF else 1))
    return offsets


def _fmt(color: str, italic: bool = False, bold: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    f.setFontItalic(italic)
    if bold:
        f.setFontWeight(700)
    return f


_IDENT = r"[^\W\d]\w*"
_CONTROL = {
    "if", "elif", "else", "for", "while", "break", "continue", "return", "yield",
    "try", "except", "finally", "raise", "with", "as", "import", "from", "pass",
    "assert", "del", "await",
}
_CONSTANTS = {"True", "False", "None"}
_KEYWORDS = set(keyword.kwlist) - _CONTROL - _CONSTANTS
_TYPES = {n for n, o in vars(builtins).items() if isinstance(o, type)}


def _words(names) -> str:
    return r"\b(?:" + "|".join(sorted(names, key=len, reverse=True)) + r")\b"


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        self._formats = {
            "string": _fmt(SYNTAX["string"]),
            "comment": _fmt(SYNTAX["comment"], italic=True),
        }
        variable = _fmt(SYNTAX["variable"])
        function = _fmt(SYNTAX["function"])
        klass = _fmt(SYNTAX["class"])
        keyword_fmt = _fmt(SYNTAX["keyword"])
        control = _fmt(SYNTAX["control"])
        number = _fmt(SYNTAX["number"])
        decorator = _fmt(SYNTAX["decorator"])

        # (regex, format, capture group). Later rules override earlier ones.
        self._rules = [
            (re.compile(rf"\b{_IDENT}\b"), variable, 0),
            (re.compile(rf"\b{_IDENT}(?=\s*\()"), function, 0),
            (re.compile(r"\b[A-Z]\w*(?=\s*\()"), klass, 0),
            (
                re.compile(
                    r"(?<![\w.])(?:0[xX][\da-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+"
                    r"|(?:\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d+)?[jJ]?)"
                ),
                number,
                0,
            ),
            (re.compile(_words(_TYPES)), klass, 0),
            (re.compile(_words(_KEYWORDS)), keyword_fmt, 0),
            (re.compile(_words(_CONSTANTS)), keyword_fmt, 0),
            (re.compile(_words(_CONTROL)), control, 0),
            (re.compile(rf"\bdef\s+({_IDENT})"), function, 1),
            (re.compile(rf"\bclass\s+({_IDENT})"), klass, 1),
            (re.compile(r"^\s*(@[\w.]+)"), decorator, 1),
            (re.compile(r"\b(?:self|cls)\b"), _fmt(SYNTAX["variable"], italic=True), 0),
        ]

    def highlightBlock(self, text: str) -> None:
        if not text:
            self.setCurrentBlockState(max(self.previousBlockState(), NORMAL))
            return
        offsets = _utf16_offsets(text)

        def paint(start: int, end: int, fmt: QTextCharFormat) -> None:
            if offsets:
                start, end = offsets[start], offsets[end]
            self.setFormat(start, end - start, fmt)

        for pattern, fmt, group in self._rules:
            for m in pattern.finditer(text):
                s, e = m.span(group)
                paint(s, e, fmt)

        state = self.previousBlockState()
        spans, state = scan_strings(text, state if state in _TRIPLE else NORMAL)
        for s, e, kind in spans:
            paint(s, e, self._formats[kind])
        self.setCurrentBlockState(state)
