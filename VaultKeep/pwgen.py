"""
pwgen.py

Cryptographically secure password generation and strength estimation.
Uses `secrets` (CSPRNG) exclusively - never `random`.
"""

from __future__ import annotations

import math
import secrets
import string

AMBIGUOUS = set("Il1O0|")

LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>/?~"

WORDLIST = [
    "orbit", "cinder", "maple", "quartz", "raven", "ember", "granite", "willow",
    "harbor", "prairie", "onyx", "cobalt", "juniper", "lantern", "meadow", "nimbus",
    "opal", "pixel", "quartet", "ridge", "solstice", "tundra", "umbra", "velvet",
    "wisteria", "xenon", "yonder", "zephyr", "basalt", "canyon", "delta", "ember",
    "falcon", "glacier", "horizon", "indigo", "jasper", "kestrel", "lumen", "monarch",
]


def generate_password(
    length: int = 20,
    use_lower: bool = True,
    use_upper: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    avoid_ambiguous: bool = True,
) -> str:
    pool = ""
    required: list[str] = []
    if use_lower:
        chars = "".join(c for c in LOWER if not avoid_ambiguous or c not in AMBIGUOUS)
        pool += chars
        required.append(secrets.choice(chars))
    if use_upper:
        chars = "".join(c for c in UPPER if not avoid_ambiguous or c not in AMBIGUOUS)
        pool += chars
        required.append(secrets.choice(chars))
    if use_digits:
        chars = "".join(c for c in DIGITS if not avoid_ambiguous or c not in AMBIGUOUS)
        pool += chars
        required.append(secrets.choice(chars))
    if use_symbols:
        chars = "".join(c for c in SYMBOLS if not avoid_ambiguous or c not in AMBIGUOUS)
        pool += chars
        required.append(secrets.choice(chars))

    if not pool:
        pool = LOWER + DIGITS
        required = [secrets.choice(pool)]

    length = max(length, len(required))
    remaining = length - len(required)
    body = [secrets.choice(pool) for _ in range(remaining)]
    all_chars = required + body

    # Fisher-Yates shuffle using the CSPRNG so required characters
    # aren't predictably placed at the front.
    for i in range(len(all_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        all_chars[i], all_chars[j] = all_chars[j], all_chars[i]

    return "".join(all_chars)


def generate_passphrase(num_words: int = 5, separator: str = "-", capitalize: bool = True,
                         add_number: bool = True) -> str:
    words = [secrets.choice(WORDLIST) for _ in range(num_words)]
    if capitalize:
        words = [w.capitalize() for w in words]
    phrase = separator.join(words)
    if add_number:
        phrase += separator + str(secrets.randbelow(9000) + 1000)
    return phrase


def estimate_entropy_bits(password: str) -> float:
    """Rough Shannon-style entropy estimate based on character pool size."""
    if not password:
        return 0.0
    pool = 0
    if any(c in LOWER for c in password):
        pool += 26
    if any(c in UPPER for c in password):
        pool += 26
    if any(c in DIGITS for c in password):
        pool += 10
    if any(c in SYMBOLS for c in password):
        pool += len(SYMBOLS)
    if any(c not in (LOWER + UPPER + DIGITS + SYMBOLS) for c in password):
        pool += 32  # unicode / other, conservative bump
    pool = max(pool, 1)
    return len(password) * math.log2(pool)


def strength_label(password: str) -> tuple[str, float, str]:
    """Returns (label, score_0_to_100, color_hex) for UI display."""
    if not password:
        return "Empty", 0.0, "#555555"

    bits = estimate_entropy_bits(password)
    score = min(100.0, (bits / 100.0) * 100.0)

    common_patterns = ["password", "123456", "qwerty", "letmein", "admin", "welcome"]
    lowered = password.lower()
    penalty = 0
    if any(p in lowered for p in common_patterns):
        penalty += 40
    if password.isdigit():
        penalty += 20
    if len(set(password)) < max(4, len(password) // 3):
        penalty += 15

    score = max(0.0, score - penalty)

    if score < 25:
        return "Very Weak", score, "#E74C3C"
    elif score < 45:
        return "Weak", score, "#E67E22"
    elif score < 65:
        return "Fair", score, "#F1C40F"
    elif score < 85:
        return "Strong", score, "#3FA7FF"
    else:
        return "Very Strong", score, "#2ECC71"
