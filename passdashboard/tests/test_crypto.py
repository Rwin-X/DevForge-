import pytest

from passvault.crypto import (
    generate_salt, derive_key, make_fernet,
    encrypt_bytes, decrypt_bytes, WrongPasswordError,
)


def test_salts_are_unique():
    a = generate_salt()
    b = generate_salt()
    assert a != b
    assert len(a) == 16


def test_same_password_and_salt_give_same_key():
    salt = generate_salt()
    k1 = derive_key("hunter2", salt)
    k2 = derive_key("hunter2", salt)
    assert k1 == k2


def test_different_salt_gives_different_key():
    salt1 = generate_salt()
    salt2 = generate_salt()
    k1 = derive_key("hunter2", salt1)
    k2 = derive_key("hunter2", salt2)
    assert k1 != k2


def test_empty_password_raises():
    with pytest.raises(ValueError):
        derive_key("", generate_salt())


def test_round_trip_encrypt_decrypt():
    salt = generate_salt()
    fernet = make_fernet("correct horse battery staple", salt)
    plaintext = b'{"hello": "world"}'
    token = encrypt_bytes(fernet, plaintext)
    assert token != plaintext
    result = decrypt_bytes(fernet, token)
    assert result == plaintext


def test_wrong_password_raises_wrong_password_error():
    salt = generate_salt()
    fernet_right = make_fernet("correct-password", salt)
    fernet_wrong = make_fernet("incorrect-password", salt)

    token = encrypt_bytes(fernet_right, b"secret data")
    with pytest.raises(WrongPasswordError):
        decrypt_bytes(fernet_wrong, token)


def test_ciphertext_does_not_leak_plaintext():
    salt = generate_salt()
    fernet = make_fernet("mypassword", salt)
    token = encrypt_bytes(fernet, b"MySuperSecretPassword123")
    assert b"MySuperSecretPassword123" not in token
