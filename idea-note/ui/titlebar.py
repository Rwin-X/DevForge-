"""
titlebar.py — frameless-window titlebar with macOS traffic-light controls.

We keep the native OS frame off (Qt.FramelessWindowHint) and draw our own,
because a real inset titlebar is what separates "an app" from "a Qt window".
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QMouseEvent


class TrafficDot(QPushButton):
    def __init__(self, color: str, hover_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("trafficDot")
        self.setFixedSize(12, 12)
        self.color = QColor(color)
        self.hover_color = QColor(hover_color)
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.hover_color if self._hovered else self.color)
        p.drawEllipse(0, 0, 12, 12)


class TitleBar(QWidget):
    closeClicked = Signal()
    minimizeClicked = Signal()
    maximizeClicked = Signal()

    def __init__(self, title="Idea Book", parent=None):
        super().__init__(parent)
        self.setObjectName("titlebar")
        self.setFixedHeight(40)
        self._drag_pos: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        close_btn = TrafficDot("#5F574E", "#FF5F57")
        min_btn = TrafficDot("#5F574E", "#FEBC2E")
        max_btn = TrafficDot("#5F574E", "#28C840")
        close_btn.clicked.connect(self.closeClicked.emit)
        min_btn.clicked.connect(self.minimizeClicked.emit)
        max_btn.clicked.connect(self.maximizeClicked.emit)

        layout.addWidget(close_btn)
        layout.addWidget(min_btn)
        layout.addWidget(max_btn)
        layout.addSpacing(8)

        self.label = QLabel(title)
        self.label.setObjectName("titlebarLabel")
        layout.addWidget(self.label)
        layout.addStretch()

    def set_title(self, text: str):
        self.label.setText(text)

    # allow dragging the frameless window by its titlebar
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.window().pos()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.window().move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, e: QMouseEvent):
        self.maximizeClicked.emit()
