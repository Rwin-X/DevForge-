# Nova — a minimal, Ubuntu-themed music player

A lightweight desktop music player for Linux, built with PyQt6.
Visually minimal, feature set inspired by Spotify (library, playlists,
queue, search, shuffle/repeat), styled with Ubuntu's actual **Yaru**
design language (Ubuntu Orange `#E95420` + Aubergine `#2C001E`).

## Features

- **Local playback** — MP3, FLAC, WAV, OGG, M4A, OPUS
- **Embedded album art** — reads cover art straight from your files'
  tags; generates a tasteful gradient placeholder for tracks that don't
  have any, so the UI never looks broken
- **Library** — point it at any folder and it recursively scans and
  tags everything (title / artist / album / duration)
- **Search** — instant filter across title, artist, and album
- **Playlists** — create playlists, add tracks from the right-click
  menu, browse them as cover-art cards
- **Queue** — a dedicated "play next" list, separate from your library
- **Full transport** — play/pause, next/previous, seek bar, shuffle,
  repeat (off / all / one), volume
- **Minimal, native-feeling UI** — rounded corners, Ubuntu's font
  stack, thin Yaru-style scrollbars, no clutter

## Requirements

- Linux with a working audio backend (PipeWire or PulseAudio — this is
  standard on any modern Ubuntu/GNOME desktop)
- Python 3.10+

## Setup

```bash
pip install PyQt6 mutagen --break-system-packages
# or, inside a virtualenv:
python3 -m venv venv && source venv/bin/activate
pip install PyQt6 mutagen
```

> `PyQt6` includes `QtMultimedia`, which Nova uses for playback — no
> separate install needed. `mutagen` reads audio tags and embedded
> cover art.

## Run

```bash
python3 nova_player.py
```

## Usage

1. Click **Add Music Folder** (top-right, or on the empty-state screen)
   and pick a directory. Nova scans it recursively.
2. Double-click any track to play it.
3. Right-click a track for **Play**, **Add to Queue**, or **Add to
   Playlist**.
4. Use the sidebar to switch between **Songs**, **Queue**, and
   **Playlists**.
5. Click **+ New Playlist** in the sidebar to create one, then add
   tracks to it from the right-click menu.
6. The bottom bar has full transport controls: shuffle, previous,
   play/pause, next, repeat, a seek bar, and volume.

## Project structure

```
nova_player.py   Main window, application logic, playback engine
theme.py         Yaru color palette + Qt stylesheet (QSS)
library.py       Track model, folder scanner, tag/cover-art extraction
widgets.py       Custom widgets: cover art tiles, track rows, buttons, cards
```

## Notes

- All playback and metadata reading is fully local — no network access,
  no telemetry, no external cover-art fetching.
- Cover art is read from whatever your files already have embedded
  (ID3 `APIC` for MP3, FLAC `PICTURE` blocks, MP4 `covr` atoms). Files
  without embedded art get a generated placeholder instead of a blank
  square.
created by Rwin-X
