from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..backend import Backend
from ..widgets.common import (
    NoticeLabel, category_label, fmt_when, make_header, make_table, selected_rows, text_item,
)


class ReviewPage(QWidget):
    """Messages the bot was not confident enough to trash on its own."""

    def __init__(self, backend: Backend):
        super().__init__()
        self.backend = backend
        self._items: list[dict] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(10)
        layout.addWidget(make_header("Review", "Messages flagged but not deleted. You decide."))

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.trash_btn = QPushButton("Trash selected")
        self.trash_btn.setObjectName("destructiveAction")
        self.trash_btn.clicked.connect(lambda: self._resolve("trash"))
        self.keep_btn = QPushButton("Keep selected")
        self.keep_btn.clicked.connect(lambda: self._resolve("keep"))
        self.trust_btn = QPushButton("Keep and trust sender")
        self.trust_btn.clicked.connect(lambda: self._resolve("trust"))
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        for button in (self.trash_btn, self.keep_btn, self.trust_btn):
            bar.addWidget(button)
        bar.addStretch()
        bar.addWidget(self.refresh_btn)
        layout.addLayout(bar)

        self.notice = NoticeLabel()
        layout.addWidget(self.notice)
        self.table = make_table(
            ["Date", "From", "Subject", "Type", "Score", "Why"], [140, 220, 260, 120, 55, 0], stretch=5
        )
        self.table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.table, 1)
        self._update_buttons()

    def on_activated(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.backend.run(self.backend.service.review_items, self._on_items, self._on_error)

    def _on_items(self, items: list[dict]) -> None:
        self._items = items
        self.table.setRowCount(0)
        for item in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, text_item(fmt_when(item["date_utc"])))
            self.table.setItem(row, 1, text_item(item["sender"]))
            self.table.setItem(row, 2, text_item(item["subject"]))
            self.table.setItem(row, 3, text_item(category_label(item["category"])))
            self.table.setItem(row, 4, text_item(f"{item['score']:.2f}"))
            self.table.setItem(row, 5, text_item("; ".join(item["reasons"])))
        if not items:
            self.notice.info("Nothing to review.")
        else:
            self.notice.clear_notice()
        self._update_buttons()

    def _on_error(self, message: str) -> None:
        self.notice.error(message)

    def _selected(self) -> list[dict]:
        return [self._items[r] for r in selected_rows(self.table)]

    def _update_buttons(self) -> None:
        has = bool(self._selected())
        for button in (self.trash_btn, self.keep_btn, self.trust_btn):
            button.setEnabled(has)

    def _resolve(self, action: str) -> None:
        items = self._selected()
        if not items:
            return
        verb = {"trash": "Trashed", "keep": "Kept", "trust": "Kept and trusted"}[action]

        def done(count: int) -> None:
            self.notice.ok(f"{verb} {count} message(s)")
            if action == "trust":
                self.backend.config_changed.emit()
            self.backend.data_changed.emit()

        self.backend.run(lambda: self.backend.service.resolve_review(items, action), done, self._on_error)
