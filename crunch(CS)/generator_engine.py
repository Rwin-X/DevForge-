"""
generator_engine.py
Core wordlist generation engine, crunch-style.

Pattern syntax (mirrors real crunch placeholders):
    @  -> lowercase letter        [a-z]
    ,  -> uppercase letter        [A-Z]
    %  -> digit                   [0-9]
    ^  -> symbol                  [!@#$%^&*()-_=+]
    Any other literal character in the pattern is kept as-is (fixed char).

Example pattern: "user@@%%^"  ->  "user" + 2 lowercase + 2 digits + 1 symbol
Example pattern: ",@@@%%"    ->  1 uppercase + 3 lowercase + 2 digits

If no pattern is given, a plain min/max length charset brute-force is used
instead (classic crunch min-max mode).

No GUI dependency here — importable/testable standalone.
"""

import itertools
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
SYMBOLS = "!@#$%^&*()-_=+"

PATTERN_TOKENS = {
    "@": LOWERCASE,
    ",": UPPERCASE,
    "%": DIGITS,
    "^": SYMBOLS,
}


class GenerationMode(Enum):
    CHARSET_RANGE = "charset_range"   # classic min/max length brute-force
    PATTERN = "pattern"               # crunch-style @,%^ pattern


@dataclass
class CharsetOptions:
    use_lower: bool = True
    use_upper: bool = False
    use_digits: bool = False
    use_symbols: bool = False

    def build_charset(self) -> str:
        charset = ""
        if self.use_lower:
            charset += LOWERCASE
        if self.use_upper:
            charset += UPPERCASE
        if self.use_digits:
            charset += DIGITS
        if self.use_symbols:
            charset += SYMBOLS
        return charset


def parse_pattern(pattern: str):
    """
    Turns a crunch-style pattern into a list of per-position character pools.
    Literal characters become single-character pools (fixed).
    Returns (slots, has_variable_slot).
    """
    slots = []
    has_variable = False
    for ch in pattern:
        if ch in PATTERN_TOKENS:
            slots.append(PATTERN_TOKENS[ch])
            has_variable = True
        else:
            slots.append(ch)  # literal, fixed character
    return slots, has_variable


def estimate_pattern_count(pattern: str) -> int:
    slots, _ = parse_pattern(pattern)
    total = 1
    for slot in slots:
        total *= len(slot)
    return total


def estimate_charset_range_count(charset_len: int, min_len: int, max_len: int) -> int:
    total = 0
    for length in range(min_len, max_len + 1):
        total += charset_len ** length
    return total


def estimate_file_size_bytes(total_words: int, avg_word_len: float) -> int:
    """Rough estimate: each line is avg_word_len chars + 1 newline byte."""
    return int(total_words * (avg_word_len + 1))


def human_readable_size(num_bytes: int) -> str:
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < step:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= step
    return f"{num_bytes:.1f} PB"


def human_readable_count(n: int) -> str:
    if n < 1000:
        return str(n)
    for suffix, div in [("K", 1e3), ("M", 1e6), ("B", 1e9), ("T", 1e12)]:
        pass
    if n < 1_000_000:
        return f"{n/1e3:.1f}K"
    if n < 1_000_000_000:
        return f"{n/1e6:.1f}M"
    if n < 1_000_000_000_000:
        return f"{n/1e9:.1f}B"
    return f"{n/1e12:.1f}T"


@dataclass
class GenerationResult:
    output_path: str
    total_written: int = 0
    elapsed_seconds: float = 0.0
    stopped_early: bool = False


class WordlistGenerator:
    """
    Streams generated words directly to disk (never holds the full list in
    memory — essential once combination counts run into the millions/billions).

    Usage (pattern mode):
        gen = WordlistGenerator.from_pattern(
            pattern="user@@%%",
            output_path="/home/user/wordlists/out.txt",
            progress_callback=lambda written, rate: print(written, rate),
        )
        result = gen.run()

    Usage (charset/range mode):
        gen = WordlistGenerator.from_charset_range(
            charset_options=CharsetOptions(use_lower=True, use_digits=True),
            min_len=4, max_len=6,
            output_path="/home/user/wordlists/out.txt",
        )
        result = gen.run()
    """

    def __init__(
        self,
        mode: GenerationMode,
        output_path: str,
        pattern: Optional[str] = None,
        charset: Optional[str] = None,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None,
        progress_callback: Optional[Callable[[int, float], None]] = None,
        progress_interval: float = 0.25,
        write_buffer_size: int = 8192,
        max_words: Optional[int] = None,
    ):
        self.mode = mode
        self.output_path = output_path
        self.pattern = pattern
        self.charset = charset
        self.min_len = min_len
        self.max_len = max_len
        self.progress_callback = progress_callback
        self.progress_interval = progress_interval
        self.write_buffer_size = write_buffer_size
        self.max_words = max_words  # safety cap; None = unlimited

        self._stop_event = threading.Event()
        self._written_count = 0
        self._lock = threading.Lock()

    @classmethod
    def from_pattern(cls, pattern: str, output_path: str, **kwargs):
        return cls(mode=GenerationMode.PATTERN, output_path=output_path, pattern=pattern, **kwargs)

    @classmethod
    def from_charset_range(
        cls, charset_options: CharsetOptions, min_len: int, max_len: int, output_path: str, **kwargs
    ):
        return cls(
            mode=GenerationMode.CHARSET_RANGE,
            output_path=output_path,
            charset=charset_options.build_charset(),
            min_len=min_len,
            max_len=max_len,
            **kwargs,
        )

    def stop(self):
        self._stop_event.set()

    def _iter_pattern_words(self):
        slots, _ = parse_pattern(self.pattern)
        pools = [s if len(s) > 1 or not s.isalnum() and len(s) == 1 else s for s in slots]
        # Each slot is either a multi-char pool (variable) or a 1-char literal (fixed).
        for combo in itertools.product(*[list(p) for p in slots]):
            yield "".join(combo)

    def _iter_charset_range_words(self):
        for length in range(self.min_len, self.max_len + 1):
            for combo in itertools.product(self.charset, repeat=length):
                yield "".join(combo)

    def run(self) -> GenerationResult:
        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)
        start_time = time.time()
        written = 0
        stopped_early = False

        word_iter = (
            self._iter_pattern_words()
            if self.mode == GenerationMode.PATTERN
            else self._iter_charset_range_words()
        )

        last_progress_time = start_time
        with open(self.output_path, "w", encoding="utf-8", buffering=1024 * 1024) as f:
            buffer = []
            for word in word_iter:
                if self._stop_event.is_set():
                    stopped_early = True
                    break
                buffer.append(word)
                written += 1

                if len(buffer) >= self.write_buffer_size:
                    f.write("\n".join(buffer) + "\n")
                    buffer.clear()

                now = time.time()
                if self.progress_callback and (now - last_progress_time) >= self.progress_interval:
                    elapsed = now - start_time
                    rate = written / elapsed if elapsed > 0 else 0.0
                    self.progress_callback(written, rate)
                    last_progress_time = now

                if self.max_words is not None and written >= self.max_words:
                    stopped_early = True
                    break

            if buffer:
                f.write("\n".join(buffer) + "\n")

        elapsed = time.time() - start_time
        if self.progress_callback:
            rate = written / elapsed if elapsed > 0 else 0.0
            self.progress_callback(written, rate)

        with self._lock:
            self._written_count = written

        return GenerationResult(
            output_path=self.output_path,
            total_written=written,
            elapsed_seconds=elapsed,
            stopped_early=stopped_early,
        )
