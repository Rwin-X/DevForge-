# YearGrid — Consistency Engine

A personal GitHub-style productivity tracker for 360 days of disciplined output.

## Stack

- HTML · CSS · Vanilla JS
- LocalStorage (no backend, no cloud)
- JetBrains Mono

## Activities

| Activity | Color  | Key      |
|----------|--------|----------|
| 🏃 RUN   | Green  | run      |
| ⚒ CREATE | Blue   | create   |
| 📚 LEARN | Orange | learn    |
| 📖 BOOK  | Purple | book     |

## Grid Logic

- **Empty** → dark cell
- **Single activity** → solid color
- **Multiple activities** → conic-gradient pie split (precision quadrant division)
- **Today** → pulsing white outline
- **Future** → faded, unclickable

## Usage

1. Open `index.html` in any modern browser
2. Click any past or current day cell
3. Toggle activities in the popup
4. Hit **SAVE**

All data persists in `localStorage` under key `yeargrid_data_v1`.

## Reset

- **CLEAR DAY** in modal → wipes a single day
- **Reset All Data** in sidebar → wipes everything (with confirmation)

## Files

```
YearGrid/
├── index.html   — markup + layout
├── style.css    — dark theme, conic-gradient cells, animations
├── script.js    — grid logic, data, stats, modal, tooltip
└── README.md
```

## Notes

- No accounts, no sync, no AI, no notifications
- Designed for offline personal use only
- Data key format: `YYYY-MM-DD`
- Streak counts any day with at least one activity
