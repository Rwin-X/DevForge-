"""Password strength scoring engine.

No PyQt widget imports. This module is pure logic so it can be unit
tested with no display attached and reused from a CLI later if needed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum

# A short list of extremely common passwords and patterns. This is
# intentionally small and illustrative rather than an exhaustive
# breach-corpus check — a real deployment would load a much larger
# list from a file, but the scoring logic below does not depend on
# the list's size.
COMMON_PASSWORDS = {
    "password",
    "123456",
    "123456789",
    "qwerty",
    "letmein",
    "admin",
    "welcome",
    "monkey",
    "dragon",
    "iloveyou",
    "trustno1",
    "abc123",
    "111111",
    "sunshine",
}

SEQUENTIAL_RUNS = [
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
]


class StrengthLevel(Enum):
    VERY_WEAK = 0
    WEAK = 1
    FAIR = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class StrengthResult:
    """Result of scoring a single password."""

    score: int  # 0-100
    level: StrengthLevel
    entropy_bits: float
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    crack_time_estimate: str = ""


def _character_pool_size(password: str) -> int:
    pool = 0
    if re.search(r"[a-z]", password):
        pool += 26
    if re.search(r"[A-Z]", password):
        pool += 26
    if re.search(r"[0-9]", password):
        pool += 10
    if re.search(r"[^a-zA-Z0-9]", password):
        pool += 32
    return pool


def _estimate_entropy_bits(password: str) -> float:
    pool = _character_pool_size(password)
    if pool == 0 or not password:
        return 0.0
    return len(password) * math.log2(pool)


def _has_sequential_run(password: str, min_run: int = 4) -> bool:
    lowered = password.lower()
    for run in SEQUENTIAL_RUNS:
        for start in range(len(run) - min_run + 1):
            chunk = run[start : start + min_run]
            if chunk in lowered or chunk[::-1] in lowered:
                return True
    return False


def _has_repeated_chars(password: str, min_repeat: int = 3) -> bool:
    return re.search(r"(.)\1{" + str(min_repeat - 1) + ",}", password) is not None


def _estimate_crack_time(entropy_bits: float) -> str:
    # Assumes 10 billion guesses/second, a reasonable offline
    # GPU-cracking baseline for a fast, unsalted hash. This is a
    # rough order-of-magnitude estimate, not a precise figure -- real
    # crack time depends heavily on the hash algorithm used to store
    # the password, which this tool has no way to know.
    guesses_per_second = 1e10
    combinations = 2**entropy_bits
    seconds = combinations / (2 * guesses_per_second)

    if seconds < 1:
        return "instantly"
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.0f} minutes"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.0f} hours"
    days = hours / 24
    if days < 365:
        return f"{days:.0f} days"
    years = days / 365
    if years < 1000:
        return f"{years:.0f} years"
    if years < 1_000_000:
        return f"{years / 1000:.0f} thousand years"
    return "millions of years"


def score_password(password: str) -> StrengthResult:
    """Score a password's strength. Pure function, no side effects."""

    issues: list[str] = []
    suggestions: list[str] = []

    if not password:
        return StrengthResult(
            score=0,
            level=StrengthLevel.VERY_WEAK,
            entropy_bits=0.0,
            issues=["Password is empty."],
            suggestions=["Enter a password to check its strength."],
        )

    length = len(password)
    entropy_bits = _estimate_entropy_bits(password)

    # Start from entropy and apply penalties for known-weak patterns.
    # Entropy alone overrates passwords that are long but highly
    # predictable (e.g. "aaaaaaaaaaaa" has low real-world strength
    # despite a nonzero character pool), so the penalties below exist
    # specifically to catch what entropy misses.
    score = min(100, entropy_bits / 0.6)  # rough scaling to a 0-100 range

    if length < 8:
        issues.append("Shorter than 8 characters.")
        suggestions.append("Use at least 12 characters.")
        score *= 0.4
    elif length < 12:
        suggestions.append("Consider 12 or more characters for extra margin.")
        score *= 0.85

    if password.lower() in COMMON_PASSWORDS:
        issues.append("This is one of the most commonly used passwords.")
        suggestions.append("Avoid common passwords and dictionary words.")
        score = min(score, 5)

    if _has_sequential_run(password):
        issues.append("Contains a sequential pattern (e.g. 'abcd', '1234', 'qwerty').")
        suggestions.append("Avoid keyboard or alphabet sequences.")
        score *= 0.5

    if _has_repeated_chars(password):
        issues.append("Contains 3 or more repeated characters in a row.")
        suggestions.append("Avoid repeating the same character multiple times.")
        score *= 0.6

    pool = _character_pool_size(password)
    if pool <= 26:
        issues.append("Uses only one character type (e.g. only lowercase letters).")
        suggestions.append("Mix uppercase, lowercase, numbers, and symbols.")
    elif pool <= 62:
        suggestions.append("Adding symbols increases strength further.")

    score = max(0, min(100, round(score)))

    if score < 20:
        level = StrengthLevel.VERY_WEAK
    elif score < 40:
        level = StrengthLevel.WEAK
    elif score < 60:
        level = StrengthLevel.FAIR
    elif score < 80:
        level = StrengthLevel.STRONG
    else:
        level = StrengthLevel.VERY_STRONG

    if not suggestions and level in (StrengthLevel.STRONG, StrengthLevel.VERY_STRONG):
        suggestions.append("No issues found. This password looks solid.")

    return StrengthResult(
        score=score,
        level=level,
        entropy_bits=round(entropy_bits, 1),
        issues=issues,
        suggestions=suggestions,
        crack_time_estimate=_estimate_crack_time(entropy_bits),
    )


LEVEL_LABELS = {
    StrengthLevel.VERY_WEAK: "Very weak",
    StrengthLevel.WEAK: "Weak",
    StrengthLevel.FAIR: "Fair",
    StrengthLevel.STRONG: "Strong",
    StrengthLevel.VERY_STRONG: "Very strong",
}
