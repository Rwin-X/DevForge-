#!/usr/bin/env python3
"""VaultNotes - Minimal Markdown Note-Taking Application"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from vaultnotes.app import VaultNotes


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VaultNotes")
    app.setOrganizationName("VaultNotes")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = VaultNotes()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
