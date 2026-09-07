"""Entry point for passcheck."""

import sys

from PyQt6.QtWidgets import QApplication

from passcheck.ui.main_window import MainWindow, apply_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    apply_stylesheet(app)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
