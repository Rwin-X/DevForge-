"""Dynamic key input panel: shows zero, one, or two key fields
depending on the selected cipher's requirements. PEM fields (RSA) get
multi-line text boxes; everything else gets a single-line field with
an optional show/hide toggle."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.models import CipherSpec, KeyFieldSpec, KeyKind


class _SingleKeyField(QWidget):
    """One key field: label, input (line or PEM box), hint, and an
    optional show/hide toggle for maskable text fields."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._kind = KeyKind.TEXT

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.label = QLabel(self)
        self.label.setObjectName("fieldLabel")
        header.addWidget(self.label)
        header.addStretch()
        self.peek_btn = QPushButton("Show", self)
        self.peek_btn.setObjectName("ghostAction")
        self.peek_btn.setFlat(True)
        self.peek_btn.clicked.connect(self._toggle_peek)
        header.addWidget(self.peek_btn)
        layout.addLayout(header)

        self.line_input = QLineEdit(self)
        self.line_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_input.textChanged.connect(self.changed.emit)
        layout.addWidget(self.line_input)

        self.pem_input = QPlainTextEdit(self)
        self.pem_input.setObjectName("monoField")
        self.pem_input.setFixedHeight(90)
        self.pem_input.textChanged.connect(self.changed.emit)
        layout.addWidget(self.pem_input)

        self.hint_label = QLabel(self)
        self.hint_label.setObjectName("tertiaryLabel")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

    def configure(self, spec: KeyFieldSpec) -> None:
        self._kind = spec.kind
        self.label.setText(spec.label)
        self.hint_label.setText(spec.hint)
        is_pem = spec.kind == KeyKind.PEM
        self.line_input.setVisible(not is_pem)
        self.pem_input.setVisible(is_pem)
        self.peek_btn.setVisible(not is_pem)
        if not is_pem:
            self.line_input.setPlaceholderText(spec.placeholder)
            self.line_input.clear()
            self.line_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.peek_btn.setText("Show")
        else:
            self.pem_input.setPlaceholderText(spec.placeholder)
            self.pem_input.clear()

    def _toggle_peek(self) -> None:
        showing = self.line_input.echoMode() == QLineEdit.EchoMode.Normal
        self.line_input.setEchoMode(
            QLineEdit.EchoMode.Password if showing else QLineEdit.EchoMode.Normal
        )
        self.peek_btn.setText("Hide" if not showing else "Show")

    def value(self) -> str:
        if self._kind == KeyKind.PEM:
            return self.pem_input.toPlainText()
        return self.line_input.text()

    def set_value(self, value: str) -> None:
        if self._kind == KeyKind.PEM:
            self.pem_input.setPlainText(value)
        else:
            self.line_input.setText(value)


class KeyPanel(QWidget):
    """Holds up to two _SingleKeyField widgets, shown/hidden per the
    active cipher's key1/key2 specs."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(28)

        self.field1 = _SingleKeyField(self)
        self.field2 = _SingleKeyField(self)
        self.field1.changed.connect(self.changed.emit)
        self.field2.changed.connect(self.changed.emit)
        layout.addWidget(self.field1, 1)
        layout.addWidget(self.field2, 1)

    def configure_for_cipher(self, spec: CipherSpec) -> None:
        if spec.key1:
            self.field1.setVisible(True)
            self.field1.configure(spec.key1)
        else:
            self.field1.setVisible(False)

        if spec.key2:
            self.field2.setVisible(True)
            self.field2.configure(spec.key2)
        else:
            self.field2.setVisible(False)

        self.setVisible(bool(spec.key1 or spec.key2))

    def key1(self) -> str:
        return self.field1.value()

    def key2(self) -> str:
        return self.field2.value()

    def set_key1(self, value: str) -> None:
        self.field1.set_value(value)

    def set_key2(self, value: str) -> None:
        self.field2.set_value(value)
