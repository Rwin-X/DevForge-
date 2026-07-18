"""
main_window.py — Idea Book main window.

Layout:
  [ titlebar                                          ]
  [ sidebar | editor / preview (toggle) / graph (tab) ]
  [ statusbar                                         ]

Three views live in a QStackedWidget on the right: editor, split
preview, and graph. One idea per note; ideas link to each other via
[[wikilinks]]; the graph view visualizes the resulting constellation.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QMainWindow, QHBoxLayout, QVBoxLayout, QSplitter, QListWidget,
    QListWidgetItem, QLineEdit, QLabel, QPushButton, QPlainTextEdit,
    QTextBrowser, QStackedWidget, QButtonGroup, QMenu, QInputDialog,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction, QTextCursor, QDesktopServices

from core.store import Store
from core.markdown_plus import render as render_md, extract_title_suggestion
from ui.theme import STYLESHEET, PREVIEW_CSS
from ui.titlebar import TitleBar
from ui.graph_view import GraphView

APP_DATA_DIR = Path.home() / ".ideabook"
DB_PATH = APP_DATA_DIR / "vault.db"


class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search ideas…")
        layout.addWidget(self.search)

        new_row = QWidget()
        new_row_l = QHBoxLayout(new_row)
        new_row_l.setContentsMargins(10, 0, 10, 6)
        self.new_btn = QPushButton("+  New Idea")
        self.new_btn.setObjectName("toolBtn")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        new_row_l.addWidget(self.new_btn)
        layout.addWidget(new_row)

        header = QLabel("ALL IDEAS")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.resize(1180, 760)

        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.store = Store(str(DB_PATH))
        self.current_note_id: int | None = None
        self._dirty = False

        self._build_ui()
        self._wire_signals()
        self._reload_note_list()

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(600)
        self.autosave_timer.timeout.connect(self._autosave)

    # ---------- UI construction ----------

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.titlebar = TitleBar("Idea Book")
        outer.addWidget(self.titlebar)

        body = QWidget()
        body_l = QHBoxLayout(body)
        body_l.setContentsMargins(0, 0, 0, 0)
        body_l.setSpacing(0)
        outer.addWidget(body, 1)

        self.sidebar = Sidebar()
        body_l.addWidget(self.sidebar)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(0)
        body_l.addWidget(right, 1)

        # view-switch toolbar
        toolbar = QWidget()
        toolbar_l = QHBoxLayout(toolbar)
        toolbar_l.setContentsMargins(14, 8, 14, 8)
        toolbar_l.setSpacing(4)

        self.title_label = QLabel("Select or create an idea")
        self.title_label.setStyleSheet("font-size: 13px; color: #9A9791;")
        toolbar_l.addWidget(self.title_label)
        toolbar_l.addStretch()

        self.btn_group = QButtonGroup(self)
        self.btn_edit = QPushButton("Write")
        self.btn_preview = QPushButton("Read")
        self.btn_graph = QPushButton("Graph")
        for i, b in enumerate([self.btn_edit, self.btn_preview, self.btn_graph]):
            b.setObjectName("toolBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.btn_group.addButton(b, i)
            toolbar_l.addWidget(b)
        self.btn_edit.setChecked(True)
        right_l.addWidget(toolbar)

        # stacked content
        self.stack = QStackedWidget()
        right_l.addWidget(self.stack, 1)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("editor")
        self.editor.setPlaceholderText(
            "# New idea\n\nWrite in Markdown+.\n\n"
            "[[Link another idea]]   #tag   > [!idea] a callout"
        )
        self.stack.addWidget(self.editor)

        self.preview = QTextBrowser()
        self.preview.setObjectName("preview")
        self.preview.setOpenExternalLinks(False)
        self.stack.addWidget(self.preview)

        self.graph = GraphView()
        self.stack.addWidget(self.graph)

        # status bar
        self.statusbar = QWidget()
        self.statusbar.setObjectName("statusbar")
        sb_l = QHBoxLayout(self.statusbar)
        sb_l.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        sb_l.addWidget(self.status_label)
        sb_l.addStretch()
        self.wordcount_label = QLabel("")
        self.wordcount_label.setObjectName("statusLabel")
        sb_l.addWidget(self.wordcount_label)
        outer.addWidget(self.statusbar)

        self.setStyleSheet(STYLESHEET)

    def _wire_signals(self):
        self.titlebar.closeClicked.connect(self.close)
        self.titlebar.minimizeClicked.connect(self.showMinimized)
        self.titlebar.maximizeClicked.connect(self._toggle_maximize)

        self.sidebar.new_btn.clicked.connect(self._create_note)
        self.sidebar.search.textChanged.connect(self._on_search)
        self.sidebar.list.currentItemChanged.connect(self._on_select_note)
        self.sidebar.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sidebar.list.customContextMenuRequested.connect(self._on_list_context_menu)

        self.editor.textChanged.connect(self._on_text_changed)
        self.preview.anchorClicked.connect(self._on_preview_link)

        self.btn_edit.clicked.connect(lambda: self._switch_view(0))
        self.btn_preview.clicked.connect(lambda: self._switch_view(1))
        self.btn_graph.clicked.connect(lambda: self._switch_view(2))

        self.graph.noteActivated.connect(self._open_note_by_id)

    # ---------- view switching ----------

    def _switch_view(self, index: int):
        if index == 1:
            self._render_preview()
        elif index == 2:
            self._refresh_graph()
        self.stack.setCurrentIndex(index)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ---------- note list ----------

    def _reload_note_list(self, query: str = ""):
        self.sidebar.list.blockSignals(True)
        self.sidebar.list.clear()
        notes = self.store.search_notes(query) if query else self.store.list_notes()
        for n in notes:
            item = QListWidgetItem(("📌 " if n.pinned else "") + n.title)
            item.setData(Qt.UserRole, n.id)
            self.sidebar.list.addItem(item)
            if n.id == self.current_note_id:
                self.sidebar.list.setCurrentItem(item)
        self.sidebar.list.blockSignals(False)

    def _on_search(self, text: str):
        self._reload_note_list(text.strip())

    def _on_select_note(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current is None:
            return
        self._save_current(silent=True)
        note_id = current.data(Qt.UserRole)
        self._load_note(note_id)

    def _on_list_context_menu(self, pos):
        item = self.sidebar.list.itemAt(pos)
        if item is None:
            return
        note_id = item.data(Qt.UserRole)
        note = self.store.get_note(note_id)
        menu = QMenu(self)
        pin_action = QAction("Unpin" if note.pinned else "Pin", self)
        rename_action = QAction("Rename…", self)
        delete_action = QAction("Delete", self)
        menu.addAction(pin_action)
        menu.addAction(rename_action)
        menu.addSeparator()
        menu.addAction(delete_action)

        pin_action.triggered.connect(lambda: self._toggle_pin(note_id))
        rename_action.triggered.connect(lambda: self._rename_note(note_id))
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.exec(self.sidebar.list.mapToGlobal(pos))

    def _toggle_pin(self, note_id: int):
        note = self.store.get_note(note_id)
        self.store.update_note(note_id, pinned=not note.pinned)
        self._reload_note_list(self.sidebar.search.text().strip())

    def _rename_note(self, note_id: int):
        note = self.store.get_note(note_id)
        new_title, ok = QInputDialog.getText(self, "Rename Idea", "Title:", text=note.title)
        if ok and new_title.strip() and new_title.strip() != note.title:
            try:
                self.store.update_note(note_id, title=new_title.strip())
            except Exception:
                QMessageBox.warning(self, "Rename failed", "An idea with that title already exists.")
            self._reload_note_list(self.sidebar.search.text().strip())
            if note_id == self.current_note_id:
                self.title_label.setText(new_title.strip())

    def _delete_note(self, note_id: int):
        reply = QMessageBox.question(
            self, "Delete Idea", "Delete this idea permanently? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.store.delete_note(note_id)
            if note_id == self.current_note_id:
                self.current_note_id = None
                self.editor.blockSignals(True)
                self.editor.clear()
                self.editor.blockSignals(False)
                self.title_label.setText("Select or create an idea")
            self._reload_note_list(self.sidebar.search.text().strip())

    # ---------- note editing ----------

    def _create_note(self):
        self._save_current(silent=True)
        base = "Untitled Idea"
        title = base
        n = 2
        while self.store.get_note_by_title(title) is not None:
            title = f"{base} {n}"
            n += 1
        note = self.store.create_note(title, "# " + title + "\n\n")
        self.current_note_id = note.id
        self._reload_note_list()
        self._load_note(note.id)
        self.editor.setFocus()
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.editor.setTextCursor(cursor)
        self._switch_view(0)
        self.btn_edit.setChecked(True)

    def _load_note(self, note_id: int):
        note = self.store.get_note(note_id)
        if note is None:
            return
        self.current_note_id = note_id
        self.editor.blockSignals(True)
        self.editor.setPlainText(note.body)
        self.editor.blockSignals(False)
        self.title_label.setText(note.title)
        self._update_wordcount()
        if self.stack.currentIndex() == 1:
            self._render_preview()

    def _open_note_by_id(self, note_id: int):
        self._save_current(silent=True)
        for i in range(self.sidebar.list.count()):
            item = self.sidebar.list.item(i)
            if item.data(Qt.UserRole) == note_id:
                self.sidebar.list.setCurrentItem(item)
                break
        else:
            self._load_note(note_id)
        self._switch_view(0)
        self.btn_edit.setChecked(True)

    def _on_text_changed(self):
        self._dirty = True
        self._update_wordcount()
        self.status_label.setText("Editing…")
        self.autosave_timer.start()

    def _update_wordcount(self):
        text = self.editor.toPlainText()
        words = len(text.split())
        self.wordcount_label.setText(f"{words} words")

    def _autosave(self):
        self.autosave_timer.stop()
        self._save_current(silent=False)

    def _save_current(self, silent: bool):
        if self.current_note_id is None or not self._dirty:
            return
        body = self.editor.toPlainText()
        title = extract_title_suggestion(body)
        note = self.store.get_note(self.current_note_id)
        # Only auto-rename if user hasn't manually diverged the title from
        # the first-line convention already, to avoid surprising renames.
        final_title = title if title and title != note.title else note.title
        try:
            self.store.update_note(self.current_note_id, title=final_title, body=body)
            self.title_label.setText(final_title)
        except Exception:
            self.store.update_note(self.current_note_id, body=body)
        self._dirty = False
        if not silent:
            self.status_label.setText("Saved")
            QTimer.singleShot(1500, lambda: self.status_label.setText("Ready"))
        self._reload_note_list(self.sidebar.search.text().strip())

    # ---------- preview ----------

    def _render_preview(self):
        if self.current_note_id is None:
            self.preview.setHtml("")
            return
        note = self.store.get_note(self.current_note_id)
        titles = {n.title for n in self.store.list_notes()}
        html_body = render_md(note.body, existing_titles=titles)
        self.preview.setHtml(PREVIEW_CSS + html_body)

    def _on_preview_link(self, url):
        scheme = url.scheme()
        path = url.path().lstrip("/")
        if scheme == "ideabook" and url.host() == "note":
            target_title = path
            note = self.store.get_note_by_title(target_title)
            if note is None:
                note = self.store.create_note(target_title, f"# {target_title}\n\n")
                self._reload_note_list()
            self._open_note_by_id(note.id)
        elif scheme == "ideabook" and url.host() == "tag":
            self.sidebar.search.setText("#" + path)

    # ---------- graph ----------

    def _refresh_graph(self):
        nodes, edges = self.store.graph_data()
        self.graph.set_data(nodes, edges)

    def closeEvent(self, event):
        self._save_current(silent=True)
        self.store.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Idea Book")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
