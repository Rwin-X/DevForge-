import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import Direction
from core.vault import make_entry


def test_make_entry_truncates_long_previews():
    entry = make_entry(
        algorithm_id="caesar", algorithm_name="Caesar", direction=Direction.ENCRYPT,
        input_text="x" * 200, output_text="y" * 200, key1="3", preview_len=50,
    )
    assert len(entry.input_preview) == 53  # 50 chars + "..."
    assert entry.input_preview.endswith("...")


def test_make_entry_omits_keys_for_asymmetric():
    entry = make_entry(
        algorithm_id="rsa", algorithm_name="RSA", direction=Direction.ENCRYPT,
        input_text="secret", output_text="cipher", key1="public-pem-data",
        key2="private-pem-data", is_asymmetric=True,
    )
    assert entry.key1 == ""
    assert entry.key2 == ""


def test_entry_round_trips_through_dict():
    entry = make_entry(
        algorithm_id="vigenere", algorithm_name="Vigenère", direction=Direction.DECRYPT,
        input_text="ciphertext", output_text="plaintext", key1="KEYWORD",
    )
    from core.models import VaultEntry
    restored = VaultEntry.from_dict(entry.to_dict())
    assert restored.uid == entry.uid
    assert restored.algorithm_id == entry.algorithm_id
    assert restored.direction == entry.direction
