"""Segmented strength meter, drawn procedurally so its fill color and
segment count update without any image assets."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from passcheck.ui.style import BORDER, LEVEL_COLORS

SEGMENT_COUNT = 5
SEGMENT_GAP = 4


class StrengthMeter(QWidget):
    """Horizontal segmented bar showing 0-5 filled segments by level."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filled_segments = 0
        self._color = QColor(BORDER)
        self.setFixedHeight(8)
        self.setMinimumWidth(200)

    def set_level(self, level_index: int) -> None:
        # level_index is 0-4 (StrengthLevel value); map to 1-5 filled
        # segments so an empty/very-weak password still shows a hint
        # of the meter rather than nothing at all.
        self._filled_segments = level_index + 1
        self._color = QColor(LEVEL_COLORS.get(level_index, BORDER))
        self.update()

    def clear(self) -> None:
        self._filled_segments = 0
        self._color = QColor(BORDER)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        total_width = self.width()
        segment_width = (total_width - SEGMENT_GAP * (SEGMENT_COUNT - 1)) / SEGMENT_COUNT

        for i in range(SEGMENT_COUNT):
            x = i * (segment_width + SEGMENT_GAP)
            rect = QRectF(x, 0, segment_width, self.height())
            if i < self._filled_segments:
                painter.setBrush(self._color)
            else:
                painter.setBrush(QColor(BORDER))
            painter.drawRoundedRect(rect, 3, 3)
