"""PyQt6 window: a rhythm-bound torus plus a minimal control bar."""
import math
import time

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton,
                             QSlider, QVBoxLayout, QWidget)

from core.audio import COLS, decode
from core.geometry import project, rotate
from ui.style import BG, FG

TU, TV = 36, 16


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
        self.p, self.yaw, self.cr, self.mx, self.my = player, 0.6, 0.0, 0.0, 0.0
        self.last = time.monotonic()
        self.setMouseTracking(True)
        self.u = np.arange(TU)[:, None]
        self.v = np.arange(TV)[None, :]

    def mouseMoveEvent(self, e):
        self.mx = e.position().x() / max(1, self.width()) * 2 - 1
        self.my = e.position().y() / max(1, self.height()) * 2 - 1

    def _torus(self, now):
        p = self.p
        phi = self.u / TU * 2 * math.pi
        lv = p.lv[np.round(self.u / TU * (COLS - 1)).astype(int)]
        rt = 62 + lv * 95 + p.bass * 30 + p.beat_pulse * 14
        tt = self.v / TV * 2 * math.pi + phi + self.cr
        rv = rt + np.sin(tt * 3 + now * 2) * min(0.4, p.mid * 2) * 28
        rm = 190 * (1 + p.bass * 0.1 + p.beat_pulse * 0.04)
        q = rm + rv * np.cos(tt)
        return np.stack([q * np.cos(phi), rv * np.sin(tt), q * np.sin(phi)], -1), rm

    def paintEvent(self, _):
        now = time.monotonic()
        dt = min(now - self.last, 0.05)
        self.last = now
        p, k = self.p, dt * 30
        p.analyse(dt)
        self.yaw += k * (0.004 + p.energy * 0.015 + p.spin * 0.012)
        self.cr += k * (0.006 + p.energy * 0.03 + p.spin * 0.03)
        w, h = self.width(), self.height()
        cx, cy, zoom = w / 2, h * 0.46, min(w, h) / 1000
        cam = (self.yaw + self.mx * 0.35, -0.55 + self.my * 0.2)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(BG))
        pts, rm = self._torus(now)
        scr, z = project(rotate(pts, *cam), cx, cy, zoom)
        nxt_u, nxt_v = np.roll(scr, -1, 0), np.roll(scr, -1, 1)
        zu, zv = (z + np.roll(z, -1, 0)) / 2, (z + np.roll(z, -1, 1)) / 2
        A = np.concatenate([scr.reshape(-1, 2), scr[::2].reshape(-1, 2)])
        B = np.concatenate([nxt_u.reshape(-1, 2), nxt_v[::2].reshape(-1, 2)])
        Z = np.concatenate([zu.ravel(), zv[::2].ravel()])
        bucket = np.where(Z < -105, 2, np.where(Z < 105, 1, 0))
        fg = QColor(FG)
        for bk, alpha in enumerate((15, 50, 128)):
            lines = [QLineF(a[0], a[1], b[0], b[1]) for a, b in zip(A[bucket == bk].tolist(), B[bucket == bk].tolist())]
            fg.setAlpha(alpha)
            painter.setPen(QPen(fg, 1))
            painter.drawLines(lines)

        ang = np.linspace(0, 2 * math.pi, 49)
        for wv in p.waves:
            age = (now - wv) / 1.5
            if age < 1:
                rad = rm * (0.5 + age * 1.1)
                ring = np.stack([np.cos(ang) * rad, 0 * ang, np.sin(ang) * rad], -1)
                sc = project(rotate(ring, *cam), cx, cy, zoom)[0]
                fg.setAlpha(int((1 - age) * 90))
                painter.setPen(QPen(fg, 1))
                painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in sc.tolist()]))

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
        for wdg in (self.btn_play, self.btn_open, self.btn_demo, self.seek, self.info, self.vol):
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
        self.info.setText("%s / %s    BPM %d" % (clock(p.position), clock(p.duration), p.bpm))
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
        else:
            super().keyPressEvent(e)
