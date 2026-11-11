import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from inboxguard.core.config import AppConfig
from inboxguard.core.context import AppContext
from inboxguard.core.mailbox import MailboxClient
from inboxguard.core.store import Store
from inboxguard.ui.backend import Backend
from inboxguard.ui.main_window import MainWindow
from inboxguard.ui.style import build_stylesheet

from fake_imap import FakeIMAP
from test_core_flow import make_fake


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    instance.setStyle("Fusion")
    instance.setStyleSheet(build_stylesheet())
    return instance


def wait_until(app, condition, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def env(app, tmp_path):
    fake = make_fake()
    cfg = AppConfig()
    cfg.account.username = "me@example.com"
    cfg.bot.scan_days = 365
    cfg.policy.dry_run = False
    ctx = AppContext(
        cfg, Store(tmp_path / "ui.db"), config_path=tmp_path / "config.json",
        client_factory=lambda h, p, u, pw: MailboxClient(h, p, u, pw, connection_factory=fake.factory),
        password_provider=lambda u: "secret",
    )
    backend = Backend(ctx)
    window = MainWindow(backend)
    window.show()
    yield fake, ctx, backend, window
    backend.shutdown()
    window.close()


def test_scan_updates_dashboard(app, env):
    fake, ctx, backend, window = env
    window.dashboard.scan_btn.click()
    assert wait_until(app, lambda: not backend.scanning and window.dashboard.table.rowCount() == 5)
    assert wait_until(app, lambda: window.dashboard.card_ads._value.text() == "1")
    assert window.dashboard.card_ai._value.text() == "1"
    assert window.dashboard.scan_btn.isEnabled()
    assert len(fake.store["[Gmail]/Trash"]) == 2


def test_mailbox_preview_and_trash(app, env):
    fake, ctx, backend, window = env
    window._show_page(1)
    mb = window.mailbox
    assert wait_until(app, lambda: mb.table.rowCount() == 5)
    assert mb.folder_box.currentText() == "INBOX"
    mb.table.selectRow(0)
    assert wait_until(app, lambda: "Advertisement score" in mb.preview.toPlainText())
    mb.table.selectRow(1)
    mb.trash_btn.click()
    assert wait_until(app, lambda: mb.table.rowCount() == 4)
    assert len(fake.store["[Gmail]/Trash"]) == 1


def test_review_and_activity_pages(app, env):
    fake, ctx, backend, window = env
    ctx.config.policy.dry_run = True
    window.dashboard.scan_btn.click()
    assert wait_until(app, lambda: not backend.scanning and window.dashboard.card_review._value.text() == "2")
    assert window.nav_buttons[2].text() == "Review (2)"
    window._show_page(2)
    assert wait_until(app, lambda: window.review.table.rowCount() == 2)
    window.review.table.selectRow(0)
    window.review.trash_btn.click()
    assert wait_until(app, lambda: window.review.table.rowCount() == 1)
    window._show_page(3)
    assert wait_until(app, lambda: window.activity.table.rowCount() == 1)
    window.activity.table.selectRow(0)
    window.activity.restore_btn.click()
    assert wait_until(app, lambda: window.activity.table.item(0, 6) and window.activity.table.item(0, 6).text() == "Restored")


def test_settings_roundtrip_and_connection_test(app, env):
    fake, ctx, backend, window = env
    s = window.settings
    s.provider.setCurrentText("Custom")
    s.host.setText("imap.example.org")
    s.username.setText("me@example.com")
    s.password.setText("secret")
    s.allowlist.setPlainText("Friend@Example.com\n\nexample.org")
    s.dry_run.setChecked(True)
    s.interval.setValue(30)
    s.test_btn.click()
    assert wait_until(app, lambda: "Connected" in s.test_notice.text())
    s.save_btn.click()
    assert ctx.config.account.host == "imap.example.org"
    assert ctx.config.policy.allowlist == ["friend@example.com", "example.org"]
    assert ctx.config.bot.interval_minutes == 30 and ctx.config.policy.dry_run
    assert (ctx.config_path).exists()


def test_bot_toggle_starts_scan(app, env):
    fake, ctx, backend, window = env
    window.dashboard.bot_btn.click()
    assert backend.bot_enabled
    assert wait_until(app, lambda: not backend.scanning and window.dashboard.card_scanned._value.text() == "5")
    assert window.dashboard.bot_btn.text() == "Stop bot"
    window.dashboard.bot_btn.click()
    assert not backend.bot_enabled


def test_auth_failure_is_shown(app, env):
    fake, ctx, backend, window = env
    fake.password = "different"
    window.dashboard.scan_btn.click()
    assert wait_until(app, lambda: "Authentication failed" in window.dashboard.notice.text())
    assert window.dashboard.scan_btn.isEnabled()
