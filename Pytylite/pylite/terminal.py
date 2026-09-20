"""Run panel: launches a script with QProcess and shows its output/stdin."""

import codecs
import re
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QShortcut, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from . import theme

# CSI sequences (colours, cursor moves) and OSC sequences (window titles).
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


class RunPanel(QWidget):
    runningChanged = pyqtSignal(bool)
    closeRequested = pyqtSignal()

    def __init__(self, font_size: int = 13, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("runPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._proc: Optional[QProcess] = None
        self._stopped = False
        self._started_at = 0.0
        self._dec_out = self._dec_err = None

        title = QLabel("TERMINAL")
        title.setObjectName("panelTitle")
        self.status = QLabel("")
        self.status.setObjectName("panelStatus")
        self.stop_btn = self._button("Stop", self.stop)
        self.clear_btn = self._button("Clear", self.clear)
        close_btn = self._button("✕", self.closeRequested.emit)
        close_btn.setToolTip("Hide panel (Ctrl+J)")

        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 6, 0)
        header.setSpacing(2)
        for w in (title,):
            header.addWidget(w)
        header.addStretch(1)
        for w in (self.status, self.stop_btn, self.clear_btn, close_btn):
            header.addWidget(w)

        self.output = QPlainTextEdit()
        self.output.setObjectName("termOutput")
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(20000)
        self.output.document().setDocumentMargin(12)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        prompt = QLabel("❯")
        prompt.setObjectName("prompt")
        self.input = QLineEdit()
        self.input.setObjectName("termInput")
        self.input.returnPressed.connect(self._send_line)
        eof = QShortcut(QKeySequence("Ctrl+D"), self.input)
        eof.setContext(Qt.ShortcutContext.WidgetShortcut)
        eof.activated.connect(self._send_eof)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(0)
        input_row.addWidget(prompt)
        input_row.addWidget(self.input, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self.output, 1)
        layout.addLayout(input_row)

        self.set_font_size(font_size)
        self._set_running(False)

    def _button(self, text: str, slot) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("flat")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.clicked.connect(lambda _checked=False: slot())
        return b

    def set_font_size(self, size: int) -> None:
        font = theme.mono_font(size)
        self.output.setFont(font)
        self.input.setFont(font)
        self.output.setTabStopDistance(8 * self.output.fontMetrics().horizontalAdvance(" "))

    # ------------------------------------------------------------ process
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def run(self, interpreter: str, script: Path, focus_input: bool = False) -> None:
        self._discard_process()
        self.clear()
        self._stopped = False
        self._dec_out = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._dec_err = codecs.getincrementaldecoder("utf-8")(errors="replace")

        proc = QProcess(self)
        proc.setProgram(interpreter)
        proc.setArguments(["-u", script.name])
        proc.setWorkingDirectory(str(script.parent))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("TERM", "dumb")
        proc.setProcessEnvironment(env)
        proc.readyReadStandardOutput.connect(lambda: self._drain(False))
        proc.readyReadStandardError.connect(lambda: self._drain(True))
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)
        self._proc = proc

        self._append(f"$ {Path(interpreter).name} {script.name}\n", theme.TERM_INFO)
        self._started_at = time.monotonic()
        self._set_running(True)
        proc.start()
        if focus_input:
            self.input.setFocus()

    def stop(self) -> None:
        proc = self._proc
        if proc is not None and proc.state() != QProcess.ProcessState.NotRunning:
            self._stopped = True
            proc.terminate()
            QTimer.singleShot(1500, lambda: self._force_kill(proc))

    @staticmethod
    def _force_kill(proc: QProcess) -> None:
        try:
            if proc.state() != QProcess.ProcessState.NotRunning:
                proc.kill()
        except RuntimeError:  # the QProcess was already deleted
            pass

    def _discard_process(self) -> None:
        """Detach from a previous process so its late signals are ignored."""
        proc = self._proc
        if proc is None:
            return
        proc.blockSignals(True)
        if proc.state() != QProcess.ProcessState.NotRunning:
            proc.kill()
            proc.waitForFinished(1000)
        proc.deleteLater()
        self._proc = None

    def shutdown(self) -> None:
        self._discard_process()

    def _on_finished(self, code: int, status: QProcess.ExitStatus) -> None:
        self._drain(False)
        self._drain(True)
        elapsed = time.monotonic() - self._started_at
        self._ensure_newline()
        if self._stopped:
            self._append(f"[Stopped after {elapsed:.2f}s]\n", theme.TERM_INFO)
            self.status.setText("stopped")
        elif status == QProcess.ExitStatus.CrashExit:
            self._append(f"[Process crashed after {elapsed:.2f}s]\n", theme.TERM_ERR)
            self.status.setText("crashed")
        else:
            ok = code == 0
            self._append(
                f"[Process finished with exit code {code} in {elapsed:.2f}s]\n",
                theme.TERM_OK if ok else theme.TERM_ERR,
            )
            self.status.setText(f"exit {code}")
        self._set_running(False, keep_status=True)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart and self._proc is not None:
            self._ensure_newline()
            self._append(
                f"[Could not start interpreter: {self._proc.program()}]\n"
                "Use Run > Select Interpreter… to choose another one.\n",
                theme.TERM_ERR,
            )
            self.status.setText("failed")
            self._set_running(False, keep_status=True)

    # ---------------------------------------------------------------- I/O
    def _drain(self, is_err: bool) -> None:
        proc = self._proc
        if proc is None:
            return
        raw = proc.readAllStandardError() if is_err else proc.readAllStandardOutput()
        decoder = self._dec_err if is_err else self._dec_out
        text = decoder.decode(bytes(raw))
        if text:
            self._append(text, theme.TERM_ERR if is_err else theme.FG)

    def _send_line(self) -> None:
        if not self.is_running():
            return
        text = self.input.text()
        self.input.clear()
        self._append(text + "\n", theme.TERM_INPUT)
        self._proc.write((text + "\n").encode("utf-8"))

    def _send_eof(self) -> None:
        if self.is_running():
            self._append("^D\n", theme.TERM_INFO)
            self._proc.closeWriteChannel()

    def _append(self, text: str, color: str) -> None:
        text = _ANSI.sub("", text).replace("\r\n", "\n")
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = QTextCursor(self.output.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for i, part in enumerate(text.split("\r")):
            if i > 0:  # carriage return: overwrite the current line
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
            cursor.insertText(part, fmt)
        bar = self.output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _ensure_newline(self) -> None:
        if self.output.document().lastBlock().text():
            self._append("\n", theme.FG)

    def clear(self) -> None:
        self.output.clear()

    def _set_running(self, running: bool, keep_status: bool = False) -> None:
        self.stop_btn.setEnabled(running)
        self.input.setEnabled(running)
        self.input.setPlaceholderText(
            "stdin — Enter to send, Ctrl+D to close" if running else "Press F5 to run the current file"
        )
        if running:
            self.status.setText("running…")
        elif not keep_status:
            self.status.setText("")
        self.runningChanged.emit(running)
