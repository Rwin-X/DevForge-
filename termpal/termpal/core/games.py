"""Mini-game logic for interacting with the creature.

Each game exposes plain functions/classes with no curses dependency,
so the rules can be unit-tested headlessly. The ui layer drives these
through keypresses and renders the state.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


# ---------------------------------------------------------------------
# Guess the number - the creature "thinks of" a number, you narrow it
# down. Simple, deterministic-with-a-seed, easy to unit test.
# ---------------------------------------------------------------------

@dataclass
class GuessGame:
    low: int = 1
    high: int = 20
    max_attempts: int = 5
    target: int = field(default=0)
    attempts_used: int = 0
    finished: bool = False
    won: bool = False

    def __post_init__(self) -> None:
        if self.target == 0:
            self.target = random.randint(self.low, self.high)

    def guess(self, value: int) -> str:
        if self.finished:
            return "The game is already over."
        self.attempts_used += 1
        if value == self.target:
            self.finished = True
            self.won = True
            return f"Correct. The number was {self.target}."
        remaining = self.max_attempts - self.attempts_used
        if remaining <= 0:
            self.finished = True
            self.won = False
            return f"Out of attempts. The number was {self.target}."
        direction = "higher" if value < self.target else "lower"
        return f"Try {direction}. {remaining} attempts left."


# ---------------------------------------------------------------------
# Reflex/catch game - a target position moves each tick; hitting the
# right key at the right moment scores a point. Modeled as pure state
# so it can be driven by a fixed sequence of ticks/inputs in tests.
# ---------------------------------------------------------------------

_UNSET_POSITION = -1


@dataclass
class CatchGame:
    track_width: int = 20
    rounds: int = 8
    score: int = 0
    round_number: int = 0
    target_position: int = field(default=_UNSET_POSITION)
    finished: bool = False

    def __post_init__(self) -> None:
        # Only randomize if the caller didn't supply a starting
        # position - callers (including tests) may seed a specific
        # target deterministically.
        if self.target_position == _UNSET_POSITION:
            self.target_position = random.randint(0, self.track_width - 1)

    def attempt_catch(self, position: int) -> bool:
        """Player attempts to catch at `position`. Returns True on hit."""
        if self.finished:
            return False
        hit = position == self.target_position
        if hit:
            self.score += 1
        self.round_number += 1
        if self.round_number >= self.rounds:
            self.finished = True
        else:
            self.target_position = random.randint(0, self.track_width - 1)
        return hit

    def result_summary(self) -> str:
        return f"Caught {self.score} of {self.rounds}."
