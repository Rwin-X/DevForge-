import pytest

from passvault.password_utils import (
    generate_password, estimate_strength,
    find_reused_passwords, find_weak_entries,
)
from passvault.models import new_entry


def test_generate_password_default_length():
    pw = generate_password()
    assert len(pw) == 20


def test_generate_password_custom_length():
    pw = generate_password(length=32)
    assert len(pw) == 32


def test_generate_password_charset_toggles():
    pw = generate_password(length=30, use_upper=False, use_symbols=False, use_digits=False)
    assert pw.islower()
    assert pw.isalpha()


def test_generate_password_no_charset_raises():
    with pytest.raises(ValueError):
        generate_password(use_upper=False, use_lower=False, use_digits=False, use_symbols=False)


def test_generate_password_is_random():
    pw1 = generate_password()
    pw2 = generate_password()
    assert pw1 != pw2


def test_strength_empty_password():
    result = estimate_strength("")
    assert result.score == 0
    assert result.label == "Empty"


def test_strength_common_password_is_flagged():
    result = estimate_strength("password")
    assert result.score == 0
    assert any("commonly used" in w for w in result.warnings)


def test_strength_short_password_is_weak():
    result = estimate_strength("ab1")
    assert result.score <= 1


def test_strength_long_random_password_is_strong():
    result = estimate_strength("xQ7!vR9$mK2#pL6&wZ4@")
    assert result.score >= 3


def test_strength_numeric_only_penalized():
    result = estimate_strength("123456789012")
    assert any("Numbers only" in w for w in result.warnings)


def test_find_reused_passwords_detects_duplicates():
    entries = [
        new_entry(name="A", password="same123"),
        new_entry(name="B", password="same123"),
        new_entry(name="C", password="different456"),
    ]
    reused = find_reused_passwords(entries)
    assert "same123" in reused
    assert len(reused["same123"]) == 2
    assert "different456" not in reused


def test_find_reused_passwords_ignores_empty():
    entries = [
        new_entry(name="A", password=""),
        new_entry(name="B", password=""),
    ]
    reused = find_reused_passwords(entries)
    assert reused == {}


def test_find_weak_entries():
    entries = [
        new_entry(name="Weak", password="123"),
        new_entry(name="Strong", password="xQ7!vR9$mK2#pL6&wZ4@"),
    ]
    weak_ids = find_weak_entries(entries)
    assert entries[0]["id"] in weak_ids
    assert entries[1]["id"] not in weak_ids
