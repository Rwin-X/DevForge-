"""Entry point: GUI by default, --headless for servers."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inboxguard", description="Mailbox cleaner for ads and AI-written mail.")
    parser.add_argument("--headless", action="store_true", help="run the scanner without the GUI")
    parser.add_argument("--once", action="store_true", help="with --headless: scan once and exit")
    args = parser.parse_args(argv)

    if args.headless:
        from .core.headless import run_headless

        return run_headless(once=args.once)

    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from .core.config import config_path, database_path, load_config
    from .core.context import AppContext
    from .core.store import Store
    from .ui.backend import Backend
    from .ui.main_window import MainWindow
    from .ui.style import build_stylesheet

    app = QApplication(sys.argv[:1])
    app.setApplicationName("InboxGuard")
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())

    ctx = AppContext(load_config(), Store(database_path()), config_path=config_path())
    backend = Backend(ctx)
    window = MainWindow(backend)
    window.show()
    if ctx.config.bot.auto_scan:
        QTimer.singleShot(1500, lambda: backend.set_bot_enabled(True, persist=False))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
