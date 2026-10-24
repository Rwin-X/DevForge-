"""PyQt6 window: a rhythm-bound torus plus a minimal control bar."""
import time

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton,
                             QSlider, QVBoxLayout, QWidget)

from core.audio import decode
from core.scenes import SCENES, point_alpha, split_segments
from ui.style import BG, FG



def clock(s):
    return "%d:%02d" % (int(s) // 60, int(s) % 60)


class DecodeWorker(QThread):
    """Decodes a file off the UI thread."""
    done = pyqtSignal(object)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            self.done.emit(decode(self.path))
        except Exception:
            self.done.emit(None)


class Visual(QWidget):
    def __init__(self, player):
        super().__init__()
        self.p, self.mx, self.my = player, 0.0, 0.0
        self.scenes, self.index = [cls() for cls in SCENES], 0
        self.last = time.monotonic()
        self.setMouseTracking(True)

    def next_scene(self, step=1):
        self.index = (self.index + step) % len(self.scenes)

    def mouseMoveEvent(self, e):
        self.mx = e.position().x() / max(1, self.width()) * 2 - 1
        self.my = e.position().y() / max(1, self.height()) * 2 - 1

    def paintEvent(self, _):
        now = time.monotonic()
        dt = min(now - self.last, 0.05)
        self.last = now
        p = self.p
        p.analyse(dt)
        w, h = self.width(), self.height()
        vp = (w / 2, h * 0.46, min(w, h) / 1000, self.mx, self.my)
        segs, pts, strips = self.scenes[self.index].build(p, now, dt, vp)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(BG))
        fg = QColor(FG)
        for A, B, Z, alpha in segs:
            for a, A_, B_ in split_segments(A, B, Z, alpha):
                fg.setAlpha(int(a * 255))
                painter.setPen(QPen(fg, 1))
                painter.drawLines([QLineF(s[0], s[1], e[0], e[1]) for s, e in zip(A_.tolist(), B_.tolist())])
        for P, alpha, fill in strips:
            poly = [QPointF(x, y) for x, y in P.tolist()]
            if fill:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(BG))
                painter.drawPolygon(QPolygonF(poly + [QPointF(poly[-1].x(), h), QPointF(poly[0].x(), h)]))
                painter.setBrush(Qt.BrushStyle.NoBrush)
            fg.setAlpha(int(alpha * 255))
            painter.setPen(QPen(fg, 1))
            painter.drawPolyline(QPolygonF(poly))
        for P, S, Z in pts:
            al = point_alpha(Z, len(P))
            for (x, y), s, a in zip(P.tolist(), np.broadcast_to(S, len(P)).tolist(), al.tolist()):
                fg.setAlpha(int(a * 255))
                painter.fillRect(QRectF(x - s / 2, y - s / 2, s, s), fg)

        fg.setAlpha(255)
        painter.setPen(fg)
        font = QFont("Inter", 30)
        font.setWeight(QFont.Weight.ExtraBold)
        painter.setFont(font)
        painter.drawText(24, 56, p.title.upper()[:28])
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self, player):
        super().__init__()
        self.player, self.worker = player, None
        self.setWindowTitle("Pulse")
        self.resize(1100, 760)
        self.visual = Visual(player)
        self.btn_play, self.btn_open, self.btn_demo = QPushButton("PLAY"), QPushButton("OPEN"), QPushButton("DEMO")
        self.btn_style = QPushButton("STYLE")
        self.btn_play.setObjectName("primary")
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, 1000)
        self.vol = QSlider(Qt.Orientation.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setValue(int(player.volume * 100))
        self.vol.setFixedWidth(100)
        self.info = QLabel("0:00 / 0:00")
        self.info.setObjectName("muted")

        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(20, 10, 20, 16)
        for wdg in (self.btn_play, self.btn_open, self.btn_demo, self.btn_style, self.seek, self.info, self.vol):
            row.addWidget(wdg)
        root = QWidget()
        col = QVBoxLayout(root)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self.visual, 1)
        col.addWidget(bar)
        self.setCentralWidget(root)

        self.btn_play.clicked.connect(player.toggle)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_demo.clicked.connect(player.load_demo)
        self.btn_style.clicked.connect(lambda: self.visual.next_scene())
        self.seek.sliderMoved.connect(lambda v: player.seek_to(v / 1000))
        self.vol.valueChanged.connect(lambda v: setattr(player, "volume", v / 100))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def tick(self):
        p = self.player
        self.visual.update()
        if not self.seek.isSliderDown():
            self.seek.setValue(int(p.pos / max(1, len(p.data)) * 1000))
        self.info.setText("%s    %s / %s    BPM %d" % (self.visual.scenes[self.visual.index].name.upper(), clock(p.position), clock(p.duration), p.bpm))
        self.btn_play.setText("PAUSE" if p.playing else "PLAY")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open audio", "", "Audio (*.wav *.flac *.ogg *.mp3)")
        if path:
            self.load_path(path)

    def load_path(self, path):
        self.worker = DecodeWorker(path)
        self.worker.done.connect(lambda res: res and self.player.set_track(*res))
        self.worker.start()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space:
            self.player.toggle()
        elif e.key() == Qt.Key.Key_Left:
            self.player.seek(-5)
        elif e.key() == Qt.Key.Key_Right:
            self.player.seek(5)
        elif e.key() == Qt.Key.Key_Tab:
            self.visual.next_scene()
        else:
            super().keyPressEvent(e)
