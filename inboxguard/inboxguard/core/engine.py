"""Scan orchestration: fetch new mail, classify, apply the policy, record results."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable

from .classifier import classify
from .context import AppContext
from .errors import MailboxError
from .mailbox import imap_date
from .models import Decision, ParsedEmail
from .policy import decide
from .store import ItemRecord

CHUNK = 25


@dataclass
class ScanItem:
    sender: str
    subject: str
    decision: str  # kept | review | trashed
    category: str
    score: float
    reasons: list[str] = field(default_factory=list)
    when: datetime | None = None


@dataclass
class ScanSummary:
    scanned: int = 0
    trashed_ads: int = 0
    trashed_ai: int = 0
    review: int = 0
    kept: int = 0
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def trashed(self) -> int:
        return self.trashed_ads + self.trashed_ai

    def describe(self) -> str:
        text = (
            f"Scanned {self.scanned}: {self.trashed_ads} ads and {self.trashed_ai} AI-written "
            f"trashed, {self.review} for review, {self.kept} kept"
        )
        if self.cancelled:
            text += " (cancelled)"
        if self.errors:
            text += f"; {len(self.errors)} error(s)"
        return text


class ScanEngine:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx

    def run(
        self,
        progress: Callable[[int, int, str], None] | None = None,
        on_item: Callable[[ScanItem], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> ScanSummary:
        cfg = self.ctx.config
        store = self.ctx.store
        account = self.ctx.account_key
        folder = cfg.bot.scan_folder
        summary = ScanSummary()

        with self.ctx.open_client() as client:
            _exists, validity = client.select_folder(folder)
            since = date.today() - timedelta(days=cfg.bot.scan_days)
            found = client.search_uids(folder, "SINCE", imap_date(since))
            done = store.processed_uids(account, folder, validity)
            todo = sorted((u for u in found if u not in done), reverse=True)
            todo = todo[: cfg.bot.max_messages_per_scan]
            total = len(todo)
            if progress:
                progress(0, total, f"Found {total} new message(s)")
            if not todo:
                return summary

            known: set[str] = set()
            if cfg.policy.protect_correspondents:
                if progress:
                    progress(0, total, "Reading sent mail to protect your contacts")
                known = client.known_correspondents()

            handled = 0
            for start in range(0, total, CHUNK):
                if should_cancel and should_cancel():
                    summary.cancelled = True
                    break
                chunk = todo[start : start + CHUNK]
                mails = client.fetch_scan(folder, chunk)
                decisions = [(m, classify(m)) for m in mails]
                planned = [(m, r, decide(m, r, cfg.policy, known)) for m, r in decisions]

                to_trash = [m for m, _r, d in planned if d.action == "trash"]
                failed: set[int] = set()
                if to_trash:
                    try:
                        client.trash(folder, [m.uid for m in to_trash])
                    except MailboxError as exc:
                        summary.errors.append(str(exc))
                        failed = {m.uid for m in to_trash}

                for mail, result, decision in planned:
                    status = {"trash": "trashed", "review": "review", "keep": "kept"}[decision.action]
                    if mail.uid in failed:
                        status = "review"
                        decision = Decision("review", decision.category, decision.score,
                                            ["Could not move to Trash"] + decision.reasons)
                    self._record(account, folder, validity, mail, result, decision, status)
                    self._count(summary, status, decision.category)
                    if on_item:
                        on_item(ScanItem(mail.sender_display, mail.subject, status,
                                         decision.category, decision.score, decision.reasons, mail.date))
                handled += len(chunk)
                if progress:
                    progress(min(handled, total), total, f"Processed {min(handled, total)} of {total}")
        return summary

    def _record(self, account, folder, validity, mail: ParsedEmail, result, decision: Decision, status: str):
        self.ctx.store.record_item(
            ItemRecord(
                account=account, folder=folder, uidvalidity=validity, uid=mail.uid,
                message_id=mail.message_id, sender=mail.sender_display, subject=mail.subject,
                date_utc=mail.date.isoformat() if mail.date else "",
                ad_score=result.ad_score, ai_score=result.ai_score,
                category=decision.category, score=decision.score,
                reasons=decision.reasons, status=status,
            )
        )
        if status == "trashed":
            self.ctx.store.log_action(
                account, "trash_auto", folder, mail.message_id, mail.sender_display,
                mail.subject, decision.category, decision.score,
            )

    @staticmethod
    def _count(summary: ScanSummary, status: str, category: str) -> None:
        summary.scanned += 1
        if status == "trashed":
            if category == "ai":
                summary.trashed_ai += 1
            else:
                summary.trashed_ads += 1
        elif status == "review":
            summary.review += 1
        else:
            summary.kept += 1
