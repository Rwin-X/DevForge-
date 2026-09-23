# Jargon

**A single-file, zero-dependency web app for finding cybersecurity learning resources — fast.**

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)
![Single file](https://img.shields.io/badge/build-single%20HTML%20file-lightgrey.svg)

Type any topic. ReconBar opens live, real search results across Google, Bing, DuckDuckGo, and YouTube for exactly what you typed — optionally restricted to a curated list of trusted security-education domains — and surfaces a hand-picked library of sites for 30 common security topics as a bonus underneath.

No backend. No API keys. No build step. One HTML file.

---

## Table of contents

- [Why ReconBar](#why-reconbar)
- [Features](#features)
- [How it works](#how-it-works)
- [Getting started](#getting-started)
- [Customization](#customization)
- [Project structure](#project-structure)
- [Limitations](#limitations)
- [Possible extensions](#possible-extensions)
- [Contributing](#contributing)


## Why ReconBar

Searching for cybersecurity learning material usually means the same manual loop: open Google, open YouTube, filter out low-quality results, repeat across a handful of engines and channels you already trust. ReconBar automates that loop into a single search box — it doesn't try to be a search engine itself (a static page can't crawl the web), it builds the correct, real query URLs for the engines that already exist and gets you there in one click.

## Features

- **Live search, not a static list.** Every query generates working links to Google, Bing, DuckDuckGo, and YouTube for exactly what you typed. No query rewriting, no filtering, by default.
- **Trusted-sources toggle.** Restrict the same four searches to a fixed set of reputable domains — OWASP, PortSwigger, HackTricks, TryHackMe, HTB Academy, SANS, MITRE ATT&CK, NIST, CISA, First.org, Exploit-DB, HackerOne, Cryptopals — using `site:` operators.
- **YouTube, by channel.** Generates search links scoped to well-known security-education channels (John Hammond, LiveOverflow, IppSec, NetworkChuck, TCM Security, HackerSploit, David Bombal, Professor Messer) instead of guessing exact video URLs that could break.
- **Curated library.** 30 built-in topics — Web Security, SQL Injection, XSS, Pentesting, Malware Analysis, Reverse Engineering, Cryptography, CTF, OSINT, Cloud Security, DFIR, Active Directory, Bug Bounty, Mobile Security, IoT, Wireless, Social Engineering, Threat Intel, Blue Team/SOC, Linux, Windows, Python for Security, Binary Exploitation, Containers/Kubernetes, API Security, GRC, Secure Coding, Auth/Passwords, Certifications — surface automatically on a matching query, shown below the live results.
- **Export.** Save the current search result as `.json`, `.md`, or `.txt`.
- **Minimal, white, accessible UI.** IBM Plex Sans/Mono, one accent color, keyboard-focus states, responsive down to mobile.

## How it works

There's no server-side crawler — a static page has no way to call arbitrary third-party APIs. Instead, ReconBar constructs real, working search-engine URLs client-side and opens them in a new tab. That's the only way a browser-only tool can return genuinely live, current results without a backend or an API key.

```
buildLiveLinks(query, trustedOnly)
  → Google / Bing / DuckDuckGo / YouTube URLs for the raw query
  → if trustedOnly: query + "(site:owasp.org OR site:portswigger.net OR ...)"
  → one YouTube search URL per curated channel
```

The curated library is a separate, independent lookup (the `TOPICS` array) matched against the query by substring/alias. It never gates or delays the live search — it's a bonus panel, not a prerequisite.

## Getting started

Open the HTML file in any browser. That's the entire setup.

```bash
open reconbar.html        # macOS
start reconbar.html       # Windows
xdg-open reconbar.html    # Linux
```

The only external requests the page makes are to Google Fonts (IBM Plex Sans / IBM Plex Mono) for typography — everything else is inline.

## Customization

**Add a topic** to the curated library — append an entry to `TOPICS`:

```js
{name:"Your Topic", aliases:["alt name","abbrev"], sites:[
  {t:"Site Title", u:"https://example.com/"}
]}
```

**Add a trusted domain** — append a bare hostname to `TRUSTED_DOMAINS`:

```js
const TRUSTED_DOMAINS = [..., "example.org"];
```

**Add a YouTube channel** — append an entry to `CHANNELS` with its `@handle`:

```js
{name:"Channel Display Name", handle:"@channelhandle"}
```

**Change the accent color / typography** — edit the CSS custom properties at the top of the `<style>` block (`--accent`, `--ink`, `--mono`, `--sans`).

## Project structure

```
reconbar.html   # everything — markup, styles, data, and logic in one file
README.md       # this file
```

No `package.json`, no bundler, no `node_modules`. The dataset (`TOPICS`, `CHANNELS`, `TRUSTED_DOMAINS`) lives as plain JS arrays inside the script tag.

## Limitations

- **Export only works inside a Claude Artifact.** The `.json` / `.md` / `.txt` download buttons use Claude's `downloads` capability (`window.claude.use('downloads')`). Opened as a plain file or hosted elsewhere (GitHub Pages, a personal server), that API doesn't exist — the buttons stay disabled and a note explains why. Search and browsing behave identically everywhere.
- Curated library entries are maintained by hand and can go stale; verify links periodically.
- Result quality on the search-engine side depends on that engine — ReconBar only builds the query URL, it doesn't rank or filter results itself.
- The topic matcher is a simple substring/alias check, not fuzzy matching — typos may not match a curated topic (the live search still works regardless).

## Possible extensions

Not implemented, but natural next steps if this grows:
- A `localStorage`-backed search history (per-device, not shared).
- A JSON file for `TOPICS`/`CHANNELS`/`TRUSTED_DOMAINS` instead of inline arrays, for easier community contributions.
- Keyboard shortcuts (e.g. `/` to focus the search box).

## Contributing

This is a single-file project — contributions are just edits to the `TOPICS`, `CHANNELS`, or `TRUSTED_DOMAINS` arrays, or CSS tweaks. Open a pull request with the new entry and a one-line reason it belongs (reputable source, active channel, etc.).

