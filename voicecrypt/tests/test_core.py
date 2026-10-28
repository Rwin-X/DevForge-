"""Core tests (no GUI, no microphone). Voices are synthetic: harmonic sources shaped by formants."""

import numpy as np
import pytest

from voicecrypt import core

SR = core.SR
SPEAKER_A = dict(f0=120, formants=[700, 1200, 2600], bw=[90, 110, 160])
SPEAKER_B = dict(f0=125, formants=[550, 1700, 2500], bw=[80, 120, 150])
PASSPHRASE = "correct horse battery staple \u00e4\u00f6"


def synth_voice(f0, formants, bw, seed, dur=4.0, jitter=0.02, noise=0.01):
    r = np.random.default_rng(seed)
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (1 + 0.08 * np.sin(2 * np.pi * 0.7 * t + r.uniform(0, 6))) * (1 + jitter * r.standard_normal())
    phase = 2 * np.pi * np.cumsum(f) / SR
    x = np.zeros_like(t)
    for h in range(1, int(4000 / f0)):
        fh = h * f0
        amp = sum(np.exp(-0.5 * ((fh - F) / (B * (1 + 0.03 * r.standard_normal()))) ** 2)
                  for F, B in zip(formants, bw)) / h
        x += amp * np.sin(h * phase)
    x *= 0.5 + 0.5 * np.sin(2 * np.pi * 3 * t + r.uniform(0, 6)) ** 2
    return x / np.max(np.abs(x)) * 0.5 + noise * r.standard_normal(len(x))


def feats(speaker, seed, **kw):
    return core.extract_features(synth_voice(**speaker, seed=seed, **kw))


@pytest.fixture(scope="module")
def enrolled():
    F = np.vstack([feats(SPEAKER_A, s) for s in range(5)])
    profile = core.create_profile(F, "test")
    for s in range(100, 120):
        secret, _ = core.recover_secret(profile, feats(SPEAKER_A, s))
        if secret is not None:
            return profile, secret
    pytest.fail("could not unlock the freshly created profile")


def test_profile_shape(enrolled):
    profile, secret = enrolled
    assert len(secret) == core.SECRET_BITS // 8
    assert len(profile["pairs"]) == core.N_BITS
    assert "secret" not in profile
    assert secret.hex() not in str(profile)


def test_same_speaker_unlocks(enrolled):
    profile, secret = enrolled
    for s in range(200, 210):
        got, mismatch = core.recover_secret(profile, feats(SPEAKER_A, s, noise=0.015))
        assert got == secret
        assert mismatch < 0.2


def test_other_speaker_rejected(enrolled):
    profile, _ = enrolled
    for s in range(300, 310):
        got, _ = core.recover_secret(profile, feats(SPEAKER_B, s))
        assert got is None


def test_stability_estimate_range():
    F = np.vstack([feats(SPEAKER_A, s) for s in range(5)])
    p, success = core.estimate_stability(F)
    assert 0.0 <= p <= 0.5
    assert 0.0 <= success <= 1.0


def test_roundtrip(enrolled, tmp_path):
    profile, secret = enrolled
    src = tmp_path / "hello.txt"
    data = b"top secret " * 1000
    src.write_bytes(data)
    dst = tmp_path / "hello.txt.vcrypt"
    core.encrypt_file(src, dst, profile, secret, PASSPHRASE)

    blob = dst.read_bytes()
    assert blob.startswith(core.MAGIC)
    assert b"hello.txt" not in blob          # file name is encrypted
    assert b"top secret" not in blob

    meta, aad, nonce, ct = core.read_container(dst)
    got_secret, _ = core.recover_secret(meta["profile"], feats(SPEAKER_A, 400))
    assert got_secret == secret
    name, plain = core.decrypt_payload(meta, aad, nonce, ct, got_secret, PASSPHRASE)
    assert name == "hello.txt" and plain == data


def test_wrong_passphrase_and_tamper(enrolled, tmp_path):
    profile, secret = enrolled
    src = tmp_path / "a.bin"
    src.write_bytes(b"x" * 64)
    dst = tmp_path / "a.bin.vcrypt"
    core.encrypt_file(src, dst, profile, secret, PASSPHRASE)
    meta, aad, nonce, ct = core.read_container(dst)

    with pytest.raises(ValueError):
        core.decrypt_payload(meta, aad, nonce, ct, secret, "wrong passphrase")
    with pytest.raises(ValueError):                      # ciphertext flipped
        core.decrypt_payload(meta, aad, nonce, ct[:-1] + bytes([ct[-1] ^ 1]), secret, PASSPHRASE)
    with pytest.raises(ValueError):                      # nonce flipped
        core.decrypt_payload(meta, aad, bytes([nonce[0] ^ 1]) + nonce[1:], ct, secret, PASSPHRASE)
    with pytest.raises(ValueError):                      # authenticated header changed
        core.decrypt_payload(meta, aad[:-1] + bytes([aad[-1] ^ 1]), nonce, ct, secret, PASSPHRASE)


def test_read_container_rejects_garbage(tmp_path):
    for blob in (b"", b"not a vcrypt file at all, just text", core.MAGIC + b"\xff\xff\xff\xff" + b"x" * 40):
        p = tmp_path / "bad.vcrypt"
        p.write_bytes(blob)
        with pytest.raises(ValueError):
            core.read_container(p)


def test_profile_validation(enrolled):
    profile, _ = enrolled
    core.check_profile(profile)
    with pytest.raises(ValueError):
        core.check_profile({})
    bad = dict(profile, pairs=[[0, 9999]] * core.N_BITS)
    with pytest.raises(ValueError):
        core.check_profile(bad)
    with pytest.raises(ValueError):
        core.check_profile(dict(profile, pairs=profile["pairs"][:-1]))


def test_audio_quality_gates():
    with pytest.raises(ValueError):
        core.extract_features(np.zeros(SR * 3))                       # silent
    with pytest.raises(ValueError):
        core.extract_features(synth_voice(**SPEAKER_A, seed=1)[: SR // 2])   # too short
