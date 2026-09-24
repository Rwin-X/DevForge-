"""Color pair setup for the phosphor-terminal aesthetic.

curses color pairs are process-global small integers, so this module
owns the numbering and exposes named constants instead of magic
numbers scattered through the render code.
"""

from __future__ import annotations

import curses

PAIR_DEFAULT = 1
PAIR_ACCENT = 2
PAIR_ACCENT_DIM = 3
PAIR_WARNING = 4
PAIR_DANGER = 5
PAIR_BORDER = 6


def init_colors() -> None:
    """Register color pairs. Safe to call once curses is initialized.

    Falls back gracefully on terminals without color support - curses
    will simply render in the default foreground/background.
    """
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK

    curses.init_pair(PAIR_DEFAULT, curses.COLOR_WHITE, bg)
    curses.init_pair(PAIR_ACCENT, curses.COLOR_GREEN, bg)
    curses.init_pair(PAIR_ACCENT_DIM, curses.COLOR_CYAN, bg)
    curses.init_pair(PAIR_WARNING, curses.COLOR_YELLOW, bg)
    curses.init_pair(PAIR_DANGER, curses.COLOR_RED, bg)
    curses.init_pair(PAIR_BORDER, curses.COLOR_GREEN, bg)


def attr(pair: int, bold: bool = False) -> int:
    a = curses.color_pair(pair)
    if bold:
        a |= curses.A_BOLD
    return a
