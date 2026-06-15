# 🔐 HashForge

**Cryptographic file hashing tool — minimalist, fast, local-only.**

---

## Features

| Feature | Detail |
|---|---|
| **Algorithms** | MD5, SHA1, SHA256, SHA512 |
| **File input** | Drag & drop · Browse dialog |
| **File metadata** | Name, size (human-readable), full path |
| **Large file support** | Streaming in 8 MB chunks — handles multi-GB files |
| **Copy hash** | One-click per algorithm |
| **Verify** | Paste any hash to compare against computed results |
| **History** | Persisted across sessions · Full-text search |
| **Export** | TXT report · JSON data |
| **Dark mode** | Toggle in sidebar |
| **Privacy** | Zero network calls — 100% local processing |

---

## Installation

```bash
# 1. Clone or download the project
cd HashForge

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependency
pip install -r requirements.txt

# 4. Run
python main.py
```

**Requirements:** Python 3.11+ · PySide6 6.6+

---

## Project Structure

```
HashForge/
├── main.py                     # Entry point
├── requirements.txt
├── README.md
└── hashforge/
    ├── core/
    │   ├── hasher.py           # Hash engine (streaming, Qt worker thread)
    │   └── history.py          # JSON-backed local history
    ├── ui/
    │   ├── main_window.py      # Root window, orchestrator
    │   ├── drop_zone.py        # Drag & drop / browse widget
    │   ├── hash_row.py         # Single algorithm result card
    │   ├── file_info_card.py   # File metadata banner
    │   ├── verify_panel.py     # Hash comparison input
    │   └── history_panel.py    # Searchable history list
    └── utils/
        ├── theme.py            # Light/dark stylesheet generator
        └── exporter.py         # TXT/JSON export helpers
```

---

## Architecture Notes

- **HashWorker** runs in a `QThread`; the UI never blocks during computation.
- **Chunked I/O**: files are read in 8 MB increments so even a 50 GB file fits in memory.
- **HistoryManager** persists to `~/.hashforge/history.json` (max 500 entries, auto-pruned).
- **ThemeManager** generates a full Qt stylesheet at runtime — no compiled resource files needed.
- All components are stateless view widgets; state lives in `MainWindow`.

---

## Usage

1. **Drag** a file onto the drop zone, or click **Browse file**.
2. HashForge computes all selected algorithms concurrently in a background thread.
3. Click **Copy** next to any hash to put it on the clipboard.
4. Paste an expected hash into the **Verify** panel to confirm integrity.
5. Use **Export TXT / JSON** from the sidebar to save a report.
6. Switch to **History** to browse or search past results.

---

## Security Notes

- HashForge is an **integrity verification** tool, not an authentication primitive.
- MD5 and SHA1 are **cryptographically broken** for collision resistance; use SHA256 or SHA512 for security-critical workflows.
- No data leaves your machine.

---

*Built with Python · PySide6 · hashlib*
