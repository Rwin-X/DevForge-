"""Custom frameless title bar: drag-to-move, procedurally drawn
minimize/maximize/close controls. Follows the reference pattern in
pyqt6-desktop-scaffold's frameless-window.md.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ui.style import ACCENT, DANGER, TEXT_PRIMARY, TEXT_SECONDARY


class WindowControlButton(QPushButton):
    """Minimal glyph button for minimize/maximize/close, drawn with
    QPainter rather than platform icons."""

    def __init__(self, glyph: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._glyph = glyph
        self.setFixedSize(28, 28)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("ghostAction")

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(DANGER) if self._glyph == "close" else QColor(TEXT_SECONDARY)
        if self.underMouse():
            color = QColor("#e07a70") if self._glyph == "close" else QColor(TEXT_PRIMARY)

        painter.setPen(color)
        rect = QRectF(0, 0, self.width(), self.height())
        cx, cy = rect.center().x(), rect.center().y()
        size = 5

        if self._glyph == "minimize":
            painter.drawLine(int(cx - size), int(cy), int(cx + size), int(cy))
        elif self._glyph == "maximize":
            painter.drawRect(int(cx - size), int(cy - size), size * 2, size * 2)
        elif self._glyph == "restore":
            painter.drawRect(int(cx - size + 2), int(cy - size), size * 2 - 2, size * 2 - 2)
            painter.drawRect(int(cx - size), int(cy - size + 2), size * 2 - 2, size * 2 - 2)
        elif self._glyph == "close":
            painter.drawLine(int(cx - size), int(cy - size), int(cx + size), int(cy + size))
            painter.drawLine(int(cx - size), int(cy + size), int(cx + size), int(cy - size))


class DiamondMark(QWidget):
    """Small procedurally drawn diamond glyph standing in for a logo,
    matching Cipherdesk's diamond motif from the web version."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(14, 14)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(ACCENT))
        painter.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        points = [
            (w / 2, 0),
            (w, h / 2),
            (w / 2, h),
            (0, h / 2),
        ]
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(*points[0])
        for p in points[1:]:
            path.lineTo(*p)
        path.closeSubpath()
        painter.drawPath(path)


class TitleBar(QWidget):
    """Slim custom title bar: drag-to-move, minimize/maximize/close."""

    BAR_HEIGHT = 40

    def __init__(self, window, parent: QWidget | None = None):
        super().__init__(parent)
        self._window = window
        self._drag_offset: QPoint | None = None

        self.setObjectName("titleBar")
        self.setFixedHeight(self.BAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(10)

        layout.addWidget(DiamondMark(self))

        title = QLabel("CIPHERDESK", self)
        title.setObjectName("appTitle")
        layout.addWidget(title)

        tagline = QLabel("Encode · Decode · Analyze", self)
        tagline.setObjectName("appTagline")
        layout.addWidget(tagline)

        layout.addStretch()

        self.minimize_btn = WindowControlButton("minimize", self)
        self.maximize_btn = WindowControlButton("maximize", self)
        self.close_btn = WindowControlButton("close", self)

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

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._window.pos()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self._toggle_maximize()
