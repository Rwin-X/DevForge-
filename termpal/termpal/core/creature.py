"""Pure logic for the TERMPAL creature.

No terminal, no curses, no I/O. This module owns the creature's state
and the rules for how that state evolves. It can be imported and
exercised in a bare Python process with no display attached.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


# Stat decay rates, in points lost per hour of real elapsed time.
# Tuned so a creature left alone for a full day is hungry and bored
# but not dead - death requires several days of total neglect.
HUNGER_DECAY_PER_HOUR = 4.0
ENERGY_DECAY_PER_HOUR = 2.5
FUN_DECAY_PER_HOUR = 3.0

# Hygiene decays slower; it is only nudged by certain actions/events.
HYGIENE_DECAY_PER_HOUR = 1.5

STAT_MIN = 0.0
STAT_MAX = 100.0

# A stat below this counts as "critical" for mood/health purposes.
CRITICAL_THRESHOLD = 15.0

# Sustained critical hunger, below this, drains health per hour.
STARVATION_HEALTH_DRAIN_PER_HOUR = 6.0

# Age thresholds, in real hours since birth, for life stage.
STAGE_HOURS = {
    "egg": 0.0,
    "hatchling": 0.25,
    "juvenile": 24.0,
    "adult": 24.0 * 5,
    "elder": 24.0 * 20,
}


class Mood(Enum):
    THRIVING = "thriving"
    CONTENT = "content"
    BORED = "bored"
    HUNGRY = "hungry"
    TIRED = "tired"
    SICK = "sick"
    CRITICAL = "critical"
    DEAD = "dead"


def _clamp(value: float) -> float:
    return max(STAT_MIN, min(STAT_MAX, value))


@dataclass
class Creature:
    name: str
    born_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    hunger: float = 80.0   # 100 = full, 0 = starving
    energy: float = 80.0   # 100 = well rested, 0 = exhausted
    fun: float = 80.0      # 100 = entertained, 0 = bored stiff
    hygiene: float = 80.0  # 100 = clean, 0 = filthy
    health: float = 100.0  # 100 = healthy, 0 = dead

    alive: bool = True
    death_reason: str | None = None

    # Lightweight counters for flavor/stats, not simulation-critical.
    feed_count: int = 0
    play_count: int = 0
    clean_count: int = 0
    games_won: int = 0
    games_played: int = 0

    # ---- time handling -------------------------------------------------

    def tick(self, now: float | None = None) -> None:
        """Advance the creature's state to `now` (defaults to wall clock).

        Safe to call with any elapsed gap - a creature checked once a
        week decays exactly as if it had been checked every second.
        """
        if not self.alive:
            return
        now = time.time() if now is None else now
        elapsed_hours = max(0.0, (now - self.last_updated) / 3600.0)
        if elapsed_hours == 0.0:
            return

        self.hunger = _clamp(self.hunger - HUNGER_DECAY_PER_HOUR * elapsed_hours)
        self.energy = _clamp(self.energy - ENERGY_DECAY_PER_HOUR * elapsed_hours)
        self.fun = _clamp(self.fun - FUN_DECAY_PER_HOUR * elapsed_hours)
        self.hygiene = _clamp(self.hygiene - HYGIENE_DECAY_PER_HOUR * elapsed_hours)

        if self.hunger <= CRITICAL_THRESHOLD:
            self.health = _clamp(
                self.health - STARVATION_HEALTH_DRAIN_PER_HOUR * elapsed_hours
            )

        # Being clean and rested slowly heals minor health loss.
        if self.hunger > 50 and self.hygiene > 50 and self.energy > 50:
            self.health = _clamp(self.health + 1.0 * elapsed_hours)

        self.last_updated = now

        if self.health <= STAT_MIN:
            self.alive = False
            self.death_reason = self._determine_death_reason()

    def _determine_death_reason(self) -> str:
        if self.hunger <= CRITICAL_THRESHOLD:
            return "starvation"
        if self.hygiene <= CRITICAL_THRESHOLD:
            return "neglect"
        return "old age"

    # ---- age / life stage -----------------------------------------------

    def age_hours(self, now: float | None = None) -> float:
        now = time.time() if now is None else now
        return max(0.0, (now - self.born_at) / 3600.0)

    def life_stage(self, now: float | None = None) -> str:
        hours = self.age_hours(now)
        stage = "egg"
        for name, threshold in STAGE_HOURS.items():
            if hours >= threshold:
                stage = name
        return stage

    # ---- mood -------------------------------------------------------------

    def mood(self) -> Mood:
        if not self.alive:
            return Mood.DEAD
        if self.health <= CRITICAL_THRESHOLD:
            return Mood.CRITICAL
        if self.health <= 40:
            return Mood.SICK
        if self.hunger <= CRITICAL_THRESHOLD:
            return Mood.HUNGRY
        if self.energy <= CRITICAL_THRESHOLD:
            return Mood.TIRED
        if self.fun <= CRITICAL_THRESHOLD:
            return Mood.BORED
        average = (self.hunger + self.energy + self.fun + self.hygiene) / 4.0
        if average >= 75:
            return Mood.THRIVING
        return Mood.CONTENT

    # ---- actions ------------------------------------------------------

    def feed(self, amount: float = 30.0) -> str:
        if not self.alive:
            return f"{self.name} cannot be fed. It is gone."
        self.tick()
        if self.hunger >= 95:
            return f"{self.name} is completely full and refuses more food."
        self.hunger = _clamp(self.hunger + amount)
        self.feed_count += 1
        return f"{self.name} eats. Hunger restored."

    def play(self, amount: float = 25.0) -> str:
        if not self.alive:
            return f"{self.name} cannot play. It is gone."
        self.tick()
        if self.energy <= 10:
            return f"{self.name} is too exhausted to play."
        self.fun = _clamp(self.fun + amount)
        self.energy = _clamp(self.energy - 8.0)
        self.play_count += 1
        return f"{self.name} plays. Fun increased, a little tired now."

    def clean(self, amount: float = 40.0) -> str:
        if not self.alive:
            return f"{self.name} cannot be cleaned. It is gone."
        self.tick()
        self.hygiene = _clamp(self.hygiene + amount)
        self.clean_count += 1
        return f"{self.name} is cleaned up."

    def rest(self, amount: float = 35.0) -> str:
        if not self.alive:
            return f"{self.name} cannot rest. It is gone."
        self.tick()
        self.energy = _clamp(self.energy + amount)
        self.fun = _clamp(self.fun - 3.0)
        return f"{self.name} rests. Energy restored."

    def record_game_result(self, won: bool) -> None:
        self.games_played += 1
        if won:
            self.games_won += 1
            self.fun = _clamp(self.fun + 15.0)
        else:
            self.fun = _clamp(self.fun + 5.0)

    # ---- serialization --------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "born_at": self.born_at,
            "last_updated": self.last_updated,
            "hunger": self.hunger,
            "energy": self.energy,
            "fun": self.fun,
            "hygiene": self.hygiene,
            "health": self.health,
            "alive": self.alive,
            "death_reason": self.death_reason,
            "feed_count": self.feed_count,
            "play_count": self.play_count,
            "clean_count": self.clean_count,
            "games_won": self.games_won,
            "games_played": self.games_played,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Creature":
        return cls(
            name=data["name"],
            born_at=data["born_at"],
            last_updated=data["last_updated"],
            hunger=data["hunger"],
            energy=data["energy"],
            fun=data["fun"],
            hygiene=data["hygiene"],
            health=data["health"],
            alive=data.get("alive", True),
            death_reason=data.get("death_reason"),
            feed_count=data.get("feed_count", 0),
            play_count=data.get("play_count", 0),
            clean_count=data.get("clean_count", 0),
            games_won=data.get("games_won", 0),
            games_played=data.get("games_played", 0),
        )
