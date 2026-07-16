"""
main.py - entry point for Local AI Notes.

Offline personal knowledge base. On first run, asks where to keep your
notes (a plain folder of .md files) and remembers that folder in a
tiny local config file next to this script -- nothing is sent
anywhere, there are no accounts, and no data leaves this machine.
"""

from __future__ import annotations

import json
import os
import sys

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from main_window import MainWindow

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".local_ai_notes_config.json")


def load_last_folder() -> str | None:
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            folder = data.get("vault_folder")
            if folder and os.path.isdir(folder):
                return folder
        except (OSError, json.JSONDecodeError):
            pass
    return None


def save_last_folder(folder: str) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"vault_folder": folder}, f)
    except OSError:
        pass  # non-fatal -- app still works, it'll just ask again next time


def choose_vault_folder(app: QApplication) -> str | None:
    default_dir = os.path.join(os.path.expanduser("~"), "LocalAINotes")

    QMessageBox.information(
        None,
        "Local AI Notes",
        "Choose (or create) a folder where your notes will be stored as "
        "plain .md files.\n\nEverything stays on this computer.",
    )
    folder = QFileDialog.getExistingDirectory(
        None, "Choose or create your notes folder", os.path.expanduser("~")
    )
    if not folder:
        return None
    os.makedirs(folder, exist_ok=True)
    return folder


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Local AI Notes")

    folder = load_last_folder()
    if folder is None:
        folder = choose_vault_folder(app)
        if folder is None:
            sys.exit(0)
        save_last_folder(folder)

    window = MainWindow(folder)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
