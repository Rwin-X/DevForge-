from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..backend import Backend
from ..widgets.common import (
    NoticeLabel, category_label, fmt_when, make_header, make_table, selected_rows, text_item,
)
from .. import style

KIND_LABELS = {
    "trash_auto": "Auto trash",
    "trash_review": "Trashed from review",
    "trash_manual": "Manual trash",
    "trash_blocked": "Blocked sender",
}


class ActivityPage(QWidget):
    """Log of everything the app moved to Trash, with one-click restore."""

    def __init__(self, backend: Backend):
        super().__init__()
        self.backend = backend
        self._actions: list[dict] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(10)
        layout.addWidget(make_header("Activity", "Every deletion is logged and can be restored from Trash"))

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.restore_btn = QPushButton("Restore selected")
        self.restore_btn.setObjectName("primaryAction")
        self.restore_btn.clicked.connect(self._restore)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        bar.addWidget(self.restore_btn)
        bar.addStretch()
        bar.addWidget(self.refresh_btn)
        layout.addLayout(bar)

        self.notice = NoticeLabel()
        layout.addWidget(self.notice)
        self.table = make_table(
            ["Time", "Action", "From", "Subject", "Type", "Score", "State"],
            [120, 150, 220, 0, 110, 55, 90], stretch=3,
        )
        self.table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.table, 1)
        self._update_buttons()

    def on_activated(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.backend.run(self.backend.service.activity, self._on_actions, self._on_error)

    def _on_actions(self, actions: list[dict]) -> None:
        self._actions = actions
        self.table.setRowCount(0)
        for action in actions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            restored = bool(action["undone"])
            self.table.setItem(row, 0, text_item(fmt_when(action["ts"])))
            self.table.setItem(row, 1, text_item(KIND_LABELS.get(action["kind"], action["kind"])))
            self.table.setItem(row, 2, text_item(action["sender"]))
            self.table.setItem(row, 3, text_item(action["subject"]))
            self.table.setItem(row, 4, text_item(category_label(action["category"])))
            self.table.setItem(row, 5, text_item(f"{action['score']:.2f}" if action["score"] else ""))
            self.table.setItem(
                row, 6,
                text_item("Restored" if restored else "In Trash", color=style.TEXT_TERTIARY if restored else None),
            )
        if not actions:
            self.notice.info("No activity yet.")
        else:
            self.notice.clear_notice()
        self._update_buttons()

    def _on_error(self, message: str) -> None:
        self.notice.error(message)

    def _selected(self) -> list[dict]:
        return [self._actions[r] for r in selected_rows(self.table) if not self._actions[r]["undone"]]

    def _update_buttons(self) -> None:
        self.restore_btn.setEnabled(bool(self._selected()))

    def _restore(self) -> None:
        targets = self._selected()
        if not targets:
            return

        def work() -> int:
            service = self.backend.service
            restored = 0
            for action in targets:
                service.restore(action["id"])
                restored += 1
            return restored

        def done(count: int) -> None:
            self.notice.ok(f"Restored {count} message(s) to their original folder")
            self.backend.data_changed.emit()

        self.backend.run(work, done, self._on_error)
