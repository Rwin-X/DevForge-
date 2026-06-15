"""
HashForge — HashRow widget.
Displays one algorithm label + digest + copy button in a glass card row.
"""

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QApplication, QSizePolicy,
)
from PySide6.QtGui import QGuiApplication


class HashRow(QWidget):
    """Single hash display row inside a glass card."""

    def __init__(self, algorithm: str, digest: str = "", parent=None):
        super().__init__(parent)
        self.algorithm = algorithm
        self._digest = digest
        self.setObjectName("hashRow")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(12)

        # Algorithm badge
        self._algo_label = QLabel(self.algorithm)
        self._algo_label.setFixedWidth(58)
        self._algo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._algo_label.setStyleSheet("""
            background: #DBEAFE;
            color: #1D4ED8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.6px;
            border-radius: 5px;
            padding: 4px 8px;
        """)

        # Hash value
        self._hash_label = QLabel(self._digest or "—")
        self._hash_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._hash_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._hash_label.setWordWrap(False)
        self._hash_label.setStyleSheet("""
            font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
            font-size: 12px;
            color: #0F172A;
            background: transparent;
            letter-spacing: 0.3px;
        """)

        # Copy button
        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setProperty("variant", "ghost")
        self._copy_btn.setFixedSize(60, 32)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._copy)
        self._copy_btn.setEnabled(bool(self._digest))

        layout.addWidget(self._algo_label)
        layout.addWidget(self._hash_label)
        layout.addWidget(self._copy_btn)

        # Outer card styling
        self.setStyleSheet("""
            #hashRow {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            #hashRow:hover {
                border-color: #CBD5E1;
                background: #FAFBFC;
            }
        """)

    def set_digest(self, digest: str):
        self._digest = digest
        self._hash_label.setText(digest if digest else "—")
        self._copy_btn.setEnabled(bool(digest))

    def _copy(self):
        if self._digest:
            QGuiApplication.clipboard().setText(self._digest)
            self._copy_btn.setText("✓ Copied")
            self._copy_btn.setProperty("variant", "success")
            self._copy_btn.style().unpolish(self._copy_btn)
            self._copy_btn.style().polish(self._copy_btn)
            QTimer.singleShot(1800, self._reset_copy)

    def _reset_copy(self):
        self._copy_btn.setText("Copy")
        self._copy_btn.setProperty("variant", "ghost")
        self._copy_btn.style().unpolish(self._copy_btn)
        self._copy_btn.style().polish(self._copy_btn)

    def set_dark(self, dark: bool):
        if dark:
            badge_bg = "#1E3A5F"
            badge_fg = "#60A5FA"
            hash_fg  = "#E6EDF3"
            card_bg  = "#161B22"
            card_border = "#30363D"
        else:
            badge_bg = "#DBEAFE"
            badge_fg = "#1D4ED8"
            hash_fg  = "#0F172A"
            card_bg  = "#FFFFFF"
            card_border = "#E2E8F0"

        self._algo_label.setStyleSheet(f"""
            background: {badge_bg};
            color: {badge_fg};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.6px;
            border-radius: 5px;
            padding: 4px 8px;
        """)
        self._hash_label.setStyleSheet(f"""
            font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
            font-size: 12px;
            color: {hash_fg};
            background: transparent;
            letter-spacing: 0.3px;
        """)
        self.setStyleSheet(f"""
            #hashRow {{
                background: {card_bg};
                border: 1px solid {card_border};
                border-radius: 10px;
            }}
        """)
