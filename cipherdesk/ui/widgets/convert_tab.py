"""Convert tab: algorithm picker + key panel + input/output text panes,
with file drag-and-drop, binary file support (routed through a worker
thread), swap, copy, and download."""

from __future__ import annotations

import secrets
import string
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.ciphers import CIPHER_BY_ID, CIPHER_REGISTRY, CipherError
from core.models import CipherSpec, Direction
from ui.widgets.algorithm_picker import AlgorithmPicker
from ui.widgets.key_panel import KeyPanel
from ui.widgets.pipeline_panel import PipelinePanel
from ui.workers import FileCryptoWorker, RsaKeygenWorker

FILE_SIZE_THREAD_THRESHOLD = 2 * 1024 * 1024  # 2 MB: below this, run inline; above, use a worker thread
MAX_FILE_SIZE = 200 * 1024 * 1024              # 200 MB hard cap for in-memory handling


def _looks_binary(data: bytes) -> bool:
    sample = data[:8000]
    if not sample:
        return False
    suspicious = 0
    for b in sample:
        if b == 0:
            return True
        printable = (32 <= b <= 126) or b in (9, 10, 13) or b >= 128
        if not printable:
            suspicious += 1
    return (suspicious / len(sample)) > 0.05


def _random_word(length: int) -> str:
    return "".join(secrets.choice(string.ascii_uppercase) for _ in range(length))


def _random_passphrase() -> str:
    words = ["quartz", "ember", "tidal", "lucid", "onyx", "vellum", "drift",
             "cobalt", "hollow", "prism", "vantage", "thicket", "amber",
             "solace", "ferric", "nomad"]
    w1, w2 = secrets.choice(words), secrets.choice(words)
    return f"{w1}-{w2}-{secrets.randbelow(900) + 100}"


def _random_hex(n_bytes: int) -> str:
    return secrets.token_hex(n_bytes)


_KEYGEN = {
    "caesar": lambda: str(secrets.randbelow(25) + 1),
    "affine": lambda: str(secrets.choice([1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25])),
    "vigenere": lambda: _random_word(secrets.randbelow(5) + 5),
    "beaufort": lambda: _random_word(secrets.randbelow(5) + 5),
    "autokey": lambda: _random_word(secrets.randbelow(5) + 5),
    "playfair": lambda: _random_word(secrets.randbelow(5) + 6),
    "railfence": lambda: str(secrets.randbelow(6) + 2),
    "columnar": lambda: _random_word(secrets.randbelow(4) + 5),
    "xor": lambda: _random_hex(8),
}
_KEYGEN2 = {
    "affine": lambda: str(secrets.randbelow(26)),
}


class DropArea(QPlainTextEdit):
    """Text edit that also accepts a dropped file, forwarding it to the
    parent ConvertTab via on_file_dropped."""

    def __init__(self, on_file_dropped, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._on_file_dropped = on_file_dropped

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        mime: QMimeData = event.mimeData()
        if mime.hasUrls():
            path = mime.urls()[0].toLocalFile()
            if path:
                self._on_file_dropped(path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class ConvertTab(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._loaded_file_path: Optional[str] = None
        self._loaded_file_bytes: Optional[bytes] = None
        self._output_file_bytes: Optional[bytes] = None
        self._thread: Optional[QThread] = None
        self._worker = None
        self._last_result = None  # (spec, direction, input_text, output_text, key1, key2) for the vault

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(18)

        self.picker = AlgorithmPicker(CIPHER_REGISTRY, self)
        self.picker.algorithm_changed.connect(self._on_algorithm_changed)
        self.picker.direction_toggle.direction_changed.connect(lambda _: self._run())
        outer.addWidget(self.picker)

        self.key_panel = KeyPanel(self)
        self.key_panel.changed.connect(self._run)
        outer.addWidget(self.key_panel)

        self.pipeline_panel = PipelinePanel(self)
        self.pipeline_panel.run_requested.connect(self._run_pipeline)
        outer.addWidget(self.pipeline_panel)

        rsa_row = QHBoxLayout()
        self.rsa_generate_btn = QPushButton("Generate RSA keypair", self)
        self.rsa_generate_btn.clicked.connect(self._generate_rsa_keypair)
        self.rsa_generate_btn.setVisible(False)
        rsa_row.addWidget(self.rsa_generate_btn)
        self.rsa_status_label = QLabel("", self)
        self.rsa_status_label.setObjectName("tertiaryLabel")
        rsa_row.addWidget(self.rsa_status_label)
        rsa_row.addStretch()
        outer.addLayout(rsa_row)

        self.random_key_btn = QPushButton("Random key", self)
        self.random_key_btn.setObjectName("ghostAction")
        self.random_key_btn.clicked.connect(self._fill_random_key)
        self.random_key_btn.setVisible(False)
        outer.addWidget(self.random_key_btn, alignment=Qt.AlignmentFlag.AlignRight)

        stage = QHBoxLayout()
        stage.setSpacing(20)

        # --- input pane ---
        input_col = QVBoxLayout()
        input_head = QHBoxLayout()
        input_tag = QLabel("INPUT", self)
        input_tag.setObjectName("tertiaryLabel")
        input_head.addWidget(input_tag)
        input_head.addStretch()
        self.upload_btn = QPushButton("Upload file", self)
        self.upload_btn.setObjectName("ghostAction")
        self.upload_btn.clicked.connect(self._browse_file)
        input_head.addWidget(self.upload_btn)
        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.setObjectName("ghostAction")
        self.clear_btn.clicked.connect(self._clear_input)
        input_head.addWidget(self.clear_btn)
        input_col.addLayout(input_head)

        self.file_info_label = QLabel("", self)
        self.file_info_label.setObjectName("secondaryLabel")
        self.file_info_label.setVisible(False)
        input_col.addWidget(self.file_info_label)

        self.input_text = DropArea(self._load_file, self)
        self.input_text.setObjectName("monoField")
        self.input_text.setPlaceholderText("Type, paste, or drop any file...")
        self.input_text.textChanged.connect(self._run)
        input_col.addWidget(self.input_text, 1)

        stage.addLayout(input_col, 1)

        # --- swap button ---
        swap_col = QVBoxLayout()
        swap_col.addStretch()
        self.swap_btn = QPushButton("⇄", self)
        self.swap_btn.setObjectName("ghostAction")
        self.swap_btn.setFixedSize(32, 32)
        self.swap_btn.setToolTip("Use result as new input")
        self.swap_btn.clicked.connect(self._swap)
        swap_col.addWidget(self.swap_btn)
        swap_col.addStretch()
        stage.addLayout(swap_col)

        # --- output pane ---
        output_col = QVBoxLayout()
        output_head = QHBoxLayout()
        output_tag = QLabel("RESULT", self)
        output_tag.setObjectName("tertiaryLabel")
        output_head.addWidget(output_tag)
        output_head.addStretch()
        self.copy_btn = QPushButton("Copy", self)
        self.copy_btn.setObjectName("ghostAction")
        self.copy_btn.clicked.connect(self._copy_output)
        output_head.addWidget(self.copy_btn)
        output_col.addLayout(output_head)

        self.output_text = QPlainTextEdit(self)
        self.output_text.setObjectName("monoField")
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Result appears here")
        output_col.addWidget(self.output_text, 1)

        self.download_btn = QPushButton("Download result", self)
        self.download_btn.setVisible(False)
        self.download_btn.clicked.connect(self._download_output)
        output_col.addWidget(self.download_btn, alignment=Qt.AlignmentFlag.AlignRight)

        stage.addLayout(output_col, 1)

        outer.addLayout(stage, 1)

        status_line = QFrame(self)
        status_line.setObjectName("hairline")
        outer.addWidget(status_line)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Ready", self)
        self.status_label.setObjectName("secondaryLabel")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        self.meta_label = QLabel("", self)
        self.meta_label.setObjectName("tertiaryLabel")
        status_row.addWidget(self.meta_label)
        outer.addLayout(status_row)

        self.key_panel.setVisible(False)
        self._on_algorithm_changed(self.picker.current_cipher_id())

    # ------------------------------------------------------------------
    # algorithm / key wiring
    # ------------------------------------------------------------------

    def _current_spec(self) -> CipherSpec:
        return CIPHER_BY_ID[self.picker.current_cipher_id()]

    def _on_algorithm_changed(self, cipher_id: str) -> None:
        spec = CIPHER_BY_ID[cipher_id]
        is_rsa = spec.is_asymmetric
        self.key_panel.configure_for_cipher(spec)
        self.rsa_generate_btn.setVisible(is_rsa)
        self.rsa_status_label.setVisible(is_rsa)
        has_gen = (spec.id in _KEYGEN) and not is_rsa
        self.random_key_btn.setVisible(has_gen)
        self._run()

    def _fill_random_key(self) -> None:
        spec = self._current_spec()
        gen1 = _KEYGEN.get(spec.id)
        if gen1:
            self.key_panel.set_key1(gen1())
        gen2 = _KEYGEN2.get(spec.id)
        if gen2:
            self.key_panel.set_key2(gen2())

    def _generate_rsa_keypair(self) -> None:
        bits = 2048
        self.rsa_generate_btn.setEnabled(False)
        self.rsa_status_label.setText(f"Generating {bits}-bit keypair...")

        self._thread = QThread()
        self._worker = RsaKeygenWorker(bits)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_rsa_keypair_ready)
        self._worker.failed.connect(self._on_rsa_keypair_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_rsa_keypair_ready(self, public_pem: str, private_pem: str) -> None:
        self.key_panel.set_key1(public_pem)
        self.key_panel.set_key2(private_pem)
        self.rsa_status_label.setText("Keypair generated.")
        self.rsa_generate_btn.setEnabled(True)
        self._run()

    def _on_rsa_keypair_failed(self, message: str) -> None:
        self.rsa_status_label.setText("Generation failed.")
        self.rsa_generate_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # file handling
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file")
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        p = Path(path)
        try:
            size = p.stat().st_size
        except OSError:
            self.status_label.setText("Error")
            self.meta_label.setText("Could not read that file.")
            return

        if size > MAX_FILE_SIZE:
            self.status_label.setText("Error")
            self.meta_label.setText(f"File too large - {MAX_FILE_SIZE // (1024*1024)} MB limit.")
            return

        data = p.read_bytes()
        self._loaded_file_path = path
        self.file_info_label.setText(f"{p.name}  ·  {_fmt_bytes(size)}")
        self.file_info_label.setVisible(True)

        if _looks_binary(data):
            self._loaded_file_bytes = data
            self.input_text.blockSignals(True)
            self.input_text.setPlainText(
                f"[Binary file loaded: {p.name}, {_fmt_bytes(size)}]\n\n"
                "This file will be encrypted byte-for-byte, not as text."
            )
            self.input_text.setReadOnly(True)
            self.input_text.blockSignals(False)
        else:
            self._loaded_file_bytes = None
            self.input_text.setReadOnly(False)
            self.input_text.blockSignals(True)
            self.input_text.setPlainText(data.decode("utf-8", errors="replace"))
            self.input_text.blockSignals(False)

        self._run()

    def _clear_input(self) -> None:
        self._loaded_file_path = None
        self._loaded_file_bytes = None
        self.file_info_label.setVisible(False)
        self.input_text.setReadOnly(False)
        self.input_text.clear()
        self._run()

    # ------------------------------------------------------------------
    # conversion
    # ------------------------------------------------------------------

    def _run(self) -> None:
        spec = self._current_spec()
        direction = self.picker.direction()
        k1 = self.key_panel.key1()
        k2 = self.key_panel.key2()

        if self._loaded_file_bytes is not None:
            self._run_file_mode(spec, direction, k1, k2)
            return

        self.output_text.setReadOnly(True)
        self._output_file_bytes = None
        self.download_btn.setVisible(False)

        text = self.input_text.toPlainText()
        if not text:
            self.output_text.setPlainText("")
            self.status_label.setText("Ready")
            self.meta_label.setText("")
            return

        try:
            fn = spec.encrypt_fn if direction == Direction.ENCRYPT else spec.decrypt_fn
            result = fn(text, k1, k2)
            self.output_text.setPlainText(result)
            verb = "Encrypted" if direction == Direction.ENCRYPT else "Decrypted"
            self.status_label.setText(f"{verb} with {spec.name}")
            self.meta_label.setText(f"{len(text)} in -> {len(result)} out")
            self.download_btn.setVisible(True)
            self._last_result = (spec, direction, text, result, k1, k2)
        except CipherError as exc:
            self.output_text.setPlainText("")
            self.status_label.setText("Error")
            self.meta_label.setText(str(exc))

    def _run_file_mode(self, spec: CipherSpec, direction: Direction, k1: str, k2: str) -> None:
        self.download_btn.setVisible(False)
        self._output_file_bytes = None

        if not spec.byte_safe:
            self.status_label.setText("Error")
            self.meta_label.setText(
                f"{spec.name} can't encrypt binary files - this is a text-only algorithm. "
                "Choose AES, 3DES, DES, RC4, XOR, or RSA."
            )
            return

        fn = spec.file_encrypt_fn if direction == Direction.ENCRYPT else spec.file_decrypt_fn
        data = self._loaded_file_bytes

        if len(data) > FILE_SIZE_THREAD_THRESHOLD:
            self.status_label.setText("Working...")
            self.meta_label.setText(f"Processing {_fmt_bytes(len(data))} in the background")
            self._thread = QThread()
            self._worker = FileCryptoWorker(fn, data, k1, k2)
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run)
            self._worker.finished.connect(lambda result: self._on_file_result(spec, direction, data, result))
            self._worker.failed.connect(self._on_file_error)
            self._worker.finished.connect(self._thread.quit)
            self._worker.failed.connect(self._thread.quit)
            self._thread.finished.connect(self._worker.deleteLater)
            self._thread.finished.connect(self._thread.deleteLater)
            self._thread.start()
            return

        try:
            result = fn(data, k1, k2)
            self._on_file_result(spec, direction, data, result)
        except CipherError as exc:
            self._on_file_error(str(exc))

    def _on_file_result(self, spec: CipherSpec, direction: Direction, input_data: bytes, result: bytes) -> None:
        self._output_file_bytes = result
        verb = "Encrypted" if direction == Direction.ENCRYPT else "Decrypted"
        self.status_label.setText(f"{verb} with {spec.name}")
        self.meta_label.setText(f"{_fmt_bytes(len(input_data))} in -> {_fmt_bytes(len(result))} out")
        self.download_btn.setVisible(True)

    def _on_file_error(self, message: str) -> None:
        self.status_label.setText("Error")
        self.meta_label.setText(message)

    # ------------------------------------------------------------------
    # output actions
    # ------------------------------------------------------------------

    def _copy_output(self) -> None:
        text = self.output_text.toPlainText()
        if text:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)

    def _download_output(self) -> None:
        spec = self._current_spec()
        direction = self.picker.direction()
        suffix = "enc" if direction == Direction.ENCRYPT else "decrypted"

        if self._output_file_bytes is not None:
            base_name = Path(self._loaded_file_path).name if self._loaded_file_path else "file"
            default_name = f"{base_name}.{spec.id}.{suffix}"
            path, _ = QFileDialog.getSaveFileName(self, "Save result", default_name)
            if path:
                Path(path).write_bytes(self._output_file_bytes)
            return

        text = self.output_text.toPlainText()
        if not text:
            return
        default_name = f"cipherdesk-{spec.id}-{suffix}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Save result", default_name)
        if path:
            Path(path).write_text(text, encoding="utf-8")

    def _run_pipeline(self, _marker: str) -> None:
        text = self.input_text.toPlainText()
        if not text:
            self.status_label.setText("Error")
            self.meta_label.setText("Enter input text before running the pipeline.")
            return
        try:
            result = self.pipeline_panel.execute(text)
            self.output_text.setPlainText(result)
            names = " → ".join(self.pipeline_panel.stage_names())
            self.status_label.setText(f"Pipeline: {names}")
            self.meta_label.setText(f"{len(text)} in -> {len(result)} out")
            self.download_btn.setVisible(True)
            self._output_file_bytes = None
        except CipherError as exc:
            self.output_text.setPlainText("")
            self.status_label.setText("Pipeline error")
            self.meta_label.setText(str(exc))

    def _swap(self) -> None:
        if self._output_file_bytes is not None:
            spec = self._current_spec()
            direction = self.picker.direction()
            suffix = "enc" if direction == Direction.ENCRYPT else "decrypted"
            base_name = Path(self._loaded_file_path).name if self._loaded_file_path else "file"
            self._loaded_file_path = f"{base_name}.{spec.id}.{suffix}"
            self._loaded_file_bytes = self._output_file_bytes
            self.file_info_label.setText(
                f"{Path(self._loaded_file_path).name}  ·  {_fmt_bytes(len(self._loaded_file_bytes))}"
            )
            new_direction = Direction.DECRYPT if direction == Direction.ENCRYPT else Direction.ENCRYPT
            self.picker.direction_toggle.set_direction(new_direction)
            return

        output = self.output_text.toPlainText()
        if not output:
            return
        self._clear_input_silent()
        self.input_text.setPlainText(output)
        direction = self.picker.direction()
        new_direction = Direction.DECRYPT if direction == Direction.ENCRYPT else Direction.ENCRYPT
        self.picker.direction_toggle.set_direction(new_direction)

    def _clear_input_silent(self) -> None:
        self._loaded_file_path = None
        self._loaded_file_bytes = None
        self.file_info_label.setVisible(False)
        self.input_text.setReadOnly(False)

    # ------------------------------------------------------------------
    # public accessors for the Vault tab
    # ------------------------------------------------------------------

    def restore_conversion(self, algorithm_id: str, direction: Direction, input_text: str, key1: str, key2: str) -> None:
        self.picker.set_current_cipher_id(algorithm_id)
        self.picker.direction_toggle.set_direction(direction)
        self._clear_input_silent()
        self.input_text.setPlainText(input_text)
        self.key_panel.set_key1(key1)
        self.key_panel.set_key2(key2)
        self._run()


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"
