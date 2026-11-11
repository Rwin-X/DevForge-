"""Application configuration: dataclasses, JSON persistence and platform paths."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

APP_NAME = "inboxguard"

# Providers that accept an IMAP app password. Microsoft personal and 365
# accounts require OAuth2, which this version does not implement.
PROVIDERS: dict[str, tuple[str, int]] = {
    "Gmail": ("imap.gmail.com", 993),
    "Yahoo": ("imap.mail.yahoo.com", 993),
    "iCloud": ("imap.mail.me.com", 993),
    "Fastmail": ("imap.fastmail.com", 993),
    "Custom": ("", 993),
}


def config_dir() -> Path:
    override = os.environ.get("INBOXGUARD_HOME")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


def database_path() -> Path:
    return config_dir() / "inboxguard.db"


@dataclass
class AccountConfig:
    provider: str = "Gmail"
    host: str = "imap.gmail.com"
    port: int = 993
    username: str = ""


@dataclass
class PolicyConfig:
    ad_trash_threshold: float = 0.80
    ad_review_threshold: float = 0.55
    ai_trash_threshold: float = 0.90
    ai_review_threshold: float = 0.60
    dry_run: bool = True
    protect_correspondents: bool = True
    allowlist: list[str] = field(default_factory=list)
    blocklist: list[str] = field(default_factory=list)


@dataclass
class BotConfig:
    scan_folder: str = "INBOX"
    scan_days: int = 14
    max_messages_per_scan: int = 200
    interval_minutes: int = 15
    auto_scan: bool = False


@dataclass
class AppConfig:
    account: AccountConfig = field(default_factory=AccountConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    bot: BotConfig = field(default_factory=BotConfig)

    def normalized(self) -> "AppConfig":
        """Clamp values into safe ranges and clean list entries in place."""
        p, b, a = self.policy, self.bot, self.account
        p.ad_trash_threshold = _clamp(p.ad_trash_threshold, 0.5, 1.0)
        p.ai_trash_threshold = _clamp(p.ai_trash_threshold, 0.5, 1.0)
        p.ad_review_threshold = _clamp(p.ad_review_threshold, 0.1, p.ad_trash_threshold)
        p.ai_review_threshold = _clamp(p.ai_review_threshold, 0.1, p.ai_trash_threshold)
        p.allowlist = clean_entries(p.allowlist)
        p.blocklist = clean_entries(p.blocklist)
        b.scan_days = int(_clamp(b.scan_days, 1, 365))
        b.max_messages_per_scan = int(_clamp(b.max_messages_per_scan, 10, 2000))
        b.interval_minutes = int(_clamp(b.interval_minutes, 1, 1440))
        b.scan_folder = b.scan_folder.strip() or "INBOX"
        a.host = a.host.strip()
        a.username = a.username.strip()
        a.port = int(_clamp(a.port, 1, 65535))
        return self


def clean_entries(entries: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for raw in entries:
        entry = str(raw).strip().lower()
        if entry:
            seen.setdefault(entry, None)
    return list(seen)


def _clamp(value: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, number))


def _build(cls, data):
    if not isinstance(data, dict):
        return cls()
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


def config_from_dict(data: dict) -> AppConfig:
    cfg = AppConfig(
        account=_build(AccountConfig, data.get("account")),
        policy=_build(PolicyConfig, data.get("policy")),
        bot=_build(BotConfig, data.get("bot")),
    )
    return cfg.normalized()


def load_config(path: Path | None = None) -> AppConfig:
    target = path or config_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return AppConfig().normalized()
    return config_from_dict(data if isinstance(data, dict) else {})


def save_config(cfg: AppConfig, path: Path | None = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
    os.replace(tmp, target)
