"""Slim custom title bar: drag-to-move, minimize/maximize/close."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QWidget

from passcheck.ui.widgets.window_controls import WindowControlButton


class TitleBar(QWidget):
    BAR_HEIGHT = 36

    def __init__(self, window: QMainWindow, title: str):
        super().__init__()
        self._window = window
        self._drag_offset: QPoint | None = None

        self.setObjectName("titleBar")
        self.setFixedHeight(self.BAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)

        title_label = QLabel(title)
        title_label.setObjectName("secondaryLabel")
        layout.addWidget(title_label)

        layout.addStretch()

        self.minimize_btn = WindowControlButton("minimize")
        self.maximize_btn = WindowControlButton("maximize")
        self.close_btn = WindowControlButton("close")

        self.minimize_btn.clicked.connect(self._window.showMinimized)
        self.maximize_btn.clicked.connect(self._toggle_maximize)
        self.close_btn.clicked.connect(self._window.close)

        for btn in (self.minimize_btn, self.maximize_btn, self.close_btn):
            layout.addWidget(btn)

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
            self.maximize_btn.set_glyph("maximize")
        else:
            self._window.showMaximized()
            self.maximize_btn.set_glyph("restore")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._window.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event) -> None:
        self._toggle_maximize()
