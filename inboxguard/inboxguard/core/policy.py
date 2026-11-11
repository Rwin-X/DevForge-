"""Turn classifier scores into a keep / review / trash decision."""
from __future__ import annotations

from .config import PolicyConfig
from .models import ClassifierResult, Decision, ParsedEmail


def matches_entry(address: str, entries: list[str]) -> bool:
    """True when the address equals an entry or belongs to an entry's domain."""
    address = address.strip().lower()
    if not address:
        return False
    domain = address.rpartition("@")[2]
    for entry in entries:
        entry = entry.strip().lower()
        if not entry:
            continue
        if "@" in entry.lstrip("@"):
            if address == entry:
                return True
            continue
        bare = entry.lstrip("@")
        if domain == bare or domain.endswith("." + bare):
            return True
    return False


def decide(
    mail: ParsedEmail,
    result: ClassifierResult,
    policy: PolicyConfig,
    known_addresses: set[str] | frozenset[str] = frozenset(),
) -> Decision:
    sender = mail.sender_address

    if matches_entry(sender, policy.blocklist):
        decision = Decision("trash", "ad", 1.0, ["Sender is on the blocklist"])
        return _apply_dry_run(decision, policy)

    if matches_entry(sender, policy.allowlist):
        return Decision("keep", "", 0.0, ["Sender is on the allowlist"])

    if policy.protect_correspondents and sender in known_addresses:
        return Decision("keep", "", 0.0, ["You have written to this address before"])

    ad, ai = result.ad_score, result.ai_score

    if ad >= policy.ad_trash_threshold:
        return _apply_dry_run(Decision("trash", "ad", ad, list(result.ad_reasons)), policy)
    if ai >= policy.ai_trash_threshold:
        return _apply_dry_run(Decision("trash", "ai", ai, list(result.ai_reasons)), policy)

    ad_over = ad - policy.ad_review_threshold
    ai_over = ai - policy.ai_review_threshold
    if ad_over >= 0 or ai_over >= 0:
        if ad_over >= ai_over:
            return Decision("review", "ad", ad, list(result.ad_reasons))
        return Decision("review", "ai", ai, list(result.ai_reasons))

    return Decision("keep", "", max(ad, ai), [])


def _apply_dry_run(decision: Decision, policy: PolicyConfig) -> Decision:
    if policy.dry_run and decision.action == "trash":
        return Decision(
            "review",
            decision.category,
            decision.score,
            ["Dry run: would have been trashed"] + decision.reasons,
        )
    return decision
