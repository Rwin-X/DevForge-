"""Unit tests for passcheck.core.strength. Runs with no display attached."""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from passcheck.core.strength import score_password, StrengthLevel


def test_empty_password():
    result = score_password("")
    assert result.score == 0
    assert result.level == StrengthLevel.VERY_WEAK
    print("test_empty_password OK")


def test_common_password():
    result = score_password("password")
    assert result.level == StrengthLevel.VERY_WEAK
    assert any("commonly used" in issue for issue in result.issues)
    print("test_common_password OK")


def test_sequential_pattern():
    result = score_password("abcd1234")
    assert any("sequential" in issue for issue in result.issues)
    print("test_sequential_pattern OK")


def test_repeated_chars():
    result = score_password("aaabbbccc111")
    assert any("repeated" in issue for issue in result.issues)
    print("test_repeated_chars OK")


def test_strong_password():
    result = score_password("Tr!ck7-Wolverine-Mango9")
    assert result.level in (StrengthLevel.STRONG, StrengthLevel.VERY_STRONG)
    assert result.score > 60
    print(f"test_strong_password OK (score={result.score})")


def test_single_char_type():
    result = score_password("aaaaaaaaaaaaaaaa")
    assert any("only one character type" in issue for issue in result.issues)
    print("test_single_char_type OK")


def test_short_password():
    result = score_password("Ab1!")
    assert any("Shorter than 8" in issue for issue in result.issues)
    print("test_short_password OK")


def test_crack_time_increases_with_entropy():
    weak = score_password("password1")
    strong = score_password("xQ9#mK2$vL8@pR5!")
    assert strong.entropy_bits > weak.entropy_bits
    print(
        f"test_crack_time_increases_with_entropy OK "
        f"(weak={weak.crack_time_estimate}, strong={strong.crack_time_estimate})"
    )


if __name__ == "__main__":
    test_empty_password()
    test_common_password()
    test_sequential_pattern()
    test_repeated_chars()
    test_strong_password()
    test_single_char_type()
    test_short_password()
    test_crack_time_increases_with_entropy()
    print("\nAll core tests passed.")
