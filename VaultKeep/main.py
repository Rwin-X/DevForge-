"""
VaultKeep - a minimal, secure local password manager.

Security summary:
    - Master password -> Argon2id -> 256-bit key (never stored, never leaves memory)
    - Every field of every entry -> AES-256-GCM (authenticated encryption)
    - SQLite file on disk contains only ciphertext + nonces
    - Auto-lock after inactivity; clipboard auto-clears after a delay
    - Encrypted export/import for backups

Run:
    pip install PyQt6 argon2-cffi cryptography
    python main.py
"""

from __future__ import annotations

import sys
import os
import csv
import json
import time
import secrets as pysecrets

from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QIcon, QFont, QAction, QGuiApplication, QColor, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QListWidget, QListWidgetItem,
    QStackedWidget, QMessageBox, QFileDialog, QCheckBox, QSlider, QComboBox,
    QTextEdit, QDialog, QFormLayout, QProgressBar, QSizePolicy, QMenu,
    QToolButton, QStatusBar, QSpacerItem, QScrollArea
)

import crypto_core as cc
import pwgen
from vault_db import VaultDB, Entry
import theme

APP_NAME = "VaultKeep"
DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".vaultkeep", "vault.db")
AUTO_LOCK_SECONDS_DEFAULT = 300  # 5 minutes
CLIPBOARD_CLEAR_SECONDS = 20


# ============================================================================
# Small reusable widgets
# ============================================================================

class IconLabel(QLabel):
    """A simple text-based glyph label used instead of external icon assets,
    so the app has zero binary/image dependencies."""
    def __init__(self, glyph: str, size: int = 16, color: str = theme.TEXT_SECONDARY):
        super().__init__(glyph)
        self.setStyleSheet(f"color: {color}; font-size: {size}px; background: transparent;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class PasswordField(QLineEdit):
    """A QLineEdit for secrets with a built-in show/hide toggle."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self._visible = False

    def toggle_visibility(self):
        self._visible = not self._visible
        self.setEchoMode(
            QLineEdit.EchoMode.Normal if self._visible else QLineEdit.EchoMode.Password
        )


class StrengthMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        row = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        row.addWidget(self.bar)
        layout.addLayout(row)

        self.label = QLabel("")
        self.label.setProperty("role", "muted")
        layout.addWidget(self.label)

    def update_for(self, password: str):
        label, score, color = pwgen.strength_label(password)
        self.bar.setValue(int(score))
        self.bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
        bits = pwgen.estimate_entropy_bits(password)
        if password:
            self.label.setText(f"{label} · ~{bits:.0f} bits of entropy")
        else:
            self.label.setText("")


def make_button(text, object_name=None, icon_glyph=None):
    btn = QPushButton(text)
    if object_name:
        btn.setObjectName(object_name)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def copy_to_clipboard_with_autoclear(text: str, status_callback=None):
    clipboard = QGuiApplication.clipboard()
    clipboard.setText(text)
    if status_callback:
        status_callback(f"Copied to clipboard - clearing in {CLIPBOARD_CLEAR_SECONDS}s")

    def clear_if_unchanged():
        if clipboard.text() == text:
            clipboard.setText("")
            if status_callback:
                status_callback("Clipboard cleared")

    QTimer.singleShot(CLIPBOARD_CLEAR_SECONDS * 1000, clear_if_unchanged)


# ============================================================================
# Setup screen (first run - create master password)
# ============================================================================

class SetupScreen(QWidget):
    finished = pyqtSignal(str)  # emits master password on success

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("panel")
        card.setFixedWidth(420)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(36, 36, 36, 36)
        cl.setSpacing(14)

        brand = QLabel("VAULTKEEP")
        brand.setProperty("role", "brand")
        brand.setStyleSheet(brand.styleSheet() + f"color: {theme.BLUE};")
        cl.addWidget(brand)

        sub = QLabel("Create your master password. This is the only key\nto every secret you store here - choose carefully.")
        sub.setProperty("role", "secondary")
        cl.addWidget(sub)
        cl.addSpacing(8)

        self.pw1 = PasswordField()
        self.pw1.setPlaceholderText("Master password")
        self.pw1.textChanged.connect(self._update_strength)
        cl.addWidget(self.pw1)

        self.meter = StrengthMeter()
        cl.addWidget(self.meter)

        self.pw2 = PasswordField()
        self.pw2.setPlaceholderText("Confirm master password")
        cl.addWidget(self.pw2)

        self.hint_label = QLabel(
            "No one, including the developer, can recover this password.\n"
            "If it's lost, your vault cannot be decrypted."
        )
        self.hint_label.setProperty("role", "muted")
        self.hint_label.setWordWrap(True)
        cl.addWidget(self.hint_label)

        self.show_chk = QCheckBox("Show password")
        self.show_chk.toggled.connect(self._toggle_show)
        cl.addWidget(self.show_chk)

        cl.addSpacing(8)
        create_btn = make_button("Create Vault", "primary")
        create_btn.clicked.connect(self._on_create)
        cl.addWidget(create_btn)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {theme.DANGER}; font-size: 12px;")
        self.error_label.setWordWrap(True)
        cl.addWidget(self.error_label)

        outer.addWidget(card)

    def _toggle_show(self, checked):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.pw1.setEchoMode(mode)
        self.pw2.setEchoMode(mode)

    def _update_strength(self, text):
        self.meter.update_for(text)

    def _on_create(self):
        p1, p2 = self.pw1.text(), self.pw2.text()
        if len(p1) < 8:
            self.error_label.setText("Master password must be at least 8 characters.")
            return
        if p1 != p2:
            self.error_label.setText("Passwords do not match.")
            return
        self.error_label.setText("")
        self.finished.emit(p1)


# ============================================================================
# Unlock screen (returning user)
# ============================================================================

class UnlockScreen(QWidget):
    unlocked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("panel")
        card.setFixedWidth(380)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(36, 36, 36, 36)
        cl.setSpacing(14)

        brand = QLabel("VAULTKEEP")
        brand.setProperty("role", "brand")
        brand.setStyleSheet(brand.styleSheet() + f"color: {theme.BLUE};")
        cl.addWidget(brand)

        sub = QLabel("Enter your master password to unlock the vault.")
        sub.setProperty("role", "secondary")
        sub.setWordWrap(True)
        cl.addWidget(sub)
        cl.addSpacing(8)

        self.pw = PasswordField()
        self.pw.setPlaceholderText("Master password")
        self.pw.returnPressed.connect(self._on_unlock)
        cl.addWidget(self.pw)

        show_chk = QCheckBox("Show password")
        show_chk.toggled.connect(
            lambda c: self.pw.setEchoMode(
                QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password
            )
        )
        cl.addWidget(show_chk)

        cl.addSpacing(8)
        unlock_btn = make_button("Unlock", "primary")
        unlock_btn.clicked.connect(self._on_unlock)
        cl.addWidget(unlock_btn)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {theme.DANGER}; font-size: 12px;")
        self.error_label.setWordWrap(True)
        cl.addWidget(self.error_label)

        outer.addWidget(card)
        self._attempts = 0

    def reset(self):
        self.pw.clear()
        self.error_label.setText("")
        self.pw.setFocus()

    def _on_unlock(self):
        pw = self.pw.text()
        if not pw:
            return
        self.unlocked.emit(pw)

    def show_error(self, msg: str):
        self._attempts += 1
        self.error_label.setText(msg)
        self.pw.clear()
        self.pw.setFocus()


# ============================================================================
# Entry editor dialog
# ============================================================================

class EntryDialog(QDialog):
    def __init__(self, parent=None, entry: Entry | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Entry" if entry else "New Entry")
        self.setMinimumWidth(460)
        self.entry = entry

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_lbl = QLabel("Edit Entry" if entry else "New Entry")
        title_lbl.setProperty("role", "heading")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.title_edit = QLineEdit(entry.title if entry else "")
        self.title_edit.setPlaceholderText("e.g. GitHub, Gmail, Bank of America")
        form.addRow("Title", self.title_edit)

        self.username_edit = QLineEdit(entry.username if entry else "")
        self.username_edit.setPlaceholderText("username or email")
        form.addRow("Username", self.username_edit)

        pw_row = QHBoxLayout()
        self.password_edit = PasswordField()
        self.password_edit.setText(entry.password if entry else "")
        pw_row.addWidget(self.password_edit)

        toggle_btn = make_button("Show", "ghost")
        toggle_btn.setFixedWidth(56)
        toggle_btn.clicked.connect(self._toggle_pw)
        pw_row.addWidget(toggle_btn)

        gen_btn = make_button("Gen", "ghost")
        gen_btn.setFixedWidth(48)
        gen_btn.clicked.connect(self._quick_generate)
        pw_row.addWidget(gen_btn)

        form.addRow("Password", pw_row)

        self.meter = StrengthMeter()
        form.addRow("", self.meter)
        self.password_edit.textChanged.connect(self.meter.update_for)
        self.meter.update_for(self.password_edit.text())

        self.url_edit = QLineEdit(entry.url if entry else "")
        self.url_edit.setPlaceholderText("https://example.com")
        form.addRow("URL", self.url_edit)

        self.tags_edit = QLineEdit(entry.tags if entry else "")
        self.tags_edit.setPlaceholderText("work, email, finance (comma-separated)")
        form.addRow("Tags", self.tags_edit)

        self.notes_edit = QTextEdit(entry.notes if entry else "")
        self.notes_edit.setPlaceholderText("Optional notes (also encrypted)")
        self.notes_edit.setFixedHeight(80)
        form.addRow("Notes", self.notes_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = make_button("Cancel", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("Save", "primary")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _toggle_pw(self):
        self.password_edit.toggle_visibility()

    def _quick_generate(self):
        pw = pwgen.generate_password(length=20)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        self.password_edit._visible = True
        self.password_edit.setText(pw)
        self.meter.update_for(pw)

    def _on_save(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Missing title", "Please enter a title for this entry.")
            return
        self.result_entry = Entry(
            id=self.entry.id if self.entry else None,
            title=self.title_edit.text().strip(),
            username=self.username_edit.text().strip(),
            password=self.password_edit.text(),
            url=self.url_edit.text().strip(),
            notes=self.notes_edit.toPlainText().strip(),
            tags=self.tags_edit.text().strip(),
        )
        self.accept()


# ============================================================================
# Password generator standalone page
# ============================================================================

class GeneratorPage(QWidget):
    def __init__(self, status_callback, parent=None):
        super().__init__(parent)
        self.status_callback = status_callback
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        heading = QLabel("Password Generator")
        heading.setProperty("role", "heading")
        layout.addWidget(heading)

        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(14)

        out_row = QHBoxLayout()
        self.output = QLineEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(f"font-family: {theme.MONO_FAMILY}; font-size: 16px; letter-spacing: 1px;")
        out_row.addWidget(self.output)
        copy_btn = make_button("Copy", "primary")
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(self._copy)
        out_row.addWidget(copy_btn)
        cl.addLayout(out_row)

        self.meter = StrengthMeter()
        cl.addWidget(self.meter)

        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(8)
        self.mode_random = make_button("Random", "primary")
        self.mode_phrase = make_button("Passphrase", "ghost")
        self.mode_random.setCheckable(True)
        self.mode_phrase.setCheckable(True)
        self.mode_random.setChecked(True)
        self.mode_random.setFixedHeight(36)
        self.mode_phrase.setFixedHeight(36)
        self.mode_random.clicked.connect(lambda: self._switch_mode("random"))
        self.mode_phrase.clicked.connect(lambda: self._switch_mode("phrase"))
        tabs_row.addWidget(self.mode_random)
        tabs_row.addWidget(self.mode_phrase)
        tabs_row.addStretch()
        cl.addLayout(tabs_row)
        self._mode = "random"

        # --- random options ---
        self.random_box = QWidget()
        rb = QVBoxLayout(self.random_box)
        rb.setContentsMargins(0, 8, 0, 0)
        rb.setSpacing(10)

        len_row = QHBoxLayout()
        len_row.addWidget(QLabel("Length"))
        self.len_slider = QSlider(Qt.Orientation.Horizontal)
        self.len_slider.setRange(8, 64)
        self.len_slider.setValue(20)
        self.len_value_label = QLabel("20")
        self.len_slider.valueChanged.connect(
            lambda v: (self.len_value_label.setText(str(v)), self._generate())
        )
        len_row.addWidget(self.len_slider)
        len_row.addWidget(self.len_value_label)
        rb.addLayout(len_row)

        chk_row = QGridLayout()
        self.chk_lower = QCheckBox("Lowercase (a-z)")
        self.chk_upper = QCheckBox("Uppercase (A-Z)")
        self.chk_digits = QCheckBox("Digits (0-9)")
        self.chk_symbols = QCheckBox("Symbols (!@#$...)")
        self.chk_ambiguous = QCheckBox("Avoid ambiguous characters (Il1O0)")
        for c in (self.chk_lower, self.chk_upper, self.chk_digits, self.chk_symbols):
            c.setChecked(True)
            c.toggled.connect(self._generate)
        self.chk_ambiguous.setChecked(True)
        self.chk_ambiguous.toggled.connect(self._generate)
        chk_row.addWidget(self.chk_lower, 0, 0)
        chk_row.addWidget(self.chk_upper, 0, 1)
        chk_row.addWidget(self.chk_digits, 1, 0)
        chk_row.addWidget(self.chk_symbols, 1, 1)
        rb.addLayout(chk_row)
        rb.addWidget(self.chk_ambiguous)
        cl.addWidget(self.random_box)

        # --- passphrase options ---
        self.phrase_box = QWidget()
        pb = QVBoxLayout(self.phrase_box)
        pb.setContentsMargins(0, 8, 0, 0)
        pb.setSpacing(10)
        words_row = QHBoxLayout()
        words_row.addWidget(QLabel("Number of words"))
        self.words_slider = QSlider(Qt.Orientation.Horizontal)
        self.words_slider.setRange(3, 8)
        self.words_slider.setValue(5)
        self.words_value_label = QLabel("5")
        self.words_slider.valueChanged.connect(
            lambda v: (self.words_value_label.setText(str(v)), self._generate())
        )
        words_row.addWidget(self.words_slider)
        words_row.addWidget(self.words_value_label)
        pb.addLayout(words_row)
        self.phrase_box.setVisible(False)
        cl.addWidget(self.phrase_box)

        regen_btn = make_button("Regenerate", "primary")
        regen_btn.clicked.connect(self._generate)
        cl.addWidget(regen_btn)

        layout.addWidget(card)
        layout.addStretch()

        self._generate()

    def _switch_mode(self, mode):
        self._mode = mode
        self.mode_random.setChecked(mode == "random")
        self.mode_phrase.setChecked(mode == "phrase")
        self.mode_random.setObjectName("primary" if mode == "random" else "ghost")
        self.mode_phrase.setObjectName("primary" if mode == "phrase" else "ghost")
        # force style re-polish so the new objectName's QSS takes effect
        for b in (self.mode_random, self.mode_phrase):
            b.style().unpolish(b)
            b.style().polish(b)
        self.random_box.setVisible(mode == "random")
        self.phrase_box.setVisible(mode == "phrase")
        self._generate()

    def _generate(self):
        if self._mode == "random":
            pw = pwgen.generate_password(
                length=self.len_slider.value(),
                use_lower=self.chk_lower.isChecked(),
                use_upper=self.chk_upper.isChecked(),
                use_digits=self.chk_digits.isChecked(),
                use_symbols=self.chk_symbols.isChecked(),
                avoid_ambiguous=self.chk_ambiguous.isChecked(),
            )
        else:
            pw = pwgen.generate_passphrase(num_words=self.words_slider.value())
        self.output.setText(pw)
        self.meter.update_for(pw)

    def _copy(self):
        copy_to_clipboard_with_autoclear(self.output.text(), self.status_callback)


# ============================================================================
# Settings page
# ============================================================================

class SettingsPage(QWidget):
    change_master_requested = pyqtSignal(str, str)  # old, new
    export_requested = pyqtSignal()
    import_requested = pyqtSignal()
    lock_now_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        heading = QLabel("Settings")
        heading.setProperty("role", "heading")
        layout.addWidget(heading)

        # --- change master password ---
        card1 = QFrame()
        card1.setObjectName("card")
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(24, 24, 24, 24)
        c1.setSpacing(10)
        c1.addWidget(QLabel("Change Master Password"))
        desc = QLabel("Re-encrypts your entire vault under a new key. This may take a moment.")
        desc.setProperty("role", "muted")
        c1.addWidget(desc)

        self.old_pw = PasswordField()
        self.old_pw.setPlaceholderText("Current master password")
        self.new_pw = PasswordField()
        self.new_pw.setPlaceholderText("New master password")
        self.new_pw2 = PasswordField()
        self.new_pw2.setPlaceholderText("Confirm new master password")
        c1.addWidget(self.old_pw)
        c1.addWidget(self.new_pw)
        c1.addWidget(self.new_pw2)

        change_btn = make_button("Update Master Password", "primary")
        change_btn.clicked.connect(self._on_change)
        c1.addWidget(change_btn)
        layout.addWidget(card1)

        # --- auto-lock ---
        card2 = QFrame()
        card2.setObjectName("card")
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(24, 24, 24, 24)
        c2.setSpacing(10)
        c2.addWidget(QLabel("Auto-Lock"))
        desc2 = QLabel("Automatically lock the vault after a period of inactivity.")
        desc2.setProperty("role", "muted")
        c2.addWidget(desc2)
        self.autolock_combo = QComboBox()
        self.autolock_combo.addItems(["1 minute", "5 minutes", "15 minutes", "30 minutes", "Never"])
        self.autolock_combo.setCurrentIndex(1)
        c2.addWidget(self.autolock_combo)
        layout.addWidget(card2)

        # --- backup ---
        card3 = QFrame()
        card3.setObjectName("card")
        c3 = QVBoxLayout(card3)
        c3.setContentsMargins(24, 24, 24, 24)
        c3.setSpacing(10)
        c3.addWidget(QLabel("Backup & Restore"))
        desc3 = QLabel("Export an encrypted backup you can restore later, on this or another device.")
        desc3.setProperty("role", "muted")
        c3.addWidget(desc3)
        row = QHBoxLayout()
        export_btn = make_button("Export Encrypted Backup", "primary")
        export_btn.clicked.connect(self.export_requested.emit)
        import_btn = make_button("Import Backup", "ghost")
        import_btn.clicked.connect(self.import_requested.emit)
        row.addWidget(export_btn)
        row.addWidget(import_btn)
        c3.addLayout(row)
        layout.addWidget(card3)

        # --- lock now ---
        card4 = QFrame()
        card4.setObjectName("card")
        c4 = QVBoxLayout(card4)
        c4.setContentsMargins(24, 24, 24, 24)
        c4.setSpacing(10)
        c4.addWidget(QLabel("Session"))
        lock_btn = make_button("Lock Vault Now", "danger")
        lock_btn.clicked.connect(self.lock_now_requested.emit)
        c4.addWidget(lock_btn)
        layout.addWidget(card4)

        layout.addStretch()

    def _on_change(self):
        old, new1, new2 = self.old_pw.text(), self.new_pw.text(), self.new_pw2.text()
        if not old or not new1:
            QMessageBox.warning(self, "Missing fields", "Please fill in all password fields.")
            return
        if new1 != new2:
            QMessageBox.warning(self, "Mismatch", "New passwords do not match.")
            return
        if len(new1) < 8:
            QMessageBox.warning(self, "Too short", "New master password must be at least 8 characters.")
            return
        self.change_master_requested.emit(old, new1)
        self.old_pw.clear()
        self.new_pw.clear()
        self.new_pw2.clear()

    def get_autolock_seconds(self) -> int | None:
        mapping = {0: 60, 1: 300, 2: 900, 3: 1800, 4: None}
        return mapping[self.autolock_combo.currentIndex()]


# ============================================================================
# Entry list item widget
# ============================================================================

class EntryCard(QWidget):
    def __init__(self, entry: Entry, on_copy_password, on_edit, on_delete, on_copy_username):
        super().__init__()
        self.entry = entry
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        # colored initial avatar
        avatar = QLabel(entry.title[:1].upper() if entry.title else "?")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background-color: {theme.BLUE_SOFT}; color: {theme.BLUE}; "
            f"border-radius: 18px; font-weight: 700; font-size: 14px;"
        )
        layout.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(2)
        title_lbl = QLabel(entry.title)
        title_lbl.setStyleSheet("font-weight: 600; font-size: 14px;")
        sub_text = entry.username if entry.username else (entry.url or "")
        sub_lbl = QLabel(sub_text)
        sub_lbl.setProperty("role", "secondary")
        sub_lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        info.addWidget(title_lbl)
        info.addWidget(sub_lbl)
        layout.addLayout(info, 1)

        if entry.tags:
            tag_lbl = QLabel(entry.tags.split(",")[0].strip())
            tag_lbl.setStyleSheet(
                f"background-color: {theme.BLUE_SOFT}; color: {theme.BLUE}; "
                f"border-radius: 8px; padding: 3px 9px; font-size: 11px;"
            )
            layout.addWidget(tag_lbl)

        layout.addSpacing(4)

        copy_user_btn = QToolButton()
        copy_user_btn.setText("User")
        copy_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_user_btn.setMinimumWidth(52)
        copy_user_btn.setStyleSheet(self._tool_btn_style())
        copy_user_btn.clicked.connect(lambda: on_copy_username(entry))
        layout.addWidget(copy_user_btn)

        copy_btn = QToolButton()
        copy_btn.setText("Copy")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setMinimumWidth(56)
        copy_btn.setStyleSheet(self._tool_btn_style(primary=True))
        copy_btn.clicked.connect(lambda: on_copy_password(entry))
        layout.addWidget(copy_btn)

        edit_btn = QToolButton()
        edit_btn.setText("Edit")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setMinimumWidth(52)
        edit_btn.setStyleSheet(self._tool_btn_style())
        edit_btn.clicked.connect(lambda: on_edit(entry))
        layout.addWidget(edit_btn)

        del_btn = QToolButton()
        del_btn.setText("Delete")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setMinimumWidth(56)
        del_btn.setStyleSheet(self._tool_btn_style(danger=True))
        del_btn.clicked.connect(lambda: on_delete(entry))
        layout.addWidget(del_btn)

    def _tool_btn_style(self, primary=False, danger=False):
        color = theme.TEXT_SECONDARY
        if primary:
            color = theme.BLUE
        if danger:
            color = theme.DANGER
        return (
            f"QToolButton {{ color: {color}; border: 1px solid {theme.BORDER}; "
            f"border-radius: 6px; padding: 5px 10px; "
            f"font-size: 11px; background: {theme.BG_PANEL}; }}"
            f"QToolButton:hover {{ color: {theme.TEXT_PRIMARY}; border: 1px solid {color}; }}"
        )


# ============================================================================
# Vault (dashboard) page
# ============================================================================

class VaultPage(QWidget):
    def __init__(self, db: VaultDB, get_key, status_callback, parent=None):
        super().__init__(parent)
        self.db = db
        self.get_key = get_key
        self.status_callback = status_callback
        self._entries_cache: list[Entry] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        heading = QLabel("My Vault")
        heading.setProperty("role", "heading")
        top_row.addWidget(heading)
        top_row.addStretch()
        add_btn = make_button("+ New Entry", "primary")
        add_btn.clicked.connect(self._on_add)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by title, username, url, or tag...")
        self.search_box.textChanged.connect(self.refresh)
        layout.addWidget(self.search_box)

        self.count_label = QLabel("")
        self.count_label.setProperty("role", "muted")
        layout.addWidget(self.count_label)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(0)
        layout.addWidget(self.list_widget)

        self.empty_label = QLabel("No entries yet. Click \"+ New Entry\" to add your first password.")
        self.empty_label.setProperty("role", "secondary")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def refresh(self):
        key = self.get_key()
        if key is None:
            return
        self._entries_cache = self.db.list_entries(key)
        query = self.search_box.text().strip().lower()
        self.list_widget.clear()

        filtered = self._entries_cache
        if query:
            filtered = [
                e for e in filtered
                if query in e.title.lower()
                or query in e.username.lower()
                or query in e.url.lower()
                or query in e.tags.lower()
            ]

        self.count_label.setText(f"{len(filtered)} of {len(self._entries_cache)} entries")
        self.empty_label.setVisible(len(self._entries_cache) == 0)
        self.list_widget.setVisible(len(self._entries_cache) > 0)

        for entry in filtered:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 56))
            card = EntryCard(
                entry,
                on_copy_password=self._copy_password,
                on_edit=self._on_edit,
                on_delete=self._on_delete,
                on_copy_username=self._copy_username,
            )
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)

    def _copy_password(self, entry: Entry):
        copy_to_clipboard_with_autoclear(entry.password, self.status_callback)

    def _copy_username(self, entry: Entry):
        copy_to_clipboard_with_autoclear(entry.username, self.status_callback)

    def _on_add(self):
        dlg = EntryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            key = self.get_key()
            self.db.add_entry(key, dlg.result_entry)
            self.status_callback("Entry saved")
            self.refresh()

    def _on_edit(self, entry: Entry):
        dlg = EntryDialog(self, entry=entry)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            key = self.get_key()
            self.db.update_entry(key, dlg.result_entry)
            self.status_callback("Entry updated")
            self.refresh()

    def _on_delete(self, entry: Entry):
        reply = QMessageBox.question(
            self, "Delete entry",
            f'Delete "{entry.title}"? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_entry(entry.id)
            self.status_callback("Entry deleted")
            self.refresh()


# ============================================================================
# Main window
# ============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1040, 680)
        self.setMinimumSize(860, 560)

        os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)
        self.db = VaultDB(DEFAULT_DB_PATH)
        self.session_key: bytes | None = None
        self.autolock_seconds = AUTO_LOCK_SECONDS_DEFAULT

        self.root = QWidget()
        self.root.setObjectName("root")
        self.setCentralWidget(self.root)
        root_layout = QVBoxLayout(self.root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._status_msg_permanent = QLabel("")
        self.status.addPermanentWidget(self._status_msg_permanent)

        # --- auth screens ---
        self.setup_screen = SetupScreen()
        self.setup_screen.finished.connect(self._on_vault_created)
        self.unlock_screen = UnlockScreen()
        self.unlock_screen.unlocked.connect(self._on_unlock_attempt)

        self.stack.addWidget(self.setup_screen)
        self.stack.addWidget(self.unlock_screen)

        # --- app shell (built after unlock) ---
        self.app_shell = None

        # --- inactivity timer ---
        self.idle_timer = QTimer(self)
        self.idle_timer.setInterval(1000)
        self.idle_timer.timeout.connect(self._tick_idle)
        self._idle_elapsed = 0
        self.idle_timer.start()

        self.app.installEventFilter(self) if hasattr(self, "app") else None

        if self.db.is_initialized():
            self.stack.setCurrentWidget(self.unlock_screen)
        else:
            self.stack.setCurrentWidget(self.setup_screen)

    def set_status(self, msg: str):
        self._status_msg_permanent.setText(msg)
        QTimer.singleShot(4000, lambda: self._status_msg_permanent.setText(""))

    # ---- lifecycle -----------------------------------------------------

    def _on_vault_created(self, master_password: str):
        key = self.db.init_vault(master_password)
        self.session_key = key
        self._build_app_shell()
        self.set_status("Vault created. Everything you save is encrypted with AES-256-GCM.")

    def _on_unlock_attempt(self, master_password: str):
        key = self.db.unlock(master_password)
        if key is None:
            self.unlock_screen.show_error("Incorrect master password.")
            return
        self.session_key = key
        if self.app_shell is None:
            self._build_app_shell()
        else:
            self.stack.setCurrentWidget(self.app_shell)
            self.vault_page.refresh()
        self._idle_elapsed = 0
        self.set_status("Vault unlocked")

    def _get_key(self):
        return self.session_key

    def _build_app_shell(self):
        self.app_shell = QWidget()
        shell_layout = QHBoxLayout(self.app_shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # --- sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(18, 24, 18, 18)
        sb.setSpacing(6)

        brand = QLabel("VAULTKEEP")
        brand.setProperty("role", "brand")
        brand.setStyleSheet(brand.styleSheet() + f"color: {theme.BLUE}; font-size: 17px;")
        sb.addWidget(brand)
        sb.addSpacing(20)

        self.nav_vault = make_button("🔒   Vault", "navItem")
        self.nav_generator = make_button("⚡   Generator", "navItem")
        self.nav_settings = make_button("⚙   Settings", "navItem")
        for b in (self.nav_vault, self.nav_generator, self.nav_settings):
            b.setCheckable(True)
            b.setFixedHeight(40)
        self.nav_vault.setChecked(True)

        sb.addWidget(self.nav_vault)
        sb.addWidget(self.nav_generator)
        sb.addWidget(self.nav_settings)
        sb.addStretch()

        entry_count_lbl = QLabel()
        entry_count_lbl.setProperty("role", "muted")
        self._sidebar_count_lbl = entry_count_lbl
        sb.addWidget(entry_count_lbl)

        lock_btn = make_button("Lock Vault", "ghost")
        lock_btn.clicked.connect(self._lock_vault)
        sb.addWidget(lock_btn)

        shell_layout.addWidget(sidebar)

        # --- content stack ---
        self.content_stack = QStackedWidget()
        self.vault_page = VaultPage(self.db, self._get_key, self.set_status)
        self.generator_page = GeneratorPage(self.set_status)
        self.settings_page = SettingsPage()
        self.settings_page.change_master_requested.connect(self._on_change_master)
        self.settings_page.export_requested.connect(self._on_export)
        self.settings_page.import_requested.connect(self._on_import)
        self.settings_page.lock_now_requested.connect(self._lock_vault)

        self.content_stack.addWidget(self.vault_page)
        self.content_stack.addWidget(self.generator_page)
        self.content_stack.addWidget(self.settings_page)
        shell_layout.addWidget(self.content_stack, 1)

        self.nav_vault.clicked.connect(lambda: self._switch_page(0, self.nav_vault))
        self.nav_generator.clicked.connect(lambda: self._switch_page(1, self.nav_generator))
        self.nav_settings.clicked.connect(lambda: self._switch_page(2, self.nav_settings))

        self.stack.addWidget(self.app_shell)
        self.stack.setCurrentWidget(self.app_shell)
        self.vault_page.refresh()
        self._update_sidebar_count()

    def _update_sidebar_count(self):
        n = self.db.entry_count()
        self._sidebar_count_lbl.setText(f"{n} saved {'entry' if n == 1 else 'entries'}")

    def _switch_page(self, index, active_btn):
        self.content_stack.setCurrentIndex(index)
        for b in (self.nav_vault, self.nav_generator, self.nav_settings):
            b.setChecked(b is active_btn)
        if index == 0:
            self.vault_page.refresh()
        self._update_sidebar_count()

    def _lock_vault(self):
        self.session_key = None
        self.unlock_screen.reset()
        self.stack.setCurrentWidget(self.unlock_screen)
        self.set_status("Vault locked")

    # ---- inactivity auto-lock -------------------------------------------

    def _tick_idle(self):
        if self.session_key is None:
            return
        if self.autolock_seconds is None:
            return
        self._idle_elapsed += 1
        if self._idle_elapsed >= self.autolock_seconds:
            self._lock_vault()

    def eventFilter(self, obj, event):
        # Any mouse/keyboard activity resets the idle counter.
        if event.type() in (
            event.Type.MouseButtonPress, event.Type.KeyPress, event.Type.MouseMove
        ):
            self._idle_elapsed = 0
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        self._idle_elapsed = 0
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        self._idle_elapsed = 0
        super().keyPressEvent(event)

    # ---- settings actions -------------------------------------------------

    def _on_change_master(self, old_pw: str, new_pw: str):
        key = self.db.unlock(old_pw)
        if key is None:
            QMessageBox.warning(self, "Incorrect password", "Current master password is incorrect.")
            return
        new_key = self.db.change_master_password(key, new_pw)
        self.session_key = new_key
        self.set_status("Master password updated. Vault re-encrypted.")
        QMessageBox.information(self, "Success", "Master password changed successfully.")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Encrypted Backup", "vaultkeep_backup.vkbak", "VaultKeep Backup (*.vkbak)"
        )
        if not path:
            return
        key = self.session_key
        entries = self.db.list_entries(key)
        payload = {
            "app": APP_NAME,
            "version": 1,
            "exported_at": time.time(),
            "entries": [
                {
                    "title": e.title, "username": e.username, "password": e.password,
                    "url": e.url, "notes": e.notes, "tags": e.tags,
                }
                for e in entries
            ],
        }
        raw = json.dumps(payload).encode("utf-8")

        # Encrypt the export under a NEW random key derived from a fresh
        # export password, so the backup file is independently protected
        # even if it ends up somewhere less trusted than the live vault.
        export_pw, ok = self._prompt_export_password()
        if not ok:
            return
        salt = cc.new_salt()
        key2 = cc.derive_key(export_pw, salt)
        nonce, ct = cc.encrypt(key2, raw)

        with open(path, "wb") as f:
            f.write(salt)
            f.write(nonce)
            f.write(ct)

        self.set_status(f"Encrypted backup exported to {path}")
        QMessageBox.information(
            self, "Export complete",
            "Backup exported and encrypted with the password you chose.\n"
            "You will need that password to restore it."
        )

    def _prompt_export_password(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Set Backup Password")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Choose a password to encrypt this backup file:"))
        pw_field = PasswordField()
        layout.addWidget(pw_field)
        btn_row = QHBoxLayout()
        ok_btn = make_button("Continue", "primary")
        cancel_btn = make_button("Cancel", "ghost")
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        result = {"ok": False}

        def accept():
            if len(pw_field.text()) < 6:
                QMessageBox.warning(dlg, "Too short", "Please use at least 6 characters.")
                return
            result["ok"] = True
            dlg.accept()

        ok_btn.clicked.connect(accept)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()
        return pw_field.text(), result["ok"]

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Encrypted Backup", "", "VaultKeep Backup (*.vkbak)"
        )
        if not path:
            return

        pw_field, ok = self._prompt_import_password()
        if not ok:
            return

        try:
            with open(path, "rb") as f:
                data = f.read()
            salt, nonce, ct = data[:16], data[16:28], data[28:]
            key2 = cc.derive_key(pw_field, salt)
            raw = cc.decrypt(key2, nonce, ct)
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            QMessageBox.critical(self, "Import failed", "Could not decrypt this backup. Wrong password or corrupted file.")
            return

        count = 0
        for e in payload.get("entries", []):
            entry = Entry(
                id=None,
                title=e.get("title", ""),
                username=e.get("username", ""),
                password=e.get("password", ""),
                url=e.get("url", ""),
                notes=e.get("notes", ""),
                tags=e.get("tags", ""),
            )
            self.db.add_entry(self.session_key, entry)
            count += 1

        self.vault_page.refresh()
        self._update_sidebar_count()
        self.set_status(f"Imported {count} entries")
        QMessageBox.information(self, "Import complete", f"Imported {count} entries into your vault.")

    def _prompt_import_password(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Backup Password")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Enter the password used to encrypt this backup:"))
        pw_field = PasswordField()
        layout.addWidget(pw_field)
        btn_row = QHBoxLayout()
        ok_btn = make_button("Continue", "primary")
        cancel_btn = make_button("Cancel", "ghost")
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        result = {"ok": False}

        def accept():
            result["ok"] = True
            dlg.accept()

        ok_btn.clicked.connect(accept)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()
        return pw_field.text(), result["ok"]

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(theme.STYLESHEET)

    window = MainWindow()
    window.app = app
    app.installEventFilter(window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
