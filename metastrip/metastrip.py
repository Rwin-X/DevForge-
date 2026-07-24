#!/usr/bin/env python3
"""
METASTRIP - Minimal metadata removal tool
Strips EXIF/XMP/ICC/embedded metadata from images, PDFs, Office documents,
and audio files. Drag-and-drop or multi-file select supported.

Dependencies: PyQt6, Pillow, mutagen, pypdf
Install: pip install PyQt6 Pillow mutagen pypdf
"""

import sys
import os
import shutil
import zipfile
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QCheckBox,
    QTextEdit, QFileDialog, QProgressBar, QFrame, QAbstractItemView,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QPalette

from strippers import strip_metadata, SUPPORTED_EXTENSIONS


# ---------------------------------------------------------------------------
# Theme constants (phosphor terminal aesthetic)
# ---------------------------------------------------------------------------
BG_COLOR = "#0a0e0c"
PANEL_COLOR = "#0f1512"
BORDER_COLOR = "#1f3d2e"
ACCENT_GREEN = "#39ff88"
ACCENT_CYAN = "#4de8e8"
TEXT_DIM = "#5a7a6a"
TEXT_BRIGHT = "#c8ffe0"
ERROR_COLOR = "#ff5c5c"
FONT_FAMILY = "JetBrains Mono, Consolas, Monaco, monospace"

STYLESHEET = f"""
QMainWindow {{
    background-color: {BG_COLOR};
}}
QWidget {{
    background-color: {BG_COLOR};
    color: {TEXT_BRIGHT};
    font-family: {FONT_FAMILY};
    font-size: 12px;
}}
QLabel#title {{
    color: {ACCENT_GREEN};
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 2px;
}}
QLabel#subtitle {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QFrame#dropzone {{
    background-color: {PANEL_COLOR};
    border: 2px dashed {BORDER_COLOR};
    border-radius: 4px;
}}
QFrame#dropzone[dragging="true"] {{
    border: 2px dashed {ACCENT_GREEN};
    background-color: #101a15;
}}
QLabel#drophint {{
    color: {TEXT_DIM};
    font-size: 13px;
}}
QListWidget {{
    background-color: {PANEL_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    padding: 4px;
    color: {TEXT_BRIGHT};
}}
QListWidget::item {{
    padding: 4px;
    border-bottom: 1px solid #14201a;
}}
QListWidget::item:selected {{
    background-color: #16281f;
    color: {ACCENT_GREEN};
}}
QPushButton {{
    background-color: {PANEL_COLOR};
    color: {ACCENT_GREEN};
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    padding: 8px 16px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #16281f;
    border: 1px solid {ACCENT_GREEN};
}}
QPushButton:pressed {{
    background-color: #0a1510;
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border: 1px solid #142018;
}}
QPushButton#danger {{
    color: {ERROR_COLOR};
}}
QPushButton#danger:hover {{
    border: 1px solid {ERROR_COLOR};
    background-color: #281010;
}}
QCheckBox {{
    color: {TEXT_BRIGHT};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER_COLOR};
    background-color: {PANEL_COLOR};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT_GREEN};
    border: 1px solid {ACCENT_GREEN};
}}
QTextEdit {{
    background-color: {PANEL_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    color: {ACCENT_CYAN};
    font-size: 11px;
}}
QProgressBar {{
    background-color: {PANEL_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    text-align: center;
    color: {TEXT_BRIGHT};
    height: 18px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_GREEN};
}}
QScrollBar:vertical {{
    background: {PANEL_COLOR};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_COLOR};
    border-radius: 4px;
    min-height: 20px;
}}
"""


# ---------------------------------------------------------------------------
# Worker thread — keeps the GUI responsive while files are processed
# ---------------------------------------------------------------------------
class StripWorker(QThread):
    progress = pyqtSignal(int, int)        # current, total
    file_done = pyqtSignal(str, bool, str)  # filepath, success, message
    finished_all = pyqtSignal()

    def __init__(self, filepaths, overwrite, output_dir):
        super().__init__()
        self.filepaths = filepaths
        self.overwrite = overwrite
        self.output_dir = output_dir

    def run(self):
        total = len(self.filepaths)
        for i, path in enumerate(self.filepaths, start=1):
            try:
                out_path, message = strip_metadata(
                    path,
                    overwrite=self.overwrite,
                    output_dir=self.output_dir
                )
                self.file_done.emit(path, True, message)
            except Exception as exc:
                self.file_done.emit(path, False, str(exc))
            self.progress.emit(i, total)
        self.finished_all.emit()


# ---------------------------------------------------------------------------
# Drop zone widget
# ---------------------------------------------------------------------------
class DropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("dropzone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setProperty("dragging", False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("[ + ]")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 22px; border: none;")

        hint_label = QLabel("DRAG & DROP FILES HERE  //  OR CLICK BROWSE BELOW")
        hint_label.setObjectName("drophint")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("border: none;")

        formats = QLabel("images · pdf · docx/xlsx/pptx · audio (mp3/flac/etc)")
        formats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formats.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none;")

        layout.addWidget(icon_label)
        layout.addWidget(hint_label)
        layout.addWidget(formats)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self.setProperty("dragging", True)
            self.setStyle(self.style())
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.setStyle(self.style())

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragging", False)
        self.setStyle(self.style())
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        files = []
        for p in paths:
            if os.path.isdir(p):
                for root, _, names in os.walk(p):
                    for n in names:
                        files.append(os.path.join(root, n))
            elif os.path.isfile(p):
                files.append(p)
        if files:
            self.files_dropped.emit(files)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MetaStripWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("METASTRIP // metadata removal utility")
        self.resize(760, 640)
        self.file_paths = []
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Header
        title = QLabel("METASTRIP")
        title.setObjectName("title")
        subtitle = QLabel("strip exif / xmp / icc / document metadata — locally, offline")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        # Drop zone
        self.dropzone = DropZone()
        self.dropzone.files_dropped.connect(self.add_files)
        root.addWidget(self.dropzone)

        # Browse / clear buttons
        btn_row = QHBoxLayout()
        self.browse_btn = QPushButton("BROWSE FILES")
        self.browse_btn.clicked.connect(self.browse_files)
        self.clear_btn = QPushButton("CLEAR LIST")
        self.clear_btn.setObjectName("danger")
        self.clear_btn.clicked.connect(self.clear_files)
        btn_row.addWidget(self.browse_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # File list
        list_label = QLabel(f"QUEUED FILES (0)")
        list_label.setStyleSheet(f"color: {TEXT_DIM};")
        self.list_label = list_label
        root.addWidget(list_label)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setMinimumHeight(140)
        root.addWidget(self.file_list)

        remove_row = QHBoxLayout()
        self.remove_btn = QPushButton("REMOVE SELECTED")
        self.remove_btn.clicked.connect(self.remove_selected)
        remove_row.addWidget(self.remove_btn)
        remove_row.addStretch()
        root.addLayout(remove_row)

        # Options
        self.overwrite_checkbox = QCheckBox("Overwrite original files (unchecked = save as *_clean copies)")
        root.addWidget(self.overwrite_checkbox)

        # Run button + progress
        run_row = QHBoxLayout()
        self.run_btn = QPushButton("▶ STRIP METADATA")
        self.run_btn.clicked.connect(self.run_strip)
        self.run_btn.setMinimumHeight(38)
        run_row.addWidget(self.run_btn)
        root.addLayout(run_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        # Log output
        log_label = QLabel("LOG")
        log_label.setStyleSheet(f"color: {TEXT_DIM};")
        root.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(140)
        root.addWidget(self.log_output)

        self.setAcceptDrops(True)

    # -- drag/drop passthrough on whole window -----------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        files = []
        for p in paths:
            if os.path.isdir(p):
                for root_dir, _, names in os.walk(p):
                    for n in names:
                        files.append(os.path.join(root_dir, n))
            elif os.path.isfile(p):
                files.append(p)
        if files:
            self.add_files(files)

    # -- file management -----------------------------------------------------
    def browse_files(self):
        filt = "All Supported (*" + " *".join(sorted(SUPPORTED_EXTENSIONS)) + ");;All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", "", filt)
        if files:
            self.add_files(files)

    def add_files(self, files):
        for f in files:
            f = os.path.abspath(f)
            if f not in self.file_paths:
                self.file_paths.append(f)
                item = QListWidgetItem(f)
                self.file_list.addItem(item)
        self.update_list_label()

    def clear_files(self):
        self.file_paths = []
        self.file_list.clear()
        self.update_list_label()

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            path = item.text()
            if path in self.file_paths:
                self.file_paths.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        self.update_list_label()

    def update_list_label(self):
        self.list_label.setText(f"QUEUED FILES ({len(self.file_paths)})")

    # -- processing -----------------------------------------------------------
    def run_strip(self):
        if not self.file_paths:
            self.append_log("No files queued.", error=True)
            return

        overwrite = self.overwrite_checkbox.isChecked()
        output_dir = None
        if not overwrite:
            # Save cleaned copies alongside originals; strippers.py handles naming
            output_dir = None

        self.run_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.file_paths))
        self.log_output.clear()
        self.append_log(f"Starting metadata strip on {len(self.file_paths)} file(s)...")

        self.worker = StripWorker(list(self.file_paths), overwrite, output_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.file_done.connect(self.on_file_done)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, current, total):
        self.progress_bar.setValue(current)

    def on_file_done(self, path, success, message):
        name = os.path.basename(path)
        if success:
            self.append_log(f"[OK] {name} — {message}")
        else:
            self.append_log(f"[FAIL] {name} — {message}", error=True)

    def on_finished(self):
        self.append_log("Done.")
        self.run_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)

    def append_log(self, text, error=False):
        color = ERROR_COLOR if error else ACCENT_CYAN
        self.log_output.append(f'<span style="color:{color}">{text}</span>')


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MetaStripWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
