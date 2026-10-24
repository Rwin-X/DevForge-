"""Pulse for PyQt6: desktop player with a rhythm-bound torus."""
import sys

from PyQt6.QtWidgets import QApplication

from core.audio import Player
from ui.qt_window import MainWindow
from ui.style import QSS


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    player = Player()
    app.aboutToQuit.connect(player.close)
    win = MainWindow(player)
    win.show()
    if len(sys.argv) > 1:
        win.load_path(sys.argv[1])
    else:
        player.load_demo()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
