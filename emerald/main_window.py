"""
main_window.py

Assembles the three-panel UI:
  [ note list ] [ markdown editor ] [ graph view ]
plus a slide-out AI helper panel with exactly three actions.

Auto-save: every edit debounces a 400ms timer, then writes straight to
the .md file on disk. No "save" button needed, no cloud sync, no
background sync of any kind.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QKeySequence, QTextCursor, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QToolBar,
    QFrame,
)

import ai_helper
from note_store import NoteStore, sanitize_filename
from graph_widget import GraphWidget
from markdown_render import render_markdown_html

APP_TITLE = "Local AI Notes"

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0b0e0d;
    color: #d7ffe9;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 10.5pt;
}
QSplitter::handle {
    background-color: #16201b;
    width: 2px;
}
QListWidget {
    background-color: #0e1512;
    border: 1px solid #16201b;
    outline: none;
}
QListWidget::item {
    padding: 7px 10px;
    border-bottom: 1px solid #121a16;
    color: #9fd9bb;
}
QListWidget::item:selected {
    background-color: #16261f;
    color: #39ff9f;
    border-left: 2px solid #39ff9f;
}
QListWidget::item:hover {
    background-color: #111a16;
}
QPlainTextEdit, QTextBrowser {
    background-color: #0e1512;
    border: 1px solid #16201b;
    color: #d7ffe9;
    selection-background-color: #204434;
    padding: 10px;
}
QLineEdit {
    background-color: #0e1512;
    border: 1px solid #223129;
    border-radius: 3px;
    padding: 6px 8px;
    color: #d7ffe9;
}
QLineEdit:focus {
    border: 1px solid #39ff9f;
}
QPushButton {
    background-color: #132019;
    border: 1px solid #2c4839;
    border-radius: 3px;
    padding: 7px 10px;
    color: #9fd9bb;
}
QPushButton:hover {
    background-color: #1a2e24;
    border: 1px solid #39ff9f;
    color: #39ff9f;
}
QPushButton:pressed {
    background-color: #0e1512;
}
QLabel#sectionLabel {
    color: #4f7a63;
    font-size: 8.5pt;
    letter-spacing: 2px;
    padding: 8px 10px 4px 10px;
}
QLabel#statusLabel {
    color: #3f5c4c;
    font-size: 8.5pt;
    padding: 4px 10px;
}
QTabWidget::pane {
    border: 1px solid #16201b;
    background-color: #0e1512;
}
QTabBar::tab {
    background-color: #0e1512;
    color: #5f7a6d;
    padding: 6px 14px;
    border: 1px solid #16201b;
}
QTabBar::tab:selected {
    color: #39ff9f;
    border-bottom: 2px solid #39ff9f;
}
QScrollBar:vertical {
    background: #0b0e0d;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #223129;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #2c4839;
}
QFrame#divider {
    background-color: #16201b;
    max-height: 1px;
}
QToolBar {
    background-color: #0b0e0d;
    border-bottom: 1px solid #16201b;
    spacing: 6px;
    padding: 4px;
}
"""


class AIPanel(QWidget):
    """Right-side collapsible panel: summarize / suggest tags / suggest related."""

    def __init__(self, main_window: "MainWindow"):
        super().__init__()
        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("LOCAL AI HELPER")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        self.btn_summarize = QPushButton("Summarize")
        self.btn_tags = QPushButton("Suggest Tags")
        self.btn_related = QPushButton("Related Notes")
        for b in (self.btn_summarize, self.btn_tags, self.btn_related):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.output = QTextBrowser()
        self.output.setOpenLinks(False)
        self.output.anchorClicked.connect(self._on_anchor_clicked)
        self.output.setPlaceholderText(
            "Runs fully offline on this device.\n\n"
            "Pick an action above:\n"
            "- Summarize: short extractive summary\n"
            "- Suggest Tags: keyword-based tags\n"
            "- Related Notes: similar notes in this vault"
        )
        layout.addWidget(self.output, stretch=1)

        note = QLabel("No network access. No accounts. Runs on-device only.")
        note.setObjectName("statusLabel")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.btn_summarize.clicked.connect(self._do_summarize)
        self.btn_tags.clicked.connect(self._do_tags)
        self.btn_related.clicked.connect(self._do_related)

    def _current_note(self):
        return self.main_window.current_note()

    def _do_summarize(self):
        note = self._current_note()
        if note is None:
            self.output.setPlainText("Open a note first.")
            return
        summary = ai_helper.summarize_note(note)
        self.output.setPlainText(summary)

    def _do_tags(self):
        note = self._current_note()
        if note is None:
            self.output.setPlainText("Open a note first.")
            return
        tags = ai_helper.suggest_tags(note, self.main_window.store.all_notes())
        if not tags:
            self.output.setPlainText("Not enough distinctive text yet to suggest tags.")
            return
        html = "<p><b>Suggested tags:</b></p><p>"
        html += " &nbsp; ".join(f"<code>#{t}</code>" for t in tags)
        html += "</p>"
        self.output.setHtml(html)

    def _do_related(self):
        note = self._current_note()
        if note is None:
            self.output.setPlainText("Open a note first.")
            return
        related = ai_helper.suggest_related(note, self.main_window.store)
        if not related:
            self.output.setPlainText("No related notes found yet.")
            return
        html = "<p><b>Related notes:</b></p><ul>"
        for note_id, score in related:
            pct = int(score * 100)
            html += f'<li><a href="note:{note_id}">{note_id}</a> &nbsp;<span style="color:#4f7a63;">({pct}% similar)</span></li>'
        html += "</ul>"
        self.output.setHtml(html)

    def _on_anchor_clicked(self, url):
        text = url.toString()
        if text.startswith("note:"):
            self.main_window.open_note(text[len("note:"):])


class MainWindow(QMainWindow):
    def __init__(self, folder: str):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1400, 860)
        self.setStyleSheet(DARK_STYLESHEET)

        self.store = NoteStore(folder)
        self.store.load_all()
        self.active_note_id: str | None = None
        self._loading_note = False  # guard against autosave firing during programmatic load

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(400)
        self.autosave_timer.timeout.connect(self._commit_autosave)

        self._build_ui()
        self._reload_note_list()
        self._reload_graph()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_note_list_panel())
        splitter.addWidget(self._build_editor_panel())
        splitter.addWidget(self._build_graph_panel())
        splitter.setSizes([260, 620, 520])
        root_layout.addWidget(splitter, stretch=1)

        self.status_label = QLabel(f"Vault: {self.store.folder}")
        self.status_label.setObjectName("statusLabel")
        root_layout.addWidget(self.status_label)

    def _build_toolbar(self) -> QToolBar:
        bar = QToolBar()
        bar.setMovable(False)

        new_btn = QPushButton("+ New Note")
        new_btn.clicked.connect(self.create_new_note)
        bar.addWidget(new_btn)

        open_folder_btn = QPushButton("Open Vault Folder…")
        open_folder_btn.clicked.connect(self.choose_folder)
        bar.addWidget(open_folder_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(self.rename_current_note)
        bar.addWidget(rename_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_current_note)
        bar.addWidget(delete_btn)

        return bar

    def _build_note_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel("NOTES")
        label.setObjectName("sectionLabel")
        layout.addWidget(label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search notes…")
        self.search_box.textChanged.connect(self._on_search_changed)
        wrapper = QWidget()
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(10, 0, 10, 8)
        wl.addWidget(self.search_box)
        layout.addWidget(wrapper)

        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self._on_note_selected)
        layout.addWidget(self.note_list, stretch=1)

        return panel

    def _build_editor_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_label = QLabel("No note open")
        self.title_label.setObjectName("sectionLabel")
        layout.addWidget(self.title_label)

        self.tabs = QTabWidget()

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("JetBrains Mono", 11))
        self.editor.setPlaceholderText(
            "Select a note, or create one.\n\nUse [[Note Title]] to link to another note."
        )
        self.editor.textChanged.connect(self._on_text_changed)
        self.tabs.addTab(self.editor, "Edit")

        self.preview = QTextBrowser()
        self.preview.setOpenLinks(False)
        self.preview.anchorClicked.connect(self._on_preview_link_clicked)
        self.tabs.addTab(self.preview, "Preview")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs, stretch=1)

        backlinks_label = QLabel("BACKLINKS")
        backlinks_label.setObjectName("sectionLabel")
        layout.addWidget(backlinks_label)

        self.backlinks_list = QListWidget()
        self.backlinks_list.setMaximumHeight(120)
        self.backlinks_list.itemClicked.connect(lambda item: self.open_note(item.text()))
        layout.addWidget(self.backlinks_list)

        return panel

    def _build_graph_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel("GRAPH")
        label.setObjectName("sectionLabel")
        label.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(label)
        top_layout.addStretch(1)
        fit_btn = QPushButton("Fit")
        fit_btn.setFixedWidth(50)
        fit_btn.clicked.connect(lambda: self.graph.frame_all())
        top_layout.addWidget(fit_btn)
        layout.addWidget(top_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.graph = GraphWidget()
        self.graph.node_clicked.connect(self.open_note)
        splitter.addWidget(self.graph)

        self.ai_panel = AIPanel(self)
        splitter.addWidget(self.ai_panel)
        splitter.setSizes([560, 280])

        layout.addWidget(splitter, stretch=1)
        return panel

    # ------------------------------------------------------------------ #
    # Note list / selection
    # ------------------------------------------------------------------ #

    def _reload_note_list(self, select_id: str | None = None):
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in self.store.all_notes():
            item = QListWidgetItem(note.note_id)
            self.note_list.addItem(item)
            if select_id is not None and note.note_id == select_id:
                self.note_list.setCurrentItem(item)
        self.note_list.blockSignals(False)

    def _on_search_changed(self, text: str):
        results = self.store.search(text)
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in results:
            self.note_list.addItem(QListWidgetItem(note.note_id))
        self.note_list.blockSignals(False)
        self.graph.highlight_search(text)

    def _on_note_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current is None:
            return
        self.open_note(current.text())

    def current_note(self):
        if self.active_note_id is None:
            return None
        return self.store.get(self.active_note_id)

    def open_note(self, note_id: str):
        note = self.store.get(note_id)
        if note is None:
            return

        self._loading_note = True
        self.active_note_id = note_id
        self.title_label.setText(note_id.upper())
        self.editor.setPlainText(note.content)
        self._loading_note = False

        self._sync_list_selection(note_id)
        self._update_backlinks_panel(note)
        self.graph.highlight_active(note_id)
        self.graph.center_on_node(note_id)
        if self.tabs.currentIndex() == 1:
            self._render_preview()

    def _sync_list_selection(self, note_id: str):
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item.text() == note_id:
                self.note_list.blockSignals(True)
                self.note_list.setCurrentItem(item)
                self.note_list.blockSignals(False)
                break

    def _update_backlinks_panel(self, note):
        self.backlinks_list.clear()
        for source_id in note.links_in:
            self.backlinks_list.addItem(QListWidgetItem(source_id))
        if not note.links_in:
            placeholder = QListWidgetItem("(no notes link here yet)")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.backlinks_list.addItem(placeholder)

    # ------------------------------------------------------------------ #
    # Editing / autosave
    # ------------------------------------------------------------------ #

    def _on_text_changed(self):
        if self._loading_note or self.active_note_id is None:
            return
        self.status_label.setText("Editing…")
        self.autosave_timer.start()

    def _commit_autosave(self):
        if self.active_note_id is None:
            return
        content = self.editor.toPlainText()
        self.store.save_note(self.active_note_id, content)
        self.status_label.setText(f"Saved · {self.active_note_id}.md")
        self._reload_graph(keep_active=True)
        note = self.store.get(self.active_note_id)
        if note is not None:
            self._update_backlinks_panel(note)

    def _on_tab_changed(self, index: int):
        if index == 1:  # Preview tab
            self._render_preview()

    def _render_preview(self):
        note = self.current_note()
        if note is None:
            self.preview.setHtml("")
            return
        html = render_markdown_html(note.content, self.store)
        self.preview.setHtml(html)

    def _on_preview_link_clicked(self, url):
        text = url.toString()
        if text.startswith("note:"):
            target = text[len("note:"):]
            if self.store.note_exists(target):
                self.open_note(target)
                self.tabs.setCurrentIndex(0)
            else:
                self._create_note_from_link(target)

    def _create_note_from_link(self, title: str):
        reply = QMessageBox.question(
            self, "Create note?",
            f'"{title}" doesn\'t exist yet. Create it?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            note = self.store.create_note(title)
            self._reload_note_list(select_id=note.note_id)
            self.open_note(note.note_id)
            self._reload_graph(keep_active=True)

    # ------------------------------------------------------------------ #
    # Note actions
    # ------------------------------------------------------------------ #

    def create_new_note(self):
        title, ok = QInputDialog.getText(self, "New Note", "Title:")
        if not ok or not title.strip():
            return
        note = self.store.create_note(title.strip())
        self._reload_note_list(select_id=note.note_id)
        self.open_note(note.note_id)
        self._reload_graph(keep_active=True)

    def rename_current_note(self):
        if self.active_note_id is None:
            return
        new_title, ok = QInputDialog.getText(self, "Rename Note", "New title:", text=self.active_note_id)
        if not ok or not new_title.strip():
            return
        renamed = self.store.rename_note(self.active_note_id, new_title.strip())
        if renamed is None:
            QMessageBox.warning(self, "Rename failed", "A note with that name already exists.")
            return
        self._reload_note_list(select_id=renamed.note_id)
        self.open_note(renamed.note_id)
        self._reload_graph(keep_active=True)

    def delete_current_note(self):
        if self.active_note_id is None:
            return
        reply = QMessageBox.question(
            self, "Delete note?",
            f'Delete "{self.active_note_id}.md"? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.store.delete_note(self.active_note_id)
        self.active_note_id = None
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
        self.title_label.setText("No note open")
        self.backlinks_list.clear()
        self._reload_note_list()
        self._reload_graph()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Vault Folder", self.store.folder)
        if not folder:
            return
        self.store = NoteStore(folder)
        self.store.load_all()
        self.active_note_id = None
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
        self.status_label.setText(f"Vault: {folder}")
        self._reload_note_list()
        self._reload_graph()

    # ------------------------------------------------------------------ #
    # Graph
    # ------------------------------------------------------------------ #

    def _reload_graph(self, keep_active: bool = False):
        note_ids = [n.note_id for n in self.store.all_notes()]
        edges = self.store.graph_edges()
        active = self.active_note_id if keep_active else None
        self.graph.set_graph(note_ids, edges, active_id=active)
