#!/usr/bin/env python3
"""
StegoForge — LSB Image Steganography Tool
Minimal white/blue GUI for hiding and extracting text data inside PNG images.

Part of the devforge toolkit.
"""

import sys
import struct
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog, QStackedWidget,
    QFrame, QMessageBox, QLineEdit, QCheckBox, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QFont, QIcon

from PIL import Image
import numpy as np

# ----------------------------------------------------------------------------
# Core LSB Steganography Engine
# ----------------------------------------------------------------------------

MAGIC_HEADER = b"SFG1"  # StegoForge v1 marker


class StegoError(Exception):
    pass


def _text_to_bits(data: bytes) -> np.ndarray:
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return bits


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits).tobytes()


def encode_image(cover_path: str, message: str, output_path: str, password: str = "") -> None:
    """Hide `message` inside the cover image using 1-bit LSB embedding."""
    img = Image.open(cover_path)
    img = img.convert("RGB")
    arr = np.array(img)

    payload = message.encode("utf-8")

    if password:
        payload = _xor_cipher(payload, password.encode("utf-8"))

    # Build packet: MAGIC (4 bytes) + length (4 bytes, big-endian) + payload
    packet = MAGIC_HEADER + struct.pack(">I", len(payload)) + payload
    bits = _text_to_bits(packet)

    capacity = arr.size  # one bit per channel value
    if bits.size > capacity:
        max_chars = (capacity // 8) - 9
        raise StegoError(
            f"Message too large for this image.\n"
            f"Capacity: ~{max_chars} characters. Message: {len(message)} characters."
        )

    flat = arr.reshape(-1)
    flat_bits = flat.copy()

    # Clear LSBs then set them to payload bits
    flat_bits[:bits.size] = (flat_bits[:bits.size] & 0xFE) | bits

    new_arr = flat_bits.reshape(arr.shape).astype(np.uint8)
    out_img = Image.fromarray(new_arr, mode="RGB")
    out_img.save(output_path, format="PNG")


def decode_image(stego_path: str, password: str = "") -> str:
    """Extract a hidden message from a stego image."""
    img = Image.open(stego_path)
    img = img.convert("RGB")
    arr = np.array(img)
    flat = arr.reshape(-1)

    header_bits_needed = 8 * 8  # magic(4) + length(4) = 8 bytes
    if flat.size < header_bits_needed:
        raise StegoError("Image too small to contain valid data.")

    header_bits = flat[:header_bits_needed] & 1
    header_bytes = _bits_to_bytes(header_bits)

    magic = header_bytes[:4]
    if magic != MAGIC_HEADER:
        raise StegoError("No hidden StegoForge data found in this image.")

    length = struct.unpack(">I", header_bytes[4:8])[0]

    total_bits_needed = 8 * (8 + length)
    if flat.size < total_bits_needed:
        raise StegoError("Image data is corrupted or incomplete.")

    payload_bits = flat[header_bits_needed:total_bits_needed] & 1
    payload = _bits_to_bytes(payload_bits)

    if password:
        payload = _xor_cipher(payload, password.encode("utf-8"))

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        raise StegoError("Wrong password or corrupted data.")


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    """Simple XOR stream cipher (lightweight obfuscation, not cryptographic security)."""
    if not key:
        return data
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def image_capacity_chars(image_path: str) -> int:
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    capacity_bits = arr.size
    capacity_bytes = capacity_bits // 8
    return max(0, capacity_bytes - 9)


# ----------------------------------------------------------------------------
# Worker Thread (keeps UI responsive)
# ----------------------------------------------------------------------------

class StegoWorker(QThread):
    finished_ok = Signal(str)
    finished_err = Signal(str)

    def __init__(self, mode: str, **kwargs):
        super().__init__()
        self.mode = mode
        self.kwargs = kwargs

    def run(self):
        try:
            if self.mode == "encode":
                encode_image(
                    self.kwargs["cover_path"],
                    self.kwargs["message"],
                    self.kwargs["output_path"],
                    self.kwargs.get("password", ""),
                )
                self.finished_ok.emit(self.kwargs["output_path"])
            elif self.mode == "decode":
                result = decode_image(
                    self.kwargs["stego_path"],
                    self.kwargs.get("password", ""),
                )
                self.finished_ok.emit(result)
        except StegoError as e:
            self.finished_err.emit(str(e))
        except Exception as e:
            self.finished_err.emit(f"Unexpected error: {e}")


# ----------------------------------------------------------------------------
# Style Sheet — Minimal White & Blue
# ----------------------------------------------------------------------------

STYLE = """
QMainWindow, QWidget {
    background-color: #FFFFFF;
    color: #10233E;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}

QLabel#Title {
    font-size: 22px;
    font-weight: 700;
    color: #0B3D91;
    letter-spacing: 1px;
}

QLabel#Subtitle {
    font-size: 12px;
    color: #7A8CA3;
    letter-spacing: 2px;
}

QLabel#SectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #2E5AAC;
    letter-spacing: 1px;
}

QLabel#InfoLabel {
    font-size: 11px;
    color: #8A98AC;
}

QLabel#PreviewFrame {
    background-color: #F4F7FC;
    border: 1px solid #DCE6F5;
    border-radius: 6px;
}

QPushButton {
    background-color: #0B57D0;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #0A46AD;
}

QPushButton:pressed {
    background-color: #083A8F;
}

QPushButton:disabled {
    background-color: #C7D4EA;
    color: #FFFFFF;
}

QPushButton#SecondaryButton {
    background-color: #FFFFFF;
    color: #0B57D0;
    border: 1px solid #B9CDEF;
}

QPushButton#SecondaryButton:hover {
    background-color: #F0F5FD;
}

QPushButton#TabButton {
    background-color: #F4F7FC;
    color: #5A6C88;
    border: 1px solid #E1E9F7;
    border-radius: 6px;
    padding: 10px 24px;
    font-weight: 600;
}

QPushButton#TabButton:checked {
    background-color: #0B57D0;
    color: #FFFFFF;
    border: 1px solid #0B57D0;
}

QTextEdit, QLineEdit {
    background-color: #FAFCFF;
    border: 1px solid #DCE6F5;
    border-radius: 6px;
    padding: 8px;
    font-size: 13px;
    color: #10233E;
    selection-background-color: #B9CDEF;
}

QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #0B57D0;
}

QCheckBox {
    font-size: 12px;
    color: #3A4A63;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #B9CDEF;
    border-radius: 3px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #0B57D0;
    border: 1px solid #0B57D0;
}

QFrame#Divider {
    background-color: #EAF0FA;
    max-height: 1px;
}

QProgressBar {
    border: none;
    background-color: #EAF0FA;
    border-radius: 3px;
    height: 4px;
}

QProgressBar::chunk {
    background-color: #0B57D0;
    border-radius: 3px;
}

QScrollBar:vertical {
    background: #F4F7FC;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: #C7D4EA;
    border-radius: 4px;
}
"""


# ----------------------------------------------------------------------------
# UI Components
# ----------------------------------------------------------------------------

class DropZone(QLabel):
    """Clickable image preview / drop target."""

    def __init__(self, on_click):
        super().__init__()
        self.setObjectName("PreviewFrame")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(220)
        self.setCursor(Qt.PointingHandCursor)
        self.setText("Click to select an image\n\nPNG recommended")
        self.setAcceptDrops(True)
        self._on_click = on_click
        self.image_path = None

    def mousePressEvent(self, event):
        self._on_click()

    def set_image(self, path: str):
        self.image_path = path
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(360, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)
        else:
            self.setText("Unable to preview this file")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith((".png", ".bmp", ".jpg", ".jpeg")):
                self.image_path = path
                self.set_image(path)
                self.parent().parent().on_image_loaded(path)


# ----------------------------------------------------------------------------
# Encode Panel
# ----------------------------------------------------------------------------

class EncodePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 16, 0, 0)

        lbl = QLabel("COVER IMAGE")
        lbl.setObjectName("SectionLabel")
        layout.addWidget(lbl)

        self.drop_zone = DropZone(self.select_image)
        layout.addWidget(self.drop_zone)

        self.capacity_label = QLabel("Select an image to see capacity")
        self.capacity_label.setObjectName("InfoLabel")
        layout.addWidget(self.capacity_label)

        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        lbl2 = QLabel("SECRET MESSAGE")
        lbl2.setObjectName("SectionLabel")
        layout.addWidget(lbl2)

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Type the message you want to hide...")
        self.message_input.setMinimumHeight(120)
        self.message_input.textChanged.connect(self.update_char_count)
        layout.addWidget(self.message_input)

        self.char_count_label = QLabel("0 characters")
        self.char_count_label.setObjectName("InfoLabel")
        layout.addWidget(self.char_count_label)

        pw_row = QHBoxLayout()
        self.use_password = QCheckBox("Protect with password (XOR obfuscation)")
        self.use_password.stateChanged.connect(self.toggle_password_field)
        pw_row.addWidget(self.use_password)
        layout.addLayout(pw_row)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setVisible(False)
        layout.addWidget(self.password_input)

        layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_row = QHBoxLayout()
        self.encode_btn = QPushButton("Hide Message in Image")
        self.encode_btn.clicked.connect(self.run_encode)
        btn_row.addWidget(self.encode_btn)
        layout.addLayout(btn_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("InfoLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def toggle_password_field(self, state):
        self.password_input.setVisible(bool(state))

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.png *.bmp *.jpg *.jpeg)"
        )
        if path:
            self.on_image_loaded(path)

    def on_image_loaded(self, path: str):
        self.drop_zone.set_image(path)
        try:
            cap = image_capacity_chars(path)
            self.capacity_label.setText(f"Capacity: ~{cap:,} characters")
        except Exception:
            self.capacity_label.setText("Could not read image")
        self.update_char_count()

    def update_char_count(self):
        text = self.message_input.toPlainText()
        self.char_count_label.setText(f"{len(text)} characters")

    def run_encode(self):
        if not self.drop_zone.image_path:
            QMessageBox.warning(self, "Missing Image", "Please select a cover image first.")
            return

        message = self.message_input.toPlainText()
        if not message:
            QMessageBox.warning(self, "Empty Message", "Please enter a message to hide.")
            return

        password = self.password_input.text() if self.use_password.isChecked() else ""

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Stego Image As", "stego_output.png", "PNG Image (*.png)"
        )
        if not output_path:
            return

        self.encode_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Encoding...")

        self.worker = StegoWorker(
            "encode",
            cover_path=self.drop_zone.image_path,
            message=message,
            output_path=output_path,
            password=password,
        )
        self.worker.finished_ok.connect(self.on_encode_success)
        self.worker.finished_err.connect(self.on_error)
        self.worker.start()

    def on_encode_success(self, output_path: str):
        self.progress.setVisible(False)
        self.encode_btn.setEnabled(True)
        self.status_label.setText(f"Message hidden successfully → {output_path}")
        QMessageBox.information(self, "Success", f"Stego image saved to:\n{output_path}")

    def on_error(self, msg: str):
        self.progress.setVisible(False)
        self.encode_btn.setEnabled(True)
        self.status_label.setText("")
        QMessageBox.critical(self, "Error", msg)


# ----------------------------------------------------------------------------
# Decode Panel
# ----------------------------------------------------------------------------

class DecodePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 16, 0, 0)

        lbl = QLabel("STEGO IMAGE")
        lbl.setObjectName("SectionLabel")
        layout.addWidget(lbl)

        self.drop_zone = DropZone(self.select_image)
        layout.addWidget(self.drop_zone)

        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        pw_row = QHBoxLayout()
        self.use_password = QCheckBox("This image is password protected")
        self.use_password.stateChanged.connect(self.toggle_password_field)
        pw_row.addWidget(self.use_password)
        layout.addLayout(pw_row)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setVisible(False)
        layout.addWidget(self.password_input)

        lbl2 = QLabel("EXTRACTED MESSAGE")
        lbl2.setObjectName("SectionLabel")
        layout.addWidget(lbl2)

        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText("Extracted message will appear here...")
        self.result_display.setMinimumHeight(140)
        layout.addWidget(self.result_display)

        layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_row = QHBoxLayout()
        self.decode_btn = QPushButton("Extract Hidden Message")
        self.decode_btn.clicked.connect(self.run_decode)
        btn_row.addWidget(self.decode_btn)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("SecondaryButton")
        self.copy_btn.clicked.connect(self.copy_result)
        btn_row.addWidget(self.copy_btn)
        layout.addLayout(btn_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("InfoLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def toggle_password_field(self, state):
        self.password_input.setVisible(bool(state))

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Stego Image", "", "Images (*.png *.bmp *.jpg *.jpeg)"
        )
        if path:
            self.on_image_loaded(path)

    def on_image_loaded(self, path: str):
        self.drop_zone.set_image(path)

    def run_decode(self):
        if not self.drop_zone.image_path:
            QMessageBox.warning(self, "Missing Image", "Please select a stego image first.")
            return

        password = self.password_input.text() if self.use_password.isChecked() else ""

        self.decode_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Extracting...")
        self.result_display.clear()

        self.worker = StegoWorker(
            "decode",
            stego_path=self.drop_zone.image_path,
            password=password,
        )
        self.worker.finished_ok.connect(self.on_decode_success)
        self.worker.finished_err.connect(self.on_error)
        self.worker.start()

    def on_decode_success(self, message: str):
        self.progress.setVisible(False)
        self.decode_btn.setEnabled(True)
        self.result_display.setPlainText(message)
        self.status_label.setText(f"Extracted {len(message)} characters")

    def on_error(self, msg: str):
        self.progress.setVisible(False)
        self.decode_btn.setEnabled(True)
        self.status_label.setText("")
        QMessageBox.critical(self, "Error", msg)

    def copy_result(self):
        text = self.result_display.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_label.setText("Copied to clipboard")


# ----------------------------------------------------------------------------
# Main Window
# ----------------------------------------------------------------------------

class StegoForgeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StegoForge — Image Steganography")
        self.setMinimumSize(520, 720)
        self.resize(520, 780)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(4)

        title = QLabel("STEGOFORGE")
        title.setObjectName("Title")
        main_layout.addWidget(title)

        subtitle = QLabel("LSB IMAGE STEGANOGRAPHY")
        subtitle.setObjectName("Subtitle")
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(16)

        # Tab buttons
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self.encode_tab_btn = QPushButton("Hide (Steganography)")
        self.encode_tab_btn.setObjectName("TabButton")
        self.encode_tab_btn.setCheckable(True)
        self.encode_tab_btn.setChecked(True)
        self.encode_tab_btn.clicked.connect(lambda: self.switch_tab(0))

        self.decode_tab_btn = QPushButton("Reveal (Desteganography)")
        self.decode_tab_btn.setObjectName("TabButton")
        self.decode_tab_btn.setCheckable(True)
        self.decode_tab_btn.clicked.connect(lambda: self.switch_tab(1))

        tab_row.addWidget(self.encode_tab_btn)
        tab_row.addWidget(self.decode_tab_btn)
        main_layout.addLayout(tab_row)

        self.stack = QStackedWidget()
        self.encode_panel = EncodePanel()
        self.decode_panel = DecodePanel()
        self.stack.addWidget(self.encode_panel)
        self.stack.addWidget(self.decode_panel)
        main_layout.addWidget(self.stack)

    def switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.encode_tab_btn.setChecked(index == 0)
        self.decode_tab_btn.setChecked(index == 1)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = StegoForgeWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
