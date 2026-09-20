"""Code editor widget: line numbers, current-line highlight, smart editing."""

import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QTextCursor, QTextFormat
from PyQt6.QtWidgets import QFrame, QPlainTextEdit, QTextEdit, QWidget

from . import theme
from .highlighter import PythonHighlighter

INDENT = " " * 4
PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
CLOSERS = ")]}\"'"
_DEDENT_AFTER = re.compile(r"(return|pass|break|continue|raise)\b")
_TRAILING_COMMENT = re.compile(r"\s+#.*$")


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    zoomRequested = pyqtSignal(int)
    filesDropped = pyqtSignal(list)

    def __init__(self, path: Optional[Path] = None, font_size: int = 13) -> None:
        super().__init__()
        self.path: Optional[Path] = path
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setCursorWidth(2)
        self.highlighter = PythonHighlighter(self.document())

        self._line_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margin)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._on_cursor_moved)

        self.set_font_size(font_size)
        self._on_cursor_moved()

    # ---------------------------------------------------------------- basics
    def set_font_size(self, size: int) -> None:
        self.setFont(theme.mono_font(size))
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self._update_margin()
        self._line_area.update()

    def is_pristine(self) -> bool:
        """An empty, never-saved, unmodified buffer."""
        return self.path is None and not self.document().isModified() and self.document().isEmpty()

    # ------------------------------------------------------- line numbers
    def line_number_width(self) -> int:
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 22 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin(self) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margin()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor(theme.BG))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        height = self.fontMetrics().height()
        width = self._line_area.width() - 12
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(theme.LINE_NO_ACTIVE if number == current else theme.LINE_NO))
                painter.drawText(0, top, width, height, Qt.AlignmentFlag.AlignRight, str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    def _on_cursor_moved(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(theme.CURRENT_LINE))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])
        self._line_area.update()

    # ---------------------------------------------------------- key handling
    def keyPressEvent(self, event) -> None:
        key = event.key()
        blocked = (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.MetaModifier
        )
        if not (event.modifiers() & blocked):
            if key == Qt.Key.Key_Tab:
                self._on_tab()
                return
            if key == Qt.Key.Key_Backtab:
                self.dedent()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._on_enter()
                return
            if key == Qt.Key.Key_Backspace and self._on_backspace():
                return
            text = event.text()
            if len(text) == 1 and (text in PAIRS or text in CLOSERS) and self._on_char(text):
                return
        super().keyPressEvent(event)

    def _on_tab(self) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            self.indent()
        else:
            cursor.insertText(" " * (4 - cursor.positionInBlock() % 4))
            self.setTextCursor(cursor)

    def _on_enter(self) -> None:
        cursor = self.textCursor()
        cursor.removeSelectedText()
        line = cursor.block().text()
        col = cursor.positionInBlock()
        before, after = line[:col], line[col:]
        indent = re.match(r"[ \t]*", before).group(0)
        code = _TRAILING_COMMENT.sub("", before.rstrip()).strip()
        depth = sum(code.count(c) for c in "([{") - sum(code.count(c) for c in ")]}")

        extra = ""
        if code.endswith(":") or depth > 0:
            extra = INDENT
        elif _DEDENT_AFTER.match(code) and indent.endswith(INDENT):
            indent = indent[: -len(INDENT)]

        cursor.beginEditBlock()
        cursor.insertText("\n" + indent + extra)
        if extra and after[:1] in (")", "]", "}"):
            inner = cursor.position()
            cursor.insertText("\n" + indent)
            cursor.setPosition(inner)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _on_backspace(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        line = cursor.block().text()
        col = cursor.positionInBlock()
        if col == 0:
            return False
        # Delete an empty auto-inserted pair: (|) -> |
        if col < len(line) and PAIRS.get(line[col - 1]) == line[col]:
            cursor.beginEditBlock()
            cursor.deleteChar()
            cursor.deletePreviousChar()
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            return True
        # Backspace inside leading spaces removes up to the previous indent stop.
        before = line[:col]
        if before.strip(" ") == "":
            n = col % 4 or 4
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, n)
            cursor.removeSelectedText()
            self.setTextCursor(cursor)
            return True
        return False

    def _on_char(self, ch: str) -> bool:
        cursor = self.textCursor()
        line = cursor.block().text()
        col = cursor.positionInBlock()
        prev = line[col - 1] if col > 0 else ""
        nxt = line[col] if col < len(line) else ""

        if cursor.hasSelection() and ch in PAIRS:  # wrap the selection
            selected = cursor.selectedText()
            cursor.insertText(ch + selected + PAIRS[ch])
            self.setTextCursor(cursor)
            return True
        if ch in CLOSERS and nxt == ch:  # type over an existing closer
            cursor.movePosition(QTextCursor.MoveOperation.Right)
            self.setTextCursor(cursor)
            return True
        if ch in PAIRS:  # opening bracket or quote: auto-close it
            if ch in "\"'":
                if prev.isalnum() or prev in "_\"'\\" or nxt.isalnum():
                    return False
            elif nxt and not (nxt.isspace() or nxt in ")]},;:"):
                return False
            cursor.beginEditBlock()
            cursor.insertText(ch + PAIRS[ch])
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            return True
        return False

    # -------------------------------------------- line-oriented operations
    def _selected_lines(self) -> range:
        cursor = self.textCursor()
        doc = self.document()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        first = doc.findBlock(start).blockNumber()
        last_block = doc.findBlock(end)
        last = last_block.blockNumber()
        if end > start and end == last_block.position():
            last -= 1
        return range(first, max(first, last) + 1)

    def indent(self) -> None:
        doc = self.document()
        edit = self.textCursor()
        edit.beginEditBlock()
        for n in self._selected_lines():
            block = doc.findBlockByNumber(n)
            if block.text().strip():
                QTextCursor(block).insertText(INDENT)
        edit.endEditBlock()

    def dedent(self) -> None:
        doc = self.document()
        edit = self.textCursor()
        edit.beginEditBlock()
        for n in self._selected_lines():
            block = doc.findBlockByNumber(n)
            text = block.text()
            width = 1 if text.startswith("\t") else min(4, len(text) - len(text.lstrip(" ")))
            if width:
                c = QTextCursor(block)
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, width)
                c.removeSelectedText()
        edit.endEditBlock()

    def toggle_comment(self) -> None:
        doc = self.document()
        blocks = [doc.findBlockByNumber(n) for n in self._selected_lines()]
        blocks = [b for b in blocks if b.text().strip()]
        if not blocks:
            return
        uncomment = all(b.text().lstrip().startswith("#") for b in blocks)
        column = min(len(b.text()) - len(b.text().lstrip()) for b in blocks)
        edit = self.textCursor()
        edit.beginEditBlock()
        for block in blocks:
            text = block.text()
            c = QTextCursor(block)
            if uncomment:
                i = len(text) - len(text.lstrip())
                c.setPosition(block.position() + i)
                size = 2 if text[i : i + 2] == "# " else 1
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, size)
                c.removeSelectedText()
            else:
                c.setPosition(block.position() + column)
                c.insertText("# ")
        edit.endEditBlock()

    # ------------------------------------------------------- mouse / mime
    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            dy = event.angleDelta().y()
            if dy:
                self.zoomRequested.emit(1 if dy > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

    def canInsertFromMimeData(self, source) -> bool:
        return source.hasUrls() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source) -> None:
        if source.hasUrls():
            paths = [u.toLocalFile() for u in source.urls() if u.isLocalFile()]
            if paths:
                self.filesDropped.emit(paths)
                return
        super().insertFromMimeData(source)
