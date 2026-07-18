"""
graph_view.py — constellation-style force-directed graph of the vault.

Nodes = notes, sized by connection degree.
Edges = [[wikilinks]] between notes.
Physics = simple spring/repulsion simulation ticked on a QTimer,
so the graph settles instead of appearing pre-baked.

This is the signature visual element of Idea Book: the vault seen as
a constellation rather than a file tree.
"""

import math
import random
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Qt, QTimer, QPointF, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient

BG = QColor("#161616")
EDGE_COLOR = QColor(255, 255, 255, 26)
EDGE_COLOR_HOVER = QColor(201, 153, 92, 140)
NODE_COLOR = QColor("#E8E6E1")
NODE_COLOR_PINNED = QColor("#C9995C")
NODE_HOVER = QColor("#C9995C")
LABEL_COLOR = QColor(232, 230, 225, 170)
LABEL_COLOR_HOVER = QColor("#F2EFE9")


class GraphNode:
    __slots__ = ("id", "title", "folder", "degree", "pinned", "x", "y", "vx", "vy")

    def __init__(self, id_, title, folder, degree, pinned):
        self.id = id_
        self.title = title
        self.folder = folder
        self.degree = degree
        self.pinned = pinned
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(50, 200)
        self.x = math.cos(angle) * r
        self.y = math.sin(angle) * r
        self.vx = 0.0
        self.vy = 0.0


class GraphView(QWidget):
    noteActivated = Signal(int)  # emits note id on double-click

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.nodes: dict[int, GraphNode] = {}
        self.edges: list[tuple[int, int]] = []
        self.hover_id: int | None = None
        self._drag_id: int | None = None
        self._pan = QPointF(0, 0)
        self._zoom = 1.0
        self._last_mouse = QPointF(0, 0)
        self._panning = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

        self.setStyleSheet("background-color: #161616;")

    # ---------- data ----------

    def set_data(self, nodes: list[dict], edges: list[dict]):
        existing = self.nodes
        new_nodes = {}
        for n in nodes:
            if n["id"] in existing:
                gn = existing[n["id"]]
                gn.title, gn.folder = n["title"], n["folder"]
                gn.degree, gn.pinned = n["degree"], n["pinned"]
            else:
                gn = GraphNode(n["id"], n["title"], n["folder"], n["degree"], n["pinned"])
            new_nodes[n["id"]] = gn
        self.nodes = new_nodes
        self.edges = [(e["src"], e["dst"]) for e in edges]
        self.update()

    # ---------- physics ----------

    def _tick(self):
        if len(self.nodes) < 2:
            self.update()
            return

        nodes = list(self.nodes.values())
        REPEL = 2400.0
        SPRING = 0.02
        SPRING_LEN = 130.0
        DAMPING = 0.85
        CENTER_PULL = 0.002

        for a in nodes:
            fx = fy = 0.0
            for b in nodes:
                if a is b:
                    continue
                dx, dy = a.x - b.x, a.y - b.y
                dist2 = dx * dx + dy * dy + 0.01
                dist = math.sqrt(dist2)
                force = REPEL / dist2
                fx += (dx / dist) * force
                fy += (dy / dist) * force
            fx -= a.x * CENTER_PULL
            fy -= a.y * CENTER_PULL
            a.vx = (a.vx + fx) * DAMPING
            a.vy = (a.vy + fy) * DAMPING

        for src, dst in self.edges:
            a, b = self.nodes.get(src), self.nodes.get(dst)
            if not a or not b:
                continue
            dx, dy = b.x - a.x, b.y - a.y
            dist = math.sqrt(dx * dx + dy * dy) + 0.01
            stretch = dist - SPRING_LEN
            force = SPRING * stretch
            ux, uy = dx / dist, dy / dist
            a.vx += ux * force
            a.vy += uy * force
            b.vx -= ux * force
            b.vy -= uy * force

        for n in nodes:
            if n.id == self._drag_id:
                continue
            n.x += n.vx
            n.y += n.vy

        self.update()

    # ---------- coordinate transforms ----------

    def _to_screen(self, x, y) -> QPointF:
        cx, cy = self.width() / 2, self.height() / 2
        return QPointF(cx + (x + self._pan.x()) * self._zoom, cy + (y + self._pan.y()) * self._zoom)

    def _to_world(self, sx, sy) -> QPointF:
        cx, cy = self.width() / 2, self.height() / 2
        return QPointF((sx - cx) / self._zoom - self._pan.x(), (sy - cy) / self._zoom - self._pan.y())

    def _node_radius(self, n: GraphNode) -> float:
        return 5 + min(n.degree, 12) * 1.15

    # ---------- painting ----------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), BG)

        if not self.nodes:
            p.setPen(QColor(255, 255, 255, 60))
            p.setFont(QFont("SF Pro Text", 12))
            p.drawText(self.rect(), Qt.AlignCenter, "No ideas linked yet\n\nUse [[Note Title]] to connect notes")
            p.end()
            return

        # edges
        for src, dst in self.edges:
            a, b = self.nodes.get(src), self.nodes.get(dst)
            if not a or not b:
                continue
            pa, pb = self._to_screen(a.x, a.y), self._to_screen(b.x, b.y)
            hot = self.hover_id in (src, dst)
            pen = QPen(EDGE_COLOR_HOVER if hot else EDGE_COLOR, 1.4 if hot else 1.0)
            p.setPen(pen)
            p.drawLine(pa, pb)

        # nodes
        font = QFont("SF Pro Text", 10)
        p.setFont(font)
        for n in self.nodes.values():
            pos = self._to_screen(n.x, n.y)
            r = self._node_radius(n) * self._zoom
            is_hot = n.id == self.hover_id

            if is_hot:
                glow = QRadialGradient(pos, r * 4)
                glow.setColorAt(0, QColor(201, 153, 92, 90))
                glow.setColorAt(1, QColor(201, 153, 92, 0))
                p.setBrush(QBrush(glow))
                p.setPen(Qt.NoPen)
                p.drawEllipse(pos, r * 4, r * 4)

            color = NODE_HOVER if is_hot else (NODE_COLOR_PINNED if n.pinned else NODE_COLOR)
            p.setBrush(QBrush(color))
            p.setPen(QPen(BG, 1.5))
            p.drawEllipse(pos, r, r)

            p.setPen(LABEL_COLOR_HOVER if is_hot else LABEL_COLOR)
            label_rect = QRectF(pos.x() - 90, pos.y() + r + 2, 180, 16)
            p.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, n.title)

        p.end()

    # ---------- interaction ----------

    def _node_at(self, pos: QPointF) -> int | None:
        world = self._to_world(pos.x(), pos.y())
        for n in self.nodes.values():
            r = self._node_radius(n) + 3
            if (n.x - world.x()) ** 2 + (n.y - world.y()) ** 2 <= r * r:
                return n.id
        return None

    def mousePressEvent(self, e):
        hit = self._node_at(e.position())
        if hit is not None:
            self._drag_id = hit
        else:
            self._panning = True
        self._last_mouse = e.position()

    def mouseMoveEvent(self, e):
        delta = e.position() - self._last_mouse
        self._last_mouse = e.position()

        if self._drag_id is not None:
            n = self.nodes[self._drag_id]
            world = self._to_world(e.position().x(), e.position().y())
            n.x, n.y = world.x(), world.y()
            n.vx = n.vy = 0
        elif self._panning:
            self._pan += QPointF(delta.x() / self._zoom, delta.y() / self._zoom)
        else:
            hit = self._node_at(e.position())
            if hit != self.hover_id:
                self.hover_id = hit
                self.setCursor(Qt.PointingHandCursor if hit is not None else Qt.ArrowCursor)
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag_id = None
        self._panning = False

    def mouseDoubleClickEvent(self, e):
        hit = self._node_at(e.position())
        if hit is not None:
            self.noteActivated.emit(hit)

    def wheelEvent(self, e):
        factor = 1.0015 ** e.angleDelta().y()
        self._zoom = max(0.25, min(3.0, self._zoom * factor))
        self.update()
