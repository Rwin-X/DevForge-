"""
HashForge — DropZone widget.
Accepts drag-and-drop or click-to-browse for a single file.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QPen, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog


ACCEPTED_MIME = "application/octet-stream"


class DropZone(QWidget):
    """
    Premium drag-and-drop area.
    Emits file_selected(path: str) when a file is chosen.
    """

    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        self._hovered = False
        self._drag_active = False
        self._setup_ui()

    # ----------------------------------------------------------------- UI ---
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 40, 32, 40)

        # Icon — shield / lock SVG-like Unicode
        self._icon = QLabel("🔒")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet("font-size: 40px; background: transparent;")

        self._title = QLabel("Drop a file here to hash it")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setProperty("role", "heading")
        self._title.setStyleSheet(
            "font-size: 17px; font-weight: 700; color: #0F172A; background: transparent;"
        )

        self._subtitle = QLabel("Supports any file type · Processed locally")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setProperty("role", "subheading")
        self._subtitle.setStyleSheet(
            "font-size: 13px; color: #64748B; background: transparent;"
        )

        self._browse_btn = QPushButton("Browse file")
        self._browse_btn.setProperty("variant", "primary")
        self._browse_btn.setFixedWidth(160)
        self._browse_btn.setFixedHeight(40)
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.clicked.connect(self._browse)

        layout.addWidget(self._icon)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        layout.addSpacing(4)
        layout.addWidget(self._browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    # ----------------------------------------------------------- Drag/Drop ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and Path(urls[0].toLocalFile()).is_file():
                self._drag_active = True
                self.update()
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._drag_active = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self._drag_active = False
        self.update()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self.file_selected.emit(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._browse()

    # ----------------------------------------------------------- Browse ------
    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a file to hash", "", "All Files (*)"
        )
        if path:
            self.file_selected.emit(path)

    # ----------------------------------------------------------- Paint -------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 16

        # Background
        if self._drag_active:
            bg = QColor("#DBEAFE")
        elif self._hovered:
            bg = QColor("#F1F5F9")
        else:
            bg = QColor("#F8FAFC")
        painter.setBrush(bg)

        # Dashed border
        pen = QPen()
        if self._drag_active:
            pen.setColor(QColor("#2563EB"))
            pen.setWidth(2)
        else:
            pen.setColor(QColor("#CBD5E1"))
            pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        painter.drawRoundedRect(rect, radius, radius)
        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def set_dark(self, dark: bool):
        if dark:
            self._title.setStyleSheet(
                "font-size: 17px; font-weight: 700; color: #E6EDF3; background: transparent;"
            )
            self._subtitle.setStyleSheet(
                "font-size: 13px; color: #8B949E; background: transparent;"
            )
        else:
            self._title.setStyleSheet(
                "font-size: 17px; font-weight: 700; color: #0F172A; background: transparent;"
            )
            self._subtitle.setStyleSheet(
                "font-size: 13px; color: #64748B; background: transparent;"
            )
        self.update()
