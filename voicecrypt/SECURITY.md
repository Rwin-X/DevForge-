# Security Policy

## Status

VoiceCrypt is an **experimental, unaudited** project. Do not rely on it as the only protection for data you cannot afford to lose or expose. Keep backups of important originals.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's *Report a vulnerability* button (Security tab) or by contacting the maintainer directly. Do not open public issues for security bugs. Include the version, steps to reproduce and impact. Do not attach real voice recordings.

## What it is designed to do

- Protect a file's contents and name with AES-256-GCM under a key that needs **both** a matching voice and the passphrase.
- Keep the secret out of storage: the profile holds only helper data and a hash commitment.
- Detect modification of the file, the embedded profile or the nonce (GCM tag over an authenticated header).

## What it does NOT protect against

| Limitation | Consequence |
|---|---|
| A voice is not a secret. Recordings and voice cloning are easy to obtain. | An attacker with a good sample can try to pass the voice step. **The passphrase is the real protection** - use a strong one. |
| No liveness detection. | A replayed recording can satisfy the voice step. |
| Low voice entropy and a weak speaker model (spectral statistics, not neural embeddings). | Similar-sounding speakers may also pass. In synthetic tests a near-identical voice sometimes unlocked the profile. |
| The commitment hash verifies the recovered secret. | Voice guesses can be tested offline without the passphrase; only the passphrase + scrypt then slows the attacker. |
| Helper data reveals which feature pairs were chosen as reliable. | Small information leak about the speaker. |
| No secure memory handling in Python. | Keys and plaintext may remain in RAM, swap or temp files. |
| Whole-file encryption in memory (limit 512 MB). | Not suited to very large files. |
| KDF parameters and feature constants are not stored in the file. | Changing them makes older profiles and files undecryptable. |

Losing the passphrase, or being unable to reproduce your voice (illness, different microphone, noisy room), means losing access to the data. There is no recovery mechanism by design.

See [docs/DESIGN.md](docs/DESIGN.md) for the full construction.
