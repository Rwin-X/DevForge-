#!/usr/bin/env python3
"""
secNT - A minimal encrypted notepad.

Everything you type is auto-encrypted (AES-256-GCM) and written to
notes.txt as an encrypted blob. On launch, secNT decrypts that file
using its saved key and shows your plain text again -- live, as you
type, with no manual save step.

Files created next to this script:
  secNT.key   -> your AES-256 key (base64), generated once on first run
  notes.txt   -> your notes, always stored encrypted, never in plaintext

Run:
  pip install PyQt6 cryptography
  python secNT.py
"""

import sys
import os
import base64
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QMessageBox, QStatusBar
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QAction, QGuiApplication

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


APP_DIR = Path(__file__).resolve().parent
KEY_FILE = APP_DIR / "secNT.key"
NOTES_FILE = APP_DIR / "notes.txt"

AUTOSAVE_DELAY_MS = 500  # debounce: save this long after the last keystroke


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------

def generate_key() -> bytes:
    """Generate a new random AES-256 key."""
    return AESGCM.generate_key(bit_length=256)


def load_or_create_key() -> tuple[bytes, bool]:
    """
    Load the key from KEY_FILE, or generate and save a new one if it
    doesn't exist yet. Returns (key_bytes, was_newly_created).
    """
    if KEY_FILE.exists():
        encoded = KEY_FILE.read_text(encoding="utf-8").strip()
        return base64.b64decode(encoded), False

    key = generate_key()
    KEY_FILE.write_text(base64.b64encode(key).decode("utf-8"), encoding="utf-8")
    return key, True


def encrypt_text(plaintext: str, key: bytes) -> str:
    """Encrypt plaintext with AES-256-GCM, return base64 (safe for a .txt file)."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_text(encoded: str, key: bytes) -> str:
    """Reverse of encrypt_text. Raises if the key is wrong or data is corrupted."""
    raw = base64.b64decode(encoded)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class SecNT(QMainWindow):
    def __init__(self):
        super().__init__()
        self.key, is_new_key = load_or_create_key()

        self.setWindowTitle("secNT")
        self.resize(760, 520)
        self.setStyleSheet("QMainWindow { background-color: #FFFFFF; }")

        self.editor = QTextEdit()
        font = QFont()
        font.setFamilies(["Consolas", "Courier New", "monospace"])
        font.setPointSize(11)
        self.editor.setFont(font)
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #1A1A1A;
                border: none;
                padding: 10px;
                selection-background-color: #CCE4FF;
            }
        """)
        self.setCentralWidget(self.editor)

        self.status = QStatusBar()
        self.status.setStyleSheet("color: #888888; background-color: #F3F3F3;")
        self.setStatusBar(self.status)

        self._build_menu()

        # Debounced autosave: every keystroke restarts the timer, so we
        # only actually write to disk once typing pauses.
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_now)
        self.editor.textChanged.connect(self._on_text_changed)

        self._load_notes()

        if is_new_key:
            self._show_key_dialog(first_time=True)

    # -- Menu ----------------------------------------------------------

    def _build_menu(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet(
            "QMenuBar { background-color: #F3F3F3; color: #1A1A1A; }"
            "QMenu { background-color: #FFFFFF; color: #1A1A1A; }"
        )
        file_menu = menu_bar.addMenu("File")

        show_key_action = QAction("Show Encryption Key", self)
        show_key_action.triggered.connect(lambda: self._show_key_dialog(first_time=False))
        file_menu.addAction(show_key_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # -- Load / autosave -------------------------------------------------

    def _load_notes(self):
        if not NOTES_FILE.exists():
            return
        encoded = NOTES_FILE.read_text(encoding="utf-8").strip()
        if not encoded:
            return
        try:
            plaintext = decrypt_text(encoded, self.key)
        except Exception:
            QMessageBox.warning(
                self,
                "secNT",
                "notes.txt could not be decrypted with the current key.\n"
                "It may be corrupted, or secNT.key was replaced.",
            )
            return
        self.editor.blockSignals(True)
        self.editor.setPlainText(plaintext)
        self.editor.blockSignals(False)
        self.status.showMessage("Loaded", 2000)

    def _on_text_changed(self):
        self.status.showMessage("Editing...")
        self.save_timer.start(AUTOSAVE_DELAY_MS)

    def _save_now(self):
        plaintext = self.editor.toPlainText()
        encoded = encrypt_text(plaintext, self.key)
        NOTES_FILE.write_text(encoded, encoding="utf-8")
        self.status.showMessage("Saved (encrypted)", 1500)

    def closeEvent(self, event):
        # Flush any change still waiting on the debounce timer.
        if self.save_timer.isActive():
            self.save_timer.stop()
        self._save_now()
        event.accept()

    # -- Key dialog --------------------------------------------------------

    def _show_key_dialog(self, first_time: bool):
        encoded_key = base64.b64encode(self.key).decode("utf-8")

        box = QMessageBox(self)
        box.setWindowTitle("secNT - Encryption Key")
        box.setIcon(QMessageBox.Icon.Information)

        intro = "A new encryption key was generated for you:" if first_time \
            else "Your current encryption key:"
        box.setText(
            f"{intro}\n\n{encoded_key}\n\n"
            "Keep this safe. Without it, notes.txt can never be decrypted again."
        )

        copy_button = box.addButton("Copy Key", QMessageBox.ButtonRole.ActionRole)
        box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        box.exec()

        if box.clickedButton() == copy_button:
            QGuiApplication.clipboard().setText(encoded_key)


def main():
    app = QApplication(sys.argv)
    window = SecNT()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
