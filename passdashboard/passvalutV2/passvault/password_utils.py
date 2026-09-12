"""
password_utils.py — Password generation and health analysis.

Strength scoring here is a heuristic (entropy estimate + pattern
penalties), not a cryptographic guarantee. It's meant to give the user
a quick, honest signal — not a false sense of precision.
"""

from __future__ import annotations

import math
import re
import secrets
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

COMMON_PASSWORDS = {
    "password", "123456", "123456789", "qwerty", "12345678", "111111",
    "1234567890", "1234567", "password1", "12345", "abc123", "iloveyou",
    "admin", "letmein", "welcome", "monkey", "login", "starwars",
    "dragon", "passw0rd", "master", "hello", "freedom", "whatever",
    "qazwsx", "trustno1", "000000", "sunshine",
}


def generate_password(
    length: int = 20,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Generate a cryptographically secure random password."""
    pools = []
    if use_lower:
        pools.append(string.ascii_lowercase)
    if use_upper:
        pools.append(string.ascii_uppercase)
    if use_digits:
        pools.append(string.digits)
    if use_symbols:
        pools.append("!@#$%^&*()-_=+[]{}")

    if not pools:
        raise ValueError("At least one character set must be enabled.")

    alphabet = "".join(pools)
    length = max(length, len(pools))  # guarantee room for at least one of each

    # Guarantee at least one character from each selected pool, then fill
    # the rest randomly, then shuffle so the guaranteed chars aren't
    # predictably placed at the front.
    result = [secrets.choice(pool) for pool in pools]
    result += [secrets.choice(alphabet) for _ in range(length - len(pools))]

    # Fisher-Yates shuffle using the secrets module for unpredictability.
    for i in range(len(result) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        result[i], result[j] = result[j], result[i]

    return "".join(result)


@dataclass
class StrengthResult:
    score: int  # 0-4 (very weak .. very strong)
    label: str
    entropy_bits: float
    warnings: list[str] = field(default_factory=list)


def estimate_strength(password: str) -> StrengthResult:
    """
    Estimate password strength using a Shannon-entropy-style heuristic
    plus penalties for common patterns. This is a local, offline
    approximation — no external service or dictionary is used beyond
    a small built-in common-password list.
    """
    warnings: list[str] = []

    if not password:
        return StrengthResult(0, "Empty", 0.0, ["No password set."])

    pool_size = 0
    if re.search(r"[a-z]", password):
        pool_size += 26
    if re.search(r"[A-Z]", password):
        pool_size += 26
    if re.search(r"[0-9]", password):
        pool_size += 10
    if re.search(r"[^a-zA-Z0-9]", password):
        pool_size += 32

    pool_size = max(pool_size, 1)
    entropy_bits = len(password) * math.log2(pool_size)

    if password.lower() in COMMON_PASSWORDS:
        entropy_bits = min(entropy_bits, 10.0)
        warnings.append("This is one of the most commonly used passwords.")

    if re.fullmatch(r"[0-9]+", password):
        warnings.append("Numbers only — much easier to brute-force.")
        entropy_bits *= 0.5

    if re.search(r"(.)\1{2,}", password):
        warnings.append("Contains repeated characters (e.g. 'aaa').")
        entropy_bits *= 0.85

    if re.search(r"(0123|1234|2345|3456|4567|5678|6789|abcd|bcde|cdef)", password.lower()):
        warnings.append("Contains a predictable sequence.")
        entropy_bits *= 0.85

    if len(password) < 8:
        warnings.append("Shorter than 8 characters.")

    if entropy_bits < 28:
        score, label = 0, "Very Weak"
    elif entropy_bits < 36:
        score, label = 1, "Weak"
    elif entropy_bits < 60:
        score, label = 2, "Fair"
    elif entropy_bits < 80:
        score, label = 3, "Strong"
    else:
        score, label = 4, "Very Strong"

    return StrengthResult(score=score, label=label, entropy_bits=entropy_bits, warnings=warnings)


def find_reused_passwords(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    """
    Return a mapping of {password: [entry_id, ...]} for every password
    used by two or more entries. Empty passwords are ignored.
    """
    counter: Counter[str] = Counter(e["password"] for e in entries if e.get("password"))
    reused_passwords = {pw for pw, count in counter.items() if count > 1}

    result: dict[str, list[str]] = {pw: [] for pw in reused_passwords}
    for e in entries:
        pw = e.get("password", "")
        if pw in reused_passwords:
            result[pw].append(e["id"])
    return result


def find_weak_entries(entries: list[dict[str, Any]], threshold_score: int = 1) -> list[str]:
    """Return entry ids whose password strength score is <= threshold_score."""
    weak_ids = []
    for e in entries:
        pw = e.get("password", "")
        if not pw:
            continue
        result = estimate_strength(pw)
        if result.score <= threshold_score:
            weak_ids.append(e["id"])
    return weak_ids
