# ⚡ TechPulse News Bot

> Automated Tech News Collector with Persian Translation — @black8arch

---

## Features

- **10 Major Sources**: The Verge, TechCrunch, Ars Technica, Wired, Hacker News, MIT Tech Review, ZDNet, VentureBeat, 9to5Google, 9to5Mac
- **Dual Language Output**: Save articles in English or Persian (فارسی)
- **Auto-Translation**: Deep Google Translate integration (EN → FA)
- **Dual Format**: JSON (structured) + TXT (human-readable)
- **Rich CLI UI**: Progress bars, tables, color-coded terminal output
- **Rate-limit Friendly**: Built-in delays between requests + retries
- **Logging**: All operations logged to `logs/bot.log`

---

## Install

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
# English output (default)
python news_bot.py

# Persian output (auto-translate)
python news_bot.py --lang fa

# Both languages saved simultaneously
python news_bot.py --lang both

# Control articles per source (default: 8)
python news_bot.py --max 5 --lang fa

# Choose specific sources
python news_bot.py --sources "TechCrunch,Wired,The Verge"

# Only JSON output, skip TXT
python news_bot.py --format json --lang fa

# All options combined
python news_bot.py --lang both --max 10 --format both --sources "TechCrunch,Ars Technica"
```

---

## Output Files

All files saved to `output/` directory:

| File | Description |
|------|-------------|
| `tech_news_en_TIMESTAMP.json` | English structured JSON |
| `tech_news_en_TIMESTAMP.txt` | English readable report |
| `tech_news_fa_TIMESTAMP.json` | Persian structured JSON |
| `tech_news_fa_TIMESTAMP.txt` | Persian readable report |

---

## JSON Structure

```json
{
  "meta": {
    "generated_at": "2025-06-27T14:30:00",
    "language": "fa",
    "total_articles": 80,
    "sources": ["TechCrunch", "Wired", ...]
  },
  "articles": [
    {
      "title": "Original English title",
      "title_fa": "عنوان فارسی",
      "url": "https://...",
      "source": "TechCrunch",
      "published": "Fri, 27 Jun 2025 ...",
      "summary": "English summary...",
      "summary_fa": "خلاصه فارسی...",
      "translated": true,
      "fetched_at": "2025-06-27T14:30:00"
    }
  ]
}
```

---

## Sources

| Source | Feed Type |
|--------|-----------|
| The Verge | RSS |
| TechCrunch | RSS |
| Ars Technica | RSS |
| Wired | RSS |
| Hacker News | RSS |
| MIT Technology Review | RSS |
| ZDNet | RSS |
| VentureBeat | RSS |
| 9to5Google | RSS |
| 9to5Mac | RSS |

---

*Built with Python · feedparser · deep-translator · rich*
