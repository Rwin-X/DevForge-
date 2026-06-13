#!/usr/bin/env python3
"""
NoteFlow — A fast, minimalist, local-first note-taking app for developers.
Single-file PyQt6 application. Dark theme. VS Code-inspired layout.

Dependencies:
    pip install PyQt6

Usage:
    python notes_app.py
"""

import sys
import os
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import (
    Qt, QTimer, QSize, QPoint, QSortFilterProxyModel,
    pyqtSignal, QThread, QObject, QRect
)
from PyQt6.QtGui import (
    QFont, QKeySequence, QColor, QPalette, QTextCharFormat,
    QSyntaxHighlighter, QIcon, QAction, QFontMetrics,
    QTextOption, QPainter, QPen, QTextCursor
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QLabel, QPushButton, QFrame, QScrollArea, QMessageBox,
    QInputDialog, QMenu, QStatusBar, QSizePolicy, QAbstractItemView
)

# ─────────────────────────────────────────────
#  CONSTANTS & PATHS
# ─────────────────────────────────────────────

APP_NAME    = "NoteFlow"
APP_VERSION = "1.0"
NOTES_DIR   = Path.home() / ".noteflow" / "notes"
META_FILE   = Path.home() / ".noteflow" / "meta.json"
AUTOSAVE_MS = 800   # ms after last keystroke before auto-saving

# ─────────────────────────────────────────────
#  DARK PALETTE — VS Code-flavored but crisper
# ─────────────────────────────────────────────

COLORS = {
    "bg_base":        "#0f0f0f",   # true near-black base
    "bg_sidebar":     "#141414",   # sidebar panel
    "bg_editor":      "#0f0f0f",   # editor background
    "bg_item":        "#141414",   # list item bg
    "bg_item_hover":  "#1e1e1e",   # hovered list item
    "bg_item_sel":    "#1a2a3a",   # selected list item (cool blue tint)
    "bg_input":       "#1a1a1a",   # search box
    "bg_titlebar":    "#0a0a0a",   # top bar
    "bg_toolbar":     "#111111",   # toolbar
    "accent":         "#4b8eff",   # primary blue accent
    "accent_dim":     "#2a5cbf",   # dimmer accent
    "text_primary":   "#e8e8e8",   # main text
    "text_secondary": "#888888",   # muted labels
    "text_disabled":  "#444444",   # very muted
    "text_accent":    "#4b8eff",   # accent-colored text
    "border":         "#222222",   # subtle dividers
    "border_focus":   "#4b8eff",   # focus ring
    "scrollbar":      "#2a2a2a",   # scrollbar track
    "scrollbar_thumb":"#3a3a3a",   # scrollbar thumb
    "danger":         "#e05555",   # delete/error
    "success":        "#4ec94e",   # saved indicator
    "pin":            "#f0c040",   # pinned star
    "fav":            "#e05599",   # favourite heart
}

# ─────────────────────────────────────────────
#  GLOBAL STYLESHEET
# ─────────────────────────────────────────────

STYLESHEET = f"""
/* ── Base ── */
QMainWindow, QWidget {{
    background: {COLORS['bg_base']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'Inter', 'SF Pro Text', system-ui, sans-serif;
    font-size: 13px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {COLORS['scrollbar']};
    width: 6px; border: none; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['scrollbar_thumb']};
    border-radius: 3px; min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {COLORS['scrollbar']};
    height: 6px; border: none; border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['scrollbar_thumb']};
    border-radius: 3px; min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Search box ── */
QLineEdit {{
    background: {COLORS['bg_input']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 12px;
    selection-background-color: {COLORS['accent_dim']};
}}
QLineEdit:focus {{
    border-color: {COLORS['border_focus']};
    outline: none;
}}
QLineEdit::placeholder {{
    color: {COLORS['text_disabled']};
}}

/* ── Note list ── */
QListWidget {{
    background: {COLORS['bg_sidebar']};
    border: none;
    outline: none;
    padding: 4px 0;
}}
QListWidget::item {{
    padding: 0;
    border: none;
}}
QListWidget::item:selected {{
    background: transparent;
}}
QListWidget::item:hover {{
    background: transparent;
}}

/* ── Buttons ── */
QPushButton {{
    background: transparent;
    color: {COLORS['text_secondary']};
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}}
QPushButton:hover {{
    background: {COLORS['bg_item_hover']};
    color: {COLORS['text_primary']};
}}
QPushButton:pressed {{
    background: {COLORS['bg_item_sel']};
}}

/* ── Context menu ── */
QMenu {{
    background: #1e1e1e;
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
    color: {COLORS['text_primary']};
}}
QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {COLORS['bg_item_sel']};
    color: {COLORS['text_primary']};
}}
QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 8px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {COLORS['border']};
    width: 1px;
}}
QSplitter::handle:hover {{
    background: {COLORS['accent_dim']};
}}

/* ── Tooltip ── */
QToolTip {{
    background: #1e1e1e;
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ── Status bar ── */
QStatusBar {{
    background: {COLORS['bg_titlebar']};
    color: {COLORS['text_secondary']};
    font-size: 11px;
    border-top: 1px solid {COLORS['border']};
}}
"""

# ─────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────

class NoteStore:
    """Handles all note persistence (JSON metadata + plain text files)."""

    def __init__(self):
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        self._meta = self._load_meta()

    # ── Meta helpers ──────────────────────────

    def _load_meta(self) -> dict:
        if META_FILE.exists():
            try:
                return json.loads(META_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"notes": {}}

    def _save_meta(self):
        META_FILE.write_text(json.dumps(self._meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Note CRUD ─────────────────────────────

    def create_note(self, title: str = "Untitled") -> str:
        """Create a new note. Returns its unique ID."""
        nid   = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        fname = f"{nid}.md"
        (NOTES_DIR / fname).write_text("", encoding="utf-8")
        self._meta["notes"][nid] = {
            "title":    title,
            "file":     fname,
            "created":  datetime.utcnow().isoformat(),
            "modified": datetime.utcnow().isoformat(),
            "pinned":   False,
            "favorite": False,
            "tags":     [],
        }
        self._save_meta()
        return nid

    def delete_note(self, nid: str):
        """Delete a note and its file."""
        if nid not in self._meta["notes"]:
            return
        fname = self._meta["notes"][nid]["file"]
        path  = NOTES_DIR / fname
        if path.exists():
            path.unlink()
        del self._meta["notes"][nid]
        self._save_meta()

    def rename_note(self, nid: str, new_title: str):
        if nid in self._meta["notes"]:
            self._meta["notes"][nid]["title"]    = new_title
            self._meta["notes"][nid]["modified"] = datetime.utcnow().isoformat()
            self._save_meta()

    def get_content(self, nid: str) -> str:
        fname = self._meta["notes"][nid]["file"]
        path  = NOTES_DIR / fname
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def save_content(self, nid: str, content: str):
        fname = self._meta["notes"][nid]["file"]
        (NOTES_DIR / fname).write_text(content, encoding="utf-8")
        self._meta["notes"][nid]["modified"] = datetime.utcnow().isoformat()
        self._save_meta()

    def toggle_pin(self, nid: str):
        self._meta["notes"][nid]["pinned"] = not self._meta["notes"][nid].get("pinned", False)
        self._save_meta()

    def toggle_favorite(self, nid: str):
        self._meta["notes"][nid]["favorite"] = not self._meta["notes"][nid].get("favorite", False)
        self._save_meta()

    def all_notes(self) -> list[dict]:
        """Return all notes sorted: pinned first, then by modified date."""
        notes = [
            {"id": nid, **meta}
            for nid, meta in self._meta["notes"].items()
        ]
        notes.sort(key=lambda n: (not n.get("pinned", False), n["modified"]), reverse=False)
        notes.sort(key=lambda n: not n.get("pinned", False))
        return notes

    def export_markdown(self, nid: str, dest: Path):
        """Copy raw note file to destination."""
        fname = self._meta["notes"][nid]["file"]
        shutil.copy(NOTES_DIR / fname, dest)

# ─────────────────────────────────────────────
#  CUSTOM WIDGETS
# ─────────────────────────────────────────────

class NoteItemWidget(QWidget):
    """Custom row widget for the note list with title + meta line."""

    def __init__(self, note: dict, parent=None):
        super().__init__(parent)
        self.note_id = note["id"]
        self._selected = False

        self.setFixedHeight(58)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        # Top row: title + badges
        top = QHBoxLayout()
        top.setSpacing(6)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.set_title(note["title"])
        top.addWidget(self.title_label)

        # Pinned badge
        if note.get("pinned"):
            pin = QLabel("⚑")
            pin.setStyleSheet(f"color: {COLORS['pin']}; font-size: 11px;")
            top.addWidget(pin)
        # Favourite badge
        if note.get("favorite"):
            fav = QLabel("♥")
            fav.setStyleSheet(f"color: {COLORS['fav']}; font-size: 11px;")
            top.addWidget(fav)

        top.addStretch()
        layout.addLayout(top)

        # Meta line: date
        try:
            dt  = datetime.fromisoformat(note["modified"])
            ts  = dt.strftime("%b %d, %Y")
        except Exception:
            ts = ""
        meta = QLabel(ts)
        meta.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(meta)

        self._apply_style(False)

    def set_title(self, title: str):
        # Truncate very long titles
        t = title if len(title) <= 40 else title[:38] + "…"
        self.title_label.setText(t)
        self.title_label.setStyleSheet(f"color: {COLORS['text_primary']};")

    def set_selected(self, sel: bool):
        self._selected = sel
        self._apply_style(sel)

    def _apply_style(self, selected: bool):
        if selected:
            bg = COLORS['bg_item_sel']
            border = f"border-left: 2px solid {COLORS['accent']};"
        else:
            bg = "transparent"
            border = "border-left: 2px solid transparent;"
        self.setStyleSheet(f"""
            NoteItemWidget {{
                background: {bg};
                {border}
            }}
            NoteItemWidget:hover {{
                background: {COLORS['bg_item_hover']};
            }}
        """)

    def enterEvent(self, e):
        if not self._selected:
            self.setStyleSheet(f"""
                NoteItemWidget {{
                    background: {COLORS['bg_item_hover']};
                    border-left: 2px solid transparent;
                }}
            """)

    def leaveEvent(self, e):
        self._apply_style(self._selected)


class LineNumberArea(QWidget):
    """Gutter that displays line numbers beside the editor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint(event)


class CodeEditor(QTextEdit):
    """
    High-performance plain-text editor with optional line numbers.
    Uses monospace font and dark styling.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_numbers = True
        self._word_wrap    = True
        self._line_area    = LineNumberArea(self)

        # Font — JetBrains Mono or fallback chain
        font = QFont()
        font.setFamilies(["JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", "Courier New"])
        font.setPointSize(13)
        font.setFixedPitch(True)
        self.setFont(font)

        self.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_editor']};
                color: {COLORS['text_primary']};
                border: none;
                selection-background-color: {COLORS['accent_dim']};
                padding-left: 8px;
            }}
        """)

        opt = self.document().defaultTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WordWrap)
        self.document().setDefaultTextOption(opt)

        # Signals for line-number repaint
        self.document().blockCountChanged.connect(self._update_line_number_width)
        self.verticalScrollBar().valueChanged.connect(self._line_area.update)
        self.cursorPositionChanged.connect(self._line_area.update)

        self._update_line_number_width(0)

    # ── Line number geometry ───────────────────

    def line_number_area_width(self) -> int:
        if not self._line_numbers:
            return 0
        digits = max(3, len(str(self.document().blockCount())))
        fm     = QFontMetrics(self.font())
        return fm.horizontalAdvance("0") * digits + 24

    def _update_line_number_width(self, _):
        w = self.line_number_area_width()
        self.setViewportMargins(w, 0, 0, 0)
        self._line_area.setGeometry(QRect(0, 0, w, self.height()))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = self.line_number_area_width()
        self._line_area.setGeometry(QRect(0, 0, w, self.height()))

    def line_number_area_paint(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor(COLORS['bg_sidebar']))

        fm     = QFontMetrics(self.font())
        block  = self.document().begin()
        number = 1
        y_top  = self.viewport().geometry().top()
        scroll = self.verticalScrollBar().value()

        while block.isValid():
            pos    = self.document().documentLayout().blockBoundingRect(block)
            block_top = int(pos.top()) - scroll + y_top
            block_bot = block_top + int(pos.height())

            if block_top > event.rect().bottom():
                break

            if block_bot >= event.rect().top():
                painter.setPen(QColor(COLORS['text_disabled']))
                painter.setFont(self.font())
                w = self._line_area.width() - 10
                painter.drawText(
                    0, block_top, w, fm.height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number)
                )
            block  = block.next()
            number += 1

        painter.end()

    # ── Public toggles ─────────────────────────

    def toggle_line_numbers(self):
        self._line_numbers = not self._line_numbers
        self._update_line_number_width(0)
        self._line_area.setVisible(self._line_numbers)

    def toggle_word_wrap(self):
        self._word_wrap = not self._word_wrap
        opt = self.document().defaultTextOption()
        opt.setWrapMode(
            QTextOption.WrapMode.WordWrap if self._word_wrap
            else QTextOption.WrapMode.NoWrap
        )
        self.document().setDefaultTextOption(opt)

    # ── Tab → spaces ────────────────────────────

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            cursor.insertText("    ")  # 4 spaces
            return
        super().keyPressEvent(e)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

class Sidebar(QWidget):
    note_selected  = pyqtSignal(str)   # nid
    note_deleted   = pyqtSignal(str)   # nid
    note_renamed   = pyqtSignal(str, str)  # nid, new_title
    note_pinned    = pyqtSignal(str)
    note_favorited = pyqtSignal(str)
    create_note    = pyqtSignal()

    def __init__(self, store: NoteStore, parent=None):
        super().__init__(parent)
        self.store        = store
        self._current_id  = None
        self._all_notes   = []
        self._items_map   = {}   # nid → QListWidgetItem

        self.setMinimumWidth(160)
        self.setMaximumWidth(400)
        self.setStyleSheet(f"background: {COLORS['bg_sidebar']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Top bar ──────────────────────────────
        top_bar = QWidget()
        top_bar.setFixedHeight(46)
        top_bar.setStyleSheet(f"""
            background: {COLORS['bg_titlebar']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        tb_layout.setSpacing(4)

        lbl = QLabel("NOTES")
        lbl.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
        """)
        tb_layout.addWidget(lbl)
        tb_layout.addStretch()

        btn_new = QPushButton("+")
        btn_new.setToolTip("New note  (Ctrl+N)")
        btn_new.setFixedSize(26, 26)
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 16px;
                font-weight: 300;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
                border-color: {COLORS['accent']};
                background: {COLORS['bg_item_hover']};
            }}
        """)
        btn_new.clicked.connect(self.create_note.emit)
        tb_layout.addWidget(btn_new)
        layout.addWidget(top_bar)

        # ── Search ───────────────────────────────
        search_wrap = QWidget()
        search_wrap.setFixedHeight(44)
        search_wrap.setStyleSheet(f"""
            background: {COLORS['bg_sidebar']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        sw_layout = QHBoxLayout(search_wrap)
        sw_layout.setContentsMargins(10, 8, 10, 8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search notes…")
        self.search_box.textChanged.connect(self._filter_notes)
        sw_layout.addWidget(self.search_box)
        layout.addWidget(search_wrap)

        # ── Note list ────────────────────────────
        self.note_list = QListWidget()
        self.note_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.note_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.note_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self._context_menu)
        self.note_list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.note_list)

    # ── Populate / refresh ─────────────────────

    def refresh(self, select_id: str = None):
        self._all_notes = self.store.all_notes()
        self._render_list(self._all_notes, select_id or self._current_id)

    def _render_list(self, notes: list, select_id: str = None):
        self.note_list.blockSignals(True)
        self.note_list.clear()
        self._items_map.clear()

        for note in notes:
            item   = QListWidgetItem(self.note_list)
            widget = NoteItemWidget(note)
            item.setSizeHint(QSize(widget.sizeHint().width(), 58))
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            self.note_list.addItem(item)
            self.note_list.setItemWidget(item, widget)
            self._items_map[note["id"]] = item

        self.note_list.blockSignals(False)

        # Restore selection
        if select_id and select_id in self._items_map:
            item = self._items_map[select_id]
            self.note_list.setCurrentItem(item)
            self._set_selected_widget(select_id)
        elif notes:
            first_id = notes[0]["id"]
            self.note_list.setCurrentRow(0)
            self._set_selected_widget(first_id)
            self._current_id = first_id
            self.note_selected.emit(first_id)

    def _set_selected_widget(self, nid: str):
        for row in range(self.note_list.count()):
            item   = self.note_list.item(row)
            widget = self.note_list.itemWidget(item)
            if widget:
                widget.set_selected(item.data(Qt.ItemDataRole.UserRole) == nid)

    def _on_row_changed(self, row: int):
        if row < 0:
            return
        item = self.note_list.item(row)
        if item:
            nid = item.data(Qt.ItemDataRole.UserRole)
            self._current_id = nid
            self._set_selected_widget(nid)
            self.note_selected.emit(nid)

    def _filter_notes(self, query: str):
        q = query.lower().strip()
        if not q:
            filtered = self._all_notes
        else:
            filtered = [
                n for n in self._all_notes
                if q in n["title"].lower() or q in self.store.get_content(n["id"]).lower()
            ]
        self._render_list(filtered, self._current_id)

    # ── Context menu ───────────────────────────

    def _context_menu(self, pos: QPoint):
        item = self.note_list.itemAt(pos)
        if not item:
            return
        nid  = item.data(Qt.ItemDataRole.UserRole)
        note = next((n for n in self._all_notes if n["id"] == nid), None)
        if not note:
            return

        menu = QMenu(self)
        pin_label = "Unpin" if note.get("pinned") else "Pin to top"
        fav_label = "Unfavourite" if note.get("favorite") else "Add to favourites"

        act_rename = menu.addAction("Rename…")
        act_pin    = menu.addAction(pin_label)
        act_fav    = menu.addAction(fav_label)
        menu.addSeparator()
        act_export = menu.addAction("Export as Markdown…")
        menu.addSeparator()
        act_delete = menu.addAction("Delete")
        act_delete.setIcon(QIcon.fromTheme("edit-delete"))

        act_rename.triggered.connect(lambda: self._rename(nid, note["title"]))
        act_pin.triggered.connect(lambda: self.note_pinned.emit(nid))
        act_fav.triggered.connect(lambda: self.note_favorited.emit(nid))
        act_export.triggered.connect(lambda: self._export(nid, note["title"]))
        act_delete.triggered.connect(lambda: self._delete(nid, note["title"]))

        menu.exec(self.note_list.viewport().mapToGlobal(pos))

    def _rename(self, nid: str, current: str):
        title, ok = QInputDialog.getText(self, "Rename note", "New title:", text=current)
        if ok and title.strip():
            self.note_renamed.emit(nid, title.strip())

    def _delete(self, nid: str, title: str):
        ans = QMessageBox.question(
            self, "Delete note",
            f'Delete "{title}"?\nThis cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.note_deleted.emit(nid)

    def _export(self, nid: str, title: str):
        from PyQt6.QtWidgets import QFileDialog
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export note", f"{title}.md", "Markdown (*.md);;All files (*)"
        )
        if dest:
            self.store.export_markdown(nid, Path(dest))

    def focus_search(self):
        self.search_box.setFocus()
        self.search_box.selectAll()

    def current_id(self) -> str:
        return self._current_id

# ─────────────────────────────────────────────
#  EDITOR PANEL
# ─────────────────────────────────────────────

class EditorPanel(QWidget):
    """Right-hand editor: title bar + text edit area."""

    content_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_id   = None
        self._ignore_change = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Editor toolbar ───────────────────────
        self.toolbar = QWidget()
        self.toolbar.setFixedHeight(40)
        self.toolbar.setStyleSheet(f"""
            background: {COLORS['bg_toolbar']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        tb = QHBoxLayout(self.toolbar)
        tb.setContentsMargins(14, 0, 14, 0)
        tb.setSpacing(4)

        self.note_title = QLabel("No note open")
        self.note_title.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 12px;
            font-weight: 500;
        """)
        tb.addWidget(self.note_title)
        tb.addStretch()

        # Toggle buttons
        self.btn_ln = self._make_toggle_btn("LN", "Toggle line numbers")
        self.btn_ww = self._make_toggle_btn("WW", "Toggle word wrap")
        self.btn_focus = self._make_toggle_btn("⌖", "Focus mode")
        tb.addWidget(self.btn_ln)
        tb.addWidget(self.btn_ww)
        tb.addWidget(self.btn_focus)

        self.save_indicator = QLabel("")
        self.save_indicator.setFixedWidth(56)
        self.save_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.save_indicator.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px;")
        tb.addWidget(self.save_indicator)

        layout.addWidget(self.toolbar)

        # ── Editor ───────────────────────────────
        self.editor = CodeEditor()
        self.editor.setEnabled(False)
        layout.addWidget(self.editor)

        # ── Placeholder ──────────────────────────
        self.placeholder = QLabel("Select a note or press Ctrl+N to create one")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet(f"color: {COLORS['text_disabled']}; font-size: 14px;")
        layout.addWidget(self.placeholder)
        self.placeholder.hide()
        self.placeholder.show()
        self.editor.hide()

        # Autosave timer
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._do_autosave)

        self.editor.textChanged.connect(self._on_text_changed)
        self.btn_ln.clicked.connect(self._toggle_ln)
        self.btn_ww.clicked.connect(self._toggle_ww)
        self.btn_focus.clicked.connect(self._toggle_focus)

        self._ln_on    = True
        self._ww_on    = True
        self._focus_on = False
        self._store    = None

    def _make_toggle_btn(self, text: str, tip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setFixedSize(30, 26)
        btn.setCheckable(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_disabled']};
                border: 1px solid transparent;
                border-radius: 3px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            QPushButton:checked {{
                color: {COLORS['accent']};
                border-color: {COLORS['accent_dim']};
                background: rgba(75,142,255,0.08);
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
                border-color: {COLORS['border']};
            }}
        """)
        return btn

    def set_store(self, store: NoteStore):
        self._store = store

    def open_note(self, nid: str, title: str, content: str):
        self._current_id = nid
        self.note_title.setText(title)
        self.note_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 500;")
        self._ignore_change = True
        self.editor.setPlainText(content)
        self._ignore_change = False
        self.editor.setEnabled(True)
        self.placeholder.hide()
        self.editor.show()
        self.editor.setFocus()
        self.save_indicator.setText("")
        # Reset toggles
        self.btn_ln.setChecked(self._ln_on)
        self.btn_ww.setChecked(self._ww_on)

    def close_note(self):
        self._current_id = None
        self.editor.hide()
        self.editor.setEnabled(False)
        self.placeholder.show()
        self.note_title.setText("No note open")
        self.note_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")

    def update_title(self, title: str):
        self.note_title.setText(title)

    def _on_text_changed(self):
        if self._ignore_change:
            return
        self.save_indicator.setText("●")
        self.save_indicator.setStyleSheet(f"color: {COLORS['text_disabled']}; font-size: 11px;")
        self._autosave_timer.start(AUTOSAVE_MS)
        self.content_changed.emit()

    def _do_autosave(self):
        if self._store and self._current_id:
            self._store.save_content(self._current_id, self.editor.toPlainText())
            self.save_indicator.setText("✓ saved")
            self.save_indicator.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px;")
            QTimer.singleShot(2000, lambda: self.save_indicator.setText(""))

    def force_save(self):
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()
        self._do_autosave()

    def _toggle_ln(self):
        self._ln_on = not self._ln_on
        self.editor.toggle_line_numbers()

    def _toggle_ww(self):
        self._ww_on = not self._ww_on
        self.editor.toggle_word_wrap()

    def _toggle_focus(self):
        self._focus_on = not self._focus_on
        self.btn_focus.setChecked(self._focus_on)
        # In focus mode, hide sidebar (handled in main window via signal)
        # Emit to main window
        if hasattr(self.parent(), "set_focus_mode"):
            self.parent().set_focus_mode(self._focus_on)

    def get_stats(self) -> str:
        text  = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        lines = text.count("\n") + 1 if text else 0
        return f"Lines: {lines}   Words: {words}   Chars: {chars}"

# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    Top-level window wiring everything together.
    Keyboard shortcuts, menus, and state coordination live here.
    """

    def __init__(self):
        super().__init__()
        self.store = NoteStore()
        self._focus_mode = False

        self.setWindowTitle(APP_NAME)
        self.resize(1100, 680)
        self.setMinimumSize(600, 400)

        self._build_ui()
        self._setup_shortcuts()
        self._setup_menu()
        self._setup_statusbar()

        # Load initial notes
        self.sidebar.refresh()
        self._update_status()

    # ── UI assembly ────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Title bar (app name + global count) ──
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet(f"""
            background: {COLORS['bg_titlebar']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(14, 0, 14, 0)

        app_label = QLabel(f"<b>{APP_NAME}</b>")
        app_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px;")
        tb_layout.addWidget(app_label)

        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {COLORS['text_disabled']}; font-size: 11px;")
        tb_layout.addWidget(self.count_label)
        tb_layout.addStretch()

        main_layout.addWidget(title_bar)

        # ── Splitter: sidebar | editor ────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)

        # Sidebar
        self.sidebar = Sidebar(self.store)
        self.sidebar.note_selected.connect(self._on_note_selected)
        self.sidebar.note_deleted.connect(self._on_note_deleted)
        self.sidebar.note_renamed.connect(self._on_note_renamed)
        self.sidebar.note_pinned.connect(self._on_note_pinned)
        self.sidebar.note_favorited.connect(self._on_note_favorited)
        self.sidebar.create_note.connect(self._new_note)

        # Editor
        self.editor_panel = EditorPanel()
        self.editor_panel.set_store(self.store)
        self.editor_panel.content_changed.connect(self._update_status)

        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.editor_panel)
        self.splitter.setSizes([240, 860])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)

    def _setup_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._stat_label = QLabel("")
        self._stat_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.status.addPermanentWidget(self._stat_label)

    def _update_status(self):
        notes = self.store.all_notes()
        self.count_label.setText(f"  {len(notes)} notes")
        self._stat_label.setText(self.editor_panel.get_stats())

    # ── Keyboard shortcuts ─────────────────────

    def _setup_shortcuts(self):
        shortcuts = {
            "Ctrl+N": self._new_note,
            "Ctrl+S": self._force_save,
            "Ctrl+F": self.sidebar.focus_search,
            "Ctrl+W": self._close_current_note,
            "Ctrl+\\": self._toggle_sidebar,
            "Escape": self._escape_pressed,
        }
        for key, slot in shortcuts.items():
            action = QAction(self)
            action.setShortcut(QKeySequence(key))
            action.triggered.connect(slot)
            self.addAction(action)

    # ── Menu bar ───────────────────────────────

    def _setup_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background: {COLORS['bg_titlebar']};
                color: {COLORS['text_secondary']};
                border-bottom: 1px solid {COLORS['border']};
                font-size: 12px;
            }}
            QMenuBar::item {{
                padding: 4px 10px;
                background: transparent;
            }}
            QMenuBar::item:selected {{
                background: {COLORS['bg_item_hover']};
                color: {COLORS['text_primary']};
            }}
        """)

        # File
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Note\tCtrl+N", self._new_note)
        file_menu.addAction("Save\tCtrl+S", self._force_save)
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close)

        # View
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Toggle Sidebar\tCtrl+\\", self._toggle_sidebar)
        view_menu.addAction("Toggle Focus Mode", self._toggle_focus)
        view_menu.addSeparator()
        view_menu.addAction("Open Notes Folder", self._open_notes_folder)

        # Help
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self._show_about)

    # ── Slots ──────────────────────────────────

    def _new_note(self):
        nid = self.store.create_note("Untitled")
        self.sidebar.refresh(select_id=nid)
        # Open the new note and immediately let user rename via inline title
        self._on_note_selected(nid)
        self._update_status()
        # Prompt for a name
        QTimer.singleShot(50, lambda: self._inline_rename(nid))

    def _inline_rename(self, nid: str):
        title, ok = QInputDialog.getText(self, "New note", "Note title:", text="Untitled")
        if ok and title.strip():
            self.store.rename_note(nid, title.strip())
            self.sidebar.refresh(select_id=nid)
            self.editor_panel.update_title(title.strip())

    def _force_save(self):
        self.editor_panel.force_save()

    def _close_current_note(self):
        self.editor_panel.close_note()

    def _toggle_sidebar(self):
        visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not visible)

    def _toggle_focus(self):
        self.set_focus_mode(not self._focus_mode)

    def set_focus_mode(self, on: bool):
        self._focus_mode = on
        self.sidebar.setVisible(not on)
        self.menuBar().setVisible(not on)
        self.statusBar().setVisible(not on)
        self.editor_panel.toolbar.setVisible(not on)

    def _escape_pressed(self):
        if self._focus_mode:
            self.set_focus_mode(False)
        elif not self.sidebar.search_box.text():
            self.editor_panel.editor.setFocus()
        else:
            self.sidebar.search_box.clear()

    def _on_note_selected(self, nid: str):
        notes = self.store.all_notes()
        note  = next((n for n in notes if n["id"] == nid), None)
        if note:
            content = self.store.get_content(nid)
            self.editor_panel.open_note(nid, note["title"], content)
            self._update_status()

    def _on_note_deleted(self, nid: str):
        current = self.sidebar.current_id()
        self.store.delete_note(nid)
        if nid == current:
            self.editor_panel.close_note()
        self.sidebar.refresh()
        self._update_status()

    def _on_note_renamed(self, nid: str, new_title: str):
        self.store.rename_note(nid, new_title)
        self.sidebar.refresh(select_id=nid)
        if nid == self.sidebar.current_id():
            self.editor_panel.update_title(new_title)

    def _on_note_pinned(self, nid: str):
        self.store.toggle_pin(nid)
        self.sidebar.refresh(select_id=nid)

    def _on_note_favorited(self, nid: str):
        self.store.toggle_favorite(nid)
        self.sidebar.refresh(select_id=nid)

    def _open_notes_folder(self):
        import subprocess, platform
        path = str(NOTES_DIR)
        if platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        elif platform.system() == "Windows":
            subprocess.Popen(["explorer", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _show_about(self):
        QMessageBox.information(
            self, f"About {APP_NAME}",
            f"<b>{APP_NAME}</b> v{APP_VERSION}<br><br>"
            "A fast, minimalist, local-first note app for developers.<br><br>"
            f"Notes stored at:<br><code>{NOTES_DIR}</code>"
        )

    def closeEvent(self, e):
        self.editor_panel.force_save()
        super().closeEvent(e)

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Qt Dark palette (base layer; stylesheet overrides most things)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(COLORS["bg_base"]))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(COLORS["bg_editor"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(COLORS["bg_sidebar"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button,          QColor(COLORS["bg_toolbar"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(COLORS["accent_dim"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(COLORS["text_primary"]))
    app.setPalette(palette)

    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
