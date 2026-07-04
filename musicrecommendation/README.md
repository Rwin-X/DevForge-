<div align="center">

# 🎧 Sonar

**Type a song. Sonar finds its echo.**

A minimal, single-file web app that discovers music similar to a track you already love —
no backend, no API key, no build step, no dependencies.

![style](https://img.shields.io/badge/style-minimal-1c7a4d?style=flat-square)
![stack](https://img.shields.io/badge/stack-vanilla%20JS-0f5c39?style=flat-square)
![api](https://img.shields.io/badge/data-iTunes%20Search%20API-2fbf7f?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-2fbf7f?style=flat-square)

</div>

---

## ✨ What it does

Give Sonar a song title, and it hands back a curated list of similar tracks —
same artist, same genre, same sonic neighborhood — each with a 30-second
preview you can play instantly, right in the browser.

No sign-up. No server. No tracking. One HTML file that runs anywhere.

<br>

## 🧠 How it works

Sonar's recommendation logic runs entirely client-side, in four steps:

| Step | What happens |
|------|--------------|
| **1. Look up the seed track** | Your query is sent to Apple's public **iTunes Search API** (`/search?media=music&entity=song`). No key required. The first match becomes the *seed track*, shown at the top of the page. |
| **2. Extract a fingerprint** | From the seed track, Sonar pulls three signals: `artistId`, `artistName`, and `primaryGenreName`. |
| **3. Search two ways, in parallel** | **Same artist** — an `iTunes Lookup` call (`/lookup?id={artistId}&entity=song`) pulls other tracks by the same artist. **Same genre** — a second search using the genre name pulls tracks from *other* artists in the same space, then filters duplicates and shuffles for variety. |
| **4. Blend and display** | ~6 same-artist tracks + ~14 same-genre tracks are merged into one list — artwork, artist, genre tag, and a play button for each. |

Everything happens live, in real time, with no caching or storage between sessions.

<br>

## 🎨 Design

The interface leans deliberately minimal — white canvas, a single green accent,
generous whitespace, and no visual noise competing with the music itself.

The only motion on the page is a small pulse-bar beside the logo, a quiet nod
to an audio waveform, animated just enough to feel alive without demanding attention.

<br>

## 🚀 Usage

```
1. Open music-finder.html in any modern browser
2. Type a song title — e.g. "Redbone"
   or "Artist — Song" — e.g. "Tame Impala — The Less I Know The Better"
3. Press Find similar (or hit Enter)
4. Click the ▶ button on any result for a 30-second preview
```

That's it — no installation, no `npm install`, no configuration.

<br>

## 🔍 Tech notes

- **No API key** — the iTunes Search API is public and free to call directly from the browser
- **No frameworks** — plain HTML, CSS, and vanilla JavaScript, in a single file
- **No storage** — every search is stateless; nothing is saved between sessions
- **Previews only** — playback uses the 30-second preview clips iTunes provides, not full tracks

<br>

## ⚠️ Known limitations

- Match quality depends on how well iTunes tags genre — niche or crossover genres return a shallower pool
- Not every track has a preview clip; those show a disabled play button
- Regional catalog differences may affect which songs and previews are available

<br>

## 📄 License

MIT — do whatever you'd like with it.
