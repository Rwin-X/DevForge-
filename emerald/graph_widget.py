"""
graph_widget.py

Visual graph of the note vault. Each note is a node, each [[wiki link]]
is an edge. Supports zoom (scroll wheel), pan (click-drag on empty
space), search-highlight, and click-to-open.

Layout is a lightweight force-directed simulation implemented from
scratch (no networkx / no extra dependency) -- fine for personal
vaults of up to a few hundred notes.
"""

from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QWidget,
)

# Palette matches the rest of the app (phosphor / terminal dark theme).
COLOR_BG = QColor("#0b0e0d")
COLOR_NODE = QColor("#1c2b24")
COLOR_NODE_BORDER = QColor("#39ff9f")
COLOR_NODE_ACTIVE = QColor("#39ff9f")
COLOR_NODE_DIM_BORDER = QColor("#2c3d36")
COLOR_EDGE = QColor(57, 255, 159, 70)
COLOR_TEXT = QColor("#d7ffe9")
COLOR_TEXT_DIM = QColor("#5f7a6d")

NODE_RADIUS = 8


class GraphNodeItem(QGraphicsEllipseItem):
    def __init__(self, note_id: str, graph_widget: "GraphWidget"):
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)
        self.note_id = note_id
        self.graph_widget = graph_widget
        self.setBrush(QBrush(COLOR_NODE))
        self.setPen(QPen(COLOR_NODE_BORDER, 1.5))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.label = QGraphicsSimpleTextItem(note_id, self)
        font = QFont("JetBrains Mono", 8)
        self.label.setFont(font)
        self.label.setBrush(QBrush(COLOR_TEXT))
        self.label.setPos(NODE_RADIUS + 4, -7)
        self.label.setZValue(3)

        self.edges: list["GraphEdgeItem"] = []
        self.vx = 0.0
        self.vy = 0.0
        self.pinned = False  # True while the user is dragging this node
        self._press_scene_pos: QPointF | None = None
        self._dragged = False

    def set_dimmed(self, dimmed: bool) -> None:
        if dimmed:
            self.setPen(QPen(COLOR_NODE_DIM_BORDER, 1.2))
            self.label.setBrush(QBrush(COLOR_TEXT_DIM))
        else:
            self.setPen(QPen(COLOR_NODE_BORDER, 1.5))
            self.label.setBrush(QBrush(COLOR_TEXT))

    def hoverEnterEvent(self, event):
        self.setPen(QPen(COLOR_NODE_ACTIVE, 2.5))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(QPen(COLOR_NODE_BORDER, 1.5))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_scene_pos = event.scenePos()
            self._dragged = False
            self.pinned = True
            self.vx = 0.0
            self.vy = 0.0
            self.graph_widget.ensure_simulation_running()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_scene_pos is not None:
            moved = (event.scenePos() - self._press_scene_pos).manhattanLength()
            if moved > 3:
                self._dragged = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._dragged:
                # A plain click (no drag): open the note.
                self.graph_widget.node_clicked.emit(self.note_id)
            self.pinned = False
            self._press_scene_pos = None
            self._dragged = False
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        # ItemPositionChange fires BEFORE the new position is committed
        # (self.pos() still reports the old value at that point), so
        # updating edges there draws them one frame behind the node.
        # ItemPositionHasChanged fires AFTER the position is committed,
        # which is what we want here.
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        return super().itemChange(change, value)


class GraphEdgeItem(QGraphicsLineItem):
    def __init__(self, source: GraphNodeItem, target: GraphNodeItem):
        super().__init__()
        self.source = source
        self.target = target
        self.setPen(QPen(COLOR_EDGE, 1.2))
        self.setZValue(1)
        source.edges.append(self)
        target.edges.append(self)
        self.update_position()

    def update_position(self) -> None:
        self.setLine(
            self.source.pos().x(),
            self.source.pos().y(),
            self.target.pos().x(),
            self.target.pos().y(),
        )


class GraphView(QGraphicsView):
    """
    QGraphicsView subclass that adds smooth wheel-zoom and drag-pan.

    Drag behavior is click-target-dependent: dragging a node moves that
    node (and its edges follow, live); dragging empty canvas pans the
    whole view. QGraphicsView's built-in ScrollHandDrag mode does NOT do
    this -- it grabs every left-drag for panning regardless of what's
    under the cursor, which is what made node dragging feel broken. So
    panning is implemented manually here, only when the click didn't
    land on an item.
    """

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(COLOR_BG))
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._zoom = 1.0
        self._panning = False
        self._pan_last_pos = None

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_zoom = self._zoom * factor
        if 0.15 <= new_zoom <= 6.0:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item is None:
                # Empty canvas: start a manual pan instead of forwarding
                # to item-drag handling.
                self._panning = True
                self._pan_last_pos = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_last_pos is not None:
            delta = event.pos() - self._pan_last_pos
            self._pan_last_pos = event.pos()
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning and event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self._pan_last_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class GraphWidget(QWidget):
    """
    Public widget wrapping the scene + view. Owns the force-directed
    layout loop and exposes set_graph() / highlight_search() / a
    node_clicked signal for the main window to react to.
    """

    node_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(COLOR_BG))
        self.view = GraphView(self.scene, self)
        self.view.node_clicked = self.node_clicked  # let node items emit through the view

        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.nodes: dict[str, GraphNodeItem] = {}
        self.edges: list[GraphEdgeItem] = []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._simulation_step)
        self._timer.setInterval(16)  # ~60fps
        self._settle_ticks = 0

    # ------------------------------------------------------------------ #

    def set_graph(self, note_ids: list[str], edges: list[tuple[str, str]], active_id: str | None = None) -> None:
        """Rebuild the graph from scratch. Called whenever notes change."""
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()

        if not note_ids:
            self._timer.stop()
            return

        # Place nodes on a rough circle to start; the simulation spreads them out.
        radius = 40 + 12 * math.sqrt(max(len(note_ids), 1))
        for i, note_id in enumerate(note_ids):
            angle = (2 * math.pi * i) / max(len(note_ids), 1)
            x = radius * math.cos(angle) + random.uniform(-10, 10)
            y = radius * math.sin(angle) + random.uniform(-10, 10)
            node = GraphNodeItem(note_id, self)
            node.setPos(x, y)
            node.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.scene.addItem(node)
            self.nodes[note_id] = node

        for source_id, target_id in edges:
            source = self.nodes.get(source_id)
            target = self.nodes.get(target_id)
            if source is not None and target is not None:
                edge = GraphEdgeItem(source, target)
                self.scene.addItem(edge)
                self.edges.append(edge)

        if active_id and active_id in self.nodes:
            self.highlight_active(active_id)

        self._settle_ticks = 240  # run the layout for a couple seconds then stop
        self._timer.start()

    def highlight_active(self, note_id: str | None) -> None:
        for nid, node in self.nodes.items():
            node.set_dimmed(note_id is not None and nid != note_id)

    def highlight_search(self, query: str) -> None:
        query = query.strip().lower()
        for nid, node in self.nodes.items():
            match = (not query) or (query in nid.lower())
            node.set_dimmed(not match)

    def center_on_node(self, note_id: str) -> None:
        node = self.nodes.get(note_id)
        if node is not None:
            self.view.centerOn(node)

    def frame_all(self) -> None:
        if self.nodes:
            self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio)

    # ------------------------------------------------------------------ #
    # Simple force-directed layout: repulsion between all nodes,
    # spring attraction along edges, mild pull to center.
    # ------------------------------------------------------------------ #

    def _simulation_step(self) -> None:
        nodes = list(self.nodes.values())
        any_pinned = any(n.pinned for n in nodes)

        if len(nodes) < 2:
            if not any_pinned:
                self._settle_ticks -= 1
                if self._settle_ticks <= 0:
                    self._timer.stop()
            return

        REPULSION = 2200.0
        SPRING_LENGTH = 110.0
        SPRING_STRENGTH = 0.02
        CENTER_PULL = 0.002
        DAMPING = 0.85

        for node in nodes:
            node.vx *= DAMPING
            node.vy *= DAMPING

        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx = a.pos().x() - b.pos().x()
                dy = a.pos().y() - b.pos().y()
                dist_sq = max(dx * dx + dy * dy, 1.0)
                dist = math.sqrt(dist_sq)
                force = REPULSION / dist_sq
                fx = (dx / dist) * force
                fy = (dy / dist) * force
                a.vx += fx
                a.vy += fy
                b.vx -= fx
                b.vy -= fy

        for edge in self.edges:
            a, b = edge.source, edge.target
            dx = b.pos().x() - a.pos().x()
            dy = b.pos().y() - a.pos().y()
            dist = max(math.sqrt(dx * dx + dy * dy), 1.0)
            stretch = dist - SPRING_LENGTH
            force = stretch * SPRING_STRENGTH
            fx = (dx / dist) * force
            fy = (dy / dist) * force
            a.vx += fx
            a.vy += fy
            b.vx -= fx
            b.vy -= fy

        for node in nodes:
            if node.pinned:
                # The user is actively dragging this node: leave its
                # position alone (their mouse is the authority), but
                # still zero out velocity so it doesn't leap once released.
                node.vx = 0.0
                node.vy = 0.0
                continue
            node.vx += -node.pos().x() * CENTER_PULL
            node.vy += -node.pos().y() * CENTER_PULL
            new_x = node.pos().x() + node.vx
            new_y = node.pos().y() + node.vy
            node.setPos(new_x, new_y)

        if not any_pinned:
            self._settle_ticks -= 1
            if self._settle_ticks <= 0:
                self._timer.stop()

    def ensure_simulation_running(self) -> None:
        """Wake the layout loop back up (e.g. when the user grabs a node
        after it had already settled), so edges keep tracking smoothly."""
        self._settle_ticks = max(self._settle_ticks, 90)
        if not self._timer.isActive():
            self._timer.start()
