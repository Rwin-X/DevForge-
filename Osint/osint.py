#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════╗
║              USERNAME OSINT TOOL — osint.py                      ║
║     Lawful OSINT & Defensive Research Use Only                   ║
╚═══════════════════════════════════════════════════════════════════╝

LEGAL NOTICE:
  This tool is designed exclusively for lawful OSINT (Open Source
  Intelligence) and defensive security research. By using this tool
  you agree to:
    - Only investigate publicly accessible information.
    - Comply with all applicable laws and platform Terms of Service.
    - Not use this tool to harass, stalk, or harm individuals.
    - Not bypass authentication or perform brute-force attacks.
  The authors assume no liability for misuse.

Usage:
  python osint.py <username> [options]

Examples:
  python osint.py johndoe
  python osint.py johndoe --json results.json
  python osint.py johndoe --csv  results.csv
  python osint.py johndoe --html report.html
  python osint.py johndoe --json results.json --html report.html
  python osint.py johndoe --timeout 15 --retries 3
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Standard-library imports (no third-party dependencies required)
# ---------------------------------------------------------------------------
import argparse
import asyncio
import csv
import html as html_module
import json
import os
import random
import re
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Python version guard
# ---------------------------------------------------------------------------
if sys.version_info < (3, 8):
    sys.exit("Python 3.8 or higher is required.")

# ═══════════════════════════════════════════════════════════════════════════
# §1  COLOUR / TERMINAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════

# Detect colour support
_COLOUR_ENABLED: bool = (
    sys.stdout.isatty()
    and os.environ.get("NO_COLOR") is None
    and os.environ.get("TERM") != "dumb"
)

# Enable VT100 on Windows
if sys.platform == "win32":
    import ctypes
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        _COLOUR_ENABLED = False


class C:
    """ANSI colour / style codes."""
    RESET   = "\033[0m"  if _COLOUR_ENABLED else ""
    BOLD    = "\033[1m"  if _COLOUR_ENABLED else ""
    DIM     = "\033[2m"  if _COLOUR_ENABLED else ""
    RED     = "\033[91m" if _COLOUR_ENABLED else ""
    GREEN   = "\033[92m" if _COLOUR_ENABLED else ""
    YELLOW  = "\033[93m" if _COLOUR_ENABLED else ""
    BLUE    = "\033[94m" if _COLOUR_ENABLED else ""
    MAGENTA = "\033[95m" if _COLOUR_ENABLED else ""
    CYAN    = "\033[96m" if _COLOUR_ENABLED else ""
    WHITE   = "\033[97m" if _COLOUR_ENABLED else ""
    GRAY    = "\033[90m" if _COLOUR_ENABLED else ""


def colour(text: str, *codes: str) -> str:
    """Wrap *text* in ANSI codes (noop when colour is disabled)."""
    if not _COLOUR_ENABLED:
        return text
    return "".join(codes) + text + C.RESET


# ═══════════════════════════════════════════════════════════════════════════
# §2  DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

class Status(Enum):
    """Result status for a single platform check."""
    FOUND       = "FOUND"
    NOT_FOUND   = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR       = "ERROR"


@dataclass
class ProfileData:
    """Collected intelligence about a discovered profile."""
    display_name:  Optional[str] = None
    bio:           Optional[str] = None
    avatar_url:    Optional[str] = None
    followers:     Optional[int] = None
    following:     Optional[int] = None
    repos:         Optional[int] = None
    public_posts:  Optional[int] = None
    location:      Optional[str] = None
    website:       Optional[str] = None
    created_at:    Optional[str] = None
    extra:         Dict[str, str] = field(default_factory=dict)


@dataclass
class PlatformResult:
    """Result of checking a single platform."""
    platform:    str
    url:         str
    status:      Status
    profile:     Optional[ProfileData] = None
    error_msg:   Optional[str] = None
    response_ms: int = 0

    # ------------------------------------------------------------------ #
    def status_label(self) -> str:
        labels = {
            Status.FOUND:        colour(" FOUND       ", C.BOLD, C.GREEN),
            Status.NOT_FOUND:    colour(" NOT FOUND   ", C.DIM, C.GRAY),
            Status.RATE_LIMITED: colour(" RATE LIMITED", C.BOLD, C.YELLOW),
            Status.ERROR:        colour(" ERROR       ", C.BOLD, C.RED),
        }
        return labels[self.status]

    def to_dict(self) -> dict:
        d: dict = {
            "platform":    self.platform,
            "url":         self.url,
            "status":      self.status.value,
            "response_ms": self.response_ms,
        }
        if self.error_msg:
            d["error"] = self.error_msg
        if self.profile:
            pd = {k: v for k, v in asdict(self.profile).items() if v is not None and v != {}}
            if pd:
                d["profile"] = pd
        return d


@dataclass
class ScanReport:
    """Complete scan report for a username."""
    username:   str
    started_at: str
    ended_at:   str
    duration_s: float
    results:    List[PlatformResult] = field(default_factory=list)

    # Convenience counters
    @property
    def found(self) -> List[PlatformResult]:
        return [r for r in self.results if r.status == Status.FOUND]

    @property
    def not_found(self) -> List[PlatformResult]:
        return [r for r in self.results if r.status == Status.NOT_FOUND]

    @property
    def rate_limited(self) -> List[PlatformResult]:
        return [r for r in self.results if r.status == Status.RATE_LIMITED]

    @property
    def errors(self) -> List[PlatformResult]:
        return [r for r in self.results if r.status == Status.ERROR]

    def to_dict(self) -> dict:
        return {
            "username":   self.username,
            "started_at": self.started_at,
            "ended_at":   self.ended_at,
            "duration_s": round(self.duration_s, 2),
            "summary": {
                "total":       len(self.results),
                "found":       len(self.found),
                "not_found":   len(self.not_found),
                "rate_limited":len(self.rate_limited),
                "errors":      len(self.errors),
            },
            "results": [r.to_dict() for r in self.results],
        }


# ═══════════════════════════════════════════════════════════════════════════
# §3  HTTP CLIENT  (pure stdlib — no aiohttp / requests)
# ═══════════════════════════════════════════════════════════════════════════

# Rotating User-Agents to reduce fingerprinting
_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4.1 Safari/605.1.15",

    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",

    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _http_get(
    url: str,
    *,
    timeout: int = 10,
    retries: int = 2,
    headers: Optional[Dict[str, str]] = None,
    allow_redirects: bool = True,
) -> Tuple[int, bytes, Dict[str, str]]:
    """
    Synchronous HTTP GET with retry logic.

    Returns:
        (status_code, body_bytes, response_headers)
    Raises:
        urllib.error.URLError / socket.timeout on final failure.
    """
    req_headers = {
        "User-Agent": _random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
    }
    if headers:
        req_headers.update(headers)

    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            # urllib follows redirects by default; to block them we'd need a
            # custom opener — keep it simple and always allow for public profiles.
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body  = resp.read()
                code  = resp.status
                hdrs  = dict(resp.headers)
                return code, body, hdrs
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read() or b"", dict(exc.headers)
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))  # brief back-off

    raise last_exc  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════
# §4  PLATFORM DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

class PlatformChecker:
    """
    Base class for a platform checker.

    Subclasses implement `check(username, timeout, retries)` and return a
    `PlatformResult`.  The async wrapper runs them in a thread-pool so the
    entire scan is concurrent without requiring aiohttp.
    """

    name: str = "Unknown"

    def url_for(self, username: str) -> str:
        raise NotImplementedError

    def check(self, username: str, timeout: int, retries: int) -> PlatformResult:
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _grep(pattern: str, text: str, group: int = 1) -> Optional[str]:
        """Return the first regex match group, stripped, or None."""
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                v = m.group(group).strip()
                return v if v else None
            except IndexError:
                return None
        return None

    @staticmethod
    def _clean(text: str) -> str:
        """Strip HTML tags and collapse whitespace."""
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


# ─────────────────────────────── GitHub ──────────────────────────────────

class GitHubChecker(PlatformChecker):
    name = "GitHub"

    def url_for(self, username: str) -> str:
        return f"https://github.com/{username}"

    def check(self, username: str, timeout: int, retries: int) -> PlatformResult:
        url   = self.url_for(username)
        t0    = time.monotonic()
        try:
            # Use the public API (unauthenticated, rate-limited at 60 req/hr)
            api_url = f"https://api.github.com/users/{username}"
            code, body, hdrs = _http_get(
                api_url,
                timeout=timeout,
                retries=retries,
                headers={"Accept": "application/vnd.github+json"},
            )
            ms = int((time.monotonic() - t0) * 1000)

            if code == 200:
                data = json.loads(body)
                profile = ProfileData(
                    display_name = data.get("name"),
                    bio          = data.get("bio"),
                    avatar_url   = data.get("avatar_url"),
                    followers    = data.get("followers"),
                    following    = data.get("following"),
                    repos        = data.get("public_repos"),
                    location     = data.get("location"),
                    website      = data.get("blog") or None,
                    created_at   = data.get("created_at"),
                    extra        = {"company": data.get("company") or ""},
                )
                return PlatformResult(self.name, url, Status.FOUND, profile, response_ms=ms)
            elif code == 404:
                return PlatformResult(self.name, url, Status.NOT_FOUND, response_ms=ms)
            elif code == 403:
                return PlatformResult(self.name, url, Status.RATE_LIMITED, response_ms=ms)
            else:
                return PlatformResult(self.name, url, Status.ERROR,
                                      error_msg=f"HTTP {code}", response_ms=ms)
        except Exception as exc:
            ms = int((time.monotonic() - t0) * 1000)
            return PlatformResult(self.name, url, Status.ERROR,
                                  error_msg=str(exc), response_ms=ms)


# ─────────────────────────────── GitLab ──────────────────────────────────

class GitLabChecker(PlatformChecker):
    name = "GitLab"

    def url_for(self, username: str) -> str:
        return f"https://gitlab.com/{username}"

    def check(self, username: str, timeout: int, retries: int) -> PlatformResult:
        url = self.url_for(username)
        t0  = time.monotonic()
        try:
            api_url = f"https://gitlab.com/api/v4/users?username={username}"
            code, body, _ = _http_get(api_url, timeout=timeout, retries=retries)
            ms = int((time.monotonic() - t0) * 1000)
            if code == 200:
                data = json.loads(body)
                if data:
                    u = data[0]
                    profile = ProfileData(
                        display_name = u.get("name"),
                        bio          = u.get("bio"),
                        avatar_url   = u.get("avatar_url"),
                        website      = u.get("website_url") or None,
                        created_at   = u.get("created_at"),
                    )
                    return PlatformResult(self.name, url, Status.FOUND, profile, response_ms=ms)
                return PlatformResult(self.name, url, Status.NOT_FOUND, response_ms=ms)
            elif code == 429:
                return PlatformResult(self.name, url, Status.RATE_LIMITED, response_ms=ms)
            else:
                return PlatformResult(self.name, url, Status.ERROR,
                                      error_msg=f"HTTP {code}", response_ms=ms)
        except Exception as exc:
            ms = int((time.monotonic() - t0) * 1000)
            return PlatformResult(self.name, url, Status.ERROR,
                                  error_msg=str(exc), response_ms=ms)


# ─────────────────────────────── Reddit ──────────────────────────────────

class RedditChecker(PlatformChecker):
    name = "Reddit"

    def url_for(self, username: str) -> str:
        return f"https://www.reddit.com/user/{username}"

    def check(self, username: str, timeout: int, retries: int) -> PlatformResult:
        url = self.url_for(username)
        t0  = time.monotonic()
        try:
            api_url = f"https://www.reddit.com/user/{username}/about.json"
            code, body, _ = _http_get(
                api_url, timeout=timeout, retries=retries,
                headers={"Accept": "application/json"},
            )
            ms = int((time.monotonic() - t0) * 1000)
            if code == 200:
                data = json.loads(body).get("data", {})
                profile = ProfileData(
                    display_name = data.get("name"),
                    avatar_url   = data.get("icon_img") or None,
                    created_at   = str(
                        datetime.fromtimestamp(data.get("created_utc", 0), tz=timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ")
                    ) if data.get("created_utc") else None,
                    extra = {
                        "karma_post":    str(data.get("link_karma",    0)),
                        "karma_comment": str(data.get("comment_karma", 0)),
                        "is_gold":       str(data.get("is_gold", False)),
                    },
                )
                return PlatformResult(self.name, url, Status.FOUND, profile, response_ms=ms)
            elif code == 404:
                return PlatformResult(self.name, url, Status.NOT_FOUND, response_ms=ms)
            elif code == 429:
                return PlatformResult(self.name, url, Status.RATE_LIMITED, response_ms=ms)
            else:
                return PlatformResult(self.name, url, Status.ERROR,
                                      error_msg=f"HTTP {code}", response_ms=ms)
        except Exception as exc:
            ms = int((time.monotonic() - t0) * 1000)
            return PlatformResult(self.name, url, Status.ERROR,
                                  error_msg=str(exc), response_ms=ms)


# ─────────────────────────── Generic HTML checker ─────────────────────────

class _HtmlChecker(PlatformChecker):
    """
    Generic checker that makes a HEAD/GET request and decides found/not-found
    purely from the HTTP status code.  Subclasses may override `_extract` to
    scrape additional profile data from the response body.
    """
    _profile_url_template: str = ""   # e.g. "https://example.com/{username}"
    _not_found_codes: Tuple[int, ...] = (404,)
    _rate_limit_codes: Tuple[int, ...] = (429,)
    _not_found_strings: Tuple[str, ...] = ()  # body substrings → NOT_FOUND

    def url_for(self, username: str) -> str:
        return self._profile_url_template.format(username=username)

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:  # noqa: ARG002
        """Override in subclasses to pull profile data from HTML."""
        return None

    def check(self, username: str, timeout: int, retries: int) -> PlatformResult:
        url = self.url_for(username)
        t0  = time.monotonic()
        try:
            code, raw, _ = _http_get(url, timeout=timeout, retries=retries)
            ms   = int((time.monotonic() - t0) * 1000)
            body = raw.decode("utf-8", errors="replace")

            if code in self._not_found_codes:
                return PlatformResult(self.name, url, Status.NOT_FOUND, response_ms=ms)
            if code in self._rate_limit_codes:
                return PlatformResult(self.name, url, Status.RATE_LIMITED, response_ms=ms)
            if code >= 400:
                return PlatformResult(self.name, url, Status.ERROR,
                                      error_msg=f"HTTP {code}", response_ms=ms)

            # Body-level not-found clues
            for phrase in self._not_found_strings:
                if phrase.lower() in body.lower():
                    return PlatformResult(self.name, url, Status.NOT_FOUND, response_ms=ms)

            profile = self._extract(username, body)
            return PlatformResult(self.name, url, Status.FOUND, profile, response_ms=ms)

        except Exception as exc:
            ms = int((time.monotonic() - t0) * 1000)
            return PlatformResult(self.name, url, Status.ERROR,
                                  error_msg=str(exc), response_ms=ms)


# ─────────────────────────────── X / Twitter ─────────────────────────────

class TwitterChecker(_HtmlChecker):
    name = "X (Twitter)"
    _profile_url_template = "https://x.com/{username}"
    _not_found_strings    = ("this account doesn't exist", "user not found",
                              "account suspended")

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name  = self._grep(r'<title>([^(]+)\(', body)
        return ProfileData(display_name=name) if name else None


# ─────────────────────────────── Instagram ────────────────────────────────

class InstagramChecker(_HtmlChecker):
    name = "Instagram"
    _profile_url_template = "https://www.instagram.com/{username}/"
    _not_found_strings    = ('"pageType":"errorPage"', "Sorry, this page",
                              "Page Not Found")

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        bio   = self._grep(r'"biography":"([^"]*)"', body)
        name  = self._grep(r'"full_name":"([^"]*)"', body)
        av    = self._grep(r'"profile_pic_url":"([^"]*)"', body)
        fl    = self._grep(r'"edge_followed_by":\{"count":(\d+)', body)
        flg   = self._grep(r'"edge_follow":\{"count":(\d+)', body)
        return ProfileData(
            display_name = name,
            bio          = bio,
            avatar_url   = av,
            followers    = int(fl)  if fl  else None,
            following    = int(flg) if flg else None,
        )


# ──────────────────────────────── TikTok ─────────────────────────────────

class TikTokChecker(_HtmlChecker):
    name = "TikTok"
    _profile_url_template = "https://www.tiktok.com/@{username}"
    _not_found_strings    = ('"statusCode":10202', "Couldn't find this account",
                              '"statusCode":404')

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        bio  = self._grep(r'"signature":"([^"]*)"', body)
        name = self._grep(r'"nickname":"([^"]*)"', body)
        av   = self._grep(r'"avatarLarger":"([^"]*)"', body)
        fl   = self._grep(r'"followerCount":(\d+)', body)
        flg  = self._grep(r'"followingCount":(\d+)', body)
        return ProfileData(
            display_name = name,
            bio          = bio,
            avatar_url   = av,
            followers    = int(fl)  if fl  else None,
            following    = int(flg) if flg else None,
        )


# ─────────────────────────────── Pinterest ───────────────────────────────

class PinterestChecker(_HtmlChecker):
    name = "Pinterest"
    _profile_url_template = "https://www.pinterest.com/{username}/"
    _not_found_strings    = ('"error": "User not found"',
                              "Sorry! We couldn't find that page")

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name  = self._grep(r'"full_name":\s*"([^"]+)"', body)
        bio   = self._grep(r'"about":\s*"([^"]+)"', body)
        av    = self._grep(r'"image_medium_url":\s*"([^"]+)"', body)
        pins  = self._grep(r'"pin_count":\s*(\d+)', body)
        fl    = self._grep(r'"follower_count":\s*(\d+)', body)
        return ProfileData(
            display_name = name,
            bio          = bio,
            avatar_url   = av,
            followers    = int(fl)   if fl   else None,
            public_posts = int(pins) if pins else None,
        )


# ──────────────────────────────── Medium ─────────────────────────────────

class MediumChecker(_HtmlChecker):
    name = "Medium"
    _profile_url_template = "https://medium.com/@{username}"
    _not_found_strings    = ("404", "Page not found", "profile you're looking for")

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name = self._grep(r'<title>([^<|]+)', body)
        bio  = self._grep(r'"bio":"([^"]+)"', body)
        av   = self._grep(r'"imageUrl":"([^"]+)"', body)
        fl   = self._grep(r'"socialStats":\{"usersFollowedByCount":(\d+)', body)
        return ProfileData(
            display_name = name,
            bio          = bio,
            avatar_url   = av,
            followers    = int(fl) if fl else None,
        )


# ──────────────────────────────── Twitch ─────────────────────────────────

class TwitchChecker(_HtmlChecker):
    name = "Twitch"
    _profile_url_template = "https://www.twitch.tv/{username}"
    _not_found_strings    = ('"statusCode":404',)

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name = self._grep(r'"displayName":"([^"]+)"', body)
        bio  = self._grep(r'"description":"([^"]+)"', body)
        av   = self._grep(r'"profileImageURL":"([^"]+)"', body)
        return ProfileData(display_name=name, bio=bio, avatar_url=av)


# ───────────────────────────────── Steam ─────────────────────────────────

class SteamChecker(_HtmlChecker):
    name = "Steam"
    _profile_url_template = "https://steamcommunity.com/id/{username}"
    _not_found_strings    = ("The specified profile could not be found",
                              "error_ctn")

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name = self._grep(r'<span class="actual_persona_name">([^<]+)', body)
        av   = self._grep(r'<div class="playerAvatarAutoSizeInner">\s*<img src="([^"]+)"', body)
        loc  = self._grep(r'class="profile_flag"[^>]*>[^<]*</img>\s*([^<]+)<', body)
        return ProfileData(display_name=name, avatar_url=av, location=loc)


# ─────────────────────────────── HackerOne ───────────────────────────────

class HackerOneChecker(_HtmlChecker):
    name = "HackerOne"
    _profile_url_template = "https://hackerone.com/{username}"
    _not_found_codes      = (404,)

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name = self._grep(r'"name":"([^"]+)"', body)
        bio  = self._grep(r'"bio":"([^"]*)"', body)
        av   = self._grep(r'"profile_picture":\{".*?"medium":"([^"]+)"', body)
        return ProfileData(display_name=name, bio=bio, avatar_url=av)


# ─────────────────────────────── TryHackMe ───────────────────────────────

class TryHackMeChecker(_HtmlChecker):
    name = "TryHackMe"
    _profile_url_template = "https://tryhackme.com/p/{username}"
    _not_found_strings    = ("There is no user with that username", "404")

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name  = self._grep(r'<title>TryHackMe \| ([^<]+)', body)
        av    = self._grep(r'<img[^>]+class="[^"]*profile-image[^"]*"[^>]+src="([^"]+)"', body)
        return ProfileData(display_name=name, avatar_url=av)


# ─────────────────────────────── HackTheBox ──────────────────────────────

class HackTheBoxChecker(_HtmlChecker):
    name = "Hack The Box"
    _profile_url_template = "https://app.hackthebox.com/users/{username}"
    _not_found_strings    = ("The page you are looking for", "404")


# ──────────────────────────────── Keybase ────────────────────────────────

class KeybaseChecker(_HtmlChecker):
    name = "Keybase"
    _profile_url_template = "https://keybase.io/{username}"
    _not_found_codes      = (404,)

    def _extract(self, username: str, body: str) -> Optional[ProfileData]:
        name  = self._grep(r'"full_name":"([^"]+)"', body)
        bio   = self._grep(r'"bio":"([^"]*)"', body)
        av    = self._grep(r'"pic_url":"([^"]+)"', body)
        loc   = self._grep(r'"location":"([^"]+)"', body)
        site  = self._grep(r'"website":"([^"]+)"', body)
        twitter = self._grep(r'"twitter":.*?"username":"([^"]+)"', body)
        return ProfileData(
            display_name = name,
            bio          = bio,
            avatar_url   = av,
            location     = loc,
            website      = site,
            extra        = {"twitter": twitter or ""},
        )


# ─────────────────────────────── Docker Hub ──────────────────────────────

class DockerHubChecker(PlatformChecker):
    name = "Docker Hub"

    def url_for(self, username: str) -> str:
        return f"https://hub.docker.com/u/{username}"

    def check(self, username: str, timeout: int, retries: int) -> PlatformResult:
        url = self.url_for(username)
        t0  = time.monotonic()
        try:
            api_url = f"https://hub.docker.com/v2/users/{username}/"
            code, body, _ = _http_get(api_url, timeout=timeout, retries=retries)
            ms = int((time.monotonic() - t0) * 1000)
            if code == 200:
                data = json.loads(body)
                profile = ProfileData(
                    display_name = data.get("full_name") or data.get("username"),
                    bio          = data.get("company"),
                    location     = data.get("location"),
                    created_at   = data.get("date_joined"),
                )
                return PlatformResult(self.name, url, Status.FOUND, profile, response_ms=ms)
            elif code == 404:
                return PlatformResult(self.name, url, Status.NOT_FOUND, response_ms=ms)
            elif code == 429:
                return PlatformResult(self.name, url, Status.RATE_LIMITED, response_ms=ms)
            else:
                return PlatformResult(self.name, url, Status.ERROR,
                                      error_msg=f"HTTP {code}", response_ms=ms)
        except Exception as exc:
            ms = int((time.monotonic() - t0) * 1000)
            return PlatformResult(self.name, url, Status.ERROR,
                                  error_msg=str(exc), response_ms=ms)


# ──────────────────────────────── Dev.to ─────────────────────────────────

class DevToChecker(PlatformChecker):
    name = "Dev.to"

    def url_for(self, username: str) -> str:
        return f"https://dev.to/{username}"

    def check(self, username: str, timeout: int, retries: int) -> PlatformResult:
        url = self.url_for(username)
        t0  = time.monotonic()
        try:
            api_url = f"https://dev.to/api/users/by_username?url={username}"
            code, body, _ = _http_get(api_url, timeout=timeout, retries=retries)
            ms = int((time.monotonic() - t0) * 1000)
            if code == 200:
                data = json.loads(body)
                profile = ProfileData(
                    display_name = data.get("name"),
                    bio          = data.get("summary"),
                    avatar_url   = data.get("profile_image"),
                    location     = data.get("location"),
                    website      = data.get("website_url") or None,
                    created_at   = data.get("joined_at"),
                    extra        = {"twitter": data.get("twitter_username") or ""},
                )
                return PlatformResult(self.name, url, Status.FOUND, profile, response_ms=ms)
            elif code == 404:
                return PlatformResult(self.name, url, Status.NOT_FOUND, response_ms=ms)
            elif code == 429:
                return PlatformResult(self.name, url, Status.RATE_LIMITED, response_ms=ms)
            else:
                return PlatformResult(self.name, url, Status.ERROR,
                                      error_msg=f"HTTP {code}", response_ms=ms)
        except Exception as exc:
            ms = int((time.monotonic() - t0) * 1000)
            return PlatformResult(self.name, url, Status.ERROR,
                                  error_msg=str(exc), response_ms=ms)


# ═══════════════════════════════════════════════════════════════════════════
# §5  PLATFORM REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

ALL_CHECKERS: List[PlatformChecker] = [
    GitHubChecker(),
    GitLabChecker(),
    RedditChecker(),
    TwitterChecker(),
    InstagramChecker(),
    TikTokChecker(),
    PinterestChecker(),
    MediumChecker(),
    TwitchChecker(),
    SteamChecker(),
    HackerOneChecker(),
    TryHackMeChecker(),
    HackTheBoxChecker(),
    KeybaseChecker(),
    DockerHubChecker(),
    DevToChecker(),
]


# ═══════════════════════════════════════════════════════════════════════════
# §6  ASYNC SCANNER
# ═══════════════════════════════════════════════════════════════════════════

class Scanner:
    """
    Runs platform checks concurrently using asyncio + executor threads.
    Each checker's synchronous `check()` runs in a ThreadPoolExecutor,
    giving true I/O concurrency without requiring any third-party async
    HTTP library.
    """

    def __init__(
        self,
        checkers: List[PlatformChecker],
        timeout:  int  = 10,
        retries:  int  = 2,
        concurrency: int = 16,
    ) -> None:
        self.checkers    = checkers
        self.timeout     = timeout
        self.retries     = retries
        self.concurrency = concurrency

    # ------------------------------------------------------------------ #
    async def _run_one(
        self,
        loop:     asyncio.AbstractEventLoop,
        sem:      asyncio.Semaphore,
        checker:  PlatformChecker,
        username: str,
        progress: "ProgressBar",
    ) -> PlatformResult:
        async with sem:
            result = await loop.run_in_executor(
                None,
                checker.check,
                username,
                self.timeout,
                self.retries,
            )
            progress.tick(checker.name, result.status)
            return result

    # ------------------------------------------------------------------ #
    async def _scan_async(self, username: str, progress: "ProgressBar") -> List[PlatformResult]:
        loop = asyncio.get_event_loop()
        sem  = asyncio.Semaphore(self.concurrency)
        tasks = [
            self._run_one(loop, sem, ch, username, progress)
            for ch in self.checkers
        ]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------ #
    def scan(self, username: str) -> ScanReport:
        """Run a full scan and return a populated `ScanReport`."""
        progress = ProgressBar(total=len(self.checkers))
        started  = datetime.now(tz=timezone.utc)
        t0       = time.monotonic()

        results: List[PlatformResult] = asyncio.run(
            self._scan_async(username, progress)
        )

        duration = time.monotonic() - t0
        ended    = datetime.now(tz=timezone.utc)
        progress.done()

        return ScanReport(
            username   = username,
            started_at = started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ended_at   = ended.strftime("%Y-%m-%dT%H:%M:%SZ"),
            duration_s = duration,
            results    = sorted(results, key=lambda r: r.platform),
        )


# ═══════════════════════════════════════════════════════════════════════════
# §7  PROGRESS BAR
# ═══════════════════════════════════════════════════════════════════════════

class ProgressBar:
    """
    Thread-safe progress bar that prints status updates to stderr.
    Uses a lock so concurrent threads don't interleave output.
    """

    def __init__(self, total: int) -> None:
        self.total    = total
        self.done_ct  = 0
        self._lock    = asyncio.Lock()
        self._width   = 30

    async def tick(self, platform_name: str, status: Status) -> None:
        async with self._lock:
            self.done_ct += 1
            pct  = self.done_ct / self.total
            fill = int(self._width * pct)
            bar  = (
                colour("█" * fill,            C.CYAN)
                + colour("░" * (self._width - fill), C.GRAY)
            )
            status_chr = {
                Status.FOUND:        colour("✔", C.GREEN),
                Status.NOT_FOUND:    colour("✘", C.GRAY),
                Status.RATE_LIMITED: colour("!", C.YELLOW),
                Status.ERROR:        colour("?", C.RED),
            }[status]
            line = (
                f"\r  [{bar}] "
                f"{colour(str(self.done_ct).rjust(2), C.BOLD)}"
                f"{colour('/', C.DIM)}"
                f"{colour(str(self.total), C.BOLD)} "
                f"{status_chr} {colour(platform_name, C.CYAN):<22}   "
            )
            sys.stderr.write(line)
            sys.stderr.flush()

    def done(self) -> None:
        sys.stderr.write("\n")
        sys.stderr.flush()


# ═══════════════════════════════════════════════════════════════════════════
# §8  REPORT GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

class ReportGenerator:
    """Collection of static factory methods for different report formats."""

    # ------------------------------------------------------------------ #
    # 8-A  Terminal
    # ------------------------------------------------------------------ #
    @staticmethod
    def terminal(report: ScanReport) -> None:
        """Print a rich terminal report."""
        sep  = colour("─" * 68, C.DIM)
        sep2 = colour("═" * 68, C.CYAN)
        print()
        print(sep2)
        print(
            colour("  USERNAME OSINT REPORT", C.BOLD, C.CYAN)
            + colour(f"  ·  @{report.username}", C.BOLD, C.WHITE)
        )
        print(
            colour(f"  Scanned {len(report.results)} platforms in "
                   f"{report.duration_s:.1f}s", C.DIM)
        )
        print(sep2)
        print()

        # Results list
        for r in report.results:
            label = r.status_label()
            url_s = colour(r.url, C.BLUE, C.DIM) if r.status == Status.NOT_FOUND \
                    else colour(r.url, C.BLUE)
            print(f"  {label}  {colour(r.platform, C.BOLD):<22} {url_s}")

            if r.status == Status.FOUND and r.profile:
                p = r.profile
                indent = "              "
                if p.display_name:
                    print(f"{indent}{colour('Name:', C.DIM)} {p.display_name}")
                if p.bio:
                    bio_wrapped = textwrap.fill(
                        p.bio, width=50,
                        initial_indent    = f"{indent}{colour('Bio: ', C.DIM)} ",
                        subsequent_indent = f"{indent}      ",
                    )
                    print(bio_wrapped)
                if p.location:
                    print(f"{indent}{colour('Loc: ', C.DIM)} {p.location}")
                if p.website:
                    print(f"{indent}{colour('Web: ', C.DIM)} {p.website}")
                if p.followers is not None:
                    fl_line = f"{p.followers:,} followers"
                    if p.following is not None:
                        fl_line += f"  ·  {p.following:,} following"
                    if p.repos is not None:
                        fl_line += f"  ·  {p.repos} repos"
                    print(f"{indent}{colour('     ', C.DIM)} {colour(fl_line, C.DIM)}")
                if p.extra:
                    for k, v in p.extra.items():
                        if v:
                            print(f"{indent}{colour(f'{k}:', C.DIM):>10} {v}")

            if r.status == Status.ERROR and r.error_msg:
                print(f"               {colour('↳ ' + r.error_msg, C.RED, C.DIM)}")
            if r.status == Status.RATE_LIMITED:
                print(f"               {colour('↳ Rate limit hit — try again later', C.YELLOW, C.DIM)}")

        # Summary
        print()
        print(sep)
        found_s = colour(f"{len(report.found)} found",        C.GREEN,  C.BOLD)
        nf_s    = colour(f"{len(report.not_found)} not found",C.GRAY,   C.DIM)
        rl_s    = colour(f"{len(report.rate_limited)} limited",C.YELLOW, C.BOLD)
        er_s    = colour(f"{len(report.errors)} errors",      C.RED,    C.BOLD)
        print(f"  Summary:  {found_s}  ·  {nf_s}  ·  {rl_s}  ·  {er_s}")
        print(f"  Duration: {colour(f'{report.duration_s:.2f}s', C.CYAN)}")
        print(sep)
        print()

    # ------------------------------------------------------------------ #
    # 8-B  JSON
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_json(report: ScanReport, path: str) -> None:
        """Write a JSON report."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)
        print(colour(f"  [JSON] Report saved → {path}", C.GREEN))

    # ------------------------------------------------------------------ #
    # 8-C  CSV
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_csv(report: ScanReport, path: str) -> None:
        """Write a flat CSV report."""
        fieldnames = [
            "platform", "status", "url",
            "display_name", "bio", "location", "website",
            "followers", "following", "repos",
            "avatar_url", "created_at", "response_ms",
        ]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in report.results:
                row: dict = {
                    "platform":    r.platform,
                    "status":      r.status.value,
                    "url":         r.url,
                    "response_ms": r.response_ms,
                }
                if r.profile:
                    p = r.profile
                    row.update({
                        "display_name": p.display_name or "",
                        "bio":          p.bio          or "",
                        "location":     p.location     or "",
                        "website":      p.website      or "",
                        "followers":    p.followers    if p.followers is not None else "",
                        "following":    p.following    if p.following is not None else "",
                        "repos":        p.repos        if p.repos     is not None else "",
                        "avatar_url":   p.avatar_url   or "",
                        "created_at":   p.created_at   or "",
                    })
                writer.writerow(row)
        print(colour(f"  [CSV] Report saved → {path}", C.GREEN))

    # ------------------------------------------------------------------ #
    # 8-D  HTML
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_html(report: ScanReport, path: str) -> None:
        """Write a self-contained HTML report."""

        def e(text: Optional[str]) -> str:
            return html_module.escape(str(text or ""))

        status_badge: Dict[Status, str] = {
            Status.FOUND:        '<span class="badge found">FOUND</span>',
            Status.NOT_FOUND:    '<span class="badge notfound">NOT FOUND</span>',
            Status.RATE_LIMITED: '<span class="badge ratelimited">RATE LIMITED</span>',
            Status.ERROR:        '<span class="badge error">ERROR</span>',
        }

        rows_html = ""
        for r in report.results:
            detail = ""
            if r.status == Status.FOUND and r.profile:
                p = r.profile
                parts = []
                if p.display_name:
                    parts.append(f"<b>{e(p.display_name)}</b>")
                if p.bio:
                    parts.append(f"<em>{e(p.bio[:120])}{'…' if len(p.bio or '') > 120 else ''}</em>")
                if p.location:
                    parts.append(f"📍 {e(p.location)}")
                if p.followers is not None:
                    parts.append(f"👥 {p.followers:,} followers")
                if p.website:
                    parts.append(f'🔗 <a href="{e(p.website)}" target="_blank">{e(p.website)}</a>')
                detail = "<br>".join(parts)
            elif r.error_msg:
                detail = f'<span class="errmsg">{e(r.error_msg)}</span>'

            rows_html += f"""
        <tr>
          <td>{e(r.platform)}</td>
          <td>{status_badge[r.status]}</td>
          <td><a href="{e(r.url)}" target="_blank" class="profile-link">{e(r.url)}</a></td>
          <td class="detail">{detail}</td>
          <td class="ms">{r.response_ms}ms</td>
        </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSINT Report — @{e(report.username)}</title>
<style>
  :root {{
    --bg: #0d1117; --bg2: #161b22; --border: #30363d;
    --text: #c9d1d9; --dim: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922; --gray: #484f58;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif;
          font-size: 14px; line-height: 1.5; padding: 2rem; }}
  h1   {{ font-size: 1.6rem; color: var(--accent); margin-bottom: .25rem; }}
  .meta {{ color: var(--dim); font-size: .85rem; margin-bottom: 1.5rem; }}
  .stats {{ display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; }}
  .stat  {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 8px;
             padding: .75rem 1.25rem; min-width: 120px; text-align: center; }}
  .stat .n {{ font-size: 1.8rem; font-weight: 700; }}
  .stat .l {{ font-size: .75rem; color: var(--dim); text-transform: uppercase; letter-spacing: .06em; }}
  .found-n {{ color: var(--green); }}
  .err-n   {{ color: var(--red); }}
  .rl-n    {{ color: var(--yellow); }}
  table {{ width: 100%; border-collapse: collapse; background: var(--bg2);
            border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: .6rem .9rem; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #0d1117; color: var(--dim); font-weight: 600; font-size: .75rem;
        text-transform: uppercase; letter-spacing: .07em; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover {{ background: rgba(255,255,255,.03); }}
  .badge {{ display: inline-block; padding: .2em .6em; border-radius: 4px;
             font-size: .72rem; font-weight: 700; letter-spacing: .05em; }}
  .found       {{ background: rgba(63,185,80,.15); color: var(--green); border: 1px solid rgba(63,185,80,.35); }}
  .notfound    {{ background: rgba(72,79,88,.15);  color: var(--gray);  border: 1px solid rgba(72,79,88,.35); }}
  .ratelimited {{ background: rgba(210,153,34,.15);color: var(--yellow);border: 1px solid rgba(210,153,34,.35); }}
  .error       {{ background: rgba(248,81,73,.15); color: var(--red);   border: 1px solid rgba(248,81,73,.35); }}
  .profile-link {{ color: var(--accent); text-decoration: none; font-size: .82rem; word-break: break-all; }}
  .profile-link:hover {{ text-decoration: underline; }}
  .detail  {{ color: var(--dim); font-size: .82rem; max-width: 320px; }}
  .detail a {{ color: var(--accent); }}
  .errmsg  {{ color: var(--red); }}
  .ms      {{ color: var(--dim); font-size: .78rem; white-space: nowrap; }}
  footer   {{ margin-top: 2rem; color: var(--dim); font-size: .78rem; text-align: center; }}
</style>
</head>
<body>
<h1>🔍 OSINT Report — <code>@{e(report.username)}</code></h1>
<p class="meta">
  Scanned {len(report.results)} platforms &nbsp;·&nbsp;
  Started {e(report.started_at)} &nbsp;·&nbsp;
  Duration {report.duration_s:.2f}s
</p>

<div class="stats">
  <div class="stat"><div class="n found-n">{len(report.found)}</div><div class="l">Found</div></div>
  <div class="stat"><div class="n">{len(report.not_found)}</div><div class="l">Not Found</div></div>
  <div class="stat"><div class="n rl-n">{len(report.rate_limited)}</div><div class="l">Rate Limited</div></div>
  <div class="stat"><div class="n err-n">{len(report.errors)}</div><div class="l">Errors</div></div>
</div>

<table>
  <thead>
    <tr>
      <th>Platform</th>
      <th>Status</th>
      <th>Profile URL</th>
      <th>Details</th>
      <th>Time</th>
    </tr>
  </thead>
  <tbody>{rows_html}
  </tbody>
</table>

<footer>
  Generated by osint.py &nbsp;·&nbsp; {e(report.ended_at)}<br>
  For lawful OSINT &amp; defensive research only.
</footer>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(colour(f"  [HTML] Report saved → {path}", C.GREEN))


# ═══════════════════════════════════════════════════════════════════════════
# §9  BANNER  &  CLI
# ═══════════════════════════════════════════════════════════════════════════

_BANNER = r"""
   ___  ___  _ __  _  _____
  / _ \/ __/| '  \| ||_   _|
 | (_) \__ \|_|_|_|_|  |_|
  \___/|___/  OSINT Tool
"""


def print_banner() -> None:
    print(colour(_BANNER, C.CYAN, C.BOLD))
    print(colour(
        "  ⚠  For lawful OSINT & defensive research only. "
        "By proceeding you accept these terms.\n",
        C.YELLOW,
    ))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osint.py",
        description="Username OSINT — check a username across multiple platforms.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python osint.py johndoe
          python osint.py johndoe --json results.json
          python osint.py johndoe --html report.html
          python osint.py johndoe --csv  report.csv
          python osint.py johndoe --timeout 15 --retries 3 --json out.json --html out.html
        """),
    )
    parser.add_argument("username", help="Target username to investigate")
    parser.add_argument("--json",    metavar="FILE", help="Save JSON report to FILE")
    parser.add_argument("--csv",     metavar="FILE", help="Save CSV  report to FILE")
    parser.add_argument("--html",    metavar="FILE", help="Save HTML report to FILE")
    parser.add_argument("--timeout", metavar="SEC",  type=int, default=10,
                        help="HTTP timeout per request in seconds (default: 10)")
    parser.add_argument("--retries", metavar="N",    type=int, default=2,
                        help="Retry count on network errors (default: 2)")
    parser.add_argument("--concurrency", metavar="N", type=int, default=16,
                        help="Max simultaneous requests (default: 16)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable coloured output")
    return parser


# ═══════════════════════════════════════════════════════════════════════════
# §10  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # Honour --no-color globally
    if args.no_color:
        global _COLOUR_ENABLED
        _COLOUR_ENABLED = False
        for attr in vars(C):
            if not attr.startswith("_"):
                setattr(C, attr, "")

    print_banner()

    # Validate username (basic sanity check — not authentication bypass)
    username = args.username.strip().lstrip("@")
    if not re.match(r"^[A-Za-z0-9_.\-]{1,64}$", username):
        print(colour(f"  [!] Username '{username}' contains unusual characters. "
                     "Proceeding anyway…\n", C.YELLOW))

    print(
        colour("  Target:", C.BOLD)
        + colour(f" @{username}", C.CYAN, C.BOLD)
        + colour(f"  ·  {len(ALL_CHECKERS)} platforms", C.DIM)
    )
    print(
        colour("  Config:", C.BOLD)
        + colour(f" timeout={args.timeout}s  retries={args.retries}"
                 f"  concurrency={args.concurrency}", C.DIM)
    )
    print()

    scanner = Scanner(
        checkers     = ALL_CHECKERS,
        timeout      = args.timeout,
        retries      = args.retries,
        concurrency  = args.concurrency,
    )

    report = scanner.scan(username)

    # Always show terminal report
    ReportGenerator.terminal(report)

    # Optional exports
    if args.json:
        ReportGenerator.to_json(report, args.json)
    if args.csv:
        ReportGenerator.to_csv(report, args.csv)
    if args.html:
        ReportGenerator.to_html(report, args.html)

    if any([args.json, args.csv, args.html]):
        print()

    sys.exit(0)


if __name__ == "__main__":
    main()
