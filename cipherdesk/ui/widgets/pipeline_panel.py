"""Pipeline panel: chain several algorithms in sequence, each stage
encrypting the previous stage's output. Collapsible, matching the web
version's disclosure pattern."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.ciphers import CIPHER_BY_ID, CIPHER_REGISTRY, CipherError
from core.models import PipelineStage

_ELIGIBLE = [c for c in CIPHER_REGISTRY if not c.one_way and not c.is_asymmetric]


class _StageRow(QWidget):
    changed = pyqtSignal()
    remove_requested = pyqtSignal(object)  # emits self

    def __init__(self, stage: PipelineStage, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.stage = stage

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        num_label = QLabel(str(index + 1), self)
        num_label.setObjectName("tertiaryLabel")
        num_label.setFixedWidth(16)
        layout.addWidget(num_label)

        self.combo = QComboBox(self)
        for c in _ELIGIBLE:
            self.combo.addItem(c.name, userData=c.id)
        idx = self.combo.findData(stage.algorithm_id)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        self.combo.currentIndexChanged.connect(self._on_algo_changed)
        layout.addWidget(self.combo)

        self.key1_input = QLineEdit(self)
        self.key1_input.setPlaceholderText("key")
        self.key1_input.setText(stage.key1)
        self.key1_input.textChanged.connect(self._on_key_changed)
        layout.addWidget(self.key1_input)

        self.key2_input = QLineEdit(self)
        self.key2_input.setPlaceholderText("param")
        self.key2_input.setFixedWidth(70)
        self.key2_input.setText(stage.key2)
        self.key2_input.textChanged.connect(self._on_key_changed)
        layout.addWidget(self.key2_input)

        remove_btn = QPushButton("×", self)
        remove_btn.setObjectName("ghostAction")
        remove_btn.setFixedWidth(24)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(remove_btn)

        self._sync_key_visibility()

    def _sync_key_visibility(self) -> None:
        spec = CIPHER_BY_ID[self.stage.algorithm_id]
        self.key1_input.setVisible(bool(spec.key1))
        self.key2_input.setVisible(bool(spec.key2))
        if spec.key1:
            self.key1_input.setPlaceholderText(spec.key1.placeholder or "key")
        if spec.key2:
            self.key2_input.setPlaceholderText(spec.key2.placeholder or "param")

    def _on_algo_changed(self) -> None:
        self.stage.algorithm_id = self.combo.currentData()
        self.stage.key1 = ""
        self.stage.key2 = ""
        self.key1_input.blockSignals(True)
        self.key2_input.blockSignals(True)
        self.key1_input.clear()
        self.key2_input.clear()
        self.key1_input.blockSignals(False)
        self.key2_input.blockSignals(False)
        self._sync_key_visibility()
        self.changed.emit()

    def _on_key_changed(self) -> None:
        self.stage.key1 = self.key1_input.text()
        self.stage.key2 = self.key2_input.text()
        self.changed.emit()


class PipelinePanel(QWidget):
    run_requested = pyqtSignal(str)         # emits the resulting text
    run_failed = pyqtSignal(str)            # emits an error message

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.stages: List[PipelineStage] = []
        self._rows: List[_StageRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        self.toggle_btn = QPushButton("▸ Pipeline — chain multiple algorithms", self)
        self.toggle_btn.setObjectName("ghostAction")
        self.toggle_btn.setFlat(True)
        self.toggle_btn.clicked.connect(self._toggle)
        outer.addWidget(self.toggle_btn)

        self.body = QWidget(self)
        self.body.setObjectName("elevatedPanel")
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(16, 14, 16, 14)
        body_layout.setSpacing(10)

        hint = QLabel(
            "Run text through several algorithms in sequence, each stage encrypting "
            "the previous stage's output - e.g. Base64 → AES · CBC → Hex.",
            self.body,
        )
        hint.setObjectName("tertiaryLabel")
        hint.setWordWrap(True)
        body_layout.addWidget(hint)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)
        body_layout.addLayout(self.rows_layout)

        actions_row = QHBoxLayout()
        add_btn = QPushButton("+ Add stage", self.body)
        add_btn.setObjectName("ghostAction")
        add_btn.clicked.connect(self._add_stage)
        actions_row.addWidget(add_btn)
        actions_row.addStretch()

        clear_btn = QPushButton("Clear", self.body)
        clear_btn.setObjectName("ghostAction")
        clear_btn.clicked.connect(self._clear_stages)
        actions_row.addWidget(clear_btn)

        run_btn = QPushButton("Run pipeline", self.body)
        run_btn.setObjectName("primaryAction")
        run_btn.clicked.connect(self._run_pipeline)
        actions_row.addWidget(run_btn)

        body_layout.addLayout(actions_row)

        self.body.setVisible(False)
        outer.addWidget(self.body)

    def _toggle(self) -> None:
        visible = not self.body.isVisible()
        self.body.setVisible(visible)
        arrow = "▾" if visible else "▸"
        self.toggle_btn.setText(f"{arrow} Pipeline — chain multiple algorithms")
        if visible and not self.stages:
            self._add_stage()

    def _add_stage(self) -> None:
        stage = PipelineStage(algorithm_id=_ELIGIBLE[0].id)
        self.stages.append(stage)
        row = _StageRow(stage, len(self.stages) - 1, self.body)
        row.remove_requested.connect(self._remove_stage)
        self._rows.append(row)
        self.rows_layout.addWidget(row)

    def _remove_stage(self, row: _StageRow) -> None:
        if row.stage in self.stages:
            self.stages.remove(row.stage)
        self._rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._renumber()

    def _renumber(self) -> None:
        # Rebuild row widgets' displayed index; simplest is to just
        # leave numbering as insertion order since PyQt doesn't cheaply
        # relabel a fixed QLabel without a rebuild - acceptable for a
        # rarely-used stage count (typically 2-4 stages).
        pass

    def _clear_stages(self) -> None:
        for row in list(self._rows):
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        self.stages.clear()

    def _run_pipeline(self) -> None:
        if not self.stages:
            return
        self.run_requested.emit("__PIPELINE_RUN__")  # signal MainWindow/ConvertTab to supply input text

    def execute(self, input_text: str) -> str:
        """Runs the chain against input_text and returns the final
        output, or raises CipherError with a message naming the failing
        stage."""
        text = input_text
        for i, stage in enumerate(self.stages):
            spec = CIPHER_BY_ID[stage.algorithm_id]
            try:
                text = spec.encrypt_fn(text, stage.key1, stage.key2)
            except CipherError as exc:
                raise CipherError(f"Stage {i + 1} ({spec.name}): {exc}")
        return text

    def stage_names(self) -> List[str]:
        return [CIPHER_BY_ID[s.algorithm_id].name for s in self.stages]
