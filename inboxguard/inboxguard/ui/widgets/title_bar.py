"""Custom frameless title bar with procedurally drawn window controls."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QWidget

from .. import style


class WindowControlButton(QPushButton):
    """Glyph button for minimize, maximize, restore and close."""

    def __init__(self, glyph: str):
        super().__init__()
        self._glyph = glyph
        self.setFixedSize(34, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setObjectName("closeControl" if glyph == "close" else "windowControl")

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        hovered = self.underMouse()
        if hovered:
            painter.fillRect(self.rect(), QColor(style.BG_HOVER))
        if self._glyph == "close":
            color = QColor("#e07a70") if hovered else QColor(style.DANGER)
        else:
            color = QColor(style.TEXT_PRIMARY if hovered else style.TEXT_SECONDARY)
        painter.setPen(QPen(color, 1.2))
        rect = QRectF(self.rect())
        cx, cy, s = rect.center().x(), rect.center().y(), 5.0
        if self._glyph == "minimize":
            painter.drawLine(int(cx - s), int(cy), int(cx + s), int(cy))
        elif self._glyph == "maximize":
            painter.drawRect(QRectF(cx - s, cy - s, 2 * s, 2 * s))
        elif self._glyph == "restore":
            painter.drawRect(QRectF(cx - s + 2, cy - s, 2 * s - 2, 2 * s - 2))
            painter.drawRect(QRectF(cx - s, cy - s + 2, 2 * s - 2, 2 * s - 2))
        elif self._glyph == "close":
            painter.drawLine(int(cx - s), int(cy - s), int(cx + s), int(cy + s))
            painter.drawLine(int(cx - s), int(cy + s), int(cx + s), int(cy - s))


class TitleBar(QWidget):
    BAR_HEIGHT = 36

    def __init__(self, window: QMainWindow, title: str):
        super().__init__()
        self._window = window
        self._drag_offset: QPoint | None = None
        self.setObjectName("titleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(self.BAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 4, 0)
        layout.setSpacing(0)
        label = QLabel(title)
        label.setObjectName("titleLabel")
        layout.addWidget(label)
        layout.addStretch()

        self.minimize_btn = WindowControlButton("minimize")
        self.maximize_btn = WindowControlButton("maximize")
        self.close_btn = WindowControlButton("close")
        self.minimize_btn.clicked.connect(self._window.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self._window.close)
        for button in (self.minimize_btn, self.maximize_btn, self.close_btn):
            layout.addWidget(button)

    def toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
            self.maximize_btn.set_glyph("maximize")
        else:
            self._window.showMaximized()
            self.maximize_btn.set_glyph("restore")

    # A frameless window has no OS drag handle. Prefer the compositor's own
    # move (works on Wayland); fall back to manual offset tracking.
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        handle = self._window.windowHandle()
        if handle is not None and not self._window.isMaximized():
            try:
                if handle.startSystemMove():
                    return
            except AttributeError:
                pass
        self._drag_offset = event.globalPosition().toPoint() - self._window.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event) -> None:
        self.toggle_maximize()
