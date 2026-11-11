from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ..backend import Backend
from ..widgets.common import (
    NoticeLabel, StatCard, category_phrase, fmt_when, make_header, make_table, text_item,
)
from .. import style

MAX_ROWS = 150


def result_text(status: str, category: str) -> str:
    label = category_phrase(category)
    if status == "trashed":
        return f"Trashed ({label})"
    if status == "review":
        return f"Review ({label})" if label else "Review"
    if status == "restored":
        return "Restored"
    return "Kept"


class DashboardPage(QWidget):
    review_count_changed = pyqtSignal(int)

    def __init__(self, backend: Backend):
        super().__init__()
        self.backend = backend
        self._build()
        backend.scan_started.connect(self._on_scan_started)
        backend.scan_progress.connect(self._on_progress)
        backend.scan_item.connect(self._on_item)
        backend.scan_finished.connect(self._on_finished)
        backend.scan_failed.connect(self._on_failed)
        backend.bot_state_changed.connect(self._on_bot_state)
        backend.config_changed.connect(self._update_banner)
        self._update_banner()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)
        layout.addWidget(make_header("Dashboard", "Automatic cleanup of advertisements and AI-written mail"))

        self.banner = QLabel("")
        self.banner.setObjectName("noticeLabel")
        self.banner.setWordWrap(True)
        layout.addWidget(self.banner)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_scanned = StatCard("MESSAGES SCANNED")
        self.card_ads = StatCard("ADVERTISEMENTS TRASHED")
        self.card_ai = StatCard("AI-WRITTEN TRASHED")
        self.card_review = StatCard("WAITING FOR REVIEW")
        for card in (self.card_scanned, self.card_ads, self.card_ai, self.card_review):
            cards.addWidget(card)
        layout.addLayout(cards)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.scan_btn = QPushButton("Scan now")
        self.scan_btn.setObjectName("primaryAction")
        self.scan_btn.clicked.connect(self._scan_clicked)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.backend.cancel_scan)
        self.cancel_btn.hide()
        self.bot_btn = QPushButton("Start bot")
        self.bot_btn.setCheckable(True)
        self.bot_btn.toggled.connect(self.backend.set_bot_enabled)
        controls.addWidget(self.scan_btn)
        controls.addWidget(self.cancel_btn)
        controls.addWidget(self.bot_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.notice = NoticeLabel()
        layout.addWidget(self.notice)

        recent = QLabel("Recent decisions")
        recent.setObjectName("secondaryLabel")
        layout.addWidget(recent)
        self.table = make_table(["Time", "From", "Subject", "Result", "Score"], [145, 250, 0, 175, 60], stretch=2)
        layout.addWidget(self.table, 1)

    # ---- data --------------------------------------------------------

    def refresh(self) -> None:
        self.backend.run(self._load, self._apply_data, self._on_load_error)

    def _load(self):
        service = self.backend.service
        return service.stats(), service.recent_items(60)

    def _apply_data(self, data) -> None:
        stats, recent = data
        self.card_scanned.set_value(stats["scanned"])
        self.card_ads.set_value(stats["ads_trashed"])
        self.card_ai.set_value(stats["ai_trashed"])
        self.card_review.set_value(stats["review"])
        self.review_count_changed.emit(stats["review"])
        if not self.backend.scanning:
            self.table.setRowCount(0)
            for item in recent:
                self._add_row(
                    fmt_when(item["scanned_at"]), item["sender"], item["subject"],
                    result_text(item["status"], item["category"]),
                    item["score"] if item["category"] else 0.0, item["status"], append=True,
                )

    def _on_load_error(self, message: str) -> None:
        self.notice.error(message)

    def _update_banner(self) -> None:
        policy = self.backend.ctx.config.policy
        if policy.dry_run:
            self.banner.setText(
                "Dry run is on: nothing is deleted. Messages that would be trashed go to the Review page. "
                "Turn it off in Settings when the results look right."
            )
        else:
            self.banner.setText(
                "Live mode: confident matches are moved to Trash and can be restored from the Activity page."
            )
        self.banner.setVisible(True)

    # ---- table -------------------------------------------------------

    def _add_row(self, when, sender, subject, result, score, status, append=False) -> None:
        row = self.table.rowCount() if append else 0
        self.table.insertRow(row)
        color = style.ACCENT if status == "trashed" else (style.TEXT_SECONDARY if status == "kept" else None)
        self.table.setItem(row, 0, text_item(when))
        self.table.setItem(row, 1, text_item(sender))
        self.table.setItem(row, 2, text_item(subject))
        self.table.setItem(row, 3, text_item(result, color=color))
        self.table.setItem(row, 4, text_item(f"{score:.2f}" if score else ""))
        while self.table.rowCount() > MAX_ROWS:
            self.table.removeRow(self.table.rowCount() - 1)

    # ---- scan signals --------------------------------------------------

    def _scan_clicked(self) -> None:
        if not self.backend.start_scan():
            self.notice.info("A scan is already running.")

    def _on_scan_started(self) -> None:
        self.scan_btn.setEnabled(False)
        self.cancel_btn.show()
        self.progress.setRange(0, 0)
        self.progress.show()
        self.notice.info("Connecting to the mail server")

    def _on_progress(self, done: int, total: int, message: str) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
        self.notice.info(message)

    def _on_item(self, item) -> None:
        self._add_row(
            fmt_when(item.when) or "", item.sender, item.subject,
            result_text(item.decision, item.category), item.score if item.category else 0.0, item.decision,
        )

    def _reset_controls(self) -> None:
        self.scan_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress.hide()

    def _on_finished(self, summary) -> None:
        self._reset_controls()
        self.notice.ok(summary.describe())
        for err in summary.errors[:2]:
            self.notice.error(err)

    def _on_failed(self, message: str) -> None:
        self._reset_controls()
        self.notice.error(message)

    def _on_bot_state(self, enabled: bool) -> None:
        self.bot_btn.blockSignals(True)
        self.bot_btn.setChecked(enabled)
        self.bot_btn.setText("Stop bot" if enabled else "Start bot")
        self.bot_btn.blockSignals(False)
