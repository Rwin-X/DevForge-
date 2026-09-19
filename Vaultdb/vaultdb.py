#!/usr/bin/env python3
"""
VaultDB - a simple, private database with a graphical interface.

Run:  python vaultdb.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QComboBox, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from core import (
    NotAVaultError, Vault, VaultError, WrongPasswordError, is_encrypted_container,
)

APP_NAME = "VaultDB"

AUTOLOCK_CHOICES = [("Never", 0), ("After 1 minute", 60), ("After 5 minutes", 300),
                    ("After 15 minutes", 900), ("After 1 hour", 3600)]
DEFAULT_AUTOLOCK = 300
CLIPBOARD_CLEAR_SECS = 30

# --------------------------------------------------------------------- theme
QSS = """
* { font-family: "Segoe UI", "SF Pro Text", "Inter", "Helvetica Neue", sans-serif; font-size: 13px; }
QMainWindow, QWidget#root { background: #0c0c0d; }
QWidget { color: #e8e8ea; }

/* sidebar */
QFrame#sidebar { background: #0c0c0d; border-right: 1px solid #1f1f22; }
QLabel#brand { font-size: 15px; font-weight: 600; letter-spacing: 3px; color: #ffffff; }
QLabel#dbname { color: #6d6d74; font-size: 12px; }
QPushButton#nav {
    background: transparent; color: #8a8a92; text-align: left;
    border: none; border-radius: 8px; padding: 10px 14px; font-size: 13px;
}
QPushButton#nav:hover { background: #151517; color: #ffffff; }
QPushButton#nav:checked { background: #1a1a1d; color: #ffffff; }

/* headings */
QLabel#h1 { font-size: 22px; font-weight: 600; color: #ffffff; }
QLabel#sub { color: #7d7d85; font-size: 13px; }
QLabel#label { color: #a0a0a8; font-size: 12px; font-weight: 600; }
QLabel#hint { color: #6d6d74; font-size: 12px; }
QLabel#empty { color: #5c5c63; font-size: 13px; }
QLabel#status { color: #6d6d74; font-size: 12px; }
QLabel#stat { font-size: 26px; font-weight: 600; color: #ffffff; }
QLabel#statlabel { color: #7d7d85; font-size: 12px; }

/* inputs */
QLineEdit, QPlainTextEdit {
    background: #121214; border: 1px solid #232327; border-radius: 8px;
    padding: 9px 12px; color: #f0f0f2; selection-background-color: #3a3a40;
}
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #6a6a72; }
QLineEdit::placeholder { color: #55555c; }

/* lists & tables */
QListWidget, QTableWidget {
    background: #0f0f10; border: 1px solid #1f1f22; border-radius: 10px;
    outline: none; gridline-color: transparent;
}
QListWidget::item { padding: 11px 12px; border-radius: 6px; margin: 2px 4px; color: #d0d0d4; }
QListWidget::item:hover { background: #151517; }
QListWidget::item:selected { background: #1f1f23; color: #ffffff; }
QTableWidget::item { padding: 8px 10px; border: none; }
QTableWidget::item:selected { background: #1f1f23; color: #ffffff; }
QHeaderView::section {
    background: #0f0f10; color: #6d6d74; border: none;
    border-bottom: 1px solid #1f1f22; padding: 9px 10px; font-size: 11px; font-weight: 600;
}
QTableCornerButton::section { background: #0f0f10; border: none; }

/* buttons */
QPushButton {
    background: #161618; border: 1px solid #262629; border-radius: 8px;
    padding: 9px 16px; color: #e8e8ea;
}
QPushButton:hover { background: #1d1d20; border-color: #34343a; }
QPushButton:pressed { background: #121214; }
QPushButton:disabled { color: #4a4a50; background: #101011; border-color: #1a1a1c; }
QPushButton#primary { background: #f2f2f4; color: #0c0c0d; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #ffffff; }
QPushButton#primary:disabled { background: #2a2a2e; color: #6a6a70; }
QPushButton#danger { color: #d98a8a; }
QPushButton#danger:hover { background: #1f1414; border-color: #4a2626; color: #ee9c9c; }
QPushButton#ghost { background: transparent; border: none; color: #8a8a92; }
QPushButton#ghost:hover { color: #ffffff; background: #151517; }

/* cards */
QFrame#card { background: #0f0f10; border: 1px solid #1f1f22; border-radius: 12px; }
QFrame#drop { background: #0f0f10; border: 1px dashed #2e2e33; border-radius: 12px; }
QFrame#drop[active="true"] { border: 1px dashed #8a8a92; background: #131315; }
QFrame#hline { background: #1f1f22; max-height: 1px; min-height: 1px; border: none; }

QProgressBar { background: #1a1a1d; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }
QProgressBar::chunk { border-radius: 2px; background: #f2f2f4; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2a2a2e; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3a3a40; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { height: 0; }

QComboBox {
    background: #121214; border: 1px solid #232327; border-radius: 8px;
    padding: 8px 12px; color: #f0f0f2; min-width: 150px;
}
QComboBox:hover { border-color: #34343a; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #121214; border: 1px solid #262629; selection-background-color: #1f1f23;
    color: #e8e8ea; outline: none; padding: 4px;
}
QPushButton#small { padding: 5px 12px; font-size: 12px; }

QDialog { background: #0c0c0d; }
QMessageBox { background: #0c0c0d; }
QToolTip { background: #1a1a1d; color: #e8e8ea; border: 1px solid #2a2a2e; padding: 6px 8px; }
"""


# ------------------------------------------------------------------- helpers
def fmt_time(ts: float) -> str:
    return time.strftime("%d %b %Y, %H:%M", time.localtime(ts))


def fmt_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def button(text: str, kind: str = "", tip: str = "") -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def hline() -> QFrame:
    f = QFrame()
    f.setObjectName("hline")
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f


def msg(parent, title: str, text: str, kind: str = "info") -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon({"info": QMessageBox.Icon.Information,
                 "warn": QMessageBox.Icon.Warning,
                 "error": QMessageBox.Icon.Critical}[kind])
    box.exec()


def confirm(parent, title: str, text: str, yes: str = "Yes", no: str = "Cancel") -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    y = box.addButton(yes, QMessageBox.ButtonRole.AcceptRole)
    box.addButton(no, QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is y


def password_strength(pw: str) -> tuple[int, str]:
    """Return (0..100, description). Length matters most; variety helps a little."""
    if not pw:
        return 0, ""
    variety = sum([any(c.islower() for c in pw), any(c.isupper() for c in pw),
                   any(c.isdigit() for c in pw), any(not c.isalnum() for c in pw)])
    unique = len(set(pw))
    score = min(len(pw) * 4, 64) + variety * 8
    if unique <= 3:                      # e.g. "aaaaaaaa"
        score = min(score, 20)
    if len(pw) < 8:
        return min(score, 25), "Too short. Use at least 8 characters."
    if score < 50:
        return score, "Weak. Make it longer, or add numbers and symbols."
    if score < 75:
        return score, "Okay. A longer phrase of several words would be better."
    return min(score, 100), "Strong."


# ------------------------------------------------------------------- dialogs
class PasswordDialog(QDialog):
    """Ask for a password. With confirm=True also asks to repeat it and shows strength."""

    def __init__(self, parent, title: str, heading: str, text: str, confirm_mode: bool = False,
                 ok_text: str = "Continue"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(440)
        self._confirm = confirm_mode

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 26, 28, 22)
        lay.setSpacing(6)
        lay.addWidget(label(heading, "h1"))
        lay.addWidget(label(text, "sub", wrap=True))
        lay.addSpacing(14)

        lay.addWidget(label("PASSWORD", "label"))
        self.pw1 = QLineEdit()
        self.pw1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw1.setPlaceholderText("Type your password")
        lay.addWidget(self.pw1)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.strength = label("", "hint")
        self.pw2 = QLineEdit()
        if confirm_mode:
            self.bar.setRange(0, 100)
            lay.addSpacing(2)
            lay.addWidget(self.bar)
            lay.addWidget(self.strength)
            lay.addSpacing(10)
            lay.addWidget(label("REPEAT PASSWORD", "label"))
            self.pw2.setEchoMode(QLineEdit.EchoMode.Password)
            self.pw2.setPlaceholderText("Type it again to make sure")
            lay.addWidget(self.pw2)
            lay.addSpacing(6)
            warn = label("Important: there is no way to recover a forgotten password. "
                         "If you lose it, your data is gone for good.", "hint", wrap=True)
            lay.addWidget(warn)
            self.pw1.textChanged.connect(self._on_change)
        else:
            self.bar.hide()
            self.strength.hide()
            self.pw2.hide()

        self.err = label("", "hint")
        self.err.setStyleSheet("color: #d98a8a;")
        lay.addWidget(self.err)
        lay.addSpacing(10)

        row = QHBoxLayout()
        row.addStretch()
        cancel = button("Cancel")
        cancel.clicked.connect(self.reject)
        self.ok = button(ok_text, "primary")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self._accept)
        row.addWidget(cancel)
        row.addWidget(self.ok)
        lay.addLayout(row)

        self.pw1.returnPressed.connect(self._accept if not confirm_mode else self.pw2.setFocus)
        if confirm_mode:
            self.pw2.returnPressed.connect(self._accept)
        self.pw1.setFocus()

    def _on_change(self, text: str):
        score, desc = password_strength(text)
        self.bar.setValue(score)
        self.strength.setText(desc)

    def _accept(self):
        pw = self.pw1.text()
        if not pw:
            self.err.setText("Please type a password.")
            return
        if self._confirm:
            if len(pw) < 8:
                self.err.setText("The password must be at least 8 characters long.")
                return
            if pw != self.pw2.text():
                self.err.setText("The two passwords do not match.")
                return
        self.accept()

    @property
    def password(self) -> str:
        return getattr(self, "_result_pw", "")

    def done(self, code):
        # read .password BEFORE exec() returns, then wipe the widgets
        self._result_pw = self.pw1.text()
        super().done(code)
        self.pw1.clear()
        self.pw2.clear()


# ------------------------------------------------------------------- pages
class Page(QWidget):
    """Base class: title + one-line explanation, then content."""

    def __init__(self, win: "MainWindow", title: str, subtitle: str):
        super().__init__()
        self.win = win
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 30, 36, 24)
        outer.setSpacing(4)
        outer.addWidget(label(title, "h1"))
        outer.addWidget(label(subtitle, "sub", wrap=True))
        outer.addSpacing(18)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body, 1)

    def refresh(self) -> None:  # overridden
        pass

    def clear_view(self) -> None:
        """Wipe on-screen data (used when auto-locking). Subclasses override."""
        pass


class OverviewPage(Page):
    def __init__(self, win):
        super().__init__(win, "Overview", "A quick summary of what is inside your database.")
        grid = QHBoxLayout()
        grid.setSpacing(12)
        self.stats: dict[str, QLabel] = {}
        for key, cap in (("texts", "Notes"), ("files", "Files"), ("kvs", "Data items"), ("size", "Stored file size")):
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 18, 20, 18)
            val = label("0", "stat")
            self.stats[key] = val
            cl.addWidget(val)
            cl.addWidget(label(cap, "statlabel"))
            grid.addWidget(card)
        self.body.addLayout(grid)
        self.body.addSpacing(14)

        info = QFrame()
        info.setObjectName("card")
        il = QVBoxLayout(info)
        il.setContentsMargins(20, 16, 20, 16)
        il.setSpacing(10)
        self.path = self._row(il, "LOCATION")
        self.enc = self._row(il, "PROTECTION")
        self.body.addWidget(info)

        self.body.addSpacing(14)
        self.body.addWidget(label(
            "How it works", "label"))
        self.body.addWidget(label(
            "•  Notes: write text and keep it organised with tags.\n"
            "•  Files: drag any file in to keep a copy inside the database.\n"
            "•  Data: store small pieces of information as a name and a value.\n"
            "•  Security: lock everything with a password.\n"
            "Every change is saved automatically.", "sub", wrap=True))
        self.body.addStretch()

    @staticmethod
    def _row(parent: QVBoxLayout, cap: str) -> QLabel:
        row = QHBoxLayout()
        c = label(cap, "label")
        c.setFixedWidth(110)
        v = label("", "")
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.setWordWrap(True)
        row.addWidget(c)
        row.addWidget(v, 1)
        parent.addLayout(row)
        return v

    def clear_view(self):
        for lab in self.stats.values():
            lab.setText("0")
        self.path.clear()
        self.enc.clear()

    def refresh(self):
        v = self.win.vault
        if not v:
            return
        s = v.stats()
        self.stats["texts"].setText(str(s.texts))
        self.stats["files"].setText(str(s.files))
        self.stats["kvs"].setText(str(s.kvs))
        self.stats["size"].setText(fmt_size(s.total_file_bytes))
        self.path.setText(str(v.path))
        self.enc.setText("Locked with a password" if v.encrypted
                         else "Not locked. Anyone with the file can read it.")


class NotesPage(Page):
    def __init__(self, win):
        super().__init__(win, "Notes",
                         "Write anything you want to keep. Pick a note on the left to read or edit it.")
        self.current_id: int | None = None

        row = QHBoxLayout()
        row.setSpacing(18)
        self.body.addLayout(row, 1)

        # left column
        left = QVBoxLayout()
        left.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search notes…")
        self.search.textChanged.connect(self.refresh)
        left.addWidget(self.search)
        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._on_select)
        left.addWidget(self.list, 1)
        self.empty = label("No notes yet.\nClick “New note” to write your first one.", "empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.empty)
        new = button("＋  New note", "primary")
        new.clicked.connect(self.new)
        left.addWidget(new)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(270)
        row.addWidget(lw)

        # right column
        right = QVBoxLayout()
        right.setSpacing(6)
        right.addWidget(label("TITLE", "label"))
        self.title = QLineEdit()
        self.title.setPlaceholderText("Give your note a short name, e.g. “Wi-Fi passwords”")
        right.addWidget(self.title)
        right.addSpacing(6)
        right.addWidget(label("TAGS (OPTIONAL)", "label"))
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("Words that help you find it later, separated by commas: home, work")
        right.addWidget(self.tags)
        right.addSpacing(6)
        right.addWidget(label("YOUR NOTE", "label"))
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Write here…")
        right.addWidget(self.text, 1)
        self.meta = label("", "hint")
        right.addWidget(self.meta)

        btns = QHBoxLayout()
        self.delete_btn = button("Delete note", "danger")
        self.delete_btn.clicked.connect(self.delete)
        self.save_btn = button("Save note", "primary")
        self.save_btn.clicked.connect(self.save)
        btns.addWidget(self.delete_btn)
        btns.addStretch()
        btns.addWidget(self.save_btn)
        right.addLayout(btns)
        row.addLayout(right, 1)

    def refresh(self, *_):
        v = self.win.vault
        self.list.blockSignals(True)
        self.list.clear()
        if v:
            for r in v.list_texts(self.search.text()):
                it = QListWidgetItem(r[1] or "(untitled)")
                it.setData(Qt.ItemDataRole.UserRole, r[0])
                self.list.addItem(it)
                if r[0] == self.current_id:
                    it.setSelected(True)
        self.list.blockSignals(False)
        self.empty.setVisible(self.list.count() == 0)
        self.delete_btn.setEnabled(self.current_id is not None)

    def _on_select(self):
        items = self.list.selectedItems()
        if not items:
            return
        row = self.win.vault.get_text(items[0].data(Qt.ItemDataRole.UserRole))
        if not row:
            return
        self.current_id = row[0]
        self.title.setText(row[1])
        self.tags.setText(row[3])
        self.text.setPlainText(row[2])
        self.meta.setText(f"Created {fmt_time(row[4])}   ·   Last changed {fmt_time(row[5])}")
        self.delete_btn.setEnabled(True)

    def clear_view(self):
        self.current_id = None
        self.search.clear()
        self.list.clear()
        self.title.clear()
        self.tags.clear()
        self.text.clear()
        self.meta.clear()

    def new(self):
        self.current_id = None
        self.list.clearSelection()
        self.title.clear()
        self.tags.clear()
        self.text.clear()
        self.meta.setText("New note. It will be stored when you click “Save note”.")
        self.delete_btn.setEnabled(False)
        self.title.setFocus()

    def save(self):
        v = self.win.vault
        title = self.title.text().strip()
        if not title:
            msg(self, "Title needed", "Please give your note a title so you can find it later.", "warn")
            self.title.setFocus()
            return
        body, tags = self.text.toPlainText(), self.tags.text().strip()
        if self.current_id is None:
            self.current_id = v.add_text(title, body, tags)
        else:
            v.update_text(self.current_id, title, body, tags)
        self.win.autosave()
        self.refresh()
        self.win.status("Note saved.")

    def delete(self):
        if self.current_id is None:
            return
        if confirm(self, "Delete note", "Delete this note permanently?", "Delete") and self.win.vault:
            self.win.vault.delete_text(self.current_id)
            self.win.autosave()
            self.new()
            self.refresh()
            self.win.status("Note deleted.")


class DropFrame(QFrame):
    """A dashed area that accepts dragged files and click-to-browse."""
    files_dropped = pyqtSignal(list)
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("drop")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 22, 20, 22)
        t = label("Drag files here to add them", "")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("font-size: 14px; color: #d0d0d4;")
        s = label("or click this area to choose files from your computer", "hint")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        lay.addWidget(s)

    def _set_active(self, on: bool):
        self.setProperty("active", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, e):
        self.clicked.emit()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_active(True)

    def dragLeaveEvent(self, e):
        self._set_active(False)

    def dropEvent(self, e: QDropEvent):
        self._set_active(False)
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        paths = [p for p in paths if Path(p).is_file()]
        if paths:
            self.files_dropped.emit(paths)


class FilesPage(Page):
    def __init__(self, win):
        super().__init__(win, "Files",
                         "Keep copies of documents, images or any file inside your database.")
        self.drop = DropFrame()
        self.drop.files_dropped.connect(self.add_paths)
        self.drop.clicked.connect(self.browse)
        self.body.addWidget(self.drop)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search files by name…")
        self.search.textChanged.connect(self.refresh)
        self.body.addWidget(self.search)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["NAME", "TYPE", "SIZE", "ADDED"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        h.setHighlightSections(False)
        self.table.itemSelectionChanged.connect(self._sel)
        self.body.addWidget(self.table, 1)

        self.empty = label("No files yet. Drag one into the box above.", "empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.empty)

        row = QHBoxLayout()
        self.export_btn = button("Save copy to computer…", "primary",
                                 "Write the selected file(s) back out of the database")
        self.export_btn.clicked.connect(self.export)
        self.delete_btn = button("Remove from database", "danger")
        self.delete_btn.clicked.connect(self.delete)
        row.addWidget(self.delete_btn)
        row.addStretch()
        row.addWidget(self.export_btn)
        self.body.addLayout(row)
        self._sel()

    def clear_view(self):
        self.search.clear()
        self.table.setRowCount(0)

    def _sel(self):
        has = bool(self.table.selectionModel().selectedRows())
        self.export_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)

    def _selected_ids(self) -> list[int]:
        ids = []
        for idx in self.table.selectionModel().selectedRows():
            ids.append(self.table.item(idx.row(), 0).data(Qt.ItemDataRole.UserRole))
        return ids

    def refresh(self, *_):
        self.table.setRowCount(0)
        v = self.win.vault
        if not v:
            return
        rows = v.list_files(self.search.text())
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            name = QTableWidgetItem(r[1])
            name.setData(Qt.ItemDataRole.UserRole, r[0])
            self.table.setItem(i, 0, name)
            self.table.setItem(i, 1, QTableWidgetItem(r[2] or "—"))
            self.table.setItem(i, 2, QTableWidgetItem(fmt_size(r[3])))
            self.table.setItem(i, 3, QTableWidgetItem(fmt_time(r[5])))
        self.empty.setVisible(len(rows) == 0)
        self.table.setVisible(len(rows) > 0)
        self._sel()

    def browse(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose files to add")
        if paths and self.win.vault:
            self.add_paths(paths)

    def add_paths(self, paths: list[str]):
        big = [p for p in paths if Path(p).stat().st_size > 200 * 1024 * 1024]
        if big and not confirm(
                self, "Large file",
                "One or more files are larger than 200 MB. The whole database is kept in "
                "memory, so this can be slow. Add anyway?", "Add anyway"):
            return
        added = 0
        for p in paths:
            try:
                self.win.vault.add_file(p)
                added += 1
            except OSError as exc:
                msg(self, "Could not add file", f"{Path(p).name}\n\n{exc}", "error")
        if added:
            self.win.autosave()
            self.refresh()
            self.win.status(f"{added} file(s) added.")

    def export(self):
        ids = self._selected_ids()
        v = self.win.vault
        if not ids or not v:
            return
        names = {r[0]: r[1] for r in v.list_files()}
        if len(ids) == 1:
            dest, _ = QFileDialog.getSaveFileName(self, "Save copy", names[ids[0]])
            if dest:
                v.export_file(ids[0], dest)
                self.win.status("File saved.")
        else:
            folder = QFileDialog.getExistingDirectory(self, "Choose a folder for the copies")
            if not folder:
                return
            used: set[str] = set()
            for i in ids:
                name = names[i]
                stem, suf, n = Path(name).stem, Path(name).suffix, 1
                while name in used or (Path(folder) / name).exists():
                    name = f"{stem} ({n}){suf}"
                    n += 1
                used.add(name)
                v.export_file(i, Path(folder) / name)
            self.win.status(f"{len(ids)} files saved.")

    def delete(self):
        ids = self._selected_ids()
        if ids and confirm(self, "Remove files",
                           f"Remove {len(ids)} file(s) from the database?\n"
                           "Your original files on the computer are not touched.",
                           "Remove") and self.win.vault:
            for i in ids:
                self.win.vault.delete_file(i)
            self.win.autosave()
            self.refresh()


class DataPage(Page):
    def __init__(self, win):
        super().__init__(win, "Data",
                         "Store small pieces of information as a name and a value, "
                         "like  “Email → me@example.com”.")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…")
        self.search.textChanged.connect(self.refresh)
        self.body.addWidget(self.search)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["NAME", "VALUE", "LAST CHANGED"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setHighlightSections(False)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.body.addWidget(self.table, 1)

        self.empty = label("Nothing here yet. Fill in the two boxes below and click “Save item”.", "empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.empty)

        self.body.addWidget(hline())
        form = QHBoxLayout()
        form.setSpacing(12)
        c1 = QVBoxLayout()
        c1.addWidget(label("NAME", "label"))
        self.key = QLineEdit()
        self.key.setPlaceholderText("e.g. Email")
        c1.addWidget(self.key)
        c2 = QVBoxLayout()
        c2.addWidget(label("VALUE", "label"))
        self.val = QLineEdit()
        self.val.setPlaceholderText("e.g. me@example.com")
        c2.addWidget(self.val)
        form.addLayout(c1, 1)
        form.addLayout(c2, 2)
        self.body.addLayout(form)
        self.hint = label("If the name already exists, its value is replaced.", "hint")
        self.body.addWidget(self.hint)

        row = QHBoxLayout()
        self.delete_btn = button("Delete item", "danger")
        self.delete_btn.clicked.connect(self.delete)
        self.copy_btn = button("Copy value", "", "Copy the value to the clipboard")
        self.copy_btn.clicked.connect(self.copy_value)
        self.copy_btn.setEnabled(False)
        clear = button("Clear boxes", "ghost")
        clear.clicked.connect(self._clear)
        save = button("Save item", "primary")
        save.clicked.connect(self.save)
        self.key.returnPressed.connect(self.val.setFocus)
        self.val.returnPressed.connect(self.save)
        row.addWidget(self.delete_btn)
        row.addStretch()
        row.addWidget(clear)
        row.addWidget(self.copy_btn)
        row.addWidget(save)
        self.body.addLayout(row)
        self.delete_btn.setEnabled(False)

    def refresh(self, *_):
        self.table.setRowCount(0)
        v = self.win.vault
        if not v:
            return
        rows = v.list_kv(self.search.text())
        self.table.setRowCount(len(rows))
        for i, (k, val, mod) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(k))
            self.table.setItem(i, 1, QTableWidgetItem(val))
            self.table.setItem(i, 2, QTableWidgetItem(fmt_time(mod)))
        self.empty.setVisible(len(rows) == 0)
        self.table.setVisible(len(rows) > 0)

    def clear_view(self):
        self.search.clear()
        self.key.clear()
        self.val.clear()
        self.table.setRowCount(0)
        self.copy_btn.setEnabled(False)
        self.win.flush_clipboard()          # only clears if it still holds our value

    def _on_select(self):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            r = rows[0].row()
            self.key.setText(self.table.item(r, 0).text())
            self.val.setText(self.table.item(r, 1).text())
            self.delete_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)

    def _clear(self):
        self.table.clearSelection()
        self.key.clear()
        self.val.clear()
        self.delete_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.key.setFocus()

    def copy_value(self):
        QApplication.clipboard().setText(self.val.text())
        self.win.status("Value copied. It will be cleared from the clipboard in 30 seconds.")
        self.win.clipboard_guard(self.val.text())

    def save(self):
        k = self.key.text().strip()
        if not k:
            msg(self, "Name needed", "Please type a name for this item.", "warn")
            self.key.setFocus()
            return
        self.win.vault.set_kv(k, self.val.text())
        self.win.autosave()
        self.refresh()
        self.win.status("Item saved.")

    def delete(self):
        k = self.key.text().strip()
        if k and confirm(self, "Delete item", f"Delete “{k}”?", "Delete") and self.win.vault:
            self.win.vault.delete_kv(k)
            self.win.autosave()
            self._clear()
            self.refresh()


class SecurityPage(Page):
    def __init__(self, win):
        super().__init__(win, "Security",
                         "Protect your database with a password so only you can open it.")
        self.card = QFrame()
        self.card.setObjectName("card")
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(24, 22, 24, 22)
        cl.setSpacing(6)
        self.state = label("", "h1")
        self.state_sub = label("", "sub", wrap=True)
        cl.addWidget(self.state)
        cl.addWidget(self.state_sub)
        cl.addSpacing(14)
        self.btn_row = QHBoxLayout()
        cl.addLayout(self.btn_row)
        self.body.addWidget(self.card)
        self.body.addSpacing(6)

        # auto-lock
        self.lock_card = QFrame()
        self.lock_card.setObjectName("card")
        lk = QHBoxLayout(self.lock_card)
        lk.setContentsMargins(24, 16, 24, 16)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label("Auto-lock", ""))
        self.lock_hint = label("", "hint", wrap=True)
        col.addWidget(self.lock_hint)
        lk.addLayout(col, 1)
        self.lock_combo = QComboBox()
        for text, secs in AUTOLOCK_CHOICES:
            self.lock_combo.addItem(text, secs)
        self.lock_combo.currentIndexChanged.connect(self._lock_changed)
        lk.addWidget(self.lock_combo)
        self.body.addWidget(self.lock_card)

        # backup
        self.bk_card = QFrame()
        self.bk_card.setObjectName("card")
        bk = QHBoxLayout(self.bk_card)
        bk.setContentsMargins(24, 16, 24, 16)
        col2 = QVBoxLayout()
        col2.setSpacing(2)
        col2.addWidget(label("Readable backup (JSON)", ""))
        col2.addWidget(label("Export everything to a plain text file, or import one. "
                             "An export is NOT protected by your password.", "hint", wrap=True))
        bk.addLayout(col2, 1)
        b_imp = button("Import…")
        b_imp.clicked.connect(self.win.import_json)
        b_exp = button("Export…")
        b_exp.clicked.connect(self.win.export_json)
        bk.addWidget(b_imp)
        bk.addWidget(b_exp)
        self.body.addWidget(self.bk_card)
        self.body.addSpacing(6)

        self.body.addWidget(label("Good to know", "label"))
        self.body.addWidget(label(
            "•  Your password never leaves this computer and is never stored.\n"
            "•  Each save keeps the previous version next to it as a “.bak” file.\n"
            "•  There is no “forgot password”. Write it down somewhere safe.\n"
            "•  Use a phrase of several words. Longer is stronger than complicated.\n"
            "•  A locked database looks like random noise to anyone without the password.",
            "sub", wrap=True))
        self.body.addSpacing(6)
        self.body.addWidget(label("Technical details", "label"))
        self.body.addWidget(label(
            "AES-256-GCM authenticated encryption  ·  scrypt key derivation (128 MiB, memory-hard)  ·  "
            "random salt on every password change  ·  fresh nonce on every save",
            "hint", wrap=True))
        self.body.addStretch()

    def _lock_changed(self, _i):
        self.win.set_autolock(self.lock_combo.currentData())

    def _clear_buttons(self):
        while self.btn_row.count():
            it = self.btn_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def refresh(self):
        self._clear_buttons()
        v = self.win.vault
        if not v:
            return
        self.lock_card.setVisible(v.encrypted)
        if v.encrypted:
            self.lock_combo.blockSignals(True)
            self.lock_combo.setCurrentIndex(max(0, self.lock_combo.findData(self.win.autolock_secs)))
            self.lock_combo.blockSignals(False)
            self.lock_hint.setText("Locks the database after a period of no activity, so it is safe "
                                   "if you walk away from the computer.")
        if v.encrypted:
            self.state.setText("🔒  Locked")
            self.state_sub.setText("Your database is protected. You need the password to open it.")
            b1 = button("Change password", "primary")
            b1.clicked.connect(self.change)
            b2 = button("Remove password", "danger")
            b2.clicked.connect(self.remove)
            self.btn_row.addWidget(b1)
            self.btn_row.addWidget(b2)
        else:
            self.state.setText("🔓  Not locked")
            self.state_sub.setText("Anyone who gets the file can read what is inside. "
                                   "Set a password to lock it.")
            b = button("Set a password", "primary")
            b.clicked.connect(self.encrypt)
            self.btn_row.addWidget(b)
        self.btn_row.addStretch()

    def _check_current(self) -> bool:
        d = PasswordDialog(self, "Current password", "Enter current password",
                           "For your safety, please confirm your current password first.")
        if d.exec() != QDialog.DialogCode.Accepted or not self.win.vault:
            return False
        if not self.win.vault.verify_password(d.password):
            msg(self, "Wrong password", "That is not the current password.", "error")
            return False
        return True

    def encrypt(self):
        d = PasswordDialog(self, "Set password", "Choose a password",
                           "This password will be needed every time you open this database.",
                           confirm_mode=True, ok_text="Lock database")
        if d.exec() == QDialog.DialogCode.Accepted and self.win.vault:
            self.win.busy("Encrypting…")
            self.win.vault.set_password(d.password)
            self.win.status("Database is now locked.")
            self.win.refresh_all()

    def change(self):
        if not self._check_current():
            return
        d = PasswordDialog(self, "New password", "Choose a new password",
                           "This replaces the old password.", confirm_mode=True,
                           ok_text="Change password")
        if d.exec() == QDialog.DialogCode.Accepted and self.win.vault:
            self.win.busy("Re-encrypting…")
            self.win.vault.set_password(d.password)
            self.win.status("Password changed.")

    def remove(self):
        if not self._check_current():
            return
        if confirm(self, "Remove password",
                   "The database will be stored without protection.\nContinue?",
                   "Remove password") and self.win.vault:
            self.win.vault.remove_password()
            self.win.status("Password removed.")
            self.win.refresh_all()


class WelcomePage(QWidget):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(6)

        t = label("Welcome to VaultDB", "h1")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = label("Your own private database — notes, files and data in one file.", "sub")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addSpacing(26)

        steps = QHBoxLayout()
        steps.setSpacing(12)
        for n, head, txt in (
            ("1", "Create or open", "Start a new database, or open one you made before."),
            ("2", "Add your things", "Write notes, drag in files, or save small data items."),
            ("3", "Lock it (optional)", "Protect everything with a password."),
        ):
            card = QFrame()
            card.setObjectName("card")
            card.setFixedWidth(220)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 16, 18, 18)
            cl.setSpacing(4)
            num = label(n, "stat")
            cl.addWidget(num)
            cl.addWidget(label(head, ""))
            cl.addWidget(label(txt, "hint", wrap=True))
            steps.addWidget(card)
        lay.addLayout(steps)
        lay.addSpacing(28)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b1 = button("Create new database", "primary")
        b1.clicked.connect(win.new_db)
        b2 = button("Open existing database")
        b2.clicked.connect(win.open_db)
        row.addWidget(b1)
        row.addWidget(b2)
        lay.addLayout(row)

        # shown instead of the intro after an auto-lock
        self.locked_box = QFrame()
        self.locked_box.setObjectName("card")
        lb = QVBoxLayout(self.locked_box)
        lb.setContentsMargins(28, 22, 28, 22)
        lb.setSpacing(6)
        self.locked_title = label("🔒  Database locked", "h1")
        self.locked_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.locked_sub = label("", "sub", wrap=True)
        self.locked_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.addWidget(self.locked_title)
        lb.addWidget(self.locked_sub)
        lb.addSpacing(10)
        unlock = button("Unlock", "primary")
        unlock.clicked.connect(win.unlock_locked)
        lb.addWidget(unlock, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(20)
        lay.addWidget(self.locked_box, alignment=Qt.AlignmentFlag.AlignCenter)
        self.locked_box.hide()

    def show_locked(self, path: Path):
        self.locked_sub.setText(f"“{path.name}” was locked to keep your data safe.\n"
                                "Enter your password to continue where you left off.")
        self.locked_box.show()

    def hide_locked(self):
        self.locked_box.hide()


# ------------------------------------------------------------------- activity
class ActivityFilter(QObject):
    """Reports real user input (keys, mouse, wheel) so the idle timer measures true inactivity."""
    _EVENTS = {QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress,
               QEvent.Type.MouseMove, QEvent.Type.Wheel}

    def __init__(self, on_activity):
        super().__init__()
        self._cb = on_activity

    def eventFilter(self, obj, event):
        if event.type() in self._EVENTS:
            self._cb()
        return False


# ------------------------------------------------------------------- window
class MainWindow(QMainWindow):
    NAV = [("Overview", OverviewPage), ("Notes", NotesPage), ("Files", FilesPage),
           ("Data", DataPage), ("Security", SecurityPage)]

    def __init__(self):
        super().__init__()
        self.vault: Vault | None = None
        self.autolock_secs = DEFAULT_AUTOLOCK
        self._last_activity = time.monotonic()
        self._locked_path: Path | None = None
        self._clip_token: str | None = None
        self.setWindowTitle(APP_NAME)
        self.resize(1120, 720)
        self.setMinimumSize(900, 600)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sl = QVBoxLayout(self.sidebar)
        sl.setContentsMargins(16, 24, 16, 16)
        sl.setSpacing(4)
        sl.addWidget(label("VAULTDB", "brand"))
        self.dbname = label("No database open", "dbname")
        self.dbname.setWordWrap(True)
        sl.addWidget(self.dbname)
        sl.addSpacing(22)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []
        for i, (name, _) in enumerate(self.NAV):
            b = QPushButton(name)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b, i)
            sl.addWidget(b)
            self.nav_buttons.append(b)
        sl.addStretch()
        sl.addWidget(hline())
        sl.addSpacing(6)
        for text, slot in (("New database", self.new_db), ("Open database…", self.open_db)):
            b = button(text, "ghost")
            b.setStyleSheet("text-align: left; padding: 8px 14px;")
            b.clicked.connect(slot)
            sl.addWidget(b)
        outer.addWidget(self.sidebar)

        # content
        right = QVBoxLayout()
        right.setSpacing(0)
        self.stack = QStackedWidget()
        self.welcome = WelcomePage(self)
        self.stack.addWidget(self.welcome)
        self.pages: list[Page] = []
        for _, cls in self.NAV:
            p = cls(self)
            self.pages.append(p)
            self.stack.addWidget(p)
        right.addWidget(self.stack, 1)
        self.status_lbl = label("", "status")
        self.status_lbl.setContentsMargins(36, 8, 36, 12)
        right.addWidget(self.status_lbl)
        outer.addLayout(right, 1)

        self.group.idClicked.connect(self._goto)

        # shortcuts
        for text, key, slot in (("New", QKeySequence.StandardKey.New, self.new_db),
                                ("Open", QKeySequence.StandardKey.Open, self.open_db),
                                ("Save", QKeySequence.StandardKey.Save, self.save)):
            act = QAction(text, self)
            act.setShortcut(key)
            act.triggered.connect(slot)
            self.addAction(act)

        # idle detection: poll once a second; cheap, and immune to timer-reset races
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(1000)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start()
        self._activity = ActivityFilter(self._touch)
        QApplication.instance().installEventFilter(self._activity)

        self._clip_timer = QTimer(self)
        self._clip_timer.setSingleShot(True)
        self._clip_timer.timeout.connect(self._clear_clipboard)

        self._set_open(False)

    # ---- auto-lock & clipboard
    def _touch(self):
        self._last_activity = time.monotonic()

    def set_autolock(self, secs: int):
        self.autolock_secs = int(secs or 0)
        self._touch()

    def _check_idle(self):
        v = self.vault
        if not v or not v.encrypted or self.autolock_secs <= 0:
            return
        if time.monotonic() - self._last_activity >= self.autolock_secs:
            self.lock_now(reason="Locked automatically after a period of inactivity.")

    def lock_now(self, reason: str = "Database locked."):
        """Save, wipe the open database from memory and ask for the password again."""
        v = self.vault
        if not v or not v.encrypted:
            return
        path = v.path
        # close any modal dialog so it cannot keep showing unlocked data
        modal = QApplication.activeModalWidget()
        if modal is not None:
            modal.reject()
        try:
            v.save()
        except OSError:
            pass
        v.close()
        self.vault = None
        self.flush_clipboard()
        for pg in self.pages:            # clear anything still displayed
            pg.clear_view()
        self._locked_path = path
        self._set_open(False)
        self.dbname.setText(f"{path.name}  (locked)")
        self.status(reason)
        self.welcome.show_locked(path)

    def unlock_locked(self):
        if not self._locked_path:
            return
        self._open_path(self._locked_path)

    def clipboard_guard(self, text: str):
        """Clear the clipboard after a delay, but only if it still holds what we put there."""
        self._clip_token = text
        self._clip_timer.start(CLIPBOARD_CLEAR_SECS * 1000)

    def _clear_clipboard(self):
        cb = QApplication.clipboard()
        if self._clip_token is not None and cb.text() == self._clip_token:
            cb.clear()
        self._clip_token = None

    def flush_clipboard(self):
        """Clear our copied value now (e.g. on lock), leaving unrelated clipboard content alone."""
        self._clip_timer.stop()
        self._clear_clipboard()

    # ---- state
    def _set_open(self, is_open: bool):
        for b in self.nav_buttons:
            b.setEnabled(is_open)
        if is_open:
            self.nav_buttons[0].setChecked(True)
            self._goto(0)
        else:
            self.group.setExclusive(False)
            for b in self.nav_buttons:
                b.setChecked(False)
            self.group.setExclusive(True)
            self.stack.setCurrentWidget(self.welcome)
            self.dbname.setText("No database open")

    def _goto(self, idx: int):
        self.stack.setCurrentWidget(self.pages[idx])
        self.pages[idx].refresh()

    def refresh_all(self):
        for p in self.pages:
            p.refresh()

    def status(self, text: str):
        self.status_lbl.setText(text)

    def busy(self, text: str):
        self.status(text)
        QApplication.processEvents()

    def autosave(self):
        if self.vault:
            try:
                self.vault.save()
            except OSError as exc:
                msg(self, "Could not save", f"Your change could not be written to disk:\n\n{exc}", "error")

    # ---- actions
    def _attach(self, vault: Vault):
        if self.vault:
            try:
                self.vault.save()
            except OSError:
                pass
            self.vault.close()
        self.vault = vault
        self._locked_path = None
        self.welcome.hide_locked()
        self._touch()
        self.dbname.setText(vault.path.name)
        self.setWindowTitle(f"{APP_NAME} — {vault.path.name}")
        self._set_open(True)
        self.pages[1].new()  # blank note editor
        self.refresh_all()
        self.status("Ready.")
        if vault.upgraded_from_v1:
            try:
                vault.save()          # write the upgraded v2 container right away
                self.status("Ready. This database was upgraded to the newer, stronger encryption format.")
            except OSError:
                pass

    def new_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Create new database", "my-database.vdb", "VaultDB (*.vdb);;All files (*)")
        if not path:
            return
        if not path.lower().endswith(".vdb") and "." not in Path(path).name:
            path += ".vdb"
        target = Path(path)

        password = None
        if confirm(self, "Password protection",
                   "Do you want to lock this database with a password?\n\n"
                   "You can also do this later in the Security section.",
                   "Yes, set a password", "No, skip for now"):
            d = PasswordDialog(self, "Set password", "Choose a password",
                               "This password will be needed every time you open this database.",
                               confirm_mode=True, ok_text="Create database")
            if d.exec() != QDialog.DialogCode.Accepted:
                return
            password = d.password

        self.busy("Creating database…")
        tmp = target.with_name(target.name + ".new")
        try:
            tmp.unlink(missing_ok=True)
            Vault.create(tmp, password).close()
            tmp.replace(target)  # only replace an existing file after a successful create
            self._attach(Vault.open(target, password))
        except (VaultError, OSError) as exc:
            tmp.unlink(missing_ok=True)
            self.status("")
            msg(self, "Could not create database", str(exc), "error")

    def open_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open database", "", "Databases (*.vdb *.db *.sqlite);;All files (*)")
        if path:
            self._open_path(path)

    def _open_path(self, path):
        path = Path(path)
        password = None
        if is_encrypted_container(path):
            d = PasswordDialog(self, "Unlock", "This database is locked",
                               f"Enter the password for “{path.name}”.", ok_text="Unlock")
            if d.exec() != QDialog.DialogCode.Accepted:
                return
            password = d.password
        self.busy("Unlocking… this takes a moment on purpose." if password else "Opening…")
        try:
            self._attach(Vault.open(path, password))
        except WrongPasswordError:
            self.status("")
            msg(self, "Could not unlock",
                "The password is wrong, or the file is damaged.\n\n"
                f"If you think the file is damaged, a backup may exist as “{path.name}.bak”.", "error")
        except NotAVaultError as exc:
            self.status("")
            msg(self, "Unsupported file", str(exc), "error")
        except (VaultError, OSError, MemoryError) as exc:
            self.status("")
            msg(self, "Could not open", str(exc) or "Not enough memory to unlock this database.", "error")

    # ---- JSON backup
    def export_json(self):
        if not self.vault:
            return
        if not confirm(self, "Export readable backup",
                       "The export is a plain text file. It is NOT protected by your password: "
                       "anyone who gets it can read everything inside.\n\nKeep it somewhere safe.",
                       "I understand, export"):
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save backup", "vaultdb-export.json",
                                              "JSON (*.json)")
        if not dest:
            return
        self.busy("Exporting…")
        try:
            self.vault.export_json(dest)
            self.status(f"Backup written to {Path(dest).name}.")
        except OSError as exc:
            self.status("")
            msg(self, "Could not export", str(exc), "error")

    def import_json(self):
        if not self.vault:
            return
        src, _ = QFileDialog.getOpenFileName(self, "Choose a VaultDB backup", "", "JSON (*.json)")
        if not src:
            return
        if not confirm(self, "Import backup",
                       "The contents of the backup will be added to this database.\n"
                       "Nothing that is already here will be removed.", "Import"):
            return
        self.busy("Importing…")
        try:
            c = self.vault.import_json(src)
            self.autosave()
            self.refresh_all()
            self.status(f"Imported {c['notes']} notes, {c['files']} files, {c['data']} data items.")
        except VaultError as exc:
            self.status("")
            msg(self, "Could not import", str(exc), "error")

    def save(self):
        if self.vault:
            self.autosave()
            self.status("Saved.")

    def closeEvent(self, e):
        if self.vault:
            try:
                self.vault.save()
            except OSError:
                pass
            self.vault.close()
        e.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
