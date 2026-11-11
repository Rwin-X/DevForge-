"""Bridge between the Qt UI and the core layer.

All IMAP and database work runs off the main thread. Results come back
through signals, so widgets are only ever touched on the UI thread.
"""
from __future__ import annotations

import itertools
from typing import Callable

from PyQt6.QtCore import QObject, QRunnable, QThread, QThreadPool, QTimer, pyqtSignal, pyqtSlot

from ..core.config import AppConfig
from ..core.context import AppContext
from ..core.engine import ScanEngine
from ..core.errors import InboxGuardError
from ..core.secrets import set_password
from ..core.service import MailService


def describe_error(exc: BaseException) -> str:
    if isinstance(exc, InboxGuardError):
        return str(exc)
    return f"Unexpected error: {exc or type(exc).__name__}"


class _TaskSignals(QObject):
    finished = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)


class _Task(QRunnable):
    def __init__(self, task_id: int, fn: Callable[[], object]):
        super().__init__()
        self.setAutoDelete(False)  # the Backend owns the lifetime
        self.task_id = task_id
        self._fn = fn
        self.signals = _TaskSignals()

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # reported to the UI, never raised on a pool thread
            self.signals.failed.emit(self.task_id, describe_error(exc))
            return
        self.signals.finished.emit(self.task_id, result)


class ScanWorker(QObject):
    progress = pyqtSignal(int, int, str)
    item = pyqtSignal(object)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self._ctx = ctx
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    @pyqtSlot()
    def run(self) -> None:
        try:
            summary = ScanEngine(self._ctx).run(
                progress=self.progress.emit,
                on_item=self.item.emit,
                should_cancel=lambda: self._cancel,
            )
        except Exception as exc:
            self.failed.emit(describe_error(exc))
            return
        self.finished.emit(summary)


class Backend(QObject):
    scan_started = pyqtSignal()
    scan_progress = pyqtSignal(int, int, str)
    scan_item = pyqtSignal(object)
    scan_finished = pyqtSignal(object)
    scan_failed = pyqtSignal(str)
    data_changed = pyqtSignal()
    config_changed = pyqtSignal()
    bot_state_changed = pyqtSignal(bool)
    status = pyqtSignal(str)

    def __init__(self, ctx: AppContext, parent: QObject | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(2)
        self._ids = itertools.count(1)
        self._tasks: dict[int, tuple[_Task, Callable | None, Callable | None]] = {}
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    # ---- generic background tasks -----------------------------------

    @property
    def service(self) -> MailService:
        return MailService(self.ctx)

    def run(
        self,
        fn: Callable[[], object],
        on_done: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        task = _Task(next(self._ids), fn)
        task.signals.finished.connect(self._task_finished)
        task.signals.failed.connect(self._task_failed)
        self._tasks[task.task_id] = (task, on_done, on_error)
        self._pool.start(task)

    @pyqtSlot(int, object)
    def _task_finished(self, task_id: int, result: object) -> None:
        _task, on_done, _err = self._tasks.pop(task_id, (None, None, None))
        if on_done:
            on_done(result)

    @pyqtSlot(int, str)
    def _task_failed(self, task_id: int, message: str) -> None:
        _task, _done, on_error = self._tasks.pop(task_id, (None, None, None))
        if on_error:
            on_error(message)
        else:
            self.status.emit(message)

    # ---- scanning ----------------------------------------------------

    @property
    def scanning(self) -> bool:
        return self._thread is not None

    def start_scan(self) -> bool:
        if self._thread is not None:
            return False
        thread = QThread(self)
        worker = ScanWorker(self.ctx)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.scan_progress)
        worker.item.connect(self.scan_item)
        worker.finished.connect(self._on_scan_finished)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        self._thread, self._worker = thread, worker
        self.scan_started.emit()
        self.status.emit("Scan started")
        thread.start()
        return True

    def cancel_scan(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status.emit("Cancelling scan")

    @pyqtSlot(object)
    def _on_scan_finished(self, summary) -> None:
        self.status.emit(summary.describe())
        self.scan_finished.emit(summary)
        self.data_changed.emit()

    @pyqtSlot(str)
    def _on_scan_failed(self, message: str) -> None:
        self.status.emit(message)
        self.scan_failed.emit(message)

    @pyqtSlot()
    def _on_thread_finished(self) -> None:
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.deleteLater()

    # ---- bot timer ---------------------------------------------------

    @property
    def bot_enabled(self) -> bool:
        return self._timer.isActive()

    def set_bot_enabled(self, enabled: bool, persist: bool = True) -> None:
        if enabled:
            self._timer.start(self.ctx.config.bot.interval_minutes * 60_000)
            self.status.emit(f"Bot running, scanning every {self.ctx.config.bot.interval_minutes} minute(s)")
            self.start_scan()
        else:
            self._timer.stop()
            self.status.emit("Bot stopped")
        if persist:
            self.ctx.config.bot.auto_scan = enabled
            self._save_quietly()
        self.bot_state_changed.emit(enabled)

    def _on_tick(self) -> None:
        self.start_scan()  # skipped automatically while a scan is still running

    def _save_quietly(self) -> None:
        try:
            self.ctx.save_config()
        except OSError as exc:
            self.status.emit(f"Could not save settings: {exc}")

    # ---- settings ----------------------------------------------------

    def apply_config(self, config: AppConfig, password: str | None) -> None:
        was_running = self.bot_enabled
        self.ctx.config = config.normalized()
        self._save_quietly()
        if was_running:  # pick up a new interval
            self._timer.start(self.ctx.config.bot.interval_minutes * 60_000)
        username = self.ctx.config.account.username
        if password and username:
            self.run(
                lambda: set_password(username, password),
                on_done=lambda _r: self.status.emit("Settings saved. Password stored in the keyring."),
                on_error=lambda msg: self.status.emit(msg),
            )
        else:
            self.status.emit("Settings saved")
        self.config_changed.emit()
        self.data_changed.emit()

    # ---- shutdown ----------------------------------------------------

    def shutdown(self) -> None:
        self._timer.stop()
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(10_000)
        self._pool.waitForDone(5_000)
