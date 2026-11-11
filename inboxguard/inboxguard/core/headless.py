"""Run the scanner without a GUI (servers, cron, systemd)."""
from __future__ import annotations

import logging
import time

from .config import database_path, load_config
from .context import AppContext
from .engine import ScanEngine
from .errors import InboxGuardError
from .store import Store

log = logging.getLogger("inboxguard")


def run_headless(once: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ctx = AppContext(load_config(), Store(database_path()))
    while True:
        ctx.config = load_config()
        try:
            summary = ScanEngine(ctx).run()
            log.info(summary.describe())
            for err in summary.errors:
                log.warning(err)
        except InboxGuardError as exc:
            log.error("Scan failed: %s", exc)
            if once:
                return 1
        if once:
            return 0
        try:
            time.sleep(ctx.config.bot.interval_minutes * 60)
        except KeyboardInterrupt:
            log.info("Stopped.")
            return 0
