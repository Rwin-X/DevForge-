"""Main window and application entry point."""

import shutil
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow, QMenu, QMessageBox, QSplitter,
    QTabBar, QTabWidget, QToolButton,
)

from . import __version__, theme
from .editor import CodeEditor
from .terminal import RunPanel

PY_FILTER = "Python files (*.py *.pyw);;All files (*)"
MIN_FONT, MAX_FONT, DEFAULT_FONT = 8, 32, 13


class MainWindow(QMainWindow):
    def __init__(self, files: List[Path]) -> None:
        super().__init__()
        self.settings = QSettings("pylite", "pylite")
        self.font_size = int(self.settings.value("font_size", DEFAULT_FONT))
        self.font_size = max(MIN_FONT, min(MAX_FONT, self.font_size))

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.panel = RunPanel(self.font_size)
        self.panel.closeRequested.connect(lambda: self.panel.setVisible(False))
        self.panel.setMinimumHeight(110)
        self.panel.hide()

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.setCentralWidget(self.splitter)

        self.position_label = QLabel("Ln 1, Col 1")
        self.interpreter_label = QLabel("")
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addPermanentWidget(self.position_label)
        self.statusBar().addPermanentWidget(QLabel("Spaces: 4"))
        self.statusBar().addPermanentWidget(QLabel("UTF-8"))
        self.statusBar().addPermanentWidget(self.interpreter_label)

        self._build_menus()
        self.resize(1000, 680)
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        for path in files:
            self.open_path(path)
        if self.tabs.count() == 0:
            self.new_tab()
        self._refresh_interpreter_label()

    # ------------------------------------------------------------- menus
    def _action(self, menu: QMenu, text: str, slot, *shortcuts: str) -> QAction:
        action = QAction(text, self)
        if shortcuts:
            action.setShortcuts([QKeySequence(s) for s in shortcuts])
        action.triggered.connect(lambda _checked=False: slot())
        menu.addAction(action)
        return action

    def _build_menus(self) -> None:
        bar = self.menuBar()

        m = bar.addMenu("&File")
        self._action(m, "New", self.new_tab, "Ctrl+N")
        self._action(m, "Open…", self.open_dialog, "Ctrl+O")
        m.addSeparator()
        self._action(m, "Save", self.save_current, "Ctrl+S")
        self._action(m, "Save As…", self.save_current_as, "Ctrl+Shift+S")
        m.addSeparator()
        self._action(m, "Close Tab", lambda: self.close_tab(self.tabs.currentIndex()), "Ctrl+W")
        self._action(m, "Quit", self.close, "Ctrl+Q")

        m = bar.addMenu("&Edit")
        self._action(m, "Undo", lambda: self._editor_call("undo"), "Ctrl+Z")
        self._action(m, "Redo", lambda: self._editor_call("redo"), "Ctrl+Shift+Z", "Ctrl+Y")
        m.addSeparator()
        self._action(m, "Toggle Comment", lambda: self._editor_call("toggle_comment"), "Ctrl+/")
        self._action(m, "Indent", lambda: self._editor_call("indent"), "Ctrl+]")
        self._action(m, "Dedent", lambda: self._editor_call("dedent"), "Ctrl+[")

        m = bar.addMenu("&Run")
        self._action(m, "Run File", self.run_current, "F5", "Ctrl+R")
        self._action(m, "Stop", self.panel.stop, "Shift+F5")
        m.addSeparator()
        self._action(m, "Select Interpreter…", self.select_interpreter)

        m = bar.addMenu("&View")
        self._action(m, "Toggle Terminal", self.toggle_panel, "Ctrl+J", "Ctrl+`")
        m.addSeparator()
        self._action(m, "Zoom In", lambda: self.zoom(1), "Ctrl+=", "Ctrl++")
        self._action(m, "Zoom Out", lambda: self.zoom(-1), "Ctrl+-")
        self._action(m, "Reset Zoom", lambda: self.zoom(0), "Ctrl+0")

        m = bar.addMenu("&Help")
        self._action(m, "About PyLite", self.about)

    # ------------------------------------------------------------ helpers
    def current_editor(self) -> Optional[CodeEditor]:
        w = self.tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _editor_call(self, name: str) -> None:
        editor = self.current_editor()
        if editor is not None:
            getattr(editor, name)()
            editor.setFocus()

    def _display_name(self, editor: CodeEditor) -> str:
        return editor.path.name if editor.path else "untitled"

    def _refresh_tab(self, editor: CodeEditor) -> None:
        index = self.tabs.indexOf(editor)
        if index < 0:
            return
        modified = editor.document().isModified()
        self.tabs.setTabText(index, self._display_name(editor) + ("  ●" if modified else ""))
        self.tabs.setTabToolTip(index, str(editor.path) if editor.path else "Unsaved file")
        if editor is self.current_editor():
            self._update_window_title()

    def _update_window_title(self) -> None:
        editor = self.current_editor()
        if editor is None:
            self.setWindowTitle("PyLite")
            return
        dot = "● " if editor.document().isModified() else ""
        self.setWindowTitle(f"{dot}{self._display_name(editor)} — PyLite")

    def _update_position(self) -> None:
        editor = self.current_editor()
        if editor is None:
            return
        c = editor.textCursor()
        self.position_label.setText(f"Ln {c.blockNumber() + 1}, Col {c.positionInBlock() + 1}")

    def _on_tab_changed(self, _index: int) -> None:
        self._update_window_title()
        self._update_position()

    # --------------------------------------------------------------- tabs
    def new_tab(self, path: Optional[Path] = None, text: str = "") -> CodeEditor:
        editor = CodeEditor(path, self.font_size)
        if text:
            editor.setPlainText(text)
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(lambda _m, e=editor: self._refresh_tab(e))
        editor.cursorPositionChanged.connect(lambda e=editor: e is self.current_editor() and self._update_position())
        editor.zoomRequested.connect(self.zoom)
        editor.filesDropped.connect(lambda paths: [self.open_path(Path(p)) for p in paths])

        index = self.tabs.addTab(editor, self._display_name(editor))
        close = QToolButton()
        close.setObjectName("tabClose")
        close.setText("×")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setToolTip("Close (Ctrl+W)")
        close.clicked.connect(lambda _c=False, e=editor: self.close_tab(self.tabs.indexOf(e)))
        self.tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, close)

        self.tabs.setCurrentIndex(index)
        self._refresh_tab(editor)
        editor.setFocus()
        return editor

    def close_tab(self, index: int) -> None:
        editor = self.tabs.widget(index)
        if not isinstance(editor, CodeEditor) or not self.maybe_save(editor):
            return
        self.tabs.removeTab(index)
        editor.deleteLater()
        if self.tabs.count() == 0:
            self.new_tab()

    # -------------------------------------------------------------- files
    def open_dialog(self) -> None:
        start = str(self.current_editor().path.parent) if self.current_editor() and self.current_editor().path else ""
        paths, _ = QFileDialog.getOpenFileNames(self, "Open file", start, PY_FILTER)
        for p in paths:
            self.open_path(Path(p))

    def open_path(self, path: Path) -> None:
        path = path.expanduser()
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if editor.path is not None and editor.path.resolve() == resolved:
                self.tabs.setCurrentIndex(i)
                return

        text = ""
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                QMessageBox.warning(self, "Cannot open file", f"{path}\n\n{exc}")
                return

        current = self.current_editor()
        if self.tabs.count() == 1 and current is not None and current.is_pristine():
            self.tabs.removeTab(0)
            current.deleteLater()
        self.new_tab(resolved, text)

    def save_current(self) -> bool:
        editor = self.current_editor()
        return self.save(editor) if editor else False

    def save_current_as(self) -> bool:
        editor = self.current_editor()
        return self.save_as(editor) if editor else False

    def save(self, editor: CodeEditor) -> bool:
        if editor.path is None:
            return self.save_as(editor)
        return self._write(editor, editor.path)

    def save_as(self, editor: CodeEditor) -> bool:
        start = str(editor.path) if editor.path else "untitled.py"
        name, _ = QFileDialog.getSaveFileName(self, "Save file", start, PY_FILTER)
        if not name:
            return False
        return self._write(editor, Path(name))

    def _write(self, editor: CodeEditor, path: Path) -> bool:
        try:
            path.write_text(editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Cannot save file", f"{path}\n\n{exc}")
            return False
        editor.path = path
        editor.document().setModified(False)
        self._refresh_tab(editor)
        self.statusBar().showMessage(f"Saved {path.name}", 2500)
        return True

    def maybe_save(self, editor: CodeEditor) -> bool:
        if not editor.document().isModified():
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setText(f"Save changes to {self._display_name(editor)}?")
        box.setStandardButtons(
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        answer = box.exec()
        if answer == QMessageBox.StandardButton.Save:
            return self.save(editor)
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event) -> None:
        for i in range(self.tabs.count()):
            self.tabs.setCurrentIndex(i)
            if not self.maybe_save(self.tabs.widget(i)):
                event.ignore()
                return
        self.settings.setValue("geometry", self.saveGeometry())
        self.panel.shutdown()
        event.accept()

    # ---------------------------------------------------------------- run
    def default_interpreter(self) -> str:
        saved = str(self.settings.value("interpreter", "") or "")
        if saved and Path(saved).exists():
            return saved
        return shutil.which("python3") or sys.executable

    def _refresh_interpreter_label(self) -> None:
        self.interpreter_label.setText(Path(self.default_interpreter()).name)
        self.interpreter_label.setToolTip(self.default_interpreter())

    def select_interpreter(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Select Python interpreter", self.default_interpreter())
        if name:
            self.settings.setValue("interpreter", name)
            self._refresh_interpreter_label()

    def run_current(self) -> None:
        editor = self.current_editor()
        if editor is None:
            return
        if editor.path is None or editor.document().isModified():
            if not self.save(editor):
                return
        self.show_panel()
        source = editor.toPlainText()
        wants_input = "input(" in source or "stdin" in source
        self.panel.run(self.default_interpreter(), editor.path, focus_input=wants_input)
        if not wants_input:
            editor.setFocus()

    def show_panel(self) -> None:
        if not self.panel.isVisible():
            self.panel.show()
            total = max(self.splitter.height(), 400)
            self.splitter.setSizes([int(total * 0.66), int(total * 0.34)])

    def toggle_panel(self) -> None:
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self.show_panel()

    # --------------------------------------------------------------- view
    def zoom(self, delta: int) -> None:
        self.font_size = DEFAULT_FONT if delta == 0 else max(MIN_FONT, min(MAX_FONT, self.font_size + delta))
        for i in range(self.tabs.count()):
            self.tabs.widget(i).set_font_size(self.font_size)
        self.panel.set_font_size(self.font_size)
        self.settings.setValue("font_size", self.font_size)

    def about(self) -> None:
        QMessageBox.about(
            self,
            "About PyLite",
            f"<b>PyLite {__version__}</b><br>A minimal Python editor with a built-in runner.<br><br>"
            "Built with PyQt6.",
        )


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName("PyLite")
    app.setDesktopFileName("pylite")
    app.setStyle("Fusion")
    app.setPalette(theme.build_palette())
    app.setStyleSheet(theme.stylesheet())
    icon = Path(__file__).parent / "assets" / "pylite.svg"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    window = MainWindow([Path(a) for a in argv[1:]])
    window.show()
    return app.exec()
