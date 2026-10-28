# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [1.0.0] - 2026-10-28

### Added
- Tkinter GUI with four tabs: Enroll voice, Encrypt, Decrypt, Verify voice.
- Microphone recording (16 kHz mono) and WAV import.
- Voice feature extraction (log-mel mean/std + MFCC mean) with speech gating.
- Fuzzy-commitment key binding: 64-bit random secret bound to voice-derived bits (repetition code, x9).
- Leave-one-out stability estimate shown at enrollment.
- Self-contained `.vcrypt` container (AES-256-GCM, scrypt, authenticated header, encrypted file name).
- `voicecrypt.core` library module and pytest suite with synthetic voices.
- GitHub Actions CI (Linux, plus Windows and macOS smoke runs).
