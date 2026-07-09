# 🔐 HashCLI

> **A fast, modern, and lightweight multi-algorithm hashing tool for the command line.**

HashCLI is a Python-based CLI application designed to generate cryptographic hashes quickly and efficiently. It provides a clean terminal interface, real-time progress bars for large files, colorful output powered by **Rich**, and support for multiple industry-standard hashing algorithms.

---

## ✨ Features

* 🚀 Fast hashing for text and files
* 🎨 Modern colored CLI interface using Rich
* 📊 Real-time progress bar for large files
* 📦 Lightweight with minimal dependencies
* ⚡ High-performance buffered file hashing
* 🛡️ Support for 14 cryptographic hash algorithms
* ⏱️ Execution time measurement
* 📁 File size detection
* ❌ Robust error handling
* 🧩 Modular and maintainable codebase
* 🐍 Built with Python 3

---

## Supported Algorithms

| Algorithm | Supported |
| --------- | --------- |
| MD5       | ✅         |
| SHA1      | ✅         |
| SHA224    | ✅         |
| SHA256    | ✅         |
| SHA384    | ✅         |
| SHA512    | ✅         |
| SHA3-224  | ✅         |
| SHA3-256  | ✅         |
| SHA3-384  | ✅         |
| SHA3-512  | ✅         |
| BLAKE2b   | ✅         |
| BLAKE2s   | ✅         |
| SHAKE128  | ✅         |
| SHAKE256  | ✅         |

---

## Project Structure

```text
hashcli/
│
├── main.py
├── algorithms.py
├── banner.py
├── filehash.py
├── texthash.py
├── timer.py
├── ui.py
└── utils.py
```

---

## Installation

```bash
pip install rich
```

Python 3.10+ is recommended.

---

## Usage

### Hash Text

```bash
python main.py -a sha256 -t "Hello World"
```

### Hash a File

```bash
python main.py -a sha512 -f document.pdf
```

---

## Example Output

```text
╭────────────────────────── HashCLI ──────────────────────────╮
│                                                            │
│ Algorithm : SHA256                                         │
│ Source    : TEXT                                           │
│ Time      : 0.0002 sec                                     │
│                                                            │
│ Hash                                                       │
│ a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57...       │
│                                                            │
╰────────────────────────────────────────────────────────────╯
```

---

## Design Goals

HashCLI is built around a few core principles:

* Simplicity
* Performance
* Readability
* Modularity
* Cross-platform compatibility
* Developer-friendly architecture

Each module has a single responsibility, making the project easy to extend and maintain.

---

## Roadmap

### Version 1.0

* [x] Multi-algorithm hashing
* [x] Text hashing
* [x] File hashing
* [x] Rich terminal interface
* [x] Progress bar
* [x] Execution timer
* [x] File size information
* [x] Modular architecture

### Version 1.1

* [ ] Interactive mode
* [ ] Algorithm listing
* [ ] File information panel
* [ ] Hash verification
* [ ] Clipboard support
* [ ] Benchmark mode

### Version 2.0

* [ ] Directory hashing
* [ ] Recursive hashing
* [ ] Multi-threaded hashing
* [ ] JSON output
* [ ] Checksum generation
* [ ] Plugin system
* [ ] Performance statistics
* [ ] Watch mode

---

## Requirements

* Python 3.10+
* Rich

---

## Why HashCLI?

Unlike many simple hashing scripts, HashCLI focuses on both usability and software architecture. It combines modern CLI design with a clean, modular implementation that is easy to understand, maintain, and extend.

Whether you are verifying downloads, checking file integrity, learning cryptographic hashing, or building automation workflows, HashCLI provides a fast and reliable solution.

---

## Security Notice

HashCLI generates cryptographic hashes for integrity verification and identification.

Please note:

* MD5 and SHA1 are considered cryptographically broken for security-sensitive applications.
* Prefer SHA-256, SHA-512, SHA-3, or BLAKE2 for modern use cases.

---

## Contributing

Contributions, bug reports, feature requests, and pull requests are always welcome.

If you have ideas to improve performance, usability, or architecture, feel free to contribute.


## Author

**RWIN-x**

Built with Python and a passion for clean command-line tools.
