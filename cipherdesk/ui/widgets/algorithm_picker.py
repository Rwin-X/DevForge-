"""Algorithm picker: a grouped combo box (categories as separators)
plus the encrypt/decrypt segmented toggle."""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.models import CipherSpec, Direction


class DirectionToggle(QWidget):
    """Encrypt / Decrypt segmented control."""

    direction_changed = pyqtSignal(Direction)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._direction = Direction.ENCRYPT

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self.setObjectName("elevatedPanel")

        self.encrypt_btn = QPushButton("Encrypt", self)
        self.decrypt_btn = QPushButton("Decrypt", self)
        for btn in (self.encrypt_btn, self.decrypt_btn):
            btn.setObjectName("segmentButton")
            btn.setCheckable(True)
            btn.setFlat(True)
            layout.addWidget(btn)

        self.encrypt_btn.setChecked(True)
        self.encrypt_btn.clicked.connect(lambda: self.set_direction(Direction.ENCRYPT))
        self.decrypt_btn.clicked.connect(lambda: self.set_direction(Direction.DECRYPT))

    def set_direction(self, direction: Direction) -> None:
        self._direction = direction
        self.encrypt_btn.setChecked(direction == Direction.ENCRYPT)
        self.decrypt_btn.setChecked(direction == Direction.DECRYPT)
        self.direction_changed.emit(direction)

    def direction(self) -> Direction:
        return self._direction

    def set_decrypt_enabled(self, enabled: bool) -> None:
        self.decrypt_btn.setEnabled(enabled)
        if not enabled and self._direction == Direction.DECRYPT:
            self.set_direction(Direction.ENCRYPT)


class AlgorithmPicker(QWidget):
    """Grouped combo box listing every CipherSpec by category, plus the
    encrypt/decrypt toggle and a one-line description label."""

    algorithm_changed = pyqtSignal(str)   # emits cipher id

    def __init__(self, ciphers: List[CipherSpec], parent: QWidget | None = None):
        super().__init__(parent)
        self._ciphers = {c.id: c for c in ciphers}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(16)

        self.combo = QComboBox(self)
        self._populate(ciphers)
        self.combo.currentIndexChanged.connect(self._on_index_changed)
        row.addWidget(self.combo)

        self.direction_toggle = DirectionToggle(self)
        row.addWidget(self.direction_toggle)

        self.description_label = QLabel(self)
        self.description_label.setObjectName("descriptionLabel")
        self.description_label.setWordWrap(True)
        row.addWidget(self.description_label, 1)

        outer.addLayout(row)

        count_label = QLabel(f"{len(ciphers)} algorithms", self)
        count_label.setObjectName("tertiaryLabel")

    def _populate(self, ciphers: List[CipherSpec]) -> None:
        groups: dict[str, List[CipherSpec]] = {}
        for c in ciphers:
            groups.setdefault(c.group, []).append(c)

        first_real_index = None
        for group_name, group_ciphers in groups.items():
            self.combo.addItem(f"—  {group_name}  —")
            idx = self.combo.count() - 1
            self.combo.model().item(idx).setEnabled(False)
            for c in group_ciphers:
                self.combo.addItem(c.name, userData=c.id)
                if first_real_index is None:
                    first_real_index = self.combo.count() - 1

        if first_real_index is not None:
            self.combo.setCurrentIndex(first_real_index)

    def _on_index_changed(self, index: int) -> None:
        cipher_id = self.combo.itemData(index)
        if cipher_id is None:
            return
        spec = self._ciphers[cipher_id]
        self.description_label.setText(spec.description)
        self.direction_toggle.set_decrypt_enabled(not spec.one_way)
        self.algorithm_changed.emit(cipher_id)

    def current_cipher_id(self) -> str | None:
        return self.combo.currentData()

    def set_current_cipher_id(self, cipher_id: str) -> None:
        idx = self.combo.findData(cipher_id)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def direction(self) -> Direction:
        return self.direction_toggle.direction()
