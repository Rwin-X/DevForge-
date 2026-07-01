# 🔍 Username OSINT Tool

> A fast, lightweight, and dependency-free Username OSINT utility written entirely in Python.

This tool searches for a username across multiple online platforms, gathers publicly available profile information, and generates detailed reports in multiple formats.

Designed for **lawful Open Source Intelligence (OSINT)** and **defensive security research**.

---

## ✨ Features

- 🚀 Concurrent scanning using `asyncio`
- ⚡ No third-party dependencies (Pure Python Standard Library)
- 🌐 Checks usernames across multiple popular platforms
- 📊 Beautiful terminal output with colored status indicators
- 📄 Export reports as:
  - JSON
  - CSV
  - HTML
- ⏱ Configurable timeout and retry logic
- 🎯 Response time measurement for every platform
- 🔄 Rotating User-Agent support
- 🛡 Built for defensive OSINT research
- 🎨 Cross-platform terminal color support
- 📦 Lightweight and portable

---

## 🌍 Supported Platforms

- GitHub
- GitLab
- Reddit
- X (Twitter)
- Instagram
- TikTok
- Pinterest
- Medium
- Twitch
- Steam
- HackerOne
- TryHackMe
- Hack The Box
- Keybase
- Docker Hub
- Dev.to

---

## 📥 Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/osint-tool.git
cd osint-tool
```

No installation of external packages is required.

Requires:

- Python 3.8+

---

## 🚀 Usage

Basic scan:

```bash
python osint.py johndoe
```

Generate a JSON report:

```bash
python osint.py johndoe --json report.json
```

Generate an HTML report:

```bash
python osint.py johndoe --html report.html
```

Generate a CSV report:

```bash
python osint.py johndoe --csv report.csv
```

Generate multiple reports:

```bash
python osint.py johndoe --json report.json --html report.html
```

Custom timeout and retries:

```bash
python osint.py johndoe --timeout 15 --retries 3
```

Disable colored output:

```bash
python osint.py johndoe --no-color
```

---

## 📋 Output

The tool provides:

- Platform status
- Profile URL
- Display name
- Biography
- Followers / Following
- Repository count (where applicable)
- Website
- Location
- Creation date
- Response time
- Error information
- Scan summary

---

## ⚙️ Architecture

The project is organized into several components:

```
├── HTTP Client
├── Platform Checkers
├── Async Scanner
├── Progress Bar
├── Report Generator
├── Command-Line Interface
└── Data Models
```

---

## 🛠 Technologies

- Python 3.8+
- asyncio
- urllib
- dataclasses
- argparse
- json
- csv
- html
- Standard Library Only

---

## 📈 Performance

- Concurrent platform scanning
- Configurable concurrency
- Retry mechanism for transient network failures
- Timeout protection
- Lightweight memory usage

---

## 📄 Report Formats

### JSON

Machine-readable structured output.

### CSV

Spreadsheet-friendly export.

### HTML

Beautiful standalone report with:

- Status badges
- Summary statistics
- Clickable profile links
- Responsive layout

---

## ⚖️ Legal Notice

This software is intended **only** for:

- Open Source Intelligence (OSINT)
- Security awareness
- Defensive security research
- Educational purposes

Users are responsible for complying with all applicable laws, regulations, and platform Terms of Service.

**Do not use this tool for:**

- Harassment
- Stalking
- Privacy violations
- Unauthorized access
- Brute-force attacks
- Any illegal activity

The authors assume no responsibility for misuse.

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome.

Feel free to open an Issue or submit a Pull Request.

---

## ⭐ Future Improvements

- Additional platforms
- Proxy support
- API authentication support
- Screenshot generation
- Avatar downloading
- Better metadata extraction
- Plugin system
- Report templates

---

## 📜 License

This project is released under the MIT License.

---

<div align="center">

**Built for Ethical OSINT & Defensive Security Research**

⭐ If you found this project useful, consider giving it a star.

</div>
