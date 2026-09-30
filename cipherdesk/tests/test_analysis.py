import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.analysis import (
    analyze,
    best_caesar_shift,
    brute_force_caesar,
    guess_nature,
    index_of_coincidence,
    kasiski_examination,
    letter_counts,
)
from core.ciphers import caesar_shift


def test_letter_counts_basic():
    counts, total = letter_counts("AABC")
    assert counts["A"] == 2
    assert counts["B"] == 1
    assert counts["C"] == 1
    assert total == 4


def test_letter_counts_ignores_non_letters():
    counts, total = letter_counts("A1B2C3 سلام")
    assert total == 3


def test_index_of_coincidence_uniform_is_low():
    # a string using every letter equally has low IC
    text = string_of_each_letter_once = "".join(chr(65 + i) for i in range(26)) * 10
    counts, total = letter_counts(string_of_each_letter_once)
    ic = index_of_coincidence(counts, total)
    assert 0.03 < ic < 0.06


def test_index_of_coincidence_repetitive_is_high():
    text = "AAAAAAAAAA"
    counts, total = letter_counts(text)
    ic = index_of_coincidence(counts, total)
    assert ic > 0.9


def test_guess_nature_thresholds():
    assert guess_nature(5, 0.05) == "Need more letters"
    assert guess_nature(100, 0.07) == "Monoalphabetic / transposition"
    assert guess_nature(100, 0.03) == "Polyalphabetic / random"


def test_brute_force_caesar_finds_correct_shift():
    plaintext = (
        "This is a reasonably long piece of English text used to test "
        "whether the Caesar brute force solver can correctly identify "
        "the shift that was used to encrypt it in the first place"
    )
    shift = 11
    ciphertext = caesar_shift(plaintext, shift, decrypt=False)
    scored = brute_force_caesar(ciphertext)
    best_shift = best_caesar_shift(scored)
    assert best_shift == shift


def test_kasiski_examination_empty_for_short_text():
    assert kasiski_examination("too short") == []


def test_kasiski_examination_finds_repeats():
    # Construct text with an obvious repeated trigram at a fixed distance,
    # long enough to clear the 60-letter minimum the function requires.
    text = "THE" + ("X" * 17) + "THE" + ("Y" * 17) + "THE" + ("Z" * 20)
    assert len(text) >= 60
    result = kasiski_examination(text)
    # distances are both 20; key length 20, 10, 5, 4, 2 all divide 20
    assert len(result) > 0


def test_analyze_returns_full_report():
    report = analyze("A reasonably long sentence for a full analysis pass.")
    assert report.total_letters > 0
    assert 0 <= report.index_of_coincidence <= 1
    assert isinstance(report.caesar_candidates, list)
