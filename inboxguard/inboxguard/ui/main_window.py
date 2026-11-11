"""Frameless main window: title bar, sidebar navigation, pages, status strip."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QSizeGrip,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .backend import Backend
from .pages.activity_page import ActivityPage
from .pages.dashboard import DashboardPage
from .pages.mailbox_page import MailboxPage
from .pages.review_page import ReviewPage
from .pages.settings_page import SettingsPage
from .widgets.title_bar import TitleBar


class MainWindow(QMainWindow):
    def __init__(self, backend: Backend):
        super().__init__()
        self.backend = backend
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("InboxGuard")
        self.setMinimumSize(1000, 640)
        self.resize(1200, 760)

        central = QWidget()
        central.setObjectName("rootContainer")
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        root = QVBoxLayout(central)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)
        root.addWidget(TitleBar(self, "InboxGuard"))

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        self.dashboard = DashboardPage(backend)
        self.mailbox = MailboxPage(backend)
        self.review = ReviewPage(backend)
        self.activity = ActivityPage(backend)
        self.settings = SettingsPage(backend)
        self.pages = [self.dashboard, self.mailbox, self.review, self.activity, self.settings]
        self.stack = QStackedWidget()
        for page in self.pages:
            self.stack.addWidget(page)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_status_strip())
        self.setCentralWidget(central)

        self.dashboard.review_count_changed.connect(self._set_review_count)
        backend.status.connect(self.status_text.setText)
        backend.bot_state_changed.connect(self._on_bot_state)
        backend.data_changed.connect(self._on_data_changed)
        self._show_page(0)
        self.dashboard.refresh()

    def _build_sidebar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("sidebar")
        bar.setFixedWidth(200)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 18, 0, 14)
        layout.setSpacing(2)
        brand = QLabel("INBOXGUARD")
        brand.setObjectName("brandLabel")
        brand.setContentsMargins(20, 0, 0, 14)
        layout.addWidget(brand)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []
        for index, name in enumerate(("Dashboard", "Mailbox", "Review", "Activity", "Settings")):
            button = QPushButton(name)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, i=index: self._show_page(i))
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()
        self.bot_label = QLabel("Bot: stopped")
        self.bot_label.setObjectName("tertiaryLabel")
        self.bot_label.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(self.bot_label)
        return bar

    def _build_status_strip(self) -> QWidget:
        strip = QWidget()
        strip.setObjectName("statusStrip")
        strip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        strip.setFixedHeight(26)
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)
        self.status_text = QLabel("Ready")
        self.status_text.setObjectName("statusText")
        layout.addWidget(self.status_text, 1)
        grip = QSizeGrip(strip)
        grip.setFixedSize(18, 18)
        layout.addWidget(grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        return strip

    # ---- navigation ----------------------------------------------------

    def _show_page(self, index: int) -> None:
        self.nav_buttons[index].setChecked(True)
        self.stack.setCurrentIndex(index)
        page = self.pages[index]
        if hasattr(page, "on_activated"):
            page.on_activated()

    def _set_review_count(self, count: int) -> None:
        self.nav_buttons[2].setText(f"Review ({count})" if count else "Review")

    def _on_bot_state(self, enabled: bool) -> None:
        self.bot_label.setText("Bot: running" if enabled else "Bot: stopped")

    def _on_data_changed(self) -> None:
        self.dashboard.refresh()
        current = self.pages[self.stack.currentIndex()]
        if current in (self.review, self.activity):
            current.refresh()

    def closeEvent(self, event) -> None:
        self.backend.shutdown()
        super().closeEvent(event)
