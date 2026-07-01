# PassVault

Terminal password manager written in pure Bash. AES-256-CBC encryption via
OpenSSL (PBKDF2, 100,000 iterations), phosphor/neon-terminal UI, zero external
dependencies beyond `openssl` and coreutils.

## Setup

```bash
chmod +x passvault.sh
./passvault.sh
```

On first run you'll be asked to create a master password (min 8 chars). This
initializes an empty encrypted vault at `~/.passvault/vault.enc` (permissions
`600`, directory `700`).

## Features

- **Add** — new entries with site, username, password (typed manually or
  randomly generated with adjustable length), and free-text notes
- **List** — table view of all stored entries with timestamps
- **View** — reveal full details (including password) for a single entry
- **Search** — case-insensitive lookup by site or username
- **Edit** — update any field of an existing entry, leaving fields blank to
  keep the current value
- **Delete** — remove an entry with a confirmation prompt
- **Generate** — standalone random password generator with a strength meter
- **Change master password** — re-encrypts the whole vault under a new key
- **Vault statistics** — entry count, file size, encryption details

## Security notes

- The vault file itself is AES-256-CBC encrypted; nothing is stored in
  plaintext on disk between sessions.
- The master password is never stored — only a salted SHA-256 HMAC used for
  verification.
- The decrypted database exists only in a `mktemp -d` temp directory for the
  duration of the session and is shredded (`shred -u`) on exit, including on
  Ctrl+C.
- This is a learning / personal-use tool. For anything beyond that, a vetted
  password manager (KeePassXC, Bitwarden, etc.) with a security-audited
  codebase is the safer choice — worth keeping in mind given your CEH/Security+
  track, where "don't roll your own crypto for production use" is a live
  principle, not just a slogan.

## File layout

```
~/.passvault/
├── vault.enc      # AES-256-CBC encrypted entries
├── master.hash    # HMAC-SHA256 of master password (verification only)
└── master.salt    # random salt used for the HMAC
```

## Menu reference

```
[1] Add new entry              [6] Delete entry
[2] List entries               [7] Generate random password
[3] View entry                 [8] Change master password
[4] Search entries             [9] Vault statistics
[5] Edit entry                 [0] Lock vault and exit
```
