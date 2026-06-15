"""
HashForge — HistoryPanel widget.
Searchable list of past hash operations.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtGui import QGuiApplication

from hashforge.core.history import HistoryManager


class HistoryEntryRow(QWidget):
    """Single history row."""

    clicked = Signal(dict)
    removed = Signal(int)   # index

    def __init__(self, entry: dict, index: int, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.index = index
        self.setObjectName("historyRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.setContentsMargins(0, 0, 0, 0)

        name = self.entry["file"]["name"]
        ts   = self.entry.get("timestamp", "")[:16].replace("T", "  ")

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            "font-weight: 600; font-size: 13px; color: #0F172A; background: transparent;"
        )

        sha256 = self.entry["hashes"].get("SHA256", "")[:24]
        meta_lbl = QLabel(f"{ts}   SHA256: {sha256}…")
        meta_lbl.setStyleSheet(
            "font-size: 11px; color: #94A3B8; background: transparent;"
        )
        meta_lbl.setProperty("role", "label")

        info.addWidget(name_lbl)
        info.addWidget(meta_lbl)

        del_btn = QPushButton("×")
        del_btn.setProperty("variant", "icon")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("Remove from history")
        del_btn.clicked.connect(lambda: self.removed.emit(self.index))

        layout.addLayout(info)
        layout.addStretch()
        layout.addWidget(del_btn)

        self.setStyleSheet("""
            #historyRow {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            #historyRow:hover {
                border-color: #93C5FD;
                background: #EFF6FF;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entry)


class HistoryPanel(QWidget):
    """Full history panel with search bar and entry list."""

    entry_selected = Signal(dict)

    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header bar ──
        header = QWidget()
        header.setObjectName("historyHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 12, 12)
        header_layout.setSpacing(8)

        title = QLabel("History")
        title.setStyleSheet("font-weight: 700; font-size: 15px; color: #0F172A; background: transparent;")

        self._count_label = QLabel("0 entries")
        self._count_label.setStyleSheet("font-size: 11px; color: #94A3B8; background: transparent;")

        clear_btn = QPushButton("Clear all")
        clear_btn.setProperty("variant", "ghost")
        clear_btn.setFixedHeight(30)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_all)

        header_layout.addWidget(title)
        header_layout.addWidget(self._count_label)
        header_layout.addStretch()
        header_layout.addWidget(clear_btn)

        # ── Search ──
        search_wrap = QWidget()
        search_wrap.setObjectName("searchWrap")
        sw_layout = QHBoxLayout(search_wrap)
        sw_layout.setContentsMargins(12, 8, 12, 8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by file name or hash…")
        self._search.setMinimumHeight(34)
        self._search.textChanged.connect(self._on_search)

        sw_layout.addWidget(self._search)

        # ── Scroll list ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(12, 8, 12, 12)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)

        self._empty_label = QLabel("No history yet.\nHash a file to get started.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #94A3B8; font-size: 13px; background: transparent;"
        )

        layout.addWidget(header)
        layout.addWidget(search_wrap)
        layout.addWidget(self._scroll)

        self.refresh()

    def refresh(self):
        q = self._search.text().strip() if hasattr(self, '_search') else ""
        entries = self.hm.search(q) if q else self.hm.all()
        self._render(entries)

    def _render(self, entries: list):
        # Clear existing rows
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        count = self.hm.count()
        self._count_label.setText(f"{count} {'entry' if count == 1 else 'entries'}")

        if not entries:
            self._list_layout.insertWidget(0, self._empty_label)
            self._empty_label.setVisible(True)
            return

        self._empty_label.setVisible(False)
        for i, entry in enumerate(entries):
            row = HistoryEntryRow(entry, i)
            row.clicked.connect(self.entry_selected.emit)
            row.removed.connect(self._remove)
            self._list_layout.insertWidget(i, row)

    def _on_search(self, text: str):
        self.refresh()

    def _remove(self, index: int):
        self.hm.remove(index)
        self.refresh()

    def _clear_all(self):
        self.hm.clear()
        self.refresh()
