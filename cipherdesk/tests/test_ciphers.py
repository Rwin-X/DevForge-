"""Tests for core/ciphers.py. Pure Python - these never touch Qt at
all, since core/ has zero widget dependencies by design.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core.ciphers import CIPHER_BY_ID, CIPHER_REGISTRY, CipherError, _rsa_generate_keypair


def get(cipher_id):
    return CIPHER_BY_ID[cipher_id]


# ---------------------------------------------------------------------
# registry sanity
# ---------------------------------------------------------------------

def test_registry_has_no_duplicate_ids():
    ids = [c.id for c in CIPHER_REGISTRY]
    assert len(ids) == len(set(ids))


def test_registry_nonempty():
    assert len(CIPHER_REGISTRY) >= 30


# ---------------------------------------------------------------------
# classical round-trips
# ---------------------------------------------------------------------

@pytest.mark.parametrize("cipher_id,key1,key2", [
    ("caesar", "7", None),
    ("rot13", None, None),
    ("rot47", None, None),
    ("atbash", None, None),
    ("affine", "5", "8"),
    ("vigenere", "KEYWORD", None),
    ("beaufort", "KEYWORD", None),
    ("autokey", "PRIMER", None),
    ("playfair", "KEYWORD", None),
    ("polybius", None, None),
    ("railfence", "4", None),
    ("columnar", "ZEBRA", None),
    ("baconian", None, None),
    ("morse", None, None),
    ("xor", "secretkey", None),
])
def test_classical_round_trip(cipher_id, key1, key2):
    spec = get(cipher_id)
    plaintext = "The quick brown fox jumps over the lazy dog"
    encrypted = spec.encrypt_fn(plaintext, key1, key2)
    decrypted = spec.decrypt_fn(encrypted, key1, key2)
    # Some classical ciphers normalize case and/or strip non-letters as
    # part of their definition (Playfair, Polybius, Baconian, Morse) -
    # compare against the letters-only uppercase form for those.
    normalizing_ciphers = {"playfair", "polybius", "baconian", "morse"}
    if cipher_id in normalizing_ciphers:
        expected = "".join(c for c in plaintext.upper() if c.isalpha())
        actual = "".join(c for c in decrypted.upper() if c.isalpha())
        if cipher_id in ("playfair", "polybius"):
            # These merge J into I (classic 5x5 grid convention).
            expected = expected.replace("J", "I")
        if cipher_id == "playfair":
            # Playfair pads a trailing unpaired letter with X - allow one
            # optional trailing X, but don't strip X's that are part of
            # the original message (e.g. "FOX").
            assert actual == expected or actual == expected + "X"
        else:
            assert actual == expected
    else:
        assert decrypted == plaintext


def test_caesar_known_vector():
    spec = get("caesar")
    assert spec.encrypt_fn("ABC", "3", None) == "DEF"
    assert spec.decrypt_fn("DEF", "3", None) == "ABC"


def test_rot13_is_self_reciprocal():
    spec = get("rot13")
    text = "Hello World"
    once = spec.encrypt_fn(text, None, None)
    twice = spec.encrypt_fn(once, None, None)
    assert twice == text


def test_atbash_known_vector():
    spec = get("atbash")
    assert spec.encrypt_fn("A", None, None) == "Z"
    assert spec.encrypt_fn("Z", None, None) == "A"


def test_affine_rejects_non_coprime_a():
    spec = get("affine")
    with pytest.raises(CipherError):
        spec.encrypt_fn("TEST", "2", "5")  # gcd(2,26) != 1


def test_vigenere_requires_alpha_key():
    spec = get("vigenere")
    with pytest.raises(CipherError):
        spec.encrypt_fn("TEST", "12345", None)


# ---------------------------------------------------------------------
# encodings
# ---------------------------------------------------------------------

@pytest.mark.parametrize("cipher_id", ["base64", "base64url", "base32", "hex", "binary", "urlencode"])
def test_encoding_round_trip(cipher_id):
    spec = get(cipher_id)
    plaintext = "Hello, World! 123"
    encoded = spec.encrypt_fn(plaintext, None, None)
    decoded = spec.decrypt_fn(encoded, None, None)
    assert decoded == plaintext


def test_encoding_round_trip_persian_text():
    """Persian/UTF-8 text must survive every encoding round-trip."""
    plaintext = "سلام دنیا"
    for cipher_id in ["base64", "base64url", "base32", "hex", "binary", "urlencode"]:
        spec = get(cipher_id)
        encoded = spec.encrypt_fn(plaintext, None, None)
        decoded = spec.decrypt_fn(encoded, None, None)
        assert decoded == plaintext, f"{cipher_id} failed on Persian text"


def test_hex_decode_rejects_invalid():
    spec = get("hex")
    with pytest.raises(CipherError):
        spec.decrypt_fn("not hex!!", None, None)


# ---------------------------------------------------------------------
# hashes (one-way)
# ---------------------------------------------------------------------

@pytest.mark.parametrize("cipher_id", ["md5", "sha-1", "sha-256", "sha-512"])
def test_hash_produces_hex_digest(cipher_id):
    spec = get(cipher_id)
    digest = spec.encrypt_fn("test input", None, None)
    assert all(c in "0123456789abcdef" for c in digest)
    assert len(digest) > 0


def test_hash_known_vector_md5():
    spec = get("md5")
    # Standard known MD5 test vector
    assert spec.encrypt_fn("", None, None) == "d41d8cd98f00b204e9800998ecf8427e"


def test_hash_decrypt_always_raises():
    spec = get("sha-256")
    with pytest.raises(CipherError):
        spec.decrypt_fn("anything", None, None)


def test_hmac_requires_key():
    spec = get("hmac-sha256")
    with pytest.raises(CipherError):
        spec.encrypt_fn("text", "", None)


def test_hmac_known_vector():
    spec = get("hmac-sha256")
    # HMAC-SHA256("key", "The quick brown fox jumps over the lazy dog")
    result = spec.encrypt_fn("The quick brown fox jumps over the lazy dog", "key", None)
    assert result == "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"


# ---------------------------------------------------------------------
# AES / DES / 3DES / RC4 - text round trip
# ---------------------------------------------------------------------

@pytest.mark.parametrize("cipher_id", [
    "aes-cbc", "aes-ecb", "aes-ctr", "aes-cfb", "aes-ofb", "triple-des", "des", "rc4",
])
def test_symmetric_text_round_trip(cipher_id):
    spec = get(cipher_id)
    plaintext = "The quick brown fox jumps over the lazy dog"
    passphrase = "correct horse battery staple"
    ct = spec.encrypt_fn(plaintext, passphrase, None)
    pt = spec.decrypt_fn(ct, passphrase, None)
    assert pt == plaintext


@pytest.mark.parametrize("cipher_id", [
    "aes-cbc", "aes-ecb", "aes-ctr", "aes-cfb", "aes-ofb", "triple-des", "des", "rc4",
])
def test_symmetric_wrong_passphrase_fails(cipher_id):
    spec = get(cipher_id)
    ct = spec.encrypt_fn("secret message", "correct-password", None)
    with pytest.raises(CipherError):
        spec.decrypt_fn(ct, "wrong-password", None)


@pytest.mark.parametrize("cipher_id", ["aes-cbc", "aes-ctr", "triple-des", "des", "rc4"])
def test_symmetric_file_round_trip_binary(cipher_id):
    spec = get(cipher_id)
    data = bytes(range(256)) * 4  # 1024 bytes covering all byte values
    ct = spec.file_encrypt_fn(data, "file-passphrase", None)
    pt = spec.file_decrypt_fn(ct, "file-passphrase", None)
    assert pt == data


@pytest.mark.parametrize("length", [0, 1, 5, 16, 17, 100, 1000])
def test_aes_cbc_file_various_lengths(length):
    spec = get("aes-cbc")
    data = bytes(i % 256 for i in range(length))
    ct = spec.file_encrypt_fn(data, "pw", None)
    pt = spec.file_decrypt_fn(ct, "pw", None)
    assert pt == data


def test_xor_file_round_trip():
    spec = get("xor")
    data = bytes(range(256))
    ct = spec.file_encrypt_fn(data, "mykey", None)
    pt = spec.file_decrypt_fn(ct, "mykey", None)
    assert pt == data


# ---------------------------------------------------------------------
# RSA
# ---------------------------------------------------------------------

def test_rsa_keypair_generation_and_round_trip():
    public_pem, private_pem = _rsa_generate_keypair(1024)  # smaller for test speed
    spec = get("rsa")
    plaintext = "a short secret"
    ct = spec.encrypt_fn(plaintext, public_pem, None)
    pt = spec.decrypt_fn(ct, public_pem, private_pem)
    assert pt == plaintext


def test_rsa_wrong_private_key_fails():
    public_pem, _ = _rsa_generate_keypair(1024)
    _, other_private_pem = _rsa_generate_keypair(1024)
    spec = get("rsa")
    ct = spec.encrypt_fn("secret", public_pem, None)
    with pytest.raises(CipherError):
        spec.decrypt_fn(ct, public_pem, other_private_pem)


def test_rsa_hybrid_file_round_trip():
    public_pem, private_pem = _rsa_generate_keypair(1024)
    spec = get("rsa")
    data = bytes(range(256)) * 10  # larger than RSA's direct capacity
    ct = spec.file_encrypt_fn(data, public_pem, None)
    pt = spec.file_decrypt_fn(ct, public_pem, private_pem)
    assert pt == data


def test_rsa_missing_public_key_raises():
    spec = get("rsa")
    with pytest.raises(CipherError):
        spec.encrypt_fn("text", "", None)


# ---------------------------------------------------------------------
# byte_safe flag correctness - only ciphers that should be byte_safe are
# ---------------------------------------------------------------------

def test_byte_safe_ciphers_have_file_functions():
    for spec in CIPHER_REGISTRY:
        if spec.byte_safe:
            assert spec.file_encrypt_fn is not None, f"{spec.id} claims byte_safe but has no file_encrypt_fn"
            assert spec.file_decrypt_fn is not None, f"{spec.id} claims byte_safe but has no file_decrypt_fn"


def test_classical_ciphers_are_not_byte_safe():
    for cid in ("caesar", "vigenere", "playfair", "railfence", "morse"):
        assert not get(cid).byte_safe
