# Cybersecurity Resource Finder

A single-file, dependency-free web app for finding cybersecurity learning resources. Type any topic and get live search links across multiple engines, plus a curated library of hand-picked sites for common security domains.

No backend, no build step, no API keys — one HTML file.

## Features

- **Live search, not a static list.** Every query fires real links to Google, Bing, DuckDuckGo, and YouTube for exactly what you typed — no query rewriting, no filtering by default.
- **Trusted-sources toggle.** Restrict the same four searches to a fixed list of reputable security-education domains (OWASP, PortSwigger, HackTricks, TryHackMe, HTB Academy, SANS, MITRE ATT&CK, NIST, CISA, and more) using `site:` operators.
- **YouTube, by channel.** Generates search links inside well-known security-education channels (John Hammond, LiveOverflow, IppSec, NetworkChuck, TCM Security, HackerSploit, David Bombal, Professor Messer) instead of guessing exact video URLs.
- **Curated library.** 30 built-in topics (Web Security, SQL Injection, XSS, Pentesting, Malware Analysis, Reverse Engineering, Cryptography, CTF, OSINT, Cloud Security, DFIR, Active Directory, Bug Bounty, Mobile, IoT, Wireless, Social Engineering, Threat Intel, Blue Team/SOC, Linux, Windows, Python, Binary Exploitation, Containers/K8s, API Security, GRC, Secure Coding, Auth/Passwords, Certifications) surface automatically when your query matches, shown as a bonus below the live results.
- **Export.** Save the current search result as `.json`, `.md`, or `.txt`.

## How it works

There's no server-side crawling — a static page can't call arbitrary APIs. Instead, the app constructs real, working search-engine URLs client-side and opens them in a new tab, which is the only way an in-browser tool can return genuinely live results without an API key or backend.

```
buildLiveLinks(query, trustedOnly)
  → Google, Bing, DuckDuckGo, YouTube URLs for the raw query
  → if trustedOnly: query + "(site:owasp.org OR site:portswigger.net OR ...)"
  → one YouTube search URL per curated channel
```

The curated library is a separate, independent lookup (`TOPICS` array) matched against the query by substring/alias — it never blocks or gates the live search.

## Usage

Open `index.html` in any browser. No install, no dependencies beyond two Google Fonts (IBM Plex Sans / IBM Plex Mono), loaded over CDN.

## Customization

**Add a topic** — append to the `TOPICS` array:

```js
{name:"Your Topic", aliases:["alt name","abbrev"], sites:[
  {t:"Site Title", u:"https://example.com/"}
]}
```

**Add a trusted domain** — append to `TRUSTED_DOMAINS`.

**Add a YouTube channel** — append to `CHANNELS` with its `@handle`.

## Limitations

- **Export only works inside a Claude Artifact.** The `.json`/`.md`/`.txt` download buttons use Claude's `downloads` capability (`window.claude.use('downloads')`). Opened as a plain file or hosted elsewhere (e.g. GitHub Pages), that API doesn't exist — the buttons stay disabled and a note explains this. Search and browsing work identically everywhere.
- Curated library entries are maintained by hand and may go stale; verify links periodically.
- Search-engine result quality depends on the engine, not this app — it only builds the query URL.

## License

Add a license of your choice (MIT is a common default for a small utility like this).
