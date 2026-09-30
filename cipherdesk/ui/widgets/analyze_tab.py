"""Analyze tab: letter frequency vs. English, index of coincidence,
brute-force Caesar shifts, and Kasiski key-length examination."""

from __future__ import annotations

import string

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core.analysis import (
    ENGLISH_FREQ,
    analyze,
    best_caesar_shift,
)
from core.models import Direction

ALPHA = string.ascii_uppercase


class FrequencyBar(QWidget):
    """One letter's frequency row: label, dual progress track (this
    text vs. reference English), percentage."""

    def __init__(self, letter: str, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.letter_label = QLabel(letter, self)
        self.letter_label.setObjectName("monoLabel")
        self.letter_label.setFixedWidth(18)
        layout.addWidget(self.letter_label)

        self.bar = QProgressBar(self)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar.setRange(0, 1000)
        layout.addWidget(self.bar, 1)

        self.ref_marker = QLabel("│", self)
        self.ref_marker.setObjectName("tertiaryLabel")
        layout.addWidget(self.ref_marker)

        self.value_label = QLabel("0.0%", self)
        self.value_label.setObjectName("tertiaryLabel")
        self.value_label.setFixedWidth(44)
        layout.addWidget(self.value_label)

    def set_value(self, pct: float, max_pct: float) -> None:
        fraction = 0 if max_pct == 0 else pct / max_pct
        self.bar.setValue(int(fraction * 1000))
        self.value_label.setText(f"{pct:.1f}%")


class AnalyzeTab(QWidget):
    restore_requested = pyqtSignal(str, object, str, str, str)  # algo_id, Direction, input_text, key1, key2

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(18)

        intro = QLabel(
            "Paste ciphertext to inspect its letter frequency against typical English, "
            "check its index of coincidence, and try every Caesar shift at once - useful "
            "when the algorithm behind a piece of text is unknown.",
            self,
        )
        intro.setObjectName("secondaryLabel")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        input_label = QLabel("CIPHERTEXT", self)
        input_label.setObjectName("tertiaryLabel")
        outer.addWidget(input_label)

        self.analyze_input = QPlainTextEdit(self)
        self.analyze_input.setObjectName("monoField")
        self.analyze_input.setFixedHeight(90)
        self.analyze_input.setPlaceholderText("Paste text to analyze...")
        self.analyze_input.textChanged.connect(self._run_analysis)
        outer.addWidget(self.analyze_input)

        grid = QHBoxLayout()
        grid.setSpacing(28)

        # --- left column: frequency bars ---
        left_col = QVBoxLayout()
        freq_label = QLabel("LETTER FREQUENCY - THIS TEXT VS. TYPICAL ENGLISH", self)
        freq_label.setObjectName("tertiaryLabel")
        left_col.addWidget(freq_label)

        self.bars: dict[str, FrequencyBar] = {}
        for letter in ALPHA:
            bar = FrequencyBar(letter, self)
            self.bars[letter] = bar
            left_col.addWidget(bar)
        left_col.addStretch()

        grid.addLayout(left_col, 1)

        # --- right column: IC box + Caesar list + Kasiski ---
        right_col = QVBoxLayout()

        ic_panel = QWidget(self)
        ic_panel.setObjectName("elevatedPanel")
        ic_layout = QVBoxLayout(ic_panel)
        ic_layout.setContentsMargins(16, 14, 16, 14)
        ic_layout.setSpacing(8)

        self.ic_letters_row = self._make_ic_row(ic_layout, "Letters analyzed")
        self.ic_value_row = self._make_ic_row(ic_layout, "Index of coincidence")
        self.ic_guess_row = self._make_ic_row(ic_layout, "Likely nature")

        ic_note = QLabel(
            "English prose sits near 0.067. Random text or a well-mixed polyalphabetic "
            "cipher sits near 0.038. A value close to 0.067 hints at a monoalphabetic "
            "substitution or transposition.",
            ic_panel,
        )
        ic_note.setObjectName("tertiaryLabel")
        ic_note.setWordWrap(True)
        ic_layout.addWidget(ic_note)

        right_col.addWidget(ic_panel)

        caesar_label = QLabel("ALL 26 CAESAR SHIFTS, RANKED BY FIT TO ENGLISH", self)
        caesar_label.setObjectName("tertiaryLabel")
        right_col.addWidget(caesar_label)

        self.caesar_list = QListWidget(self)
        self.caesar_list.setMaximumHeight(220)
        self.caesar_list.itemDoubleClicked.connect(self._on_caesar_item_activated)
        right_col.addWidget(self.caesar_list)

        kasiski_label = QLabel("LIKELY VIGENÈRE KEY LENGTH (KASISKI EXAMINATION)", self)
        kasiski_label.setObjectName("tertiaryLabel")
        right_col.addWidget(kasiski_label)

        self.kasiski_panel = QWidget(self)
        self.kasiski_panel.setObjectName("elevatedPanel")
        self.kasiski_layout = QVBoxLayout(self.kasiski_panel)
        self.kasiski_layout.setContentsMargins(16, 14, 16, 14)
        self.kasiski_layout.setSpacing(6)
        right_col.addWidget(self.kasiski_panel)

        right_col.addStretch()
        grid.addLayout(right_col, 1)

        outer.addLayout(grid, 1)

        self._render_empty_kasiski()

    def _make_ic_row(self, parent_layout: QVBoxLayout, label_text: str) -> QLabel:
        row = QHBoxLayout()
        key_label = QLabel(label_text, self)
        key_label.setObjectName("secondaryLabel")
        row.addWidget(key_label)
        row.addStretch()
        value_label = QLabel("—", self)
        value_label.setObjectName("monoLabel")
        row.addWidget(value_label)
        parent_layout.addLayout(row)
        return value_label

    # ------------------------------------------------------------------

    def _run_analysis(self) -> None:
        text = self.analyze_input.toPlainText()
        report = analyze(text)

        max_pct = max(
            [c / report.total_letters * 100 if report.total_letters else 0 for c in report.letter_counts.values()]
            + list(ENGLISH_FREQ.values())
        ) or 1.0

        for letter in ALPHA:
            count = report.letter_counts[letter]
            pct = (count / report.total_letters * 100) if report.total_letters else 0
            self.bars[letter].set_value(pct, max_pct)

        self.ic_letters_row.setText(str(report.total_letters))
        self.ic_value_row.setText(f"{report.index_of_coincidence:.4f}" if report.total_letters >= 2 else "—")

        from core.analysis import guess_nature
        self.ic_guess_row.setText(guess_nature(report.total_letters, report.index_of_coincidence))

        self._render_caesar_list(text, report.caesar_candidates)
        self._render_kasiski(report.kasiski_candidates)

    def _render_caesar_list(self, original_text: str, candidates) -> None:
        self.caesar_list.clear()
        if not candidates:
            item = QListWidgetItem("Paste at least a few words of ciphertext.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.caesar_list.addItem(item)
            return

        best_shift = best_caesar_shift(candidates)
        by_shift = sorted(candidates, key=lambda c: c[0])
        for shift, attempt, score in by_shift:
            preview = attempt[:60].replace("\n", " ")
            marker = " ★" if shift == best_shift else ""
            item = QListWidgetItem(f"{shift:>2}  {preview}{marker}")
            item.setData(Qt.ItemDataRole.UserRole, (shift, original_text))
            self.caesar_list.addItem(item)

    def _on_caesar_item_activated(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        shift, original_text = data
        self.restore_requested.emit("caesar", Direction.DECRYPT, original_text, str(shift), "")

    def _render_kasiski(self, candidates) -> None:
        while self.kasiski_layout.count():
            child = self.kasiski_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not candidates:
            self._render_empty_kasiski()
            return

        max_score = candidates[0][1] or 1
        for key_len, score in candidates:
            row = QHBoxLayout()
            label = QLabel(f"Key length {key_len}", self.kasiski_panel)
            label.setObjectName("secondaryLabel")
            row.addWidget(label)
            row.addStretch()

            bar = QProgressBar(self.kasiski_panel)
            bar.setTextVisible(False)
            bar.setFixedSize(60, 6)
            bar.setRange(0, 100)
            bar.setValue(int(score / max_score * 100))
            row.addWidget(bar)

            score_label = QLabel(str(score), self.kasiski_panel)
            score_label.setObjectName("tertiaryLabel")
            row.addWidget(score_label)

            self.kasiski_layout.addLayout(row)

    def _render_empty_kasiski(self) -> None:
        label = QLabel(
            "Need at least a couple hundred letters to find repeated sequences.",
            self.kasiski_panel,
        )
        label.setObjectName("tertiaryLabel")
        label.setWordWrap(True)
        self.kasiski_layout.addWidget(label)
