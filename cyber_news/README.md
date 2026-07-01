# 🛡️ CYBER_NEWS

**Real-time security intelligence aggregator for the terminal.**

Pulls live stories from trusted infosec RSS/Atom feeds, flags high-severity items (zero-days, active exploitation, ransomware, CVEs) with regex-based heuristics, renders a live cyberpunk-themed dashboard, and exports everything to a clean Markdown digest — all with zero external dependencies beyond an optional `rich` for the terminal UI.

```
▓▓▓ CYBER_NEWS // SECURITY INTEL AGGREGATOR ▓▓▓
```

---

## Features

- **Concurrent multi-source fetching** — pulls from up to 8 feeds in parallel via `ThreadPoolExecutor`
- **Stdlib-only parsing** — handles both RSS 2.0 and Atom feeds using `xml.etree`, no `feedparser` required
- **Severity heuristics** — automatically flags stories mentioning zero-days, active exploitation, ransomware, RCEs, breaches, or CVE identifiers
- **Live terminal dashboard** — real-time fetch progress, per-source status, and a cyberpunk-styled summary panel (powered by [`rich`](https://github.com/Textualize/rich))
- **Graceful degradation** — auto-installs `rich` on first run; falls back to clean plain-text output if unavailable or offline
- **Markdown digest export** — generates a dated, linkable report with a table of contents, per-source sections, and flagged high-severity callouts
- **Source filtering** — select any subset of feeds via CLI flags
- **Resilient by design** — network errors, malformed XML, and unreachable feeds are caught per-source and reported without crashing the run

## Sources

| Key | Source |
|---|---|
| `krebs` | Krebs on Security |
| `thehackernews` | The Hacker News |
| `bleepingcomputer` | BleepingComputer |
| `darkreading` | Dark Reading |
| `threatpost` | Threatpost |
| `schneier` | Schneier on Security |
| `securityweek` | SecurityWeek |
| `cisa` | CISA Advisories |

## Installation

```bash
git clone https://github.com/<your-username>/devforge.git
cd devforge/cyber_news
python3 cyber_news.py
```

No manual dependency setup required — `rich` installs itself on first run if missing. Requires only Python 3.7+.

## Usage

```bash
# Fetch all sources, 8 stories each (default)
python3 cyber_news.py

# Limit stories per source
python3 cyber_news.py --limit 5

# Custom output path for the Markdown digest
python3 cyber_news.py --output report.md

# Fetch only specific sources
python3 cyber_news.py --sources krebs,thehackernews,cisa

# Force plain-text output (skip the rich UI)
python3 cyber_news.py --no-rich
```

### CLI Options

| Flag | Description | Default |
|---|---|---|
| `--limit N` | Max stories per source | `8` |
| `--output PATH` | Output Markdown file path | `cyber_digest_YYYY-MM-DD.md` |
| `--sources KEYS` | Comma-separated source keys | all sources |
| `--no-rich` | Disable rich terminal UI | off |

## Output

Every run writes a Markdown digest with:

- A summary line (total stories, flagged high-severity count, sources reached)
- A table of contents linking to each source section
- Per-story entries with timestamp, link, and a trimmed summary
- High-severity stories marked with a 🔴 flag
- A logged error section for any sources that failed to fetch

## How It Works

1. **Fetch** — each configured feed is requested concurrently with a spoofed User-Agent and a 12s timeout
2. **Parse** — raw XML is normalized into a common schema regardless of RSS/Atom format
3. **Classify** — titles and descriptions are scanned against a severity regex to flag critical stories
4. **Render** — results stream into a live `rich` dashboard (or plain stdout as fallback)
5. **Export** — the full result set is serialized into a structured Markdown report

## Requirements

- Python 3.7+
- `rich` (auto-installed on first run; optional — the script runs fine without it)

## License

MIT

---

<sub>Part of the <code>devforge</code> toolkit.</sub>
