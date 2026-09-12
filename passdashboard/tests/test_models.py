from passvault.models import new_entry, update_entry, normalize_entry, all_categories, all_tags


def test_new_entry_has_required_fields():
    e = new_entry(name="Test", password="abc123")
    assert e["name"] == "Test"
    assert e["password"] == "abc123"
    assert e["category"] == "General"
    assert e["tags"] == []
    assert e["history"] == []
    assert "id" in e and len(e["id"]) > 0


def test_new_entry_ids_are_unique():
    e1 = new_entry(name="A")
    e2 = new_entry(name="B")
    assert e1["id"] != e2["id"]


def test_update_entry_pushes_old_password_to_history():
    e = new_entry(name="Test", password="old_password")
    updated = update_entry(e, password="new_password")

    assert updated["password"] == "new_password"
    assert len(updated["history"]) == 1
    assert updated["history"][0]["password"] == "old_password"


def test_update_entry_no_history_entry_if_password_unchanged():
    e = new_entry(name="Test", password="same")
    updated = update_entry(e, name="Renamed")

    assert updated["name"] == "Renamed"
    assert updated["password"] == "same"
    assert len(updated["history"]) == 0


def test_normalize_entry_backfills_missing_fields():
    old_style_entry = {"id": "abc123", "name": "Legacy", "password": "x"}
    normalized = normalize_entry(old_style_entry)

    assert normalized["category"] == "General"
    assert normalized["tags"] == []
    assert normalized["history"] == []
    assert normalized["username"] == ""


def test_all_categories_includes_defaults_and_custom():
    entries = [
        new_entry(name="A", category="Custom Category"),
        new_entry(name="B", category="Work"),
    ]
    cats = all_categories(entries)
    assert "Custom Category" in cats
    assert "Work" in cats
    assert "General" in cats  # default, even if unused


def test_all_tags_collects_unique_tags():
    entries = [
        new_entry(name="A", tags=["dev", "important"]),
        new_entry(name="B", tags=["important", "personal"]),
    ]
    tags = all_tags(entries)
    assert tags == ["dev", "important", "personal"]
