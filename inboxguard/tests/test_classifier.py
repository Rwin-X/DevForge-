from inboxguard.core.classifier import classify
from inboxguard.core.config import PolicyConfig
from inboxguard.core.parser import parse_message
from inboxguard.core.policy import decide, matches_entry

import samples


def run(raw):
    mail = parse_message(raw, uid=1, folder="INBOX")
    return mail, classify(mail)


def test_parser_extracts_fields():
    mail = parse_message(samples.PROMO, uid=7, folder="INBOX", flags=("\\Seen",))
    assert mail.sender_address == "deals@e.shoply.com"
    assert mail.subject.startswith("FLASH SALE")
    assert mail.message_id == "<promo-1@shoply.com>"
    assert mail.has_html and mail.tracking_pixels == 1 and mail.image_count == 5
    assert "Use code SAVE40" in mail.text
    assert not mail.is_unread
    assert mail.date is not None and mail.date.year == 2026


def test_parser_survives_garbage():
    mail = parse_message(b"\x00\xff garbage with no headers", uid=3)
    assert mail.uid == 3


def test_promo_scores_high_as_ad():
    _, result = run(samples.PROMO)
    assert result.ad_score >= 0.90
    assert any("List-Unsubscribe" in r for r in result.ad_reasons)


def test_plain_newsletter_goes_to_review_not_trash():
    _, result = run(samples.NEWSLETTER_ONLY_UNSUB)
    policy = PolicyConfig(dry_run=False)
    mail = parse_message(samples.NEWSLETTER_ONLY_UNSUB)
    decision = decide(mail, result, policy)
    assert 0.55 <= result.ad_score < 0.80
    assert decision.action == "review" and decision.category == "ad"


def test_personal_mail_is_kept():
    mail, result = run(samples.PERSONAL)
    assert result.ad_score < 0.2 and result.ai_score < 0.2
    assert decide(mail, result, PolicyConfig(dry_run=False)).action == "keep"


def test_transactional_mail_is_not_treated_as_ad():
    mail, result = run(samples.TRANSACTIONAL)
    assert result.ad_score < 0.55
    assert decide(mail, result, PolicyConfig(dry_run=False)).action == "keep"


def test_ai_boilerplate_is_trashed():
    mail, result = run(samples.AI_BOILERPLATE)
    assert result.ai_score >= 0.90
    decision = decide(mail, result, PolicyConfig(dry_run=False))
    assert (decision.action, decision.category) == ("trash", "ai")


def test_ai_placeholder_plus_style_is_trashed_at_default_threshold():
    mail, result = run(samples.AI_PLACEHOLDER)
    assert result.ai_score >= 0.90
    assert any("placeholder" in r.lower() for r in result.ai_reasons)


def test_style_only_signals_never_reach_trash_threshold():
    mail, result = run(samples.AI_STYLE_ONLY)
    assert 0.60 <= result.ai_score <= 0.85
    decision = decide(mail, result, PolicyConfig(dry_run=False))
    assert (decision.action, decision.category) == ("review", "ai")


def test_dry_run_downgrades_trash_to_review():
    mail, result = run(samples.PROMO)
    decision = decide(mail, result, PolicyConfig(dry_run=True))
    assert decision.action == "review"
    assert decision.reasons[0].startswith("Dry run")


def test_allowlist_blocklist_and_correspondents():
    mail, result = run(samples.PROMO)
    allow = PolicyConfig(dry_run=False, allowlist=["shoply.com"])
    assert decide(mail, result, allow).action == "keep"
    sub = PolicyConfig(dry_run=False, allowlist=["@shoply.com"])
    assert decide(mail, result, sub).action == "keep"
    known = {"deals@e.shoply.com"}
    assert decide(mail, result, PolicyConfig(dry_run=False), known).action == "keep"
    block = PolicyConfig(dry_run=False, blocklist=["deals@e.shoply.com"], allowlist=[])
    pers, pres = run(samples.PERSONAL)
    assert decide(pers, pres, PolicyConfig(dry_run=False, blocklist=["bob@example.net"])).action == "trash"
    assert decide(mail, result, block).action == "trash"


def test_matches_entry_edge_cases():
    assert matches_entry("a@mail.shoply.com", ["shoply.com"])
    assert not matches_entry("a@notshoply.com", ["shoply.com"])
    assert matches_entry("a@x.org", ["a@x.org"])
    assert not matches_entry("b@x.org", ["a@x.org"])
    assert not matches_entry("", ["x.org"])
