import json
import os

import pytest

from passvault.crypto import make_fernet, generate_salt, WrongPasswordError
from passvault.models import new_entry
from passvault import storage
from passvault.storage import VaultPaths


@pytest.fixture
def tmp_paths(tmp_path):
    return VaultPaths(str(tmp_path))


@pytest.fixture
def sample_entries():
    return [
        new_entry(name="GitHub", username="rwin", password="Sup3rSecret!", url="github.com", category="Work"),
        new_entry(name="Bank", username="rwin2", password="AnotherOne$1", url="bank.com", category="Banking"),
    ]


def test_load_vault_returns_empty_list_when_no_file(tmp_paths):
    fernet = make_fernet("pw", generate_salt())
    assert storage.load_vault(fernet, tmp_paths) == []


def test_save_and_load_round_trip(tmp_paths, sample_entries):
    salt = generate_salt()
    fernet = make_fernet("masterpw", salt)
    storage.save_vault(fernet, tmp_paths, sample_entries)

    loaded = storage.load_vault(fernet, tmp_paths)
    assert len(loaded) == 2
    assert loaded[0]["name"] == "GitHub"
    assert loaded[1]["password"] == "AnotherOne$1"


def test_load_vault_wrong_password_raises(tmp_paths, sample_entries):
    salt = generate_salt()
    fernet_right = make_fernet("rightpw", salt)
    storage.save_vault(fernet_right, tmp_paths, sample_entries)

    fernet_wrong = make_fernet("wrongpw", salt)
    with pytest.raises(WrongPasswordError):
        storage.load_vault(fernet_wrong, tmp_paths)


def test_vault_file_is_encrypted_on_disk(tmp_paths, sample_entries):
    fernet = make_fernet("masterpw", generate_salt())
    storage.save_vault(fernet, tmp_paths, sample_entries)

    with open(tmp_paths.vault_file, "rb") as f:
        raw = f.read()
    assert b"Sup3rSecret!" not in raw
    assert b"GitHub" not in raw


def test_encrypted_export_import_round_trip(tmp_path, sample_entries):
    out_path = os.path.join(str(tmp_path), "backup.pvexport")
    storage.export_encrypted(sample_entries, "export-password", out_path)

    imported = storage.import_encrypted("export-password", out_path)
    assert len(imported) == 2
    names = {e["name"] for e in imported}
    assert names == {"GitHub", "Bank"}


def test_encrypted_export_wrong_password_fails(tmp_path, sample_entries):
    out_path = os.path.join(str(tmp_path), "backup.pvexport")
    storage.export_encrypted(sample_entries, "export-password", out_path)

    with pytest.raises(WrongPasswordError):
        storage.import_encrypted("wrong-password", out_path)


def test_plaintext_json_export_import_round_trip(tmp_path, sample_entries):
    out_path = os.path.join(str(tmp_path), "backup.json")
    storage.export_plaintext_json(sample_entries, out_path)

    with open(out_path) as f:
        data = json.load(f)
    assert data[0]["name"] == "GitHub"

    imported = storage.import_plaintext_json(out_path)
    assert len(imported) == 2
    assert imported[0]["password"] == "Sup3rSecret!"


def test_plaintext_csv_export_import_round_trip(tmp_path, sample_entries):
    sample_entries[0]["tags"] = ["dev", "important"]
    out_path = os.path.join(str(tmp_path), "backup.csv")
    storage.export_plaintext_csv(sample_entries, out_path)

    imported = storage.import_plaintext_csv(out_path)
    assert len(imported) == 2
    assert set(imported[0]["tags"]) == {"dev", "important"}


def test_atomic_save_does_not_corrupt_on_repeated_writes(tmp_paths, sample_entries):
    fernet = make_fernet("masterpw", generate_salt())
    for _ in range(5):
        storage.save_vault(fernet, tmp_paths, sample_entries)
    loaded = storage.load_vault(fernet, tmp_paths)
    assert len(loaded) == 2
    # no leftover .tmp file
    assert not os.path.exists(tmp_paths.vault_file + ".tmp")
