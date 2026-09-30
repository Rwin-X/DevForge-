"""Main window: frameless chrome + tab bar hosting Convert, Analyze,
and Vault. Wires cross-tab actions (Analyze's restore, Vault's
save/restore) back into the Convert tab.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from core.models import Direction
from core.vault import make_entry
from ui.widgets.analyze_tab import AnalyzeTab
from ui.widgets.convert_tab import ConvertTab
from ui.widgets.title_bar import TitleBar
from ui.widgets.vault_tab import VaultTab

_RESIZE_MARGIN = 6


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(880, 600)
        self.resize(1080, 700)
        self.setMouseTracking(True)

        self._resize_edge = None
        self._resize_start_geom = None
        self._resize_start_pos = None

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        root_layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)

        self.tabs = QTabWidget(content)
        self.tabs.setDocumentMode(True)

        self.convert_tab = ConvertTab(self)
        self.analyze_tab = AnalyzeTab(self)
        self.vault_tab = VaultTab(self)

        self.tabs.addTab(self.convert_tab, "Convert")
        self.tabs.addTab(self.analyze_tab, "Analyze")
        self.tabs.addTab(self.vault_tab, "Vault")

        content_layout.addWidget(self.tabs)
        root_layout.addWidget(content, 1)

        self.setCentralWidget(central)

        self._wire_cross_tab_actions()

    def _wire_cross_tab_actions(self) -> None:
        # Analyze tab: double-clicking a Caesar candidate jumps to
        # Convert with that shift pre-filled.
        self.analyze_tab.restore_requested.connect(self._restore_into_convert)

        # Vault tab: restoring a saved entry jumps to Convert; saving
        # asks the Convert tab for its current result.
        self.vault_tab.restore_requested.connect(self._restore_into_convert)
        self.vault_tab.on_save_requested = self._make_vault_entry_from_convert

    def _restore_into_convert(self, algorithm_id: str, direction: Direction, input_text: str, key1: str, key2: str) -> None:
        self.convert_tab.restore_conversion(algorithm_id, direction, input_text, key1, key2)
        self.tabs.setCurrentWidget(self.convert_tab)

    def _make_vault_entry_from_convert(self):
        last = getattr(self.convert_tab, "_last_result", None)
        if last is None:
            return None
        spec, direction, input_text, output_text, k1, k2 = last
        return make_entry(
            algorithm_id=spec.id,
            algorithm_name=spec.name,
            direction=direction,
            input_text=input_text,
            output_text=output_text,
            key1=k1,
            key2=k2,
            is_asymmetric=spec.is_asymmetric,
        )

    # ------------------------------------------------------------------
    # edge-drag resize (frameless windows get no native resize handles)
    # ------------------------------------------------------------------

    def _edge_at(self, pos: QPoint) -> str | None:
        rect = self.rect()
        m = _RESIZE_MARGIN
        left = pos.x() <= m
        right = pos.x() >= rect.width() - m
        top = pos.y() <= m
        bottom = pos.y() >= rect.height() - m
        if top and left:
            return "top-left"
        if top and right:
            return "top-right"
        if bottom and left:
            return "bottom-left"
        if bottom and right:
            return "bottom-right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    _CURSOR_FOR_EDGE = {
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "top-left": Qt.CursorShape.SizeFDiagCursor,
        "bottom-right": Qt.CursorShape.SizeFDiagCursor,
        "top-right": Qt.CursorShape.SizeBDiagCursor,
        "bottom-left": Qt.CursorShape.SizeBDiagCursor,
    }

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            edge = self._edge_at(event.position().toPoint())
            if edge:
                self._resize_edge = edge
                self._resize_start_geom = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._resize_edge and event.buttons() & Qt.MouseButton.LeftButton:
            self._perform_resize(event.globalPosition().toPoint())
            return
        if not self.isMaximized():
            edge = self._edge_at(event.position().toPoint())
            cursor = self._CURSOR_FOR_EDGE.get(edge, Qt.CursorShape.ArrowCursor)
            self.setCursor(QCursor(cursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._resize_edge = None
        self._resize_start_geom = None
        self._resize_start_pos = None
        super().mouseReleaseEvent(event)

    def _perform_resize(self, global_pos: QPoint) -> None:
        delta = global_pos - self._resize_start_pos
        geom = self._resize_start_geom
        x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()
        min_w, min_h = self.minimumWidth(), self.minimumHeight()

        if "left" in self._resize_edge:
            new_w = max(min_w, w - delta.x())
            x = x + (w - new_w)
            w = new_w
        elif "right" in self._resize_edge:
            w = max(min_w, w + delta.x())

        if "top" in self._resize_edge:
            new_h = max(min_h, h - delta.y())
            y = y + (h - new_h)
            h = new_h
        elif "bottom" in self._resize_edge:
            h = max(min_h, h + delta.y())

        self.setGeometry(x, y, w, h)
