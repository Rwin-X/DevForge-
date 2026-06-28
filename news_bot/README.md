# ⚡ TechPulse News Bot

> Automated Tech News Collector — @Rwin-X

---

## Features

- **10 Major Sources**: The Verge, TechCrunch, Ars Technica, Wired, Hacker News, MIT Tech Review, ZDNet, VentureBeat, 9to5Google, 9to5Mac


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
  
      "url": "https://...",
      "source": "TechCrunch",
      "published": "Fri, 27 Jun 2025 ...",
      "summary": "English summary...",
   
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
