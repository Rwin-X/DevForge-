"""Headless tests for termpal.core.storage - real filesystem, temp dirs only."""

from pathlib import Path

from termpal.core.creature import Creature
from termpal.core.storage import delete_save, load_creature, save_creature


def test_save_and_load_round_trip(tmp_path: Path):
    save_path = tmp_path / "creature.json"
    c = Creature(name="Persisted", hunger=55, feed_count=2)

    save_creature(c, path=save_path)
    assert save_path.exists()

    loaded = load_creature(path=save_path)
    assert loaded is not None
    assert loaded.name == "Persisted"
    assert loaded.hunger == 55
    assert loaded.feed_count == 2


def test_load_returns_none_when_no_save_exists(tmp_path: Path):
    save_path = tmp_path / "does-not-exist.json"
    assert load_creature(path=save_path) is None


def test_delete_save_removes_file(tmp_path: Path):
    save_path = tmp_path / "creature.json"
    save_creature(Creature(name="Temp"), path=save_path)
    assert save_path.exists()

    deleted = delete_save(path=save_path)
    assert deleted
    assert not save_path.exists()

    assert delete_save(path=save_path) is False


def test_save_creates_parent_directories(tmp_path: Path):
    nested_path = tmp_path / "nested" / "dir" / "creature.json"
    save_creature(Creature(name="Nested"), path=nested_path)
    assert nested_path.exists()
