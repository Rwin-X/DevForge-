#!/usr/bin/env python3
"""
HashForge - Cryptographic File Hash Tool
Entry point
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFontDatabase, QFont

from hashforge.ui.main_window import MainWindow
from hashforge.utils.theme import ThemeManager


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("HashForge")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("HashForge")

    # Apply global stylesheet
    theme = ThemeManager()
    app.setStyleSheet(theme.get_stylesheet())

    # Set default font
    font = QFont("Inter", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
