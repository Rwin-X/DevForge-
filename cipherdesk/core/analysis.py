"""Cryptanalysis helpers: letter frequency, index of coincidence, a
brute-force Caesar solver, and Kasiski examination for guessing a
Vigenere key length. Pure Python, no PyQt imports.
"""

from __future__ import annotations

import string
from typing import Dict, List, Tuple

from core.ciphers import caesar_shift
from core.models import FrequencyReport

ALPHA = string.ascii_uppercase

ENGLISH_FREQ = {
    "A": 8.17, "B": 1.49, "C": 2.78, "D": 4.25, "E": 12.70, "F": 2.23,
    "G": 2.02, "H": 6.09, "I": 7.00, "J": 0.15, "K": 0.77, "L": 4.03,
    "M": 2.41, "N": 6.75, "O": 7.51, "P": 1.93, "Q": 0.10, "R": 5.99,
    "S": 6.33, "T": 9.06, "U": 2.76, "V": 0.98, "W": 2.36, "X": 0.15,
    "Y": 1.97, "Z": 0.07,
}


def letter_counts(text: str) -> Tuple[Dict[str, int], int]:
    counts = {letter: 0 for letter in ALPHA}
    total = 0
    for ch in text.upper():
        if ch in counts:
            counts[ch] += 1
            total += 1
    return counts, total


def index_of_coincidence(counts: Dict[str, int], total: int) -> float:
    if total < 2:
        return 0.0
    numerator = sum(c * (c - 1) for c in counts.values())
    return numerator / (total * (total - 1))


def english_fit_score(counts: Dict[str, int], total: int) -> float:
    """Chi-squared-style fit against English letter frequencies. Lower is
    a better match."""
    if total == 0:
        return float("inf")
    score = 0.0
    for letter in ALPHA:
        observed = counts[letter]
        expected = (ENGLISH_FREQ[letter] / 100) * total
        score += (observed - expected) ** 2 / (expected or 0.01)
    return score


def guess_nature(total_letters: int, ic: float) -> str:
    if total_letters < 20:
        return "Need more letters"
    if ic > 0.058:
        return "Monoalphabetic / transposition"
    if ic < 0.045:
        return "Polyalphabetic / random"
    return "Ambiguous"


def brute_force_caesar(text: str) -> List[Tuple[int, str, float]]:
    """Try all 26 Caesar shifts as decryption attempts, scored by fit to
    English. Returns a list of (shift, decrypted_text, score) sorted by
    shift (0..25), with the best-fit shift identifiable by minimum score."""
    results = []
    for shift in range(26):
        attempt = caesar_shift(text, shift, decrypt=True)
        counts, total = letter_counts(attempt)
        score = english_fit_score(counts, total)
        results.append((shift, attempt, score))
    return results


def best_caesar_shift(scored: List[Tuple[int, str, float]]) -> int:
    return min(scored, key=lambda item: item[2])[0]


def kasiski_examination(text: str) -> List[Tuple[int, int]]:
    """Find repeated trigrams and the distances between their
    occurrences, then score candidate key lengths 2..20 by how many of
    those distances they divide evenly. Returns [(key_length, score), ...]
    sorted by score descending, top 5."""
    clean = "".join(c for c in text.upper() if c.isalpha())
    if len(clean) < 60:
        return []

    positions: Dict[str, List[int]] = {}
    for i in range(len(clean) - 2):
        tri = clean[i:i + 3]
        positions.setdefault(tri, []).append(i)

    distances = []
    for occurrences in positions.values():
        if len(occurrences) < 2:
            continue
        for i in range(1, len(occurrences)):
            distances.append(occurrences[i] - occurrences[0])

    if not distances:
        return []

    scores = {}
    for key_len in range(2, 21):
        scores[key_len] = sum(1 for d in distances if d % key_len == 0)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return ranked[:5]


def analyze(text: str) -> FrequencyReport:
    counts, total = letter_counts(text)
    ic = index_of_coincidence(counts, total)
    caesar = brute_force_caesar(text) if total >= 5 else []
    kasiski = kasiski_examination(text)
    return FrequencyReport(
        letter_counts=counts,
        total_letters=total,
        index_of_coincidence=ic,
        caesar_candidates=caesar,
        kasiski_candidates=kasiski,
    )
