# Sonar

A minimal, single-file web app that finds music similar to a song you already love — no backend, no API key, no build step.

Type in a track, and Sonar looks up its artist and genre, then surfaces other songs that share that sonic fingerprint, each with a 30-second preview you can play right in the browser.

![style](https://img.shields.io/badge/style-minimal-1c7a4d?style=flat-square)
![stack](https://img.shields.io/badge/stack-vanilla%20JS-0f5c39?style=flat-square)
![api](https://img.shields.io/badge/data-iTunes%20Search%20API-2fbf7f?style=flat-square)

## How it works

1. **Look up the seed track** — your query is sent to Apple's public `iTunes Search API` (`/search?media=music&entity=song`). No API key required. The first match becomes the "seed" track shown at the top of the page.
2. **Extract a fingerprint** — from the seed track, Sonar pulls the `artistId`, `artistName`, and `primaryGenreName`.
3. **Search two ways, in parallel**:
   - **Same artist** — an `iTunes Lookup` call (`/lookup?id={artistId}&entity=song`) returns other tracks by the same artist.
   - **Same genre** — a second search using the genre name returns tracks from *other* artists in the same space, then filters out duplicates and shuffles for variety.
4. **Blend and display** — roughly 6 same-artist tracks + 14 same-genre tracks are combined into one result list, each with artwork, artist, genre tag, and a play button for the 30-second preview clip.

Everything runs client-side in the browser. There's no server, no database, and no build process — just one HTML file.

## Usage

1. Download `music-finder.html`.
2. Open it in any modern browser (Chrome, Firefox, Safari, Edge).
3. Type a song title (e.g. `Redbone`) or `Artist — Song` (e.g. `Tame Impala — The Less I Know The Better`) for a more precise match.
4. Press **Find similar** or hit **Enter**.
5. Click the play button on any result to hear a 30-second preview.

No installation, no dependencies, no `npm install`.

## Why it looks the way it does

The interface is intentionally minimal: white background, a single green accent, generous whitespace, and no unnecessary chrome. The only motion is a small animated pulse-bar next to the logo — a nod to an audio waveform — kept quiet so it doesn't compete with the content.

## Tech notes

- **No API key** — the iTunes Search API is public and free to call directly from the browser.
- **No frameworks** — plain HTML, CSS, and vanilla JavaScript in a single file.
- **No storage** — nothing is saved between sessions; every search is stateless.
- **Previews only** — playback uses the 30-second preview clips iTunes provides, not full tracks.

## Known limitations

- Match quality depends on how well iTunes tags genre — some niche or crossover genres return a shallower pool of results.
- Not every track has a preview clip; those show a disabled play button.
- Regional catalog differences may affect which songs and previews are available.

## License

MIT — do whatever you'd like with it.
