# Contributing

Thanks for helping improve VoiceCrypt. This is a security-sensitive project, so small, well-tested changes are preferred.

## Development setup

```bash
git clone https://github.com/YOUR_USER/voicecrypt.git
cd voicecrypt
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

Linux also needs `python3-tk` and `libportaudio2` to run the GUI. The tests do not need a GUI or a microphone.

## Guidelines

- Keep `voicecrypt/core.py` free of GUI imports so tests and library use stay headless.
- Any change to feature extraction, bit selection, the KDF parameters or the container layout is a **format change**: bump the version, update `docs/DESIGN.md` and `CHANGELOG.md`, and say how old files are handled.
- Add or update tests for behaviour changes. Tests use synthetic voices; never commit real voice recordings, `.vkey` or `.vcrypt` files.
- Open an issue before large changes.
- Report security problems privately - see [SECURITY.md](SECURITY.md).

## Good first areas

Liveness / anti-replay checks, a stronger error-correcting code (BCH or Reed-Solomon), speaker-embedding features, KDF parameters stored in the header, a command-line interface, and packaged releases.
