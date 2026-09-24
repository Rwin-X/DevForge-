"""Small reusable curses drawing helpers.

Every function here takes a curses window and plain data - no
knowledge of the Creature class or game rules. Keeps rendering
separate from what is being rendered.
"""

from __future__ import annotations

import curses

from termpal.ui.theme import PAIR_ACCENT, PAIR_BORDER, PAIR_DANGER, PAIR_DEFAULT, PAIR_WARNING, attr


def safe_addstr(win, y: int, x: int, text: str, attrs: int = 0) -> None:
    """addstr that swallows the curses.error thrown when text would
    overflow the bottom-right corner of the window - a well-known
    curses quirk rather than a bug in the caller.
    """
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x < 0 or x >= max_x:
        return
    try:
        win.addstr(y, x, text[: max(0, max_x - x)], attrs)
    except curses.error:
        pass


def draw_box(win, y: int, x: int, height: int, width: int, title: str = "") -> None:
    try:
        win.attron(attr(PAIR_BORDER))
        win.hline(y, x + 1, curses.ACS_HLINE, max(0, width - 2))
        win.hline(y + height - 1, x + 1, curses.ACS_HLINE, max(0, width - 2))
        win.vline(y + 1, x, curses.ACS_VLINE, max(0, height - 2))
        win.vline(y + 1, x + width - 1, curses.ACS_VLINE, max(0, height - 2))
        win.addch(y, x, curses.ACS_ULCORNER)
        win.addch(y, x + width - 1, curses.ACS_URCORNER)
        win.addch(y + height - 1, x, curses.ACS_LLCORNER)
        win.addch(y + height - 1, x + width - 1, curses.ACS_LRCORNER)
        win.attroff(attr(PAIR_BORDER))
    except curses.error:
        pass
    if title:
        safe_addstr(win, y, x + 2, f" {title} ", attr(PAIR_ACCENT, bold=True))


def draw_stat_bar(win, y: int, x: int, width: int, label: str, value: float, max_value: float = 100.0) -> None:
    fraction = max(0.0, min(1.0, value / max_value if max_value else 0.0))
    bar_width = max(1, width - len(label) - 8)
    filled = int(round(bar_width * fraction))

    if fraction <= 0.15:
        pair = PAIR_DANGER
    elif fraction <= 0.4:
        pair = PAIR_WARNING
    else:
        pair = PAIR_ACCENT

    safe_addstr(win, y, x, f"{label:<8}", attr(PAIR_DEFAULT))
    bar_x = x + 9
    safe_addstr(win, y, bar_x, "[", attr(PAIR_DEFAULT))
    safe_addstr(win, y, bar_x + 1, "#" * filled, attr(pair, bold=True))
    safe_addstr(win, y, bar_x + 1 + filled, "-" * (bar_width - filled), attr(PAIR_DEFAULT))
    safe_addstr(win, y, bar_x + 1 + bar_width, "]", attr(PAIR_DEFAULT))
    safe_addstr(win, y, bar_x + bar_width + 3, f"{int(value):>3}", attr(PAIR_DEFAULT))


def center_text(win, y: int, width_start: int, width: int, text: str, attrs: int = 0) -> None:
    x = width_start + max(0, (width - len(text)) // 2)
    safe_addstr(win, y, x, text, attrs)
