"""Headless tests for termpal.core.sprites - pure lookup logic."""

from termpal.core.creature import Mood
from termpal.core.sprites import EGG, TOMBSTONE, get_sprite


def test_egg_stage_ignores_mood():
    assert get_sprite("egg", Mood.THRIVING) == EGG
    assert get_sprite("egg", Mood.CRITICAL) == EGG


def test_dead_mood_always_returns_tombstone():
    for stage in ("egg", "hatchling", "juvenile", "adult", "elder"):
        assert get_sprite(stage, Mood.DEAD) == TOMBSTONE


def test_every_stage_has_art_for_every_live_mood():
    live_moods = [m for m in Mood if m != Mood.DEAD]
    for stage in ("hatchling", "juvenile", "adult", "elder"):
        for mood in live_moods:
            sprite = get_sprite(stage, mood)
            assert isinstance(sprite, list)
            assert len(sprite) > 0
            assert all(isinstance(line, str) for line in sprite)


def test_unknown_stage_falls_back_to_juvenile_table():
    from termpal.core.sprites import JUVENILE
    sprite = get_sprite("nonsense-stage", Mood.CONTENT)
    assert sprite == JUVENILE[Mood.CONTENT]
