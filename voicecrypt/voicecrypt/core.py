#!/usr/bin/env python3
"""
VoiceCrypt - voice-bound file encryption (tkinter GUI)

How it works (fuzzy commitment / key binding):
  1. ENROLL   : record >= 5 samples of the same phrase. Voice features (log-mel
                band statistics + MFCC means) are turned into stable bits by
                comparing pairs of features (threshold-free, gain-invariant).
                A random secret is bound to those bits with an error-correcting
                (repetition) code. Only "helper data" is stored in the profile
                (.vkey); neither the secret nor the voice bits are stored.
  2. ENCRYPT  : the speaker says the phrase again -> secret is recovered from the
                helper data -> key = scrypt(secret || passphrase) -> AES-256-GCM.
  3. DECRYPT  : same voice + same passphrase recovers the key. The profile is
                embedded in the .vcrypt file, so no other file is needed.

SECURITY NOTE: a voice is not a secret (it can be recorded / cloned), and
voice biometrics have low entropy. Treat the voice as a second factor and use a
strong passphrase - the passphrase is what carries the cryptographic strength.

Library module (no GUI dependencies): numpy, scipy, cryptography.
"""

import os
import json
import hmac
import hashlib
import secrets
import unicodedata
from math import gcd, comb
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.fft import dct
from scipy.signal import resample_poly
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

# ----------------------------------------------------------------------------
# Parameters
# ----------------------------------------------------------------------------
SR = 16000                  # sample rate
FRAME, HOP, NFFT = 400, 160, 1024
N_MELS, N_MFCC = 32, 16
FEATURE_DIM = 2 * N_MELS + N_MFCC
SECRET_BITS = 64            # random secret bound to the voice
REPEAT = 9                  # repetition code length (tolerates 4 flips / group)
N_BITS = SECRET_BITS * REPEAT
FEATURE_USE_CAP = 20        # max times one feature is reused in bit pairs
MIN_ENROLL = 5
MAGIC = b"VCRYPT01"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 15, 8, 1
MAX_FILE = 512 * 1024 * 1024

GROUPS = [(0, N_MELS), (N_MELS, 2 * N_MELS), (2 * N_MELS, FEATURE_DIM)]


# ----------------------------------------------------------------------------
# Audio -> features
# ----------------------------------------------------------------------------
def _mel_filterbank():
    hz2mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)
    mel2hz = lambda m: 700.0 * (10 ** (m / 2595.0) - 1.0)
    hz = mel2hz(np.linspace(hz2mel(100.0), hz2mel(7000.0), N_MELS + 2))
    bins = np.floor((NFFT + 1) * hz / SR).astype(int)
    fb = np.zeros((N_MELS, NFFT // 2 + 1))
    for m in range(1, N_MELS + 1):
        l, c, r = bins[m - 1], bins[m], bins[m + 1]
        for k in range(l, c):
            fb[m - 1, k] = (k - l) / max(c - l, 1)
        for k in range(c, r):
            fb[m - 1, k] = (r - k) / max(r - c, 1)
    return fb


_FB = _mel_filterbank()
_WIN = np.hamming(FRAME)


def load_wav(path):
    sr, x = wavfile.read(path)
    if x.dtype == np.int16:
        x = x / 32768.0
    elif x.dtype == np.int32:
        x = x / 2147483648.0
    elif x.dtype == np.uint8:
        x = (x.astype(np.float64) - 128.0) / 128.0
    else:
        x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        g = gcd(int(sr), SR)
        x = resample_poly(x, SR // g, int(sr) // g)
    return x


def extract_features(x):
    """Return a FEATURE_DIM vector describing the speaker's long-term spectrum."""
    x = np.asarray(x, dtype=np.float64)
    if x.size < SR:
        raise ValueError("Recording is too short (need at least 1 second).")
    peak = np.max(np.abs(x))
    if peak < 1e-3:
        raise ValueError("Recording is silent - check your microphone.")
    if np.mean(np.abs(x) > 0.98 * peak) > 0.01 and peak > 0.98:
        raise ValueError("Audio is clipping - lower the mic gain or speak softer.")
    x = x - x.mean()
    n = 1 + (len(x) - FRAME) // HOP
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    e_db = 10 * np.log10((x[idx] ** 2).sum(axis=1) + 1e-10)   # loudness for speech detection
    xp = np.append(x[0], x[1:] - 0.97 * x[:-1])                # pre-emphasis for the spectrum
    spec = np.abs(np.fft.rfft(xp[idx] * _WIN, NFFT, axis=1)) ** 2
    thr = e_db.max() - 30.0
    floor = np.percentile(e_db, 5)
    if e_db.max() - floor > 25.0:                  # clear silence present -> noise-aware gate
        thr = max(thr, floor + 10.0)
    voiced = e_db > thr
    if voiced.sum() < 60:
        raise ValueError("Not enough speech detected - speak clearly during the whole recording.")
    lm = np.log(spec[voiced] @ _FB.T + 1e-10)
    mfcc = dct(lm, type=2, norm="ortho", axis=1)[:, 1:1 + N_MFCC]
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0), mfcc.mean(axis=0)])


# ----------------------------------------------------------------------------
# Fuzzy commitment (voice -> bits -> bound secret)
# ----------------------------------------------------------------------------
def _candidate_pairs():
    I, J = [], []
    for a, b in GROUPS:
        for i in range(a, b):
            for j in range(i + 1, b):
                I.append(i)
                J.append(j)
    return np.array(I), np.array(J)


CI, CJ = _candidate_pairs()


def _commit(salt, secret):
    return hashlib.sha256(b"voicecrypt/commit" + salt + secret).hexdigest()


def select_pairs(F):
    """Choose the N_BITS most reliable feature pairs from enrollment samples."""
    Dm = F[:, CI] - F[:, CJ]
    mean = Dm.mean(axis=0)
    sd = Dm.std(axis=0, ddof=1)
    consistent = np.all(np.sign(Dm) == np.sign(mean), axis=0) & (mean != 0)
    score = np.where(consistent, np.abs(mean) / (sd + 0.05), 0.0)
    order = np.argsort(-score)
    usage = np.zeros(F.shape[1], dtype=int)
    taken = np.zeros(len(CI), dtype=bool)
    chosen = []
    for p in order:
        if score[p] <= 0:
            break
        i, j = CI[p], CJ[p]
        if usage[i] < FEATURE_USE_CAP and usage[j] < FEATURE_USE_CAP:
            chosen.append(p)
            taken[p] = True
            usage[i] += 1
            usage[j] += 1
            if len(chosen) == N_BITS:
                break
    if len(chosen) < N_BITS:                          # fill (less reliable)
        for p in order:
            if not taken[p]:
                chosen.append(p)
                taken[p] = True
                if len(chosen) == N_BITS:
                    break
    chosen = np.array(chosen)
    return chosen, (mean[chosen] > 0).astype(np.uint8)


def create_profile(F, name):
    chosen, ref = select_pairs(F)
    perm = np.random.default_rng(secrets.randbits(64)).permutation(N_BITS)
    chosen, ref = chosen[perm], ref[perm]
    secret = secrets.token_bytes(SECRET_BITS // 8)
    sbits = np.unpackbits(np.frombuffer(secret, dtype=np.uint8))
    helper = np.repeat(sbits, REPEAT) ^ ref
    salt = secrets.token_bytes(16)
    return {
        "format": "voicecrypt-profile",
        "version": 1,
        "name": name,
        "salt": salt.hex(),
        "pairs": [[int(CI[p]), int(CJ[p])] for p in chosen],
        "helper": np.packbits(helper).tobytes().hex(),
        "repeat": REPEAT,
        "secret_bits": SECRET_BITS,
        "commit": _commit(salt, secret),
    }


def estimate_stability(F):
    """Leave-one-out bit mismatch rate and a rough unlock-success estimate."""
    rates = []
    for k in range(len(F)):
        ch, ref = select_pairs(np.delete(F, k, axis=0))
        bits = (F[k, CI[ch]] - F[k, CJ[ch]] > 0).astype(np.uint8)
        rates.append(np.mean(bits != ref))
    p = float(np.mean(rates))
    tol = REPEAT // 2
    p_fail = sum(comb(REPEAT, k) * p ** k * (1 - p) ** (REPEAT - k)
                 for k in range(tol + 1, REPEAT + 1))
    return p, (1 - p_fail) ** SECRET_BITS


def check_profile(p):
    need = ("salt", "pairs", "helper", "repeat", "secret_bits", "commit")
    if not isinstance(p, dict) or any(k not in p for k in need):
        raise ValueError("Invalid or corrupted voice profile.")
    try:
        pairs = np.array(p["pairs"])
        ok = (pairs.ndim == 2 and pairs.shape[1] == 2 and pairs.min() >= 0
              and pairs.max() < FEATURE_DIM
              and len(pairs) == int(p["repeat"]) * int(p["secret_bits"]))
        bytes.fromhex(p["salt"])
        bytes.fromhex(p["helper"])
    except Exception:
        ok = False
    if not ok:
        raise ValueError("Invalid or corrupted voice profile.")
    return p


def recover_secret(profile, feat):
    """Return (secret or None, fraction of voice bits disagreeing with consensus)."""
    pairs = np.array(profile["pairs"])
    rep, sb = int(profile["repeat"]), int(profile["secret_bits"])
    bits = (feat[pairs[:, 0]] - feat[pairs[:, 1]] > 0).astype(np.uint8)
    helper = np.unpackbits(np.frombuffer(bytes.fromhex(profile["helper"]), dtype=np.uint8))[:len(pairs)]
    cw = helper ^ bits
    sbits = (cw.reshape(sb, rep).sum(axis=1) * 2 > rep).astype(np.uint8)
    mismatch = float(np.mean(cw != np.repeat(sbits, rep)))
    secret = np.packbits(sbits).tobytes()
    ok = hmac.compare_digest(_commit(bytes.fromhex(profile["salt"]), secret), profile["commit"])
    return (secret if ok else None), mismatch


# ----------------------------------------------------------------------------
# Encryption container
# ----------------------------------------------------------------------------
def derive_key(secret, passphrase, salt):
    pw = secret + unicodedata.normalize("NFC", passphrase).encode("utf-8")
    return hashlib.scrypt(pw, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
                          maxmem=256 * 1024 * 1024, dklen=32)


def encrypt_file(src, dst, profile, secret, passphrase):
    src = Path(src)
    if src.stat().st_size > MAX_FILE:
        raise ValueError("File is too large (limit 512 MB).")
    name = src.name.encode("utf-8")
    payload = len(name).to_bytes(2, "big") + name + src.read_bytes()
    file_salt = os.urandom(16)
    header = json.dumps({"version": 1, "profile": profile, "file_salt": file_salt.hex()},
                        sort_keys=True, separators=(",", ":")).encode()
    aad = MAGIC + len(header).to_bytes(4, "big") + header
    key = derive_key(secret, passphrase, bytes.fromhex(profile["salt"]) + file_salt)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, payload, aad)
    Path(dst).write_bytes(aad + nonce + ct)


def read_container(path):
    blob = Path(path).read_bytes()
    if blob[:8] != MAGIC:
        raise ValueError("This is not a VoiceCrypt file.")
    hlen = int.from_bytes(blob[8:12], "big")
    if hlen > 2_000_000 or 12 + hlen + 12 + 16 > len(blob):
        raise ValueError("File is corrupted.")
    try:
        meta = json.loads(blob[12:12 + hlen])
        meta["profile"] = check_profile(meta["profile"])
        bytes.fromhex(meta["file_salt"])
    except (ValueError, KeyError, TypeError):
        raise ValueError("File header is corrupted.")
    return meta, blob[:12 + hlen], blob[12 + hlen:24 + hlen], blob[24 + hlen:]


def decrypt_payload(meta, aad, nonce, ct, secret, passphrase):
    p = meta["profile"]
    key = derive_key(secret, passphrase, bytes.fromhex(p["salt"]) + bytes.fromhex(meta["file_salt"]))
    try:
        payload = AESGCM(key).decrypt(nonce, ct, aad)
    except InvalidTag:
        raise ValueError("Decryption failed: wrong passphrase, or the file was modified.")
    n = int.from_bytes(payload[:2], "big")
    return payload[2:2 + n].decode("utf-8", "replace"), payload[2 + n:]


def load_profile(path):
    try:
        p = json.loads(Path(path).read_text())
    except Exception:
        raise ValueError("Could not read the voice profile file.")
    return check_profile(p)
