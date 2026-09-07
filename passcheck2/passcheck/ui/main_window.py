"""Main window for passcheck.

Password scoring runs directly on the main thread: score_password() is
a pure, fast (sub-millisecond) computation with no I/O, so it does not
need a worker thread under this skill's threading guidance (only
operations that take roughly 50ms or more need to move off the main
thread).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from passcheck.core.strength import LEVEL_LABELS, score_password
from passcheck.ui.style import build_stylesheet
from passcheck.ui.widgets.strength_meter import StrengthMeter
from passcheck.ui.widgets.title_bar import TitleBar

WINDOW_WIDTH = 480
WINDOW_HEIGHT = 520


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        central = QWidget()
        central.setObjectName("rootContainer")
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.title_bar = TitleBar(self, "Password Strength Checker")
        root_layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        content_layout.addWidget(self._build_input_row())
        content_layout.addWidget(self._build_meter_row())
        content_layout.addWidget(self._build_detail_row())
        content_layout.addStretch()

        root_layout.addWidget(content)
        self.setCentralWidget(central)

        self._refresh("")

    def _build_input_row(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel("Enter a password to check")
        label.setObjectName("secondaryLabel")
        layout.addWidget(label)

        input_row = QWidget()
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Type a password...")
        self.password_input.textChanged.connect(self._refresh)
        input_layout.addWidget(self.password_input)

        self.visibility_btn = QPushButton("Show")
        self.visibility_btn.setFixedWidth(64)
        self.visibility_btn.clicked.connect(self._toggle_visibility)
        input_layout.addWidget(self.visibility_btn)

        layout.addWidget(input_row)
        return container

    def _build_meter_row(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.meter = StrengthMeter()
        layout.addWidget(self.meter)

        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)

        self.level_label = QLabel("")
        self.level_label.setObjectName("monoLabel")
        status_layout.addWidget(self.level_label)

        status_layout.addStretch()

        self.crack_time_label = QLabel("")
        self.crack_time_label.setObjectName("tertiaryLabel")
        status_layout.addWidget(self.crack_time_label)

        layout.addWidget(status_row)
        return container

    def _build_detail_row(self) -> QWidget:
        container = QWidget()
        container.setObjectName("elevatedPanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        issues_label = QLabel("Issues")
        issues_label.setObjectName("tertiaryLabel")
        layout.addWidget(issues_label)

        self.issues_list = QListWidget()
        self.issues_list.setFixedHeight(90)
        layout.addWidget(self.issues_list)

        suggestions_label = QLabel("Suggestions")
        suggestions_label.setObjectName("tertiaryLabel")
        layout.addWidget(suggestions_label)

        self.suggestions_list = QListWidget()
        self.suggestions_list.setFixedHeight(90)
        layout.addWidget(self.suggestions_list)

        return container

    def _toggle_visibility(self) -> None:
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.visibility_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.visibility_btn.setText("Show")

    def _refresh(self, password: str) -> None:
        result = score_password(password)

        self.meter.set_level(result.level.value)
        self.level_label.setText(f"{LEVEL_LABELS[result.level]}  ({result.score}/100)")

        if password:
            self.crack_time_label.setText(f"Est. crack time: {result.crack_time_estimate}")
        else:
            self.crack_time_label.setText("")

        self.issues_list.clear()
        for issue in result.issues:
            item = QListWidgetItem(issue)
            item.setForeground(_issue_color())
            self.issues_list.addItem(item)
        if not result.issues and password:
            self.issues_list.addItem(QListWidgetItem("No issues found."))

        self.suggestions_list.clear()
        for suggestion in result.suggestions:
            self.suggestions_list.addItem(QListWidgetItem(suggestion))


def _issue_color():
    from PyQt6.QtGui import QColor

    from passcheck.ui.style import DANGER

    return QColor(DANGER)


def apply_stylesheet(app) -> None:
    app.setStyleSheet(build_stylesheet())
