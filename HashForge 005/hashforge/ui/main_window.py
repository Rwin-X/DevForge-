"""
HashForge — Main Window
Orchestrates drop zone, hash results, verify panel, history, and export.
"""

import json
import os
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QGuiApplication, QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QSplitter, QScrollArea,
    QFrame, QProgressBar, QFileDialog, QStatusBar,
    QCheckBox, QSizePolicy, QTabWidget, QToolBar,
)

from hashforge.core.hasher import HashWorker, HashResult, ALGORITHMS
from hashforge.core.history import HistoryManager
from hashforge.utils.theme import ThemeManager
from hashforge.utils.exporter import export_txt, export_json, suggest_filename

from hashforge.ui.drop_zone import DropZone
from hashforge.ui.hash_row import HashRow
from hashforge.ui.file_info_card import FileInfoCard
from hashforge.ui.verify_panel import VerifyPanel
from hashforge.ui.history_panel import HistoryPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme = ThemeManager(dark=False)
        self.history = HistoryManager()
        self._worker: HashWorker | None = None
        self._current_result: HashResult | None = None
        self._hash_rows: dict[str, HashRow] = {}

        self.setWindowTitle("HashForge")
        self.setMinimumSize(900, 640)
        self.resize(1100, 740)

        self._setup_ui()
        self._apply_theme()

    # ═══════════════════════════════════════════════════ UI Construction ════
    def _setup_ui(self):
        # ── Root ──
        root = QWidget()
        root.setObjectName("rootWidget")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──
        self._sidebar = self._build_sidebar()
        root_layout.addWidget(self._sidebar)

        # ── Main area ──
        main_area = self._build_main_area()
        root_layout.addWidget(main_area, stretch=1)

        # ── Status bar ──
        self._status = QStatusBar()
        self._status.setFixedHeight(28)
        self._status_label = QLabel("Ready")
        self._status.addWidget(self._status_label)
        self.setStatusBar(self._status)

    # ──────────────────────────────────────────────── Sidebar ────────────────
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo / title
        brand = QWidget()
        brand.setObjectName("brand")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(20, 24, 20, 24)
        brand_layout.setSpacing(10)

        icon_lbl = QLabel("🔐")
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        title_lbl = QLabel("HashForge")
        title_lbl.setStyleSheet(
            "font-size: 17px; font-weight: 800; letter-spacing: -0.5px;"
            " color: #0F172A; background: transparent;"
        )
        brand_layout.addWidget(icon_lbl)
        brand_layout.addWidget(title_lbl)
        brand_layout.addStretch()

        # Nav items
        nav = QWidget()
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(2)

        self._nav_forge = self._nav_button("  ⚡  Forge", True)
        self._nav_history = self._nav_button("  🗂  History", False)
        self._nav_forge.clicked.connect(lambda: self._switch_view(0))
        self._nav_history.clicked.connect(lambda: self._switch_view(1))

        nav_layout.addWidget(self._nav_forge)
        nav_layout.addWidget(self._nav_history)

        # Options section
        opts = QWidget()
        opts_layout = QVBoxLayout(opts)
        opts_layout.setContentsMargins(16, 12, 16, 12)
        opts_layout.setSpacing(8)

        opts_title = QLabel("ALGORITHMS")
        opts_title.setProperty("role", "label")
        opts_layout.addWidget(opts_title)

        self._algo_checks: dict[str, QCheckBox] = {}
        for algo in ALGORITHMS:
            cb = QCheckBox(algo)
            cb.setChecked(True)
            self._algo_checks[algo] = cb
            opts_layout.addWidget(cb)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Bottom actions
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(12, 8, 12, 16)
        bottom_layout.setSpacing(6)

        self._dark_btn = QPushButton("🌙  Dark mode")
        self._dark_btn.setProperty("variant", "ghost")
        self._dark_btn.setFixedHeight(36)
        self._dark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dark_btn.clicked.connect(self._toggle_dark)

        self._export_txt_btn = QPushButton("Export TXT")
        self._export_txt_btn.setProperty("variant", "ghost")
        self._export_txt_btn.setFixedHeight(36)
        self._export_txt_btn.setEnabled(False)
        self._export_txt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_txt_btn.clicked.connect(self._export_txt)

        self._export_json_btn = QPushButton("Export JSON")
        self._export_json_btn.setProperty("variant", "ghost")
        self._export_json_btn.setFixedHeight(36)
        self._export_json_btn.setEnabled(False)
        self._export_json_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_json_btn.clicked.connect(self._export_json)

        bottom_layout.addWidget(self._dark_btn)
        bottom_layout.addWidget(self._export_txt_btn)
        bottom_layout.addWidget(self._export_json_btn)

        layout.addWidget(brand)
        layout.addWidget(nav)
        layout.addWidget(opts)
        layout.addWidget(spacer)
        layout.addWidget(bottom)

        return sidebar

    def _nav_button(self, text: str, active: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setChecked(active)
        return btn

    # ──────────────────────────────────────────────── Main Area ──────────────
    def _build_main_area(self) -> QWidget:
        area = QWidget()
        area.setObjectName("mainArea")
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stack: page 0 = Forge, page 1 = History
        self._stack = QWidget()
        self._stack_layout = QVBoxLayout(self._stack)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        self._stack_layout.setSpacing(0)

        self._forge_page = self._build_forge_page()
        self._history_page_widget = HistoryPanel(self.history)
        self._history_page_widget.entry_selected.connect(self._load_history_entry)

        self._stack_layout.addWidget(self._forge_page)
        self._stack_layout.addWidget(self._history_page_widget)
        self._history_page_widget.setVisible(False)

        layout.addWidget(self._stack)
        return area

    def _build_forge_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # Page title
        title_row = QHBoxLayout()
        page_title = QLabel("Hash Forge")
        page_title.setStyleSheet(
            "font-size: 22px; font-weight: 800; letter-spacing: -0.5px;"
            " color: #0F172A; background: transparent;"
        )
        page_sub = QLabel("Generate cryptographic hashes for any file, locally and instantly.")
        page_sub.setStyleSheet("font-size: 13px; color: #64748B; background: transparent;")
        page_sub.setAlignment(Qt.AlignmentFlag.AlignBottom)

        title_row.addWidget(page_title)
        title_row.addWidget(page_sub, alignment=Qt.AlignmentFlag.AlignBottom)
        title_row.addStretch()

        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)

        # File info card
        self._file_card = FileInfoCard()

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(6)
        self._progress.setVisible(False)

        # Hash rows section
        hash_section = QWidget()
        hash_section.setObjectName("hashSection")
        hash_section_layout = QVBoxLayout(hash_section)
        hash_section_layout.setContentsMargins(0, 0, 0, 0)
        hash_section_layout.setSpacing(6)

        hash_header = QLabel("Hash Results")
        hash_header.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: #0F172A; background: transparent;"
        )
        hash_section_layout.addWidget(hash_header)

        for algo in ALGORITHMS:
            row = HashRow(algo)
            self._hash_rows[algo] = row
            hash_section_layout.addWidget(row)

        # Elapsed time label
        self._elapsed_label = QLabel("")
        self._elapsed_label.setStyleSheet(
            "font-size: 11px; color: #94A3B8; background: transparent;"
        )
        hash_section_layout.addWidget(self._elapsed_label)

        # Verify panel
        self._verify_panel = VerifyPanel()
        self._verify_panel.verify_requested.connect(self._verify_hash)

        # Cancel / re-hash button
        action_row = QHBoxLayout()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("variant", "ghost")
        self._cancel_btn.setFixedHeight(36)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_hash)

        action_row.addStretch()
        action_row.addWidget(self._cancel_btn)

        layout.addLayout(title_row)
        layout.addWidget(self._drop_zone)
        layout.addWidget(self._file_card)
        layout.addWidget(self._progress)
        layout.addWidget(hash_section)
        layout.addWidget(self._verify_panel)
        layout.addLayout(action_row)
        layout.addStretch()

        return page

    # ═══════════════════════════════════════════════════ Logic ═══════════════
    def _on_file_selected(self, path: str):
        self._verify_panel.clear()
        self._reset_hash_rows()
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._cancel_btn.setVisible(True)
        self._elapsed_label.setText("")
        self._export_txt_btn.setEnabled(False)
        self._export_json_btn.setEnabled(False)
        self._status_label.setText(f"Computing hashes for: {Path(path).name}")

        algos = [a for a, cb in self._algo_checks.items() if cb.isChecked()]
        if not algos:
            self._set_status("No algorithms selected — check at least one in the sidebar.")
            return

        from hashforge.core.hasher import FileInfo
        try:
            file_info = FileInfo.from_path(path)
            self._file_card.update_info(file_info)
            self._file_card.set_dark(self.theme.dark)
        except Exception as e:
            self._set_status(f"Error reading file: {e}")
            return

        # Show placeholder dashes immediately
        for algo in algos:
            if algo in self._hash_rows:
                self._hash_rows[algo].set_digest("")

        self._worker = HashWorker(path, algos)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_hashes_done)
        self._worker.error.connect(self._on_hash_error)
        self._worker.start()

    def _on_hashes_done(self, result: HashResult):
        self._current_result = result
        self._progress.setVisible(False)
        self._cancel_btn.setVisible(False)

        for algo, digest in result.hashes.items():
            if algo in self._hash_rows:
                self._hash_rows[algo].set_digest(digest)

        self._elapsed_label.setText(f"Computed in {result.elapsed:.3f}s")
        self._export_txt_btn.setEnabled(True)
        self._export_json_btn.setEnabled(True)
        self._status_label.setText(f"Done — {result.file_info.name}")

        # Save to history
        self.history.add(result)
        self._history_page_widget.refresh()

    def _on_hash_error(self, msg: str):
        self._progress.setVisible(False)
        self._cancel_btn.setVisible(False)
        self._set_status(f"Error: {msg}")

    def _cancel_hash(self):
        if self._worker:
            self._worker.cancel()
            self._worker.wait()
        self._progress.setVisible(False)
        self._cancel_btn.setVisible(False)
        self._set_status("Cancelled.")

    def _verify_hash(self, user_hash: str):
        if not self._current_result:
            return
        for algo, digest in self._current_result.hashes.items():
            if digest.lower() == user_hash.lower():
                self._verify_panel.show_result(True, algo)
                return
        self._verify_panel.show_result(False)

    def _reset_hash_rows(self):
        for row in self._hash_rows.values():
            row.set_digest("")

    def _load_history_entry(self, entry: dict):
        """Load a history entry into the forge view."""
        self._switch_view(0)
        from hashforge.core.hasher import FileInfo, HashResult
        fi = FileInfo(
            path=entry["file"]["path"],
            name=entry["file"]["name"],
            size=entry["file"]["size"],
            size_human=entry["file"]["size_human"],
        )
        result = HashResult(
            file_info=fi,
            hashes=entry["hashes"],
            elapsed=entry.get("elapsed_seconds", 0),
            timestamp=entry.get("timestamp", ""),
        )
        self._current_result = result
        self._file_card.update_info(fi)
        self._file_card.set_dark(self.theme.dark)
        self._reset_hash_rows()
        for algo, digest in result.hashes.items():
            if algo in self._hash_rows:
                self._hash_rows[algo].set_digest(digest)
        self._export_txt_btn.setEnabled(True)
        self._export_json_btn.setEnabled(True)
        self._elapsed_label.setText(f"Loaded from history · {result.timestamp[:10]}")
        self._status_label.setText(f"History: {fi.name}")
        self._verify_panel.clear()

    # ─────────────────────────────────────────────── Export ──────────────────
    def _export_txt(self):
        if not self._current_result:
            return
        name = suggest_filename(self._current_result, "txt")
        dest, _ = QFileDialog.getSaveFileName(self, "Export as TXT", name, "Text Files (*.txt)")
        if dest:
            export_txt(self._current_result, dest)
            self._set_status(f"Exported TXT → {dest}")

    def _export_json(self):
        if not self._current_result:
            return
        name = suggest_filename(self._current_result, "json")
        dest, _ = QFileDialog.getSaveFileName(self, "Export as JSON", name, "JSON Files (*.json)")
        if dest:
            export_json(self._current_result, dest)
            self._set_status(f"Exported JSON → {dest}")

    # ─────────────────────────────────────────────── Nav ─────────────────────
    def _switch_view(self, index: int):
        self._forge_page.setVisible(index == 0)
        self._history_page_widget.setVisible(index == 1)
        self._nav_forge.setChecked(index == 0)
        self._nav_history.setChecked(index == 1)
        if index == 1:
            self._history_page_widget.refresh()

    # ─────────────────────────────────────────────── Theme ───────────────────
    def _toggle_dark(self):
        self.theme.toggle()
        self._apply_theme()

    def _apply_theme(self):
        dark = self.theme.dark
        app = QGuiApplication.instance()

        # Re-generate full stylesheet
        app.setStyleSheet(self.theme.get_stylesheet())

        if dark:
            self._sidebar.setStyleSheet(
                "#sidebar { background: #161B22; border-right: 1px solid #30363D; }"
            )
            self._forge_page.setStyleSheet("background: #0D1117;")
            self._history_page_widget.setStyleSheet("background: #0D1117;")
            self.centralWidget().setStyleSheet("#rootWidget { background: #0D1117; }")
            self._dark_btn.setText("☀️  Light mode")
        else:
            self._sidebar.setStyleSheet(
                "#sidebar { background: #FFFFFF; border-right: 1px solid #E2E8F0; }"
            )
            self._forge_page.setStyleSheet("background: #F8FAFC;")
            self._history_page_widget.setStyleSheet("background: #F8FAFC;")
            self.centralWidget().setStyleSheet("#rootWidget { background: #F8FAFC; }")
            self._dark_btn.setText("🌙  Dark mode")

        # Propagate to child components
        self._drop_zone.set_dark(dark)
        if self._current_result:
            self._file_card.set_dark(dark)
        for row in self._hash_rows.values():
            row.set_dark(dark)
        self._verify_panel.set_dark(dark)

        # Nav buttons
        nav_style_active = (
            "background: #DBEAFE; color: #1D4ED8; border-radius: 8px; "
            "font-weight: 600; text-align: left; padding-left: 12px;"
        ) if not dark else (
            "background: #1E3A5F; color: #60A5FA; border-radius: 8px; "
            "font-weight: 600; text-align: left; padding-left: 12px;"
        )
        nav_style_inactive = (
            "background: transparent; color: #475569; border-radius: 8px; "
            "font-weight: 500; text-align: left; padding-left: 12px;"
        ) if not dark else (
            "background: transparent; color: #8B949E; border-radius: 8px; "
            "font-weight: 500; text-align: left; padding-left: 12px;"
        )

        for btn in [self._nav_forge, self._nav_history]:
            if btn.isChecked():
                btn.setStyleSheet(nav_style_active)
            else:
                btn.setStyleSheet(nav_style_inactive)

    def _set_status(self, msg: str):
        self._status_label.setText(msg)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        super().closeEvent(event)
