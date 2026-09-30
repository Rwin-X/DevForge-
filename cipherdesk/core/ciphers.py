"""Cipher engine: every algorithm Cipherdesk supports.

Pure Python. No PyQt imports of any kind. Every algorithm is exposed
as a CipherSpec with encrypt_fn/decrypt_fn (text) and, where the
operation is byte-safe, file_encrypt_fn/file_decrypt_fn (raw bytes).
"""

from __future__ import annotations

import base64
import hashlib
import hmac as hmac_lib
import json
import string
from typing import List

from Crypto.Cipher import AES, DES, DES3, ARC4
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as RSA_PKCS1_v1_5
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256 as CryptoSHA256

from core.models import CipherSpec, KeyFieldSpec, KeyKind

ALPHA = string.ascii_uppercase


class CipherError(Exception):
    """Raised for any user-facing cipher failure (bad key, bad input, etc.)."""


# ---------------------------------------------------------------------
# helpers shared by several ciphers
# ---------------------------------------------------------------------

def _mod(n: int, m: int) -> int:
    return ((n % m) + m) % m


def _gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def _mod_inverse(a: int, m: int) -> int | None:
    a = _mod(a, m)
    for x in range(1, m):
        if _mod(a * x, m) == 1:
            return x
    return None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CipherError(message)


# ---------------------------------------------------------------------
# classical: shift / substitution family
# ---------------------------------------------------------------------

def _caesar_shift(text: str, shift: int, decrypt: bool) -> str:
    s = -shift if decrypt else shift
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr(_mod(ord(ch) - base + s, 26) + base))
        else:
            out.append(ch)
    return "".join(out)


def _rot13(text: str) -> str:
    return _caesar_shift(text, 13, False)


def _rot47(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 33 <= code <= 126:
            out.append(chr(33 + _mod(code - 33 + 47, 94)))
        else:
            out.append(ch)
    return "".join(out)


def _atbash(text: str) -> str:
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr(base + (25 - (ord(ch) - base))))
        else:
            out.append(ch)
    return "".join(out)


def _clean_key_letters(key: str) -> str:
    letters = "".join(c for c in key.upper() if c.isalpha())
    _require(bool(letters), "Key must contain letters.")
    return letters


def _vigenere(text: str, key: str, decrypt: bool) -> str:
    k = _clean_key_letters(key)
    out = []
    ki = 0
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            shift = ord(k[ki % len(k)]) - ord("A")
            ki += 1
            s = -shift if decrypt else shift
            out.append(chr(_mod(ord(ch) - base + s, 26) + base))
        else:
            out.append(ch)
    return "".join(out)


def _beaufort(text: str, key: str) -> str:
    k = _clean_key_letters(key)
    out = []
    ki = 0
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            p = ord(ch) - base
            kc = ord(k[ki % len(k)]) - ord("A")
            ki += 1
            out.append(chr(_mod(kc - p, 26) + base))
        else:
            out.append(ch)
    return "".join(out)


def _autokey(text: str, key: str, decrypt: bool) -> str:
    k0 = _clean_key_letters(key)
    out = []
    if not decrypt:
        stream = k0 + "".join(c for c in text.upper() if c.isalpha())
        si = 0
        for ch in text:
            if ch.isalpha():
                base = ord("A") if ch.isupper() else ord("a")
                shift = ord(stream[si]) - ord("A")
                si += 1
                out.append(chr(_mod(ord(ch) - base + shift, 26) + base))
            else:
                out.append(ch)
    else:
        stream = list(k0)
        si = 0
        for ch in text:
            if ch.isalpha():
                base = ord("A") if ch.isupper() else ord("a")
                shift = ord(stream[si]) - ord("A")
                p = _mod(ord(ch) - base - shift, 26)
                stream.append(chr(p + ord("A")))
                si += 1
                out.append(chr(p + base))
            else:
                out.append(ch)
    return "".join(out)


def _rail_fence(text: str, rails: str, decrypt: bool) -> str:
    try:
        n = int(rails)
    except (TypeError, ValueError):
        raise CipherError("Rail count must be an integer.")
    _require(n >= 2, "Rail count must be an integer >= 2.")
    length = len(text)

    pattern: List[int] = []
    rail, direction = 0, 1
    for _ in range(length):
        pattern.append(rail)
        if rail == 0:
            direction = 1
        elif rail == n - 1:
            direction = -1
        rail += direction

    if not decrypt:
        rows: List[List[str]] = [[] for _ in range(n)]
        for i, ch in enumerate(text):
            rows[pattern[i]].append(ch)
        return "".join("".join(r) for r in rows)
    else:
        counts = [0] * n
        for r in pattern:
            counts[r] += 1
        rows = []
        idx = 0
        for r in range(n):
            rows.append(list(text[idx: idx + counts[r]]))
            idx += counts[r]
        row_pos = [0] * n
        out = []
        for i in range(length):
            r = pattern[i]
            out.append(rows[r][row_pos[r]])
            row_pos[r] += 1
        return "".join(out)


def _columnar_transpose(text: str, key: str, decrypt: bool) -> str:
    _require(bool(key and key.strip()), "Key required (word or number sequence).")
    k = key.strip()
    cols = len(k)
    order = sorted(range(cols), key=lambda i: (k[i].lower(), i))
    col_order = [0] * cols
    for rank, orig in enumerate(order):
        col_order[orig] = rank

    if not decrypt:
        rows = -(-len(text) // cols)  # ceil div
        padded = text.ljust(rows * cols, "\0")
        grid = [list(padded[r * cols:(r + 1) * cols]) for r in range(rows)]
        out = []
        for rank in range(cols):
            col = col_order.index(rank)
            for r in range(rows):
                if grid[r][col] != "\0":
                    out.append(grid[r][col])
        return "".join(out)
    else:
        rows = -(-len(text) // cols)
        total_cells = rows * cols
        short_cols = total_cells - len(text)
        grid = [[None] * cols for _ in range(rows)]
        pos = 0
        for rank in range(cols):
            col = col_order.index(rank)
            col_len = rows if col < (cols - short_cols) else rows - 1
            for r in range(col_len):
                grid[r][col] = text[pos]
                pos += 1
        out = []
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] is not None:
                    out.append(grid[r][c])
        return "".join(out)


def _playfair_square(key: str) -> List[str]:
    key = key.upper().replace("J", "I")
    key = "".join(c for c in key if c.isalpha())
    seen = []
    for c in key:
        if c not in seen:
            seen.append(c)
    for c in ALPHA:
        if c != "J" and c not in seen:
            seen.append(c)
    return seen


def _playfair(text: str, key: str, decrypt: bool) -> str:
    _require(bool(key) and any(c.isalpha() for c in key), "Key must contain letters.")
    sq = _playfair_square(key)

    def pos(c: str):
        i = sq.index(c)
        return divmod(i, 5)

    clean = "".join(c for c in text.upper().replace("J", "I") if c.isalpha())
    _require(bool(clean), "Input must contain letters for Playfair.")

    pairs = []
    if not decrypt:
        i = 0
        while i < len(clean):
            a = clean[i]
            b = clean[i + 1] if i + 1 < len(clean) else None
            if b is None:
                pairs.append((a, "X"))
                i += 1
            elif a == b:
                pairs.append((a, "X"))
                i += 1
            else:
                pairs.append((a, b))
                i += 2
    else:
        _require(len(clean) % 2 == 0, "Playfair ciphertext length must be even.")
        for i in range(0, len(clean), 2):
            pairs.append((clean[i], clean[i + 1]))

    out = []
    d = -1 if decrypt else 1
    for a, b in pairs:
        ar, ac = pos(a)
        br, bc = pos(b)
        if ar == br:
            out.append(sq[ar * 5 + _mod(ac + d, 5)])
            out.append(sq[br * 5 + _mod(bc + d, 5)])
        elif ac == bc:
            out.append(sq[_mod(ar + d, 5) * 5 + ac])
            out.append(sq[_mod(br + d, 5) * 5 + bc])
        else:
            out.append(sq[ar * 5 + bc])
            out.append(sq[br * 5 + ac])
    return "".join(out)


def _polybius(text: str, decrypt: bool) -> str:
    sq = _playfair_square("")
    if not decrypt:
        clean = "".join(c for c in text.upper().replace("J", "I") if c.isalpha())
        _require(bool(clean), "Input must contain letters.")
        out = []
        for c in clean:
            i = sq.index(c)
            out.append(f"{i // 5 + 1}{i % 5 + 1}")
        return " ".join(out)
    else:
        nums = text.strip().split()
        out = []
        for pair in nums:
            _require(len(pair) == 2 and pair.isdigit() and pair[0] in "12345" and pair[1] in "12345",
                      f'Invalid Polybius pair: "{pair}"')
            r, c = int(pair[0]) - 1, int(pair[1]) - 1
            out.append(sq[r * 5 + c])
        return "".join(out)


def _baconian_map() -> dict:
    def to_ab(n: int) -> str:
        return format(n, "05b").replace("0", "A").replace("1", "B")
    return {letter: to_ab(i) for i, letter in enumerate(ALPHA)}


def _baconian(text: str, decrypt: bool) -> str:
    mapping = _baconian_map()
    if not decrypt:
        clean = "".join(c for c in text.upper() if c.isalpha())
        _require(bool(clean), "Input must contain letters.")
        return " ".join(mapping[c] for c in clean)
    else:
        reverse = {v: k for k, v in mapping.items()}
        raw = "".join(c for c in text.upper() if c in "AB ")
        tokens = [t for t in raw.split() if t]
        if not tokens:
            flat = "".join(c for c in text.upper() if c in "AB")
            _require(len(flat) % 5 == 0, "Baconian ciphertext must be groups of 5 A/B letters.")
            tokens = [flat[i:i + 5] for i in range(0, len(flat), 5)]
        out = []
        for t in tokens:
            _require(t in reverse, f'Invalid Baconian group: "{t}"')
            out.append(reverse[t])
        return "".join(out)


_MORSE_MAP = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}


def _morse(text: str, decrypt: bool) -> str:
    if not decrypt:
        out = []
        for ch in text.upper():
            if ch == " ":
                out.append("/")
            elif ch in _MORSE_MAP:
                out.append(_MORSE_MAP[ch])
        return " ".join(out)
    else:
        reverse = {v: k for k, v in _MORSE_MAP.items()}
        out = []
        for tok in text.strip().split():
            if tok == "/":
                out.append(" ")
                continue
            _require(tok in reverse, f'Unknown Morse token: "{tok}"')
            out.append(reverse[tok])
        return "".join(out)


def _xor_text_encrypt(text: str, key: str) -> str:
    _require(bool(key), "Key required.")
    data = text.encode("utf-8")
    key_bytes = key.encode("utf-8")
    out = bytes(data[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data)))
    return out.hex()


def _xor_text_decrypt(text: str, key: str) -> str:
    _require(bool(key), "Key required.")
    clean = "".join(text.split())
    _require(bool(clean) and len(clean) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in clean),
              "Ciphertext must be hex.")
    data = bytes.fromhex(clean)
    key_bytes = key.encode("utf-8")
    out = bytes(data[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data)))
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        raise CipherError("Wrong key or corrupted ciphertext (invalid UTF-8 result).")


def _xor_file(data: bytes, key: str) -> bytes:
    _require(bool(key), "Key required.")
    key_bytes = key.encode("utf-8")
    return bytes(data[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data)))


def _affine_encrypt(text: str, a: str, b: str) -> str:
    try:
        A, B = int(a), int(b)
    except (TypeError, ValueError):
        raise CipherError("a and b must be integers.")
    _require(_gcd(A, 26) == 1, "a must be coprime with 26.")
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            x = ord(ch) - base
            out.append(chr(_mod(A * x + B, 26) + base))
        else:
            out.append(ch)
    return "".join(out)


def _affine_decrypt(text: str, a: str, b: str) -> str:
    try:
        A, B = int(a), int(b)
    except (TypeError, ValueError):
        raise CipherError("a and b must be integers.")
    _require(_gcd(A, 26) == 1, "a must be coprime with 26.")
    inv = _mod_inverse(A, 26)
    _require(inv is not None, "a has no modular inverse mod 26.")
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            y = ord(ch) - base
            out.append(chr(_mod(inv * (y - B), 26) + base))
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------
# encodings
# ---------------------------------------------------------------------

def _b64_encode(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _b64_decode(text: str) -> str:
    try:
        return base64.b64decode(text.strip()).decode("utf-8")
    except Exception:
        raise CipherError("Invalid Base64 input.")


def _b64url_encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> str:
    t = text.strip()
    padding = "=" * (-len(t) % 4)
    try:
        return base64.urlsafe_b64decode(t + padding).decode("utf-8")
    except Exception:
        raise CipherError("Invalid Base64 (URL-safe) input.")


def _b32_encode(text: str) -> str:
    return base64.b32encode(text.encode("utf-8")).decode("ascii")


def _b32_decode(text: str) -> str:
    try:
        return base64.b32decode(text.strip().upper()).decode("utf-8")
    except Exception:
        raise CipherError("Invalid Base32 input.")


def _hex_encode(text: str) -> str:
    return text.encode("utf-8").hex()


def _hex_decode(text: str) -> str:
    clean = "".join(text.split())
    _require(bool(clean) and len(clean) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in clean),
              "Invalid hex input.")
    try:
        return bytes.fromhex(clean).decode("utf-8")
    except UnicodeDecodeError:
        raise CipherError("Decoded bytes are not valid UTF-8.")


def _bin_encode(text: str) -> str:
    return " ".join(format(b, "08b") for b in text.encode("utf-8"))


def _bin_decode(text: str) -> str:
    tokens = text.strip().split()
    _require(bool(tokens) and all(len(t) <= 8 and all(c in "01" for c in t) for t in tokens),
              "Invalid binary input.")
    try:
        return bytes(int(t, 2) for t in tokens).decode("utf-8")
    except UnicodeDecodeError:
        raise CipherError("Decoded bytes are not valid UTF-8.")


def _url_encode(text: str) -> str:
    from urllib.parse import quote
    return quote(text, safe="")


def _url_decode(text: str) -> str:
    from urllib.parse import unquote
    try:
        return unquote(text)
    except Exception:
        raise CipherError("Invalid percent-encoded input.")


# ---------------------------------------------------------------------
# hashes / HMAC (one-way)
# ---------------------------------------------------------------------

def _hash_fn(name: str):
    algo_map = {
        "MD5": hashlib.md5,
        "SHA-1": hashlib.sha1,
        "SHA-224": hashlib.sha224,
        "SHA-256": hashlib.sha256,
        "SHA-384": hashlib.sha384,
        "SHA-512": hashlib.sha512,
        "SHA-3": hashlib.sha3_256,
        "RIPEMD-160": None,  # not in stdlib hashlib on most builds
    }

    def enc(text: str, *_):
        if name == "RIPEMD-160":
            try:
                h = hashlib.new("ripemd160")
            except ValueError:
                raise CipherError("RIPEMD-160 is not available in this Python's OpenSSL build.")
            h.update(text.encode("utf-8"))
            return h.hexdigest()
        return algo_map[name](text.encode("utf-8")).hexdigest()

    def dec(*_):
        raise CipherError("Hashes cannot be decrypted or reversed.")

    return enc, dec


def _hmac_fn(digestmod: str):
    def enc(text: str, key: str, *_):
        _require(bool(key), "Key required.")
        return hmac_lib.new(key.encode("utf-8"), text.encode("utf-8"), digestmod).hexdigest()

    def dec(*_):
        raise CipherError("HMAC output cannot be reversed.")

    return enc, dec


# ---------------------------------------------------------------------
# modern symmetric ciphers (AES modes, 3DES, DES, RC4)
# passphrase -> key via PBKDF2-HMAC-SHA256, salt embedded in output
# (OpenSSL "Salted__" prefix format, matching CryptoJS's default so
# files/text encrypted by the web version stay decryptable here too)
# ---------------------------------------------------------------------

_SALTED_PREFIX = b"Salted__"
_KEY_LEN = 32     # 256-bit key
_IV_LEN = 16
_KDF_ITERATIONS = 1  # CryptoJS's default OpenSSL-style KDF is EVP_BytesToKey (MD5-based, 1 round),
                     # so we replicate that exactly rather than PBKDF2 to stay cross-compatible.


def _evp_bytes_to_key(password: bytes, salt: bytes, key_len: int, iv_len: int):
    """Replicates OpenSSL's (and CryptoJS's default) EVP_BytesToKey with MD5,
    so ciphertext produced by the web version of Cipherdesk (CryptoJS) can
    be decrypted here, and vice versa."""
    d = d_i = b""
    while len(d) < key_len + iv_len:
        d_i = hashlib.md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_len], d[key_len:key_len + iv_len]


def _derive_key_iv(passphrase: str, salt: bytes):
    return _evp_bytes_to_key(passphrase.encode("utf-8"), salt, _KEY_LEN, _IV_LEN)


def _aes_encrypt_bytes(data: bytes, passphrase: str, mode_name: str) -> bytes:
    salt = get_random_bytes(8)
    key, iv = _derive_key_iv(passphrase, salt)

    if mode_name == "ECB":
        cipher = AES.new(key, AES.MODE_ECB)
        ct = cipher.encrypt(pad(data, AES.block_size))
        return _SALTED_PREFIX + salt + ct

    mode_map = {
        "CBC": AES.MODE_CBC,
        "CTR": AES.MODE_CTR,
        "CFB": AES.MODE_CFB,
        "OFB": AES.MODE_OFB,
    }
    if mode_name == "CTR":
        cipher = AES.new(key, AES.MODE_CTR, nonce=iv[:8], initial_value=int.from_bytes(iv[8:], "big"))
        ct = cipher.encrypt(data)
    elif mode_name == "CBC":
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        ct = cipher.encrypt(pad(data, AES.block_size))
    else:
        cipher = AES.new(key, mode_map[mode_name], iv=iv)
        ct = cipher.encrypt(data)
    return _SALTED_PREFIX + salt + ct


def _aes_decrypt_bytes(blob: bytes, passphrase: str, mode_name: str) -> bytes:
    _require(blob[:8] == _SALTED_PREFIX, "Not a recognized salted ciphertext.")
    salt = blob[8:16]
    ct = blob[16:]
    key, iv = _derive_key_iv(passphrase, salt)

    try:
        if mode_name == "ECB":
            cipher = AES.new(key, AES.MODE_ECB)
            return unpad(cipher.decrypt(ct), AES.block_size)
        if mode_name == "CTR":
            cipher = AES.new(key, AES.MODE_CTR, nonce=iv[:8], initial_value=int.from_bytes(iv[8:], "big"))
            return cipher.decrypt(ct)
        if mode_name == "CBC":
            cipher = AES.new(key, AES.MODE_CBC, iv=iv)
            return unpad(cipher.decrypt(ct), AES.block_size)
        mode_map = {"CFB": AES.MODE_CFB, "OFB": AES.MODE_OFB}
        cipher = AES.new(key, mode_map[mode_name], iv=iv)
        return cipher.decrypt(ct)
    except Exception:
        raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")


def _aes_mode_cipher(mode_name: str) -> CipherSpec:
    def enc(text: str, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        blob = _aes_encrypt_bytes(text.encode("utf-8"), k1, mode_name)
        return base64.b64encode(blob).decode("ascii")

    def dec(text: str, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        try:
            blob = base64.b64decode(text.strip())
        except Exception:
            raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")
        raw = _aes_decrypt_bytes(blob, k1, mode_name)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")

    def file_enc(data: bytes, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        return _aes_encrypt_bytes(data, k1, mode_name)

    def file_dec(data: bytes, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        return _aes_decrypt_bytes(data, k1, mode_name)

    return CipherSpec(
        id=f"aes-{mode_name.lower()}",
        name=f"AES · {mode_name}",
        group="Symmetric (modern)",
        description=f"AES-256 in {mode_name} mode. Passphrase-derived key, salted output.",
        key1=KeyFieldSpec("Passphrase", "256-bit key derived from this passphrase. Salted output.", "passphrase"),
        byte_safe=True,
        encrypt_fn=enc, decrypt_fn=dec,
        file_encrypt_fn=file_enc, file_decrypt_fn=file_dec,
    )


def _legacy_cipher(name: str, cipher_id: str, description: str, encryptor, decryptor) -> CipherSpec:
    """DES / 3DES / RC4 share the same passphrase -> salted-blob shape as AES."""

    def enc(text: str, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        blob = encryptor(text.encode("utf-8"), k1)
        return base64.b64encode(blob).decode("ascii")

    def dec(text: str, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        try:
            blob = base64.b64decode(text.strip())
        except Exception:
            raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")
        raw = decryptor(blob, k1)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")

    def file_enc(data: bytes, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        return encryptor(data, k1)

    def file_dec(data: bytes, k1: str, *_):
        _require(bool(k1), "Passphrase required.")
        return decryptor(data, k1)

    return CipherSpec(
        id=cipher_id, name=name, group="Symmetric (modern)", description=description,
        key1=KeyFieldSpec("Passphrase", "Key is derived from this passphrase automatically.", "passphrase"),
        byte_safe=True,
        encrypt_fn=enc, decrypt_fn=dec,
        file_encrypt_fn=file_enc, file_decrypt_fn=file_dec,
    )


def _des3_encrypt(data: bytes, passphrase: str) -> bytes:
    salt = get_random_bytes(8)
    key, iv = _evp_bytes_to_key(passphrase.encode("utf-8"), salt, 24, 8)
    # DES3 requires 3 distinct single-DES keys in the classic sense, but
    # pycryptodome accepts a 24-byte key directly for EDE3.
    key = DES3.adjust_key_parity(key)
    cipher = DES3.new(key, DES3.MODE_CBC, iv=iv)
    ct = cipher.encrypt(pad(data, DES3.block_size))
    return _SALTED_PREFIX + salt + ct


def _des3_decrypt(blob: bytes, passphrase: str) -> bytes:
    _require(blob[:8] == _SALTED_PREFIX, "Not a recognized salted ciphertext.")
    salt, ct = blob[8:16], blob[16:]
    key, iv = _evp_bytes_to_key(passphrase.encode("utf-8"), salt, 24, 8)
    key = DES3.adjust_key_parity(key)
    try:
        cipher = DES3.new(key, DES3.MODE_CBC, iv=iv)
        return unpad(cipher.decrypt(ct), DES3.block_size)
    except Exception:
        raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")


def _des_encrypt(data: bytes, passphrase: str) -> bytes:
    salt = get_random_bytes(8)
    key, iv = _evp_bytes_to_key(passphrase.encode("utf-8"), salt, 8, 8)
    cipher = DES.new(key, DES.MODE_CBC, iv=iv)
    ct = cipher.encrypt(pad(data, DES.block_size))
    return _SALTED_PREFIX + salt + ct


def _des_decrypt(blob: bytes, passphrase: str) -> bytes:
    _require(blob[:8] == _SALTED_PREFIX, "Not a recognized salted ciphertext.")
    salt, ct = blob[8:16], blob[16:]
    key, iv = _evp_bytes_to_key(passphrase.encode("utf-8"), salt, 8, 8)
    try:
        cipher = DES.new(key, DES.MODE_CBC, iv=iv)
        return unpad(cipher.decrypt(ct), DES.block_size)
    except Exception:
        raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")


def _rc4_encrypt(data: bytes, passphrase: str) -> bytes:
    salt = get_random_bytes(8)
    key, _ = _evp_bytes_to_key(passphrase.encode("utf-8"), salt, 16, 0)
    cipher = ARC4.new(key)
    return _SALTED_PREFIX + salt + cipher.encrypt(data)


def _rc4_decrypt(blob: bytes, passphrase: str) -> bytes:
    _require(blob[:8] == _SALTED_PREFIX, "Not a recognized salted ciphertext.")
    salt, ct = blob[8:16], blob[16:]
    key, _ = _evp_bytes_to_key(passphrase.encode("utf-8"), salt, 16, 0)
    try:
        cipher = ARC4.new(key)
        return cipher.decrypt(ct)
    except Exception:
        raise CipherError("Decryption failed - wrong passphrase or corrupted ciphertext.")


# ---------------------------------------------------------------------
# RSA (asymmetric) - hybrid encryption for files
# ---------------------------------------------------------------------

def _rsa_generate_keypair(bits: int = 2048):
    key = RSA.generate(bits)
    private_pem = key.export_key().decode("ascii")
    public_pem = key.publickey().export_key().decode("ascii")
    return public_pem, private_pem


def _rsa_encrypt(text: str, public_pem: str, *_):
    _require(bool(public_pem and public_pem.strip()), "Public key required - generate a keypair.")
    try:
        key = RSA.import_key(public_pem.strip())
        cipher = RSA_PKCS1_v1_5.new(key)
        ct = cipher.encrypt(text.encode("utf-8"))
    except Exception:
        raise CipherError("Encryption failed - message may be too long for this key size, or the key is invalid.")
    return base64.b64encode(ct).decode("ascii")


def _rsa_decrypt(text: str, public_pem: str, private_pem: str):
    _require(bool(private_pem and private_pem.strip()), "Private key required to decrypt.")
    sentinel = get_random_bytes(16)
    try:
        key = RSA.import_key(private_pem.strip())
        cipher = RSA_PKCS1_v1_5.new(key)
        ct = base64.b64decode(text.strip())
        pt = cipher.decrypt(ct, sentinel)
        if pt == sentinel or not pt:
            raise CipherError("Decryption failed - wrong private key or corrupted ciphertext.")
        return pt.decode("utf-8")
    except CipherError:
        raise
    except Exception:
        raise CipherError("Decryption failed - wrong private key or corrupted ciphertext.")


def _rsa_file_encrypt(data: bytes, public_pem: str, *_):
    """Hybrid encryption: a random AES-256 key encrypts the file, and RSA
    wraps only that key - RSA alone can only hold ~200 bytes at 2048-bit."""
    _require(bool(public_pem and public_pem.strip()), "Public key required - generate a keypair.")
    aes_key_phrase = base64.b64encode(get_random_bytes(24)).decode("ascii")
    try:
        key = RSA.import_key(public_pem.strip())
        cipher = RSA_PKCS1_v1_5.new(key)
        wrapped_key = cipher.encrypt(aes_key_phrase.encode("utf-8"))
    except Exception:
        raise CipherError("Encryption failed - the public key looks invalid.")
    blob = _aes_encrypt_bytes(data, aes_key_phrase, "CBC")
    payload = {
        "k": base64.b64encode(wrapped_key).decode("ascii"),
        "d": base64.b64encode(blob).decode("ascii"),
    }
    return json.dumps(payload).encode("utf-8")


def _rsa_file_decrypt(data: bytes, public_pem: str, private_pem: str):
    _require(bool(private_pem and private_pem.strip()), "Private key required to decrypt.")
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception:
        raise CipherError("Not a Cipherdesk RSA-encrypted file (expected JSON envelope).")
    _require("k" in payload and "d" in payload, "Malformed RSA file envelope.")
    sentinel = get_random_bytes(16)
    try:
        key = RSA.import_key(private_pem.strip())
        cipher = RSA_PKCS1_v1_5.new(key)
        wrapped_key = base64.b64decode(payload["k"])
        unwrapped = cipher.decrypt(wrapped_key, sentinel)
        if unwrapped == sentinel or not unwrapped:
            raise CipherError("Decryption failed - wrong private key.")
        aes_key_phrase = unwrapped.decode("utf-8")
    except CipherError:
        raise
    except Exception:
        raise CipherError("Decryption failed - wrong private key.")
    blob = base64.b64decode(payload["d"])
    return _aes_decrypt_bytes(blob, aes_key_phrase, "CBC")


# ---------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------

def build_cipher_registry() -> List[CipherSpec]:
    specs: List[CipherSpec] = []

    specs.append(CipherSpec(
        id="caesar", name="Caesar", group="Classical / substitution",
        description="Shifts each letter by a fixed amount - the oldest known substitution cipher.",
        key1=KeyFieldSpec("Shift", "Integer 0-25.", "3", KeyKind.INTEGER),
        encrypt_fn=lambda t, k, *_: _caesar_shift(t, _parse_int(k, "Shift"), False),
        decrypt_fn=lambda t, k, *_: _caesar_shift(t, _parse_int(k, "Shift"), True),
    ))
    specs.append(CipherSpec(
        id="rot13", name="ROT13", group="Classical / substitution",
        description="Caesar shift fixed at 13. Self-reciprocal - applying it twice returns the original.",
        encrypt_fn=lambda t, *_: _rot13(t), decrypt_fn=lambda t, *_: _rot13(t),
    ))
    specs.append(CipherSpec(
        id="rot47", name="ROT47", group="Classical / substitution",
        description="ROT13's cousin over the full printable ASCII range. Self-reciprocal.",
        encrypt_fn=lambda t, *_: _rot47(t), decrypt_fn=lambda t, *_: _rot47(t),
    ))
    specs.append(CipherSpec(
        id="atbash", name="Atbash", group="Classical / substitution",
        description="Reverses the alphabet - A<->Z, B<->Y. Self-reciprocal, no key.",
        encrypt_fn=lambda t, *_: _atbash(t), decrypt_fn=lambda t, *_: _atbash(t),
    ))
    specs.append(CipherSpec(
        id="affine", name="Affine", group="Classical / substitution",
        description="E(x) = (a*x + b) mod 26. a must be coprime with 26.",
        key1=KeyFieldSpec("a - coprime to 26", "e.g. 1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25.", "5", KeyKind.INTEGER),
        key2=KeyFieldSpec("b - shift", "Integer 0-25.", "8", KeyKind.INTEGER),
        encrypt_fn=_affine_encrypt, decrypt_fn=_affine_decrypt,
    ))
    specs.append(CipherSpec(
        id="vigenere", name="Vigenère", group="Classical / polyalphabetic",
        description="Polyalphabetic shift using a repeating keyword.",
        key1=KeyFieldSpec("Key", "Letters only; repeats across the message.", "KEYWORD"),
        encrypt_fn=lambda t, k, *_: _vigenere(t, k, False), decrypt_fn=lambda t, k, *_: _vigenere(t, k, True),
    ))
    specs.append(CipherSpec(
        id="beaufort", name="Beaufort", group="Classical / polyalphabetic",
        description="Vigenère variant (E = K - P). Self-reciprocal - the same operation both ways.",
        key1=KeyFieldSpec("Key", "Letters only. Self-reciprocal cipher.", "KEYWORD"),
        encrypt_fn=lambda t, k, *_: _beaufort(t, k), decrypt_fn=lambda t, k, *_: _beaufort(t, k),
    ))
    specs.append(CipherSpec(
        id="autokey", name="Autokey", group="Classical / polyalphabetic",
        description="Vigenère variant where the plaintext extends the key stream after the primer.",
        key1=KeyFieldSpec("Primer key", "Letters only; plaintext extends the key stream.", "PRIMER"),
        encrypt_fn=lambda t, k, *_: _autokey(t, k, False), decrypt_fn=lambda t, k, *_: _autokey(t, k, True),
    ))
    specs.append(CipherSpec(
        id="playfair", name="Playfair", group="Classical / digraph",
        description="Encrypts letter pairs using a 5x5 key square. Used militarily into the 20th century.",
        key1=KeyFieldSpec("Key", "Letters only; builds a 5x5 grid (I/J merged).", "KEYWORD"),
        encrypt_fn=lambda t, k, *_: _playfair(t, k, False), decrypt_fn=lambda t, k, *_: _playfair(t, k, True),
    ))
    specs.append(CipherSpec(
        id="polybius", name="Polybius square", group="Classical / digraph",
        description="Maps each letter to a row/column pair in a 5x5 grid (I/J merged).",
        encrypt_fn=lambda t, *_: _polybius(t, False), decrypt_fn=lambda t, *_: _polybius(t, True),
    ))
    specs.append(CipherSpec(
        id="railfence", name="Rail fence", group="Classical / transposition",
        description="Writes text in a zigzag across N rails, then reads row by row.",
        key1=KeyFieldSpec("Rails", "Number of zigzag rows, integer >= 2.", "3", KeyKind.INTEGER),
        encrypt_fn=lambda t, k, *_: _rail_fence(t, k, False), decrypt_fn=lambda t, k, *_: _rail_fence(t, k, True),
    ))
    specs.append(CipherSpec(
        id="columnar", name="Columnar transposition", group="Classical / transposition",
        description="Writes text into a grid of columns ordered by the key, then reads columns in order.",
        key1=KeyFieldSpec("Key", "Word or sequence - its letter order sets the column order.", "ZEBRA"),
        encrypt_fn=lambda t, k, *_: _columnar_transpose(t, k, False),
        decrypt_fn=lambda t, k, *_: _columnar_transpose(t, k, True),
    ))
    specs.append(CipherSpec(
        id="baconian", name="Baconian", group="Classical / steganographic",
        description="Each letter becomes a 5-bit A/B sequence. Francis Bacon's biliteral cipher.",
        encrypt_fn=lambda t, *_: _baconian(t, False), decrypt_fn=lambda t, *_: _baconian(t, True),
    ))
    specs.append(CipherSpec(
        id="morse", name="Morse code", group="Classical / encoding",
        description="Dots and dashes per character, space-separated. / marks a word boundary.",
        encrypt_fn=lambda t, *_: _morse(t, False), decrypt_fn=lambda t, *_: _morse(t, True),
    ))
    specs.append(CipherSpec(
        id="xor", name="XOR", group="Classical / stream",
        description="Each byte XORed with a repeating key byte. Symmetric - the same operation encrypts and decrypts.",
        key1=KeyFieldSpec("Key", "Repeats across the message. Output is hex.", "key"),
        byte_safe=True,
        encrypt_fn=lambda t, k, *_: _xor_text_encrypt(t, k),
        decrypt_fn=lambda t, k, *_: _xor_text_decrypt(t, k),
        file_encrypt_fn=lambda d, k, *_: _xor_file(d, k),
        file_decrypt_fn=lambda d, k, *_: _xor_file(d, k),
    ))

    # encodings
    specs.append(CipherSpec(
        id="base64", name="Base64", group="Encoding",
        description="Binary-to-text encoding, not encryption. Fully reversible with no key.",
        encrypt_fn=lambda t, *_: _b64_encode(t), decrypt_fn=lambda t, *_: _b64_decode(t),
    ))
    specs.append(CipherSpec(
        id="base64url", name="Base64 URL-safe", group="Encoding",
        description="Uses - and _ instead of + and /, no padding. Not encryption - trivially reversible.",
        encrypt_fn=lambda t, *_: _b64url_encode(t), decrypt_fn=lambda t, *_: _b64url_decode(t),
    ))
    specs.append(CipherSpec(
        id="base32", name="Base32", group="Encoding",
        description="RFC 4648 binary-to-text encoding using a 32-symbol alphabet.",
        encrypt_fn=lambda t, *_: _b32_encode(t), decrypt_fn=lambda t, *_: _b32_decode(t),
    ))
    specs.append(CipherSpec(
        id="hex", name="Hexadecimal", group="Encoding",
        description="Each byte written as two hex digits.",
        encrypt_fn=lambda t, *_: _hex_encode(t), decrypt_fn=lambda t, *_: _hex_decode(t),
    ))
    specs.append(CipherSpec(
        id="binary", name="Binary", group="Encoding",
        description="Each byte written as 8 bits, space-separated.",
        encrypt_fn=lambda t, *_: _bin_encode(t), decrypt_fn=lambda t, *_: _bin_decode(t),
    ))
    specs.append(CipherSpec(
        id="urlencode", name="URL encoding", group="Encoding",
        description="Escapes reserved characters for use inside a URL.",
        encrypt_fn=lambda t, *_: _url_encode(t), decrypt_fn=lambda t, *_: _url_decode(t),
    ))

    # modern symmetric - AES mode variants
    for mode_name in ("CBC", "ECB", "CTR", "CFB", "OFB"):
        specs.append(_aes_mode_cipher(mode_name))

    specs.append(_legacy_cipher(
        "Triple DES", "triple-des",
        "Applies DES three times with derived subkeys. Legacy standard, superseded by AES.",
        _des3_encrypt, _des3_decrypt,
    ))
    specs.append(_legacy_cipher(
        "DES", "des",
        "56-bit-key block cipher from 1977. Broken by brute force today - reference only.",
        _des_encrypt, _des_decrypt,
    ))
    specs.append(_legacy_cipher(
        "RC4", "rc4",
        "Classic stream cipher. Known biases make it unsuitable for new systems.",
        _rc4_encrypt, _rc4_decrypt,
    ))

    # RSA (asymmetric)
    specs.append(CipherSpec(
        id="rsa", name="RSA", group="Asymmetric (public-key)",
        description=(
            "Public-key cryptography - encrypt with the public key, decrypt only with the "
            "matching private key. PKCS#1 v1.5 padding. For files, a random AES key encrypts "
            "the data and RSA wraps only that key (hybrid encryption)."
        ),
        key1=KeyFieldSpec("Public key (PEM)", "Used to encrypt. Generate a pair in the Keys tab.", kind=KeyKind.PEM),
        key2=KeyFieldSpec("Private key (PEM)", "Used to decrypt. Keep this secret.", kind=KeyKind.PEM),
        is_asymmetric=True, byte_safe=True,
        encrypt_fn=_rsa_encrypt, decrypt_fn=_rsa_decrypt,
        file_encrypt_fn=_rsa_file_encrypt, file_decrypt_fn=_rsa_file_decrypt,
    ))

    # hashes
    for hname in ("MD5", "SHA-1", "SHA-224", "SHA-256", "SHA-384", "SHA-512", "SHA-3", "RIPEMD-160"):
        enc, dec = _hash_fn(hname)
        specs.append(CipherSpec(
            id=hname.lower(), name=hname, group="Hash (one-way)",
            description=f"{hname} is a one-way hash. There is no decrypt direction - hashing cannot be reversed.",
            one_way=True, encrypt_fn=enc, decrypt_fn=dec,
        ))

    # HMAC
    for hmac_name, digestmod in (("MD5", hashlib.md5), ("SHA1", hashlib.sha1),
                                  ("SHA256", hashlib.sha256), ("SHA512", hashlib.sha512)):
        enc, dec = _hmac_fn(digestmod)
        specs.append(CipherSpec(
            id=f"hmac-{hmac_name.lower()}", name=f"HMAC-{hmac_name}", group="Hash (one-way)",
            description=f"HMAC-{hmac_name} is a keyed one-way hash. There is no decrypt direction.",
            key1=KeyFieldSpec("Key", "Shared secret used for the HMAC.", "secret key"),
            one_way=True, encrypt_fn=enc, decrypt_fn=dec,
        ))

    return specs


def _parse_int(value: str, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise CipherError(f"{field_name} must be an integer.")


# Public alias for cryptanalysis code (core/analysis.py) that needs to
# run raw Caesar shifts directly, outside the CipherSpec dispatch table.
caesar_shift = _caesar_shift


CIPHER_REGISTRY: List[CipherSpec] = build_cipher_registry()
CIPHER_BY_ID = {c.id: c for c in CIPHER_REGISTRY}
