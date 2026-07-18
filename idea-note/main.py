#!/usr/bin/env python3
"""
Idea Book
=========

A local-only, distraction-free idea vault. Markdown+ notes, linked with
[[wikilinks]], visualized as a constellation graph. No cloud, no login,
no telemetry — just a SQLite file on your disk and your own thinking.

Run:
    pip install -r requirements.txt
    python main.py

Data lives at ~/.ideabook/vault.db
"""

from ui.main_window import main

if __name__ == "__main__":
    main()
