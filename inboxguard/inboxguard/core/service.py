"""Interactive mailbox operations used by the dashboard.

Each method opens its own IMAP connection, so calls are safe to run on
worker threads.
"""
from __future__ import annotations

from dataclasses import dataclass

from .classifier import classify
from .context import AppContext
from .errors import MailboxError
from .mailbox import FolderInfo, MailboxClient, decode_imap_utf7
from .models import ClassifierResult, ParsedEmail


@dataclass
class MessageRow:
    mail: ParsedEmail
    status: str = ""  # kept | review | trashed | restored | empty
    category: str = ""
    score: float = 0.0


@dataclass
class Listing:
    folder: str
    uidvalidity: int
    rows: list[MessageRow]


@dataclass
class MessageDetail:
    mail: ParsedEmail
    result: ClassifierResult


class MailService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx

    # ---- reading -----------------------------------------------------

    def folders(self) -> list[FolderInfo]:
        with self.ctx.open_client() as client:
            return list(client.list_folders())

    def list_messages(self, folder: str, limit: int = 100) -> Listing:
        with self.ctx.open_client() as client:
            _exists, validity = client.select_folder(folder, readonly=True)
            uids = client.search_uids(folder, "ALL", readonly=True)[-limit:]
            mails = client.fetch_summaries(folder, uids)
        mails.sort(key=lambda m: m.uid, reverse=True)
        verdicts = self.ctx.store.verdicts(self.ctx.account_key, folder, validity, [m.uid for m in mails])
        rows = []
        for mail in mails:
            v = verdicts.get(mail.uid)
            rows.append(MessageRow(mail, v["status"], v["category"], v["score"]) if v else MessageRow(mail))
        return Listing(folder, validity, rows)

    def load_message(self, folder: str, uid: int) -> MessageDetail:
        with self.ctx.open_client() as client:
            mail = client.fetch_full(folder, uid)
        if mail is None:
            raise MailboxError("The message no longer exists in this folder.")
        return MessageDetail(mail, classify(mail))

    # ---- changing ----------------------------------------------------

    def trash_messages(self, folder: str, mails: list[ParsedEmail], kind: str = "trash_manual") -> int:
        if not mails:
            return 0
        with self.ctx.open_client() as client:
            client.trash(folder, [m.uid for m in mails])
        for mail in mails:
            self.ctx.store.log_action(
                self.ctx.account_key, kind, folder, mail.message_id, mail.sender_display, mail.subject
            )
            self.ctx.store.set_status_by_message_id(self.ctx.account_key, mail.message_id, "trashed")
        return len(mails)

    def delete_permanently(self, folder: str, mails: list[ParsedEmail]) -> int:
        if not mails:
            return 0
        with self.ctx.open_client() as client:
            client.delete_permanently(folder, [m.uid for m in mails])
        return len(mails)

    def move_messages(self, folder: str, mails: list[ParsedEmail], dest: str) -> int:
        if not mails:
            return 0
        with self.ctx.open_client() as client:
            client.move(folder, [m.uid for m in mails], dest)
        return len(mails)

    def set_seen(self, folder: str, mails: list[ParsedEmail], seen: bool) -> int:
        if not mails:
            return 0
        with self.ctx.open_client() as client:
            client.set_flag(folder, [m.uid for m in mails], "\\Seen", seen)
        return len(mails)

    def block_sender(self, folder: str, mails: list[ParsedEmail]) -> int:
        for mail in mails:
            self.ctx.add_to_list("blocklist", mail.sender_address)
        return self.trash_messages(folder, mails, kind="trash_blocked")

    def trust_sender(self, mails: list[ParsedEmail]) -> int:
        added = 0
        for mail in mails:
            added += int(self.ctx.add_to_list("allowlist", mail.sender_address))
        return added

    # ---- review queue ------------------------------------------------

    def review_items(self) -> list[dict]:
        return self.ctx.store.review_items(self.ctx.account_key)

    def resolve_review(self, items: list[dict], action: str) -> int:
        """action: 'trash' | 'keep' | 'trust'."""
        account = self.ctx.account_key
        store = self.ctx.store
        if action in ("keep", "trust"):
            for item in items:
                store.set_item_status(account, item["folder"], item["uidvalidity"], item["uid"], "kept")
                if action == "trust":
                    address = _address_of(item["sender"])
                    if address:
                        self.ctx.add_to_list("allowlist", address)
            return len(items)

        moved = 0
        by_folder: dict[str, list[dict]] = {}
        for item in items:
            by_folder.setdefault(item["folder"], []).append(item)
        with self.ctx.open_client() as client:
            for folder, group in by_folder.items():
                _e, validity = client.select_folder(folder)
                targets: list[tuple[dict, int]] = []
                for item in group:
                    uid = item["uid"] if item["uidvalidity"] == validity else \
                        client.find_uid_by_message_id(folder, item["message_id"])
                    if uid:
                        targets.append((item, uid))
                if targets:
                    client.trash(folder, [uid for _item, uid in targets])
                for item, _uid in targets:
                    store.set_item_status(account, folder, item["uidvalidity"], item["uid"], "trashed")
                    store.log_action(account, "trash_review", folder, item["message_id"],
                                     item["sender"], item["subject"], item["category"], item["score"])
                    moved += 1
        return moved

    # ---- undo --------------------------------------------------------

    def activity(self) -> list[dict]:
        return self.ctx.store.recent_actions(self.ctx.account_key)

    def restore(self, action_id: int) -> str:
        action = self.ctx.store.get_action(action_id)
        if not action or not action["kind"].startswith("trash"):
            raise MailboxError("This action cannot be restored.")
        if action["undone"]:
            raise MailboxError("This message was already restored.")
        with self.ctx.open_client() as client:
            trash = client.trash_folder()
            uid = client.find_uid_by_message_id(trash, action["message_id"])
            if uid is None:
                raise MailboxError("The message is no longer in Trash (it may have been purged).")
            client.move(trash, [uid], action["folder"] or "INBOX")
        self.ctx.store.mark_undone(action_id)
        self.ctx.store.set_status_by_message_id(self.ctx.account_key, action["message_id"], "restored")
        return action["subject"]

    # ---- misc --------------------------------------------------------

    def stats(self) -> dict[str, int]:
        return self.ctx.store.stats(self.ctx.account_key)

    def recent_items(self, limit: int = 60) -> list[dict]:
        return self.ctx.store.recent_items(self.ctx.account_key, limit)


def check_connection(factory, host: str, port: int, username: str, password: str) -> str:
    """Connect with explicit settings (not the saved ones) and report what was found."""
    if not host or not username or not password:
        raise MailboxError("Enter the server, username and password first.")
    client: MailboxClient = factory(host, port, username, password)
    with client:
        folders = client.list_folders()
        try:
            trash = decode_imap_utf7(client.trash_folder())
        except MailboxError:
            trash = "not found"
    return f"Connected. {len(folders)} folders found. Trash folder: {trash}."


def _address_of(display: str) -> str:
    from email.utils import parseaddr

    return parseaddr(display)[1].lower()
