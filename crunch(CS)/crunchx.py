"""
CRUNCHX — Wordlist Generation Utility
A small-scale, GUI-based Crunch-style wordlist generator.

Modes:
    - Pattern mode  : crunch-style placeholders (@ , % ^) + literal chars
    - Range mode    : classic min/max length + charset brute-force

UI: PyQt6, pure white "inverted hacker" aesthetic — white background,
black text/borders, monospace, sharp edges, no rounded softness.

Run:
    pip install PyQt6
    python3 crunchx_gui.py
"""

import os
import sys
import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QFileDialog,
    QProgressBar,
    QPlainTextEdit,
    QFrame,
    QGridLayout,
    QCheckBox,
    QTabWidget,
    QMessageBox,
)

from generator_engine import (
    WordlistGenerator,
    CharsetOptions,
    GenerationMode,
    estimate_pattern_count,
    estimate_charset_range_count,
    human_readable_count,
    human_readable_size,
    estimate_file_size_bytes,
)


# ---------------------------------------------------------------------------
# Palette — pure white, inverted-hacker aesthetic
# ---------------------------------------------------------------------------
BG = "#ffffff"
BG_PANEL = "#f7f7f7"
FG_BLACK = "#0a0a0a"
FG_GRAY = "#6b6b6b"
FG_ACCENT = "#000000"
BORDER = "#0a0a0a"
BORDER_LIGHT = "#c9c9c9"
DANGER = "#c1121f"
SUCCESS = "#0a7d34"
MONO_FONT = "JetBrains Mono"


STYLE_SHEET = f"""
QWidget {{
    background-color: {BG};
    color: {FG_BLACK};
    font-family: '{MONO_FONT}', 'Consolas', monospace;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {BG};
}}

QFrame#panel {{
    background-color: {BG_PANEL};
    border: 1.5px solid {BORDER};
    border-radius: 0px;
}}

QLabel#title {{
    color: {FG_BLACK};
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 6px;
}}

QLabel#subtitle {{
    color: {FG_GRAY};
    font-size: 11px;
    letter-spacing: 2px;
}}

QLabel#fieldLabel {{
    color: {FG_BLACK};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QLabel#statLabel {{
    color: {FG_GRAY};
    font-size: 11px;
    letter-spacing: 1px;
}}

QLabel#statValue {{
    color: {FG_BLACK};
    font-size: 16px;
    font-weight: bold;
}}

QLabel#estimateBanner {{
    color: {FG_BLACK};
    font-size: 12px;
    font-weight: bold;
    background-color: {BG_PANEL};
    border: 1.5px dashed {BORDER};
    padding: 8px;
}}

QLabel#warningBanner {{
    color: {DANGER};
    font-size: 12px;
    font-weight: bold;
    background-color: #fff0f0;
    border: 1.5px solid {DANGER};
    padding: 8px;
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {BG};
    color: {FG_BLACK};
    border: 1.5px solid {BORDER};
    border-radius: 0px;
    padding: 6px 8px;
    selection-background-color: {FG_BLACK};
    selection-color: {BG};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 2px solid {FG_BLACK};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG};
    color: {FG_BLACK};
    selection-background-color: {FG_BLACK};
    selection-color: {BG};
    border: 1.5px solid {BORDER};
}}

QCheckBox {{
    color: {FG_BLACK};
    font-size: 12px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1.5px solid {BORDER};
    background-color: {BG};
}}

QCheckBox::indicator:checked {{
    background-color: {FG_BLACK};
}}

QPushButton {{
    background-color: {BG};
    color: {FG_BLACK};
    border: 1.5px solid {BORDER};
    border-radius: 0px;
    padding: 9px 18px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QPushButton:hover {{
    background-color: {FG_BLACK};
    color: {BG};
}}

QPushButton:pressed {{
    background-color: {FG_GRAY};
    color: {BG};
}}

QPushButton:disabled {{
    color: {BORDER_LIGHT};
    border: 1.5px solid {BORDER_LIGHT};
}}

QPushButton#stopButton {{
    border: 1.5px solid {DANGER};
    color: {DANGER};
}}

QPushButton#stopButton:hover {{
    background-color: {DANGER};
    color: {BG};
}}

QProgressBar {{
    background-color: {BG};
    border: 1.5px solid {BORDER};
    border-radius: 0px;
    text-align: center;
    color: {FG_BLACK};
    height: 20px;
    font-weight: bold;
}}

QProgressBar::chunk {{
    background-color: {FG_BLACK};
}}

QPlainTextEdit {{
    background-color: {BG};
    color: {FG_BLACK};
    border: 1.5px solid {BORDER};
    border-radius: 0px;
    font-family: '{MONO_FONT}', 'Consolas', monospace;
    font-size: 12px;
}}

QTabWidget::pane {{
    border: 1.5px solid {BORDER};
    background-color: {BG};
}}

QTabBar::tab {{
    background-color: {BG_PANEL};
    color: {FG_BLACK};
    border: 1.5px solid {BORDER};
    padding: 8px 20px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QTabBar::tab:selected {{
    background-color: {FG_BLACK};
    color: {BG};
}}

QLabel#resultDone {{
    color: {SUCCESS};
    font-size: 15px;
    font-weight: bold;
}}
"""


class GenerateWorker(QThread):
    """Runs WordlistGenerator on a background thread, re-emits progress
    and completion as Qt signals so the GUI never blocks."""

    progress_updated = pyqtSignal(int, float)
    log_message = pyqtSignal(str)
    finished_result = pyqtSignal(bool, str, int, float)  # stopped_early, path, written, elapsed

    def __init__(self, generator: WordlistGenerator):
        super().__init__()
        self.generator = generator

    def run(self):
        self.generator.progress_callback = self._on_progress
        result = self.generator.run()
        self.finished_result.emit(
            result.stopped_early, result.output_path, result.total_written, result.elapsed_seconds
        )

    def _on_progress(self, written, rate):
        self.progress_updated.emit(written, rate)

    def stop(self):
        self.generator.stop()
        self.log_message.emit("[!] Stop requested — flushing buffer and closing file...")


class CrunchXWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRUNCHX // wordlist generation utility")
        self.resize(820, 700)
        self.worker: GenerateWorker | None = None
        self._start_time = None
        self._output_dir = os.path.expanduser("~")

        self._build_ui()
        self._update_estimate()

    # -- UI construction ----------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Header
        header = QVBoxLayout()
        title = QLabel("C R U N C H X")
        title.setObjectName("title")
        subtitle = QLabel("PATTERN-BASED WORDLIST GENERATOR")
        subtitle.setObjectName("subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)
        root.addWidget(self._divider())

        # Tabs: PATTERN MODE / RANGE MODE
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_pattern_tab(), "PATTERN MODE")
        self.tabs.addTab(self._build_range_tab(), "RANGE MODE")
        self.tabs.currentChanged.connect(self._update_estimate)
        root.addWidget(self.tabs)

        # Output directory panel
        output_panel = QFrame()
        output_panel.setObjectName("panel")
        output_layout = QGridLayout(output_panel)
        output_layout.setContentsMargins(16, 16, 16, 16)
        output_layout.setSpacing(10)

        output_layout.addWidget(self._field_label("OUTPUT DIRECTORY"), 0, 0)
        self.output_dir_input = QLineEdit(self._output_dir)
        output_layout.addWidget(self.output_dir_input, 0, 1)
        browse_dir_btn = QPushButton("BROWSE")
        browse_dir_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(browse_dir_btn, 0, 2)

        output_layout.addWidget(self._field_label("FILENAME"), 1, 0)
        self.filename_input = QLineEdit("wordlist.txt")
        output_layout.addWidget(self.filename_input, 1, 1, 1, 2)

        root.addWidget(output_panel)

        # Estimate banner
        self.estimate_label = QLabel("")
        self.estimate_label.setObjectName("estimateBanner")
        root.addWidget(self.estimate_label)

        # Controls
        controls = QHBoxLayout()
        self.start_btn = QPushButton("▶ GENERATE WORDLIST")
        self.start_btn.clicked.connect(self._start_generation)
        self.stop_btn = QPushButton("■ STOP")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.clicked.connect(self._stop_generation)
        self.stop_btn.setEnabled(False)
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        root.addLayout(controls)

        # Stats panel
        stats_panel = QFrame()
        stats_panel.setObjectName("panel")
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setContentsMargins(16, 12, 16, 12)

        self.written_value = self._stat_block(stats_layout, "WORDS WRITTEN")
        self.rate_value = self._stat_block(stats_layout, "WORDS/SEC")
        self.elapsed_value = self._stat_block(stats_layout, "ELAPSED")
        self.size_value = self._stat_block(stats_layout, "FILE SIZE")

        root.addWidget(stats_panel)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        # Result label
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.result_label)

        # Log console
        root.addWidget(self._field_label("LOG"))
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(150)
        root.addWidget(self.log_console)

    def _build_pattern_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        panel = QFrame()
        panel.setObjectName("panel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(10)

        grid.addWidget(self._field_label("PATTERN"), 0, 0)
        self.pattern_input = QLineEdit("user@@%%")
        self.pattern_input.setPlaceholderText("e.g. user@@%%^  or  ,@@@@%%")
        self.pattern_input.textChanged.connect(self._update_estimate)
        grid.addWidget(self.pattern_input, 0, 1)

        legend = QLabel(
            "@ = lowercase [a-z]     , = uppercase [A-Z]     "
            "% = digit [0-9]     ^ = symbol     other chars = fixed literal"
        )
        legend.setObjectName("statLabel")
        legend.setWordWrap(True)
        grid.addWidget(legend, 1, 0, 1, 2)

        layout.addWidget(panel)
        layout.addStretch()
        return tab

    def _build_range_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        panel = QFrame()
        panel.setObjectName("panel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(10)

        grid.addWidget(self._field_label("MIN LENGTH"), 0, 0)
        self.min_len_spin = QSpinBox()
        self.min_len_spin.setRange(1, 12)
        self.min_len_spin.setValue(3)
        self.min_len_spin.valueChanged.connect(self._update_estimate)
        grid.addWidget(self.min_len_spin, 0, 1)

        grid.addWidget(self._field_label("MAX LENGTH"), 0, 2)
        self.max_len_spin = QSpinBox()
        self.max_len_spin.setRange(1, 12)
        self.max_len_spin.setValue(4)
        self.max_len_spin.valueChanged.connect(self._update_estimate)
        grid.addWidget(self.max_len_spin, 0, 3)

        grid.addWidget(self._field_label("CHARACTER SET"), 1, 0)
        charset_row = QHBoxLayout()
        self.chk_lower = QCheckBox("lowercase")
        self.chk_lower.setChecked(True)
        self.chk_upper = QCheckBox("UPPERCASE")
        self.chk_digits = QCheckBox("digits")
        self.chk_symbols = QCheckBox("symbols")
        for chk in (self.chk_lower, self.chk_upper, self.chk_digits, self.chk_symbols):
            chk.stateChanged.connect(self._update_estimate)
            charset_row.addWidget(chk)
        charset_widget = QWidget()
        charset_widget.setLayout(charset_row)
        grid.addWidget(charset_widget, 1, 1, 1, 3)

        layout.addWidget(panel)
        layout.addStretch()
        return tab

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {BORDER}; color: {BORDER};")
        line.setFixedHeight(2)
        return line

    def _field_label(self, text):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _stat_block(self, parent_layout, name):
        block = QVBoxLayout()
        name_label = QLabel(name)
        name_label.setObjectName("statLabel")
        value_label = QLabel("0")
        value_label.setObjectName("statValue")
        block.addWidget(name_label)
        block.addWidget(value_label)
        container = QWidget()
        container.setLayout(block)
        parent_layout.addWidget(container)
        return value_label

    # -- estimation ----------------------------------------------------------

    def _current_charset_options(self) -> CharsetOptions:
        return CharsetOptions(
            use_lower=self.chk_lower.isChecked(),
            use_upper=self.chk_upper.isChecked(),
            use_digits=self.chk_digits.isChecked(),
            use_symbols=self.chk_symbols.isChecked(),
        )

    def _update_estimate(self):
        try:
            if self.tabs.currentIndex() == 0:
                pattern = self.pattern_input.text()
                if not pattern:
                    self.estimate_label.setText("Enter a pattern to see the estimate.")
                    return
                count = estimate_pattern_count(pattern)
                avg_len = len(pattern)
            else:
                opts = self._current_charset_options()
                charset = opts.build_charset()
                if not charset:
                    self.estimate_label.setText("Select at least one character set.")
                    return
                min_len = self.min_len_spin.value()
                max_len = self.max_len_spin.value()
                if min_len > max_len:
                    self.estimate_label.setText("MIN LENGTH cannot exceed MAX LENGTH.")
                    return
                count = estimate_charset_range_count(len(charset), min_len, max_len)
                avg_len = (min_len + max_len) / 2

            size_bytes = estimate_file_size_bytes(count, avg_len)
            self.estimate_label.setObjectName(
                "warningBanner" if count > 50_000_000 else "estimateBanner"
            )
            self.estimate_label.setText(
                f"ESTIMATED OUTPUT: {human_readable_count(count)} words "
                f"({count:,})   ≈  {human_readable_size(size_bytes)} on disk"
                + ("   — LARGE OUTPUT, consider narrowing the range" if count > 50_000_000 else "")
            )
            self.estimate_label.style().unpolish(self.estimate_label)
            self.estimate_label.style().polish(self.estimate_label)
        except Exception as e:
            self.estimate_label.setText(f"Could not estimate: {e}")

    # -- behaviour -------------------------------------------------------------

    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select output directory", self._output_dir)
        if path:
            self._output_dir = path
            self.output_dir_input.setText(path)

    def _append_log(self, message):
        self.log_console.appendPlainText(message)

    def _build_generator(self) -> WordlistGenerator | None:
        output_dir = self.output_dir_input.text().strip()
        filename = self.filename_input.text().strip()

        if not output_dir:
            self._append_log("[!] Error: output directory is empty.")
            return None
        if not filename:
            self._append_log("[!] Error: filename is empty.")
            return None
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                self._append_log(f"[!] Error: cannot create directory — {e}")
                return None

        output_path = os.path.join(output_dir, filename)

        if self.tabs.currentIndex() == 0:
            pattern = self.pattern_input.text()
            if not pattern:
                self._append_log("[!] Error: pattern is empty.")
                return None
            return WordlistGenerator.from_pattern(pattern=pattern, output_path=output_path)
        else:
            opts = self._current_charset_options()
            charset = opts.build_charset()
            if not charset:
                self._append_log("[!] Error: select at least one character set.")
                return None
            min_len = self.min_len_spin.value()
            max_len = self.max_len_spin.value()
            if min_len > max_len:
                self._append_log("[!] Error: MIN LENGTH cannot exceed MAX LENGTH.")
                return None
            return WordlistGenerator.from_charset_range(
                charset_options=opts, min_len=min_len, max_len=max_len, output_path=output_path
            )

    def _start_generation(self):
        generator = self._build_generator()
        if generator is None:
            return

        # Warn on very large outputs before committing
        try:
            if self.tabs.currentIndex() == 0:
                count = estimate_pattern_count(self.pattern_input.text())
            else:
                opts = self._current_charset_options()
                count = estimate_charset_range_count(
                    len(opts.build_charset()), self.min_len_spin.value(), self.max_len_spin.value()
                )
            if count > 200_000_000:
                reply = QMessageBox.question(
                    self,
                    "Large output warning",
                    f"This will generate approximately {human_readable_count(count)} words "
                    f"({count:,}). This may take a long time and use significant disk space.\n\n"
                    "Continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return
        except Exception:
            pass

        self.log_console.clear()
        self.result_label.setText("")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate while running
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.tabs.setEnabled(False)

        self._append_log(f"[*] Output file : {generator.output_path}")
        self._append_log(
            f"[*] Mode        : {'PATTERN' if generator.mode == GenerationMode.PATTERN else 'RANGE'}"
        )
        self._append_log("[*] Starting generation...")

        self._start_time = time.time()
        self.worker = GenerateWorker(generator)
        self.worker.log_message.connect(self._append_log)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.finished_result.connect(self._on_finished)
        self.worker.start()

    def _stop_generation(self):
        if self.worker:
            self.worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_progress_updated(self, written, rate):
        self.written_value.setText(f"{written:,}")
        self.rate_value.setText(f"{rate:,.0f}")
        elapsed = time.time() - self._start_time if self._start_time else 0
        self.elapsed_value.setText(f"{elapsed:.1f}s")

    def _on_finished(self, stopped_early, path, written, elapsed):
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.tabs.setEnabled(True)

        self.written_value.setText(f"{written:,}")
        self.elapsed_value.setText(f"{elapsed:.2f}s")
        rate = written / elapsed if elapsed > 0 else 0
        self.rate_value.setText(f"{rate:,.0f}")

        try:
            size_bytes = os.path.getsize(path)
            self.size_value.setText(human_readable_size(size_bytes))
        except OSError:
            self.size_value.setText("—")

        self.result_label.setObjectName("resultDone")
        status = "STOPPED (partial file saved)" if stopped_early else "COMPLETE"
        self.result_label.setText(f"✓ {status} — {written:,} words written to {path}")
        self.result_label.style().unpolish(self.result_label)
        self.result_label.style().polish(self.result_label)

        self._append_log(
            f"[*] {status} — {written:,} words in {elapsed:.2f}s ({rate:,.0f} words/sec)"
        )
        self._append_log(f"[*] Saved to: {path}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    window = CrunchXWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
