# Design and file formats

## 1. Voice features

Audio is mono, 16 kHz. For each recording:

1. Remove DC offset, compute frame energy (25 ms frames, 10 ms hop) and keep voiced frames: energy within 30 dB of the peak, and 10 dB above the noise floor when clear silence is present. At least 60 voiced frames are required. Clipping, silence and very short audio are rejected.
2. Pre-emphasis (0.97), Hamming window, 1024-point FFT, 32 mel bands (100-7000 Hz), natural log.
3. Feature vector (80 values): mean of each log-mel band (32), standard deviation of each band (32), mean of MFCC 1-16 (16).

## 2. Bits from features (threshold-free)

A "bit" is the sign of `feature[i] - feature[j]` for a pair inside the same feature group. Differences are invariant to overall recording gain and need no population statistics.

At enrollment (>= 5 samples of the same phrase) every candidate pair is scored by `|mean diff| / (std diff + 0.05)` and must have the same sign in every sample. The 576 best pairs are chosen greedily, with each feature used at most 20 times, then shuffled (if too few pairs qualify, the remainder is filled with less reliable ones). The reference bit of each pair is the sign of its enrollment mean.

## 3. Fuzzy commitment

```
secret   = 64 random bits
codeword = each secret bit repeated 9 times        (576 bits)
helper   = codeword XOR reference_bits             (stored in the profile)
commit   = SHA-256("voicecrypt/commit" || salt || secret)
```

Recovery XORs the helper data with the bits of a new recording and takes a majority vote per group of 9, which tolerates up to 4 flipped bits per group. The result is accepted only if its commitment matches. `estimate_stability` reports a leave-one-out bit mismatch rate and a rough unlock probability that assumes independent bit errors, so treat it as indicative.

## 4. Profile (`.vkey`, JSON)

| Field | Meaning |
|---|---|
| `format`, `version`, `name` | Metadata |
| `salt` | 16 random bytes (hex) |
| `pairs` | 576 `[i, j]` feature index pairs, in shuffled order |
| `helper` | 576 bits, packed, hex |
| `repeat`, `secret_bits` | 9, 64 |
| `commit` | SHA-256 commitment (hex) |

The profile contains no voice samples and no secret. It is still personal data; do not publish it.

## 5. Key derivation and encryption

```
key = scrypt(password = secret || NFC(passphrase).utf8,
             salt     = profile.salt || file_salt,     # 32 bytes
             N = 2^15, r = 8, p = 1, dkLen = 32)
```

Each file gets a fresh 16-byte `file_salt` and a fresh 12-byte nonce, so every file has its own key. Encryption is AES-256-GCM.

## 6. `.vcrypt` container

```
offset  size   field
0       8      magic  "VCRYPT01"
8       4      header length N (big-endian)
12      N      header JSON: {"version":1, "profile":{...}, "file_salt":"<hex>"}
12+N    12     GCM nonce
24+N    ...    ciphertext || 16-byte tag
```

Associated data is `magic || header length || header`, so any change to the embedded profile or salt makes decryption fail.

Plaintext payload: `u16 name_length || file name (UTF-8) || file bytes`. The original file name is therefore encrypted.

## 7. Compatibility

Feature constants, scrypt parameters and the container layout are fixed in `voicecrypt/core.py` and are not recorded in the file. Changing them is a format change and requires a new version (see CONTRIBUTING.md).
