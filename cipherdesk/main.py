"""Cipherdesk desktop entry point.

Build the QApplication, apply the stylesheet, show the main window,
run the event loop.
"""

import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.style import build_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Cipherdesk")
    app.setStyleSheet(build_stylesheet())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
