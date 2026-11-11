"""Shared runtime context: configuration, storage and client construction."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import AppConfig, clean_entries, save_config
from .errors import MailboxError
from .mailbox import MailboxClient
from .secrets import get_password
from .store import Store


@dataclass
class AppContext:
    config: AppConfig
    store: Store
    config_path: Path | None = None
    client_factory: Callable[..., MailboxClient] = MailboxClient
    password_provider: Callable[[str], str] = get_password

    @property
    def account_key(self) -> str:
        return f"{self.config.account.username}@{self.config.account.host}"

    def open_client(self) -> MailboxClient:
        acc = self.config.account
        if not acc.username or not acc.host:
            raise MailboxError("The account is not configured. Open Settings and enter your IMAP details.")
        password = self.password_provider(acc.username)
        return self.client_factory(acc.host, acc.port, acc.username, password)

    def save_config(self) -> None:
        save_config(self.config, self.config_path)

    def add_to_list(self, which: str, entry: str) -> bool:
        """Add an address or domain to the 'allowlist' or 'blocklist'. Returns True if new."""
        policy = self.config.policy
        target = policy.allowlist if which == "allowlist" else policy.blocklist
        other = policy.blocklist if which == "allowlist" else policy.allowlist
        entry = entry.strip().lower()
        if not entry:
            return False
        if entry in other:
            other.remove(entry)
        if entry in target:
            return False
        target.append(entry)
        policy.allowlist = clean_entries(policy.allowlist)
        policy.blocklist = clean_entries(policy.blocklist)
        self.save_config()
        return True
