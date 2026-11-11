"""Exception hierarchy for the core layer."""
from __future__ import annotations


class InboxGuardError(RuntimeError):
    """Base class for all expected, user-presentable errors."""


class MailboxError(InboxGuardError):
    """IMAP connection, authentication or command failure."""


class SecretError(InboxGuardError):
    """Credential storage failure."""
