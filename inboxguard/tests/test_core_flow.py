import imaplib

import pytest

from inboxguard.core.config import AppConfig
from inboxguard.core.context import AppContext
from inboxguard.core.engine import ScanEngine
from inboxguard.core.errors import MailboxError
from inboxguard.core.mailbox import MailboxClient
from inboxguard.core.service import MailService, check_connection
from inboxguard.core.store import Store

import samples
from fake_imap import FakeIMAP

SENT_TO_ALICE = b"From: me@example.com\r\nTo: Alice Writer <alice@blog.example.org>\r\nSubject: hi\r\n\r\nhello\r\n"


def make_fake(**kw):
    return FakeIMAP(
        {
            "INBOX": {1: samples.PROMO, 2: samples.PERSONAL, 3: samples.AI_BOILERPLATE,
                      4: samples.NEWSLETTER_ONLY_UNSUB, 5: samples.TRANSACTIONAL},
            "[Gmail]/Trash": {},
            "[Gmail]/Sent Mail": {1: SENT_TO_ALICE},
        },
        **kw,
    )


def make_ctx(tmp_path, fake, dry_run=False):
    cfg = AppConfig()
    cfg.account.username = "me@example.com"
    cfg.policy.dry_run = dry_run
    cfg.bot.scan_days = 365
    return AppContext(
        cfg, Store(tmp_path / "t.db"), config_path=tmp_path / "config.json",
        client_factory=lambda h, p, u, pw: MailboxClient(h, p, u, pw, connection_factory=fake.factory),
        password_provider=lambda u: "secret",
    )


def test_folder_listing_and_special_use():
    fake = make_fake()
    with MailboxClient("h", 993, "u", "secret", connection_factory=fake.factory) as c:
        names = [f.name for f in c.list_folders()]
        assert "INBOX" in names and "[Gmail]" not in names  # \Noselect skipped
        assert c.trash_folder() == "[Gmail]/Trash"
        assert c.sent_folder() == "[Gmail]/Sent Mail"


def test_bad_password_gives_friendly_error():
    fake = make_fake()
    with pytest.raises(MailboxError, match="app password"):
        MailboxClient("h", 993, "u", "wrong", connection_factory=fake.factory).connect()


def test_scan_trashes_only_confident_matches(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake)
    summary = ScanEngine(ctx).run()
    assert summary.scanned == 5
    assert summary.trashed_ads == 1 and summary.trashed_ai == 1
    assert sorted(fake.store["INBOX"]) == [2, 4, 5]  # personal, newsletter (protected), receipt
    assert len(fake.store["[Gmail]/Trash"]) == 2
    stats = ctx.store.stats(ctx.account_key)
    assert stats["ads_trashed"] == 1 and stats["ai_trashed"] == 1 and stats["kept"] == 3


def test_second_scan_skips_processed_messages(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake)
    ScanEngine(ctx).run()
    again = ScanEngine(ctx).run()
    assert again.scanned == 0


def test_dry_run_moves_nothing(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake, dry_run=True)
    summary = ScanEngine(ctx).run()
    assert summary.trashed == 0 and summary.review == 2
    assert len(fake.store["INBOX"]) == 5
    assert not fake.store["[Gmail]/Trash"]


def test_scan_does_not_mark_messages_read(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake)
    ScanEngine(ctx).run()
    assert all("\\Seen" not in m["flags"] for m in fake.store["INBOX"].values())


def test_restore_returns_message_to_inbox(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake)
    ScanEngine(ctx).run()
    service = MailService(ctx)
    actions = [a for a in service.activity() if a["kind"] == "trash_auto"]
    assert len(actions) == 2
    service.restore(actions[0]["id"])
    assert len(fake.store["INBOX"]) == 4
    with pytest.raises(MailboxError, match="already restored"):
        service.restore(actions[0]["id"])


def test_review_queue_trash_and_trust(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake, dry_run=True)
    ScanEngine(ctx).run()
    service = MailService(ctx)
    items = service.review_items()
    assert len(items) == 2
    promo = next(i for i in items if i["category"] == "ad")
    other = next(i for i in items if i["category"] == "ai")
    assert service.resolve_review([promo], "trash") == 1
    assert len(fake.store["[Gmail]/Trash"]) == 1
    service.resolve_review([other], "trust")
    assert "sam@growthco.example" in ctx.config.policy.allowlist
    assert service.review_items() == []


def test_move_fallback_without_move_capability(tmp_path):
    fake = make_fake(caps=b"IMAP4rev1")
    ctx = make_ctx(tmp_path, fake)
    ScanEngine(ctx).run()
    kinds = [c[0] for c in fake.commands]
    assert "COPY" in kinds and "STORE" in kinds and "EXPUNGE" in kinds and "MOVE" not in kinds
    assert sorted(fake.store["INBOX"]) == [2, 4, 5]


def test_listing_shows_verdicts_and_flags(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake, dry_run=True)
    ScanEngine(ctx).run()
    listing = MailService(ctx).list_messages("INBOX", limit=10)
    assert [r.mail.uid for r in listing.rows] == [5, 4, 3, 2, 1]
    by_uid = {r.mail.uid: r for r in listing.rows}
    assert by_uid[1].status == "review" and by_uid[1].category == "ad"
    assert by_uid[2].status == "kept"
    assert by_uid[2].mail.is_unread


def test_manual_actions(tmp_path):
    fake = make_fake()
    ctx = make_ctx(tmp_path, fake)
    service = MailService(ctx)
    listing = service.list_messages("INBOX")
    target = [r.mail for r in listing.rows if r.mail.uid == 2]
    service.set_seen("INBOX", target, True)
    assert "\\Seen" in fake.store["INBOX"][2]["flags"]
    service.move_messages("INBOX", target, "[Gmail]/Sent Mail")
    assert 2 not in fake.store["INBOX"]
    blocked = [r.mail for r in listing.rows if r.mail.uid == 1]
    service.block_sender("INBOX", blocked)
    assert "deals@e.shoply.com" in ctx.config.policy.blocklist
    assert 1 not in fake.store["INBOX"]
    detail = service.load_message("INBOX", 3)
    assert detail.result.ai_score >= 0.9


def test_check_connection_reports_trash():
    fake = make_fake()
    text = check_connection(lambda h, p, u, pw: MailboxClient(h, p, u, pw, connection_factory=fake.factory),
                            "h", 993, "u", "secret")
    assert "Trash folder: [Gmail]/Trash" in text
