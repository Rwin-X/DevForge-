"""Headless tests for termpal.core.creature.

No curses, no display, no I/O beyond what dataclasses need. Run with:
    python3 -m pytest tests/
"""

import time

from termpal.core.creature import Creature, Mood, STAT_MAX


def test_new_creature_starts_alive_and_content():
    c = Creature(name="Test")
    assert c.alive
    assert c.mood() in (Mood.CONTENT, Mood.THRIVING)


def test_tick_decays_stats_over_time():
    c = Creature(name="Test", hunger=80, energy=80, fun=80, hygiene=80)
    now = c.last_updated
    c.tick(now=now + 3600)  # one hour later
    assert c.hunger < 80
    assert c.energy < 80
    assert c.fun < 80
    assert c.hygiene < 80


def test_tick_is_idempotent_at_same_timestamp():
    c = Creature(name="Test")
    now = time.time()
    c.tick(now=now)
    hunger_after_first = c.hunger
    c.tick(now=now)
    assert c.hunger == hunger_after_first


def test_feed_increases_hunger_and_is_clamped():
    c = Creature(name="Test", hunger=90)
    c.feed(amount=30)
    assert c.hunger == STAT_MAX


def test_feed_refuses_when_already_full():
    c = Creature(name="Test", hunger=98)
    msg = c.feed()
    assert "refuses" in msg
    assert c.feed_count == 0


def test_play_increases_fun_but_costs_energy():
    c = Creature(name="Test", fun=50, energy=80)
    c.play()
    assert c.fun > 50
    assert c.energy < 80


def test_play_refuses_when_exhausted():
    c = Creature(name="Test", energy=5)
    msg = c.play()
    assert "too exhausted" in msg
    assert c.play_count == 0


def test_starvation_drains_health_over_time():
    c = Creature(name="Test", hunger=5, health=100)
    now = c.last_updated
    c.tick(now=now + 3600 * 5)  # 5 hours of starvation
    assert c.health < 100


def test_creature_dies_when_health_hits_zero():
    c = Creature(name="Test", hunger=0, health=1)
    now = c.last_updated
    c.tick(now=now + 3600)
    assert not c.alive
    assert c.death_reason is not None


def test_dead_creature_ignores_further_ticks_and_actions():
    c = Creature(name="Test", hunger=0, health=0.5)
    now = c.last_updated
    c.tick(now=now + 3600)
    assert not c.alive

    health_after_death = c.health
    c.tick(now=now + 7200)
    assert c.health == health_after_death

    msg = c.feed()
    assert "cannot be fed" in msg


def test_mood_reflects_critical_hunger():
    c = Creature(name="Test", hunger=5, energy=80, fun=80, hygiene=80, health=80)
    assert c.mood() == Mood.HUNGRY


def test_mood_thriving_when_all_stats_high():
    c = Creature(name="Test", hunger=95, energy=95, fun=95, hygiene=95, health=100)
    assert c.mood() == Mood.THRIVING


def test_life_stage_progression_by_age():
    now = time.time()
    c = Creature(name="Test", born_at=now)
    assert c.life_stage(now=now) == "egg"
    assert c.life_stage(now=now + 3600 * 1) == "hatchling"
    assert c.life_stage(now=now + 3600 * 30) == "juvenile"
    assert c.life_stage(now=now + 3600 * 24 * 6) == "adult"
    assert c.life_stage(now=now + 3600 * 24 * 25) == "elder"


def test_serialization_round_trip():
    c = Creature(name="Roundtrip", hunger=42, feed_count=3)
    data = c.to_dict()
    restored = Creature.from_dict(data)
    assert restored.name == c.name
    assert restored.hunger == c.hunger
    assert restored.feed_count == c.feed_count
    assert restored.alive == c.alive


def test_record_game_result_updates_counters():
    c = Creature(name="Test", fun=50)
    c.record_game_result(won=True)
    assert c.games_played == 1
    assert c.games_won == 1
    assert c.fun > 50

    c.record_game_result(won=False)
    assert c.games_played == 2
    assert c.games_won == 1
