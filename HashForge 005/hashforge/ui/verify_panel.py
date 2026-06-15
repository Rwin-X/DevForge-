"""
HashForge — VerifyPanel widget.
Lets users paste a hash value and compares it against computed results.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
)


class VerifyPanel(QWidget):
    """Hash verification input + result display."""

    verify_requested = Signal(str)  # emits the user-supplied hash string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("verifyPanel")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel("Verify Hash")
        header.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: #0F172A; background: transparent;"
        )

        sub = QLabel("Paste an expected hash to compare against computed results")
        sub.setStyleSheet("font-size: 12px; color: #64748B; background: transparent;")

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Paste MD5 / SHA1 / SHA256 / SHA512 hash here…")
        self._input.setMinimumHeight(38)
        self._input.returnPressed.connect(self._verify)

        self._btn = QPushButton("Verify")
        self._btn.setProperty("variant", "primary")
        self._btn.setFixedHeight(38)
        self._btn.setFixedWidth(80)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.clicked.connect(self._verify)

        input_row.addWidget(self._input)
        input_row.addWidget(self._btn)

        self._result_label = QLabel("")
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent;")
        self._result_label.setVisible(False)

        layout.addWidget(header)
        layout.addWidget(sub)
        layout.addLayout(input_row)
        layout.addWidget(self._result_label)

        self.setStyleSheet("""
            #verifyPanel {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

    def _verify(self):
        value = self._input.text().strip().lower()
        if value:
            self.verify_requested.emit(value)

    def show_result(self, matched: bool, algorithm: str = ""):
        self._result_label.setVisible(True)
        if matched:
            self._result_label.setText(f"✓  Match — {algorithm}")
            self._result_label.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #10B981; "
                "background: #D1FAE5; border-radius: 8px; padding: 8px;"
            )
        else:
            self._result_label.setText("✗  No match — hash does not correspond to this file")
            self._result_label.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #EF4444; "
                "background: #FEE2E2; border-radius: 8px; padding: 8px;"
            )

    def clear(self):
        self._input.clear()
        self._result_label.setVisible(False)

    def set_dark(self, dark: bool):
        if dark:
            self.setStyleSheet("""
                #verifyPanel {
                    background: #161B22;
                    border: 1px solid #30363D;
                    border-radius: 12px;
                }
            """)
            for lbl_style, lbl in [
                ("font-weight: 700; font-size: 13px; color: #E6EDF3; background: transparent;", None),
            ]:
                pass
        else:
            self.setStyleSheet("""
                #verifyPanel {
                    background: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
