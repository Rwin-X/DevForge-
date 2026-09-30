"""Vault tab: lists saved conversions from core/vault.py, with restore
and delete actions per entry."""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.models import VaultEntry
from core.vault import load_vault, save_vault


class VaultRow(QWidget):
    restore_clicked = pyqtSignal(VaultEntry)
    delete_clicked = pyqtSignal(str)  # uid

    def __init__(self, entry: VaultEntry, parent: QWidget | None = None):
        super().__init__(parent)
        self._entry = entry

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)

        text_col = QVBoxLayout()
        meta = QLabel(
            f"{entry.algorithm_name} · {entry.direction.value.capitalize()} · "
            f"{entry.timestamp.strftime('%b %d, %H:%M')}",
            self,
        )
        meta.setObjectName("tertiaryLabel")
        text_col.addWidget(meta)

        in_line = QLabel(entry.input_preview, self)
        in_line.setObjectName("tertiaryLabel")
        text_col.addWidget(in_line)

        out_line = QLabel(f"→ {entry.output_preview}", self)
        out_line.setObjectName("secondaryLabel")
        text_col.addWidget(out_line)

        layout.addLayout(text_col, 1)

        restore_btn = QPushButton("Restore", self)
        restore_btn.setObjectName("ghostAction")
        restore_btn.clicked.connect(lambda: self.restore_clicked.emit(self._entry))
        layout.addWidget(restore_btn)

        delete_btn = QPushButton("Delete", self)
        delete_btn.setObjectName("ghostAction")
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self._entry.uid))
        layout.addWidget(delete_btn)


class VaultTab(QWidget):
    restore_requested = pyqtSignal(str, object, str, str, str)  # algo_id, Direction, input, key1, key2

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._entries: List[VaultEntry] = load_vault()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        intro = QLabel(
            "Conversions saved during this session, persisted to a local config file. "
            "Nothing leaves this machine.",
            self,
        )
        intro.setObjectName("secondaryLabel")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        actions_row = QHBoxLayout()
        self.save_btn = QPushButton("+ Save current result", self)
        self.save_btn.clicked.connect(self._save_requested)
        actions_row.addWidget(self.save_btn)
        actions_row.addStretch()
        clear_btn = QPushButton("Clear vault", self)
        clear_btn.setObjectName("ghostAction")
        clear_btn.clicked.connect(self._clear_vault)
        actions_row.addWidget(clear_btn)
        outer.addLayout(actions_row)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()
        self.scroll.setWidget(self._list_container)
        outer.addWidget(self.scroll, 1)

        self.on_save_requested = None  # set by MainWindow: callable returning a VaultEntry or None

        self._render()

    def _render(self) -> None:
        while self._list_layout.count():
            child = self._list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self._entries:
            empty = QLabel("Nothing saved yet.", self)
            empty.setObjectName("tertiaryLabel")
            self._list_layout.addWidget(empty)
            self._list_layout.addStretch()
            return

        for entry in reversed(self._entries):
            row = VaultRow(entry, self)
            row.restore_clicked.connect(self._on_restore)
            row.delete_clicked.connect(self._on_delete)
            self._list_layout.addWidget(row)
        self._list_layout.addStretch()

    def _save_requested(self) -> None:
        if self.on_save_requested is None:
            return
        entry = self.on_save_requested()
        if entry is not None:
            self._entries.append(entry)
            save_vault(self._entries)
            self._render()

    def _on_restore(self, entry: VaultEntry) -> None:
        self.restore_requested.emit(
            entry.algorithm_id, entry.direction, entry.input_preview, entry.key1, entry.key2
        )

    def _on_delete(self, uid: str) -> None:
        self._entries = [e for e in self._entries if e.uid != uid]
        save_vault(self._entries)
        self._render()

    def _clear_vault(self) -> None:
        self._entries = []
        save_vault(self._entries)
        self._render()

    def refresh(self) -> None:
        self._entries = load_vault()
        self._render()
