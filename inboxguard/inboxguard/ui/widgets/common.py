"""Small reusable widgets and helpers shared by the pages."""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QFrame, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)


def fmt_when(value) -> str:
    """Format a datetime or ISO string in local time; empty on failure."""
    if not value:
        return ""
    try:
        moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        if moment.tzinfo is not None:
            moment = moment.astimezone()
        return moment.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return ""


CATEGORY_LABELS = {"ad": "Advertisement", "ai": "AI-written", "": ""}


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def category_phrase(category: str) -> str:
    """Lowercase-friendly phrase for use inside a sentence or parentheses."""
    return {"ad": "advertisement", "ai": "AI-written"}.get(category, category)


def make_table(headers: list[str], widths: list[int], stretch: int) -> QTableWidget:
    """Read-only, row-selecting table. widths[i] is ignored for the stretch column."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setStretchLastSection(False)
    for col, width in enumerate(widths):
        if col == stretch:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            table.setColumnWidth(col, width)
    return table


def text_item(text: str, data=None, bold: bool = False, color: str | None = None) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if data is not None:
        item.setData(Qt.ItemDataRole.UserRole, data)
    if bold:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    if color:
        item.setForeground(QColor(color))
    item.setToolTip(text)
    return item


def selected_rows(table: QTableWidget) -> list[int]:
    return sorted({index.row() for index in table.selectionModel().selectedRows()})


class StatCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("elevatedPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        self._title = QLabel(title)
        self._title.setObjectName("statTitle")
        self._value = QLabel("0")
        self._value.setObjectName("statValue")
        layout.addWidget(self._title)
        layout.addWidget(self._value)

    def set_value(self, value: int) -> None:
        self._value.setText(f"{value:,}")


class NoticeLabel(QLabel):
    """One-line status text that can switch between neutral, ok and error tones."""

    def __init__(self):
        super().__init__("")
        self.setObjectName("noticeLabel")
        self.setWordWrap(True)
        self.hide()

    def _show(self, text: str, level: str) -> None:
        self.setProperty("level", level)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(text)
        self.setVisible(bool(text))

    def info(self, text: str) -> None:
        self._show(text, "info")

    def ok(self, text: str) -> None:
        self._show(text, "ok")

    def error(self, text: str) -> None:
        self._show(text, "error")

    def clear_notice(self) -> None:
        self._show("", "info")


def make_header(title: str, subtitle: str = "") -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    layout.addWidget(heading)
    if subtitle:
        sub = QLabel(subtitle)
        sub.setObjectName("secondaryLabel")
        layout.addWidget(sub)
    return box
