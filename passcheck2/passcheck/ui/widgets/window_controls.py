"""Procedurally drawn minimize/maximize/close glyphs for the custom
title bar. No image assets, matches the app's own palette."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QPushButton


class WindowControlButton(QPushButton):
    """Minimal glyph button for minimize/maximize/close."""

    def __init__(self, glyph: str):
        super().__init__()
        self._glyph = glyph
        self.setFixedSize(28, 28)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if glyph == "close":
            self.setObjectName("closeControl")

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor("#c0524a") if self._glyph == "close" else QColor("#8a8a92")
        if self.underMouse():
            color = QColor("#e8e8ea") if self._glyph != "close" else QColor("#e07a70")

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
