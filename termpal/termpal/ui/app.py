"""The curses TUI application.

Owns the main loop, screen state, and input handling. Imports from
core (Creature, storage, sprites, games) but core never imports this
module or curses.
"""

from __future__ import annotations

import curses
import time

from termpal.core.creature import Creature, Mood
from termpal.core.games import CatchGame, GuessGame
from termpal.core.sprites import get_sprite
from termpal.core.storage import get_save_path, save_creature
from termpal.ui.theme import PAIR_ACCENT, PAIR_ACCENT_DIM, PAIR_DANGER, PAIR_DEFAULT, PAIR_WARNING, attr, init_colors
from termpal.ui.widgets import center_text, draw_box, draw_stat_bar, safe_addstr

TICK_SECONDS = 2.0
AUTOSAVE_SECONDS = 20.0

MOOD_LABELS = {
    Mood.THRIVING: "THRIVING",
    Mood.CONTENT: "CONTENT",
    Mood.BORED: "BORED",
    Mood.HUNGRY: "HUNGRY",
    Mood.TIRED: "TIRED",
    Mood.SICK: "UNWELL",
    Mood.CRITICAL: "CRITICAL",
    Mood.DEAD: "GONE",
}


class App:
    def __init__(self, stdscr, creature: Creature):
        self.stdscr = stdscr
        self.creature = creature
        self.message = "Welcome back."
        self.screen = "home"  # home | guess | catch | confirm_reset
        self.guess_game: GuessGame | None = None
        self.guess_input = ""
        self.catch_game: CatchGame | None = None
        self.catch_flash_until = 0.0
        self.catch_hit_last = False
        self.last_save = time.time()
        self.running = True

        try:
            curses.curs_set(0)
        except curses.error:
            pass  # some terminals/mocked screens do not support this
        stdscr.nodelay(True)
        stdscr.timeout(int(TICK_SECONDS * 1000))
        init_colors()

    # ---- main loop ------------------------------------------------------

    def run(self) -> None:
        while self.running:
            self.creature.tick()
            self._autosave_if_due()
            self._render()
            self._handle_input()
        save_creature(self.creature)

    def _autosave_if_due(self) -> None:
        now = time.time()
        if now - self.last_save >= AUTOSAVE_SECONDS:
            save_creature(self.creature)
            self.last_save = now

    # ---- input dispatch ---------------------------------------------------

    def _handle_input(self) -> None:
        try:
            key = self.stdscr.getch()
        except curses.error:
            key = -1
        if key == -1:
            return

        if self.screen == "home":
            self._handle_home_input(key)
        elif self.screen == "guess":
            self._handle_guess_input(key)
        elif self.screen == "catch":
            self._handle_catch_input(key)
        elif self.screen == "confirm_reset":
            self._handle_confirm_reset_input(key)

    def _handle_home_input(self, key: int) -> None:
        ch = chr(key) if 0 <= key < 256 else ""
        if ch in ("q", "Q"):
            self.running = False
        elif ch in ("f", "F"):
            self.message = self.creature.feed()
        elif ch in ("p", "P"):
            self.message = self.creature.play()
        elif ch in ("c", "C"):
            self.message = self.creature.clean()
        elif ch in ("r", "R"):
            self.message = self.creature.rest()
        elif ch in ("g", "G"):
            if self.creature.alive:
                self.guess_game = GuessGame()
                self.guess_input = ""
                self.screen = "guess"
                self.message = ""
        elif ch in ("m", "M"):
            if self.creature.alive:
                # track_width=10 matches the single-digit (0-9) key
                # input and the 10-cell track drawn by the overlay.
                self.catch_game = CatchGame(track_width=10)
                self.screen = "catch"
                self.message = ""
        elif ch in ("x", "X"):
            self.screen = "confirm_reset"

    def _handle_guess_input(self, key: int) -> None:
        assert self.guess_game is not None
        if key in (curses.KEY_ENTER, 10, 13):
            if self.guess_input:
                try:
                    value = int(self.guess_input)
                except ValueError:
                    self.message = "Enter a number."
                    self.guess_input = ""
                    return
                result = self.guess_game.guess(value)
                self.guess_input = ""
                if self.guess_game.finished:
                    self.creature.record_game_result(self.guess_game.won)
                    self.message = result
                    self.screen = "home"
                    self.guess_game = None
                else:
                    self.message = result
            return
        if key in (curses.KEY_BACKSPACE, 127, 8):
            self.guess_input = self.guess_input[:-1]
            return
        ch = chr(key) if 0 <= key < 256 else ""
        if ch == "\x1b":  # ESC
            self.screen = "home"
            self.guess_game = None
            self.message = "Left the guessing game."
            return
        if ch.isdigit() and len(self.guess_input) < 3:
            self.guess_input += ch

    def _handle_catch_input(self, key: int) -> None:
        assert self.catch_game is not None
        ch = chr(key) if 0 <= key < 256 else ""
        if ch == "\x1b":
            self.screen = "home"
            self.catch_game = None
            self.message = "Left the catch game."
            return
        if ch.isdigit():
            position = int(ch)
            hit = self.catch_game.attempt_catch(position)
            self.catch_hit_last = hit
            self.catch_flash_until = time.time() + 0.6
            if self.catch_game.finished:
                won = self.catch_game.score >= (self.catch_game.rounds // 2 + 1)
                self.creature.record_game_result(won)
                self.message = self.catch_game.result_summary()
                self.screen = "home"
                self.catch_game = None

    def _handle_confirm_reset_input(self, key: int) -> None:
        ch = chr(key) if 0 <= key < 256 else ""
        if ch in ("y", "Y"):
            name = self.creature.name
            self.creature = Creature(name=name)
            save_creature(self.creature)
            self.message = f"A new creature begins. Farewell, {name}."
            self.screen = "home"
        elif ch in ("n", "N", "\x1b"):
            self.screen = "home"
            self.message = "Reset cancelled."

    # ---- rendering ------------------------------------------------------

    def _render(self) -> None:
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()

        if height < 20 or width < 50:
            safe_addstr(
                self.stdscr, 0, 0,
                "Terminal too small. Resize to at least 50x20.",
                attr(PAIR_WARNING, bold=True),
            )
            self.stdscr.refresh()
            return

        self._draw_header(width)
        self._draw_creature_panel(3, width)
        self._draw_stats_panel(3 + 12, width)
        self._draw_message_bar(height - 3, width)
        self._draw_footer(height - 1, width)

        if self.screen == "guess":
            self._draw_guess_overlay(height, width)
        elif self.screen == "catch":
            self._draw_catch_overlay(height, width)
        elif self.screen == "confirm_reset":
            self._draw_confirm_reset_overlay(height, width)

        self.stdscr.refresh()

    def _draw_header(self, width: int) -> None:
        center_text(
            self.stdscr, 0, 0, width,
            f"TERMPAL :: {self.creature.name}",
            attr(PAIR_ACCENT, bold=True),
        )
        stage = self.creature.life_stage()
        mood = self.creature.mood()
        mood_pair = PAIR_DANGER if mood in (Mood.CRITICAL, Mood.DEAD) else (
            PAIR_WARNING if mood in (Mood.SICK, Mood.HUNGRY, Mood.TIRED, Mood.BORED) else PAIR_ACCENT
        )
        subtitle = f"stage: {stage}   mood: {MOOD_LABELS[mood]}   age: {self.creature.age_hours():.1f}h"
        center_text(self.stdscr, 1, 0, width, subtitle, attr(mood_pair))

    def _draw_creature_panel(self, y: int, width: int) -> None:
        draw_box(self.stdscr, y, 2, 10, width - 4, title="creature")
        sprite = get_sprite(self.creature.life_stage(), self.creature.mood())
        start_y = y + 2
        for i, line in enumerate(sprite):
            center_text(self.stdscr, start_y + i, 2, width - 4, line, attr(PAIR_ACCENT, bold=True))

    def _draw_stats_panel(self, y: int, width: int) -> None:
        draw_box(self.stdscr, y, 2, 8, width - 4, title="status")
        bar_width = min(40, width - 10)
        draw_stat_bar(self.stdscr, y + 1, 4, bar_width, "hunger", self.creature.hunger)
        draw_stat_bar(self.stdscr, y + 2, 4, bar_width, "energy", self.creature.energy)
        draw_stat_bar(self.stdscr, y + 3, 4, bar_width, "fun", self.creature.fun)
        draw_stat_bar(self.stdscr, y + 4, 4, bar_width, "hygiene", self.creature.hygiene)
        draw_stat_bar(self.stdscr, y + 5, 4, bar_width, "health", self.creature.health)

        if not self.creature.alive:
            safe_addstr(
                self.stdscr, y + 6, 4,
                f"Cause: {self.creature.death_reason}. Press X to begin again.",
                attr(PAIR_DANGER, bold=True),
            )

    def _draw_message_bar(self, y: int, width: int) -> None:
        if self.message:
            center_text(self.stdscr, y, 0, width, self.message, attr(PAIR_ACCENT_DIM))

    def _draw_footer(self, y: int, width: int) -> None:
        footer = "[F]eed  [P]lay  [C]lean  [R]est  [G]uess game  [M]atch game  [X]reset  [Q]uit"
        center_text(self.stdscr, y, 0, width, footer[: max(0, width - 1)], attr(PAIR_DEFAULT))

    def _draw_guess_overlay(self, height: int, width: int) -> None:
        assert self.guess_game is not None
        box_h, box_w = 9, min(50, width - 4)
        y = (height - box_h) // 2
        x = (width - box_w) // 2
        draw_box(self.stdscr, y, x, box_h, box_w, title="guessing game")
        lines = [
            f"Guess a number between {self.guess_game.low} and {self.guess_game.high}.",
            f"Attempts left: {self.guess_game.max_attempts - self.guess_game.attempts_used}",
            "",
            f"Your guess: {self.guess_input}",
            "",
            "[Enter] submit    [Esc] leave",
        ]
        for i, line in enumerate(lines):
            safe_addstr(self.stdscr, y + 2 + i, x + 3, line, attr(PAIR_DEFAULT))
        if self.message:
            safe_addstr(self.stdscr, y + box_h - 2, x + 3, self.message[: box_w - 6], attr(PAIR_ACCENT_DIM))

    def _draw_catch_overlay(self, height: int, width: int) -> None:
        assert self.catch_game is not None
        box_h, box_w = 9, min(50, width - 4)
        y = (height - box_h) // 2
        x = (width - box_w) // 2
        draw_box(self.stdscr, y, x, box_h, box_w, title="catch game")

        track = ["."] * 10
        pos = self.catch_game.target_position
        if 0 <= pos < 10:
            track[pos] = "*"
        track_str = " ".join(track)

        safe_addstr(self.stdscr, y + 2, x + 3, "Press the number matching the '*' position.", attr(PAIR_DEFAULT))
        center_text(self.stdscr, y + 4, x, box_w, track_str, attr(PAIR_ACCENT, bold=True))
        center_text(
            self.stdscr, y + 5, x, box_w,
            "0 1 2 3 4 5 6 7 8 9",
            attr(PAIR_DEFAULT),
        )
        safe_addstr(
            self.stdscr, y + 6, x + 3,
            f"Round {self.catch_game.round_number + 1}/{self.catch_game.rounds}   Score {self.catch_game.score}",
            attr(PAIR_DEFAULT),
        )
        if time.time() < self.catch_flash_until:
            flash = "HIT" if self.catch_hit_last else "MISS"
            pair = PAIR_ACCENT if self.catch_hit_last else PAIR_DANGER
            safe_addstr(self.stdscr, y + box_h - 2, x + 3, flash, attr(pair, bold=True))
        else:
            safe_addstr(self.stdscr, y + box_h - 2, x + 3, "[Esc] leave", attr(PAIR_DEFAULT))

    def _draw_confirm_reset_overlay(self, height: int, width: int) -> None:
        box_h, box_w = 7, min(54, width - 4)
        y = (height - box_h) // 2
        x = (width - box_w) // 2
        draw_box(self.stdscr, y, x, box_h, box_w, title="confirm")
        safe_addstr(
            self.stdscr, y + 2, x + 3,
            f"Release {self.creature.name} and start a brand new creature?",
            attr(PAIR_WARNING, bold=True),
        )
        safe_addstr(self.stdscr, y + 3, x + 3, "This cannot be undone.", attr(PAIR_DEFAULT))
        safe_addstr(self.stdscr, y + 5, x + 3, "[Y] confirm    [N] cancel", attr(PAIR_DEFAULT))


def run_app(stdscr, creature: Creature) -> None:
    app = App(stdscr, creature)
    app.run()
