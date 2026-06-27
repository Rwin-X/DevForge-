#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║           TechPulse News Bot — @Rwin-x              ║
║      Automated Tech News Collector + FA Translator       ║
╚══════════════════════════════════════════════════════════╝
"""

import feedparser
import requests
import json
import time
import re
import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.live import Live
from rich.columns import Columns

# ──────────────────────────────────────────────
# GLOBALS
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

console = Console()

logging.basicConfig(
    filename=LOG_DIR / "bot.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("TechPulseBot")


# ──────────────────────────────────────────────
# DATA MODEL
# ──────────────────────────────────────────────
@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    published: str
    summary: str
    category: str = "Tech"
    title_fa: Optional[str] = None
    summary_fa: Optional[str] = None
    translated: bool = False
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ──────────────────────────────────────────────
# RSS FEED SOURCES  (major tech news outlets)
# ──────────────────────────────────────────────
SOURCES = {
    "The Verge":        "https://www.theverge.com/rss/index.xml",
    "TechCrunch":       "https://techcrunch.com/feed/",
    "Ars Technica":     "https://feeds.arstechnica.com/arstechnica/index",
    "Wired":            "https://www.wired.com/feed/rss",
    "Hacker News":      "https://news.ycombinator.com/rss",
    "MIT Tech Review":  "https://www.technologyreview.com/feed/",
    "ZDNet":            "https://www.zdnet.com/news/rss.xml",
    "VentureBeat":      "https://venturebeat.com/feed/",
    "9to5Google":       "https://9to5google.com/feed/",
    "9to5Mac":          "https://9to5mac.com/feed/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def clean_html(raw: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "lxml")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:800]  # cap summary at 800 chars


def parse_date(entry) -> str:
    """Try to extract a readable publication date from RSS entry."""
    for attr in ("published", "updated", "created"):
        val = getattr(entry, attr, None)
        if val:
            return val
    return datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")


def translate_text(text: str, retries: int = 3) -> Optional[str]:
    """Translate English → Persian via Google Translate. Returns None on failure."""
    if not text or len(text.strip()) < 5:
        return None
    for attempt in range(retries):
        try:
            translated = GoogleTranslator(source="en", target="fa").translate(text[:4500])
            return translated
        except Exception as exc:
            log.warning(f"Translation attempt {attempt+1} failed: {exc}")
            time.sleep(1.5)
    return None


# ──────────────────────────────────────────────
# FETCHER
# ──────────────────────────────────────────────
def fetch_source(name: str, url: str, max_articles: int = 10) -> list[NewsArticle]:
    """Fetch and parse a single RSS feed. Returns list of NewsArticle."""
    articles: list[NewsArticle] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        entries = feed.entries[:max_articles]
        for entry in entries:
            title = clean_html(getattr(entry, "title", "")) or "Untitled"
            link  = getattr(entry, "link", "")
            # grab summary from several possible fields
            raw_summary = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or getattr(entry, "content", [{}])[0].get("value", "")
            )
            summary = clean_html(raw_summary)
            pub_date = parse_date(entry)

            if not link:
                continue

            articles.append(NewsArticle(
                title=title,
                url=link,
                source=name,
                published=pub_date,
                summary=summary,
            ))

        log.info(f"[{name}] fetched {len(articles)} articles")
    except requests.RequestException as exc:
        log.error(f"[{name}] HTTP error: {exc}")
    except Exception as exc:
        log.error(f"[{name}] unexpected error: {exc}")
    return articles


# ──────────────────────────────────────────────
# TRANSLATOR PASS
# ──────────────────────────────────────────────
def translate_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    """Add Persian translations to every article in-place."""
    total = len(articles)
    console.print()
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40, style="cyan", complete_style="bright_cyan"),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]ترجمه به فارسی...", total=total)
        for art in articles:
            art.title_fa   = translate_text(art.title)
            art.summary_fa = translate_text(art.summary) if art.summary else None
            art.translated = bool(art.title_fa)
            progress.advance(task)
            time.sleep(0.3)   # gentle rate limiting
    return articles


# ──────────────────────────────────────────────
# SAVE — JSON
# ──────────────────────────────────────────────
def save_json(articles: list[NewsArticle], language: str) -> Path:
    """Save all articles as structured JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"tech_news_{language}_{timestamp}.json"

    data = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "language": language,
            "total_articles": len(articles),
            "sources": list({a.source for a in articles}),
        },
        "articles": [asdict(a) for a in articles],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"Saved JSON → {path}")
    return path


# ──────────────────────────────────────────────
# SAVE — TXT  (human-readable)
# ──────────────────────────────────────────────
def save_txt(articles: list[NewsArticle], language: str) -> Path:
    """Save all articles as formatted plain-text report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"tech_news_{language}_{timestamp}.txt"

    is_fa = language == "fa"
    lines = []

    header = (
        "══════════════════════════════════════════════════════════\n"
        "         TechPulse News Bot — گزارش اخبار تکنولوژی\n"
        f"         تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"         زبان: {'فارسی' if is_fa else 'English'} | تعداد خبر: {len(articles)}\n"
        "══════════════════════════════════════════════════════════\n"
        if is_fa else
        "══════════════════════════════════════════════════════════\n"
        "              TechPulse News Bot — Tech Report\n"
        f"              Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"              Language: English | Articles: {len(articles)}\n"
        "══════════════════════════════════════════════════════════\n"
    )
    lines.append(header)

    for idx, art in enumerate(articles, 1):
        sep = "──────────────────────────────────────────────────────────\n"
        if is_fa:
            lines.append(f"{sep}")
            lines.append(f"[{idx}]  منبع: {art.source}\n")
            lines.append(f"📰 عنوان (FA): {art.title_fa or '—'}\n")
            lines.append(f"📰 عنوان (EN): {art.title}\n")
            lines.append(f"📅 تاریخ: {art.published}\n")
            lines.append(f"🔗 لینک: {art.url}\n")
            if art.summary_fa:
                lines.append(f"\n📝 خلاصه:\n{art.summary_fa}\n")
            elif art.summary:
                lines.append(f"\n📝 Summary:\n{art.summary}\n")
        else:
            lines.append(f"{sep}")
            lines.append(f"[{idx}]  Source: {art.source}\n")
            lines.append(f"📰 Title: {art.title}\n")
            lines.append(f"📅 Date:  {art.published}\n")
            lines.append(f"🔗 URL:   {art.url}\n")
            if art.summary:
                lines.append(f"\n📝 Summary:\n{art.summary}\n")
        lines.append("\n")

    path.write_text("".join(lines), encoding="utf-8")
    log.info(f"Saved TXT → {path}")
    return path


# ──────────────────────────────────────────────
# DISPLAY — RICH TABLE
# ──────────────────────────────────────────────
def display_results(articles: list[NewsArticle], language: str):
    """Pretty-print a summary table in terminal."""
    is_fa = language == "fa"
    table = Table(
        title="[bold cyan]TechPulse — Latest Tech News[/bold cyan]",
        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        show_lines=True,
        header_style="bold bright_cyan",
    )
    table.add_column("#",         style="dim",          width=3)
    table.add_column("Source",    style="bright_white", width=14)
    if is_fa:
        table.add_column("عنوان فارسی", style="bright_yellow", width=45, no_wrap=False)
    else:
        table.add_column("Title",  style="bright_yellow", width=55, no_wrap=False)
    table.add_column("Date",      style="dim cyan",     width=15)

    for idx, art in enumerate(articles[:50], 1):   # cap display at 50
        title_cell = (art.title_fa or art.title) if is_fa else art.title
        # trim for display
        if len(title_cell) > 65:
            title_cell = title_cell[:62] + "…"
        pub = art.published[:16] if art.published else "—"
        table.add_row(str(idx), art.source, title_cell, pub)

    console.print()
    console.print(table)


# ──────────────────────────────────────────────
# CLI / MAIN
# ──────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="TechPulse — Automated Tech News Collector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python news_bot.py                       # collect & save in English
  python news_bot.py --lang fa             # collect + translate → Persian
  python news_bot.py --lang both           # save BOTH languages
  python news_bot.py --max 5 --lang fa    # 5 articles per source, Persian
  python news_bot.py --sources "TechCrunch,Wired"
        """,
    )
    parser.add_argument(
        "--lang",
        choices=["en", "fa", "both"],
        default="en",
        help="Output language: en (English), fa (Persian/فارسی), both",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=8,
        metavar="N",
        help="Max articles per source (default: 8)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "txt", "both"],
        default="both",
        help="Output file format (default: both)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=None,
        metavar="LIST",
        help='Comma-separated source names, e.g. "TechCrunch,Wired"',
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Skip terminal table display",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Banner ────────────────────────────────
    banner = Panel(
        Text.assemble(
            ("  ████████╗███████╗ ██████╗██╗  ██╗\n", "bright_cyan"),
            ("  ╚══██╔══╝██╔════╝██╔════╝██║  ██║\n", "cyan"),
            ("     ██║   █████╗  ██║     ███████║\n", "bright_cyan"),
            ("     ██║   ██╔══╝  ██║     ██╔══██║\n", "cyan"),
            ("     ██║   ███████╗╚██████╗██║  ██║\n", "bright_cyan"),
            ("     ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝\n\n", "cyan"),
            ("  ⚡ TechPulse News Bot ", "bold white"),
            ("— @Rwin-X", "dim cyan"),
        ),
        border_style="cyan",
        subtitle="[dim]Automated Tech Intelligence Collector[/dim]",
        padding=(0, 2),
    )
    console.print(banner)

    # ── Select sources ─────────────────────────
    active_sources = dict(SOURCES)
    if args.sources:
        names = [s.strip() for s in args.sources.split(",")]
        active_sources = {k: v for k, v in SOURCES.items() if k in names}
        if not active_sources:
            console.print(f"[red]No matching sources found. Available: {', '.join(SOURCES)}[/red]")
            sys.exit(1)

    need_translate = args.lang in ("fa", "both")

    # ── Fetch phase ────────────────────────────
    console.print(
        f"\n[bold cyan]▶[/bold cyan] Fetching from [bold]{len(active_sources)}[/bold] sources "
        f"([cyan]{args.max}[/cyan] articles each) …\n"
    )

    all_articles: list[NewsArticle] = []
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40, style="cyan", complete_style="bright_cyan"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching feeds…", total=len(active_sources))
        for name, url in active_sources.items():
            progress.update(task, description=f"[cyan]{name}[/cyan]")
            arts = fetch_source(name, url, max_articles=args.max)
            all_articles.extend(arts)
            progress.advance(task)
            time.sleep(0.5)

    console.print(
        f"\n[green]✔[/green] Collected [bold bright_yellow]{len(all_articles)}[/bold bright_yellow] articles total\n"
    )

    if not all_articles:
        console.print("[red]No articles collected. Check your internet connection.[/red]")
        sys.exit(1)

    # ── Translate phase (if needed) ─────────────
    if need_translate:
        console.print("[bold cyan]▶[/bold cyan] Translating to Persian (فارسی)…")
        all_articles = translate_articles(all_articles)
        translated_count = sum(1 for a in all_articles if a.translated)
        console.print(
            f"[green]✔[/green] Translated [bold bright_yellow]{translated_count}[/bold bright_yellow] / "
            f"{len(all_articles)} articles\n"
        )

    # ── Save files ─────────────────────────────
    saved_files: list[Path] = []
    langs_to_save = ["en", "fa"] if args.lang == "both" else [args.lang]

    for lang in langs_to_save:
        if args.format in ("json", "both"):
            p = save_json(all_articles, lang)
            saved_files.append(p)
        if args.format in ("txt", "both"):
            p = save_txt(all_articles, lang)
            saved_files.append(p)

    # ── Display table ──────────────────────────
    if not args.no_display:
        display_lang = "fa" if args.lang in ("fa", "both") else "en"
        display_results(all_articles, display_lang)

    # ── Summary panel ─────────────────────────
    file_list = "\n".join(f"  [cyan]→[/cyan] [white]{p.name}[/white]" for p in saved_files)
    console.print(Panel(
        f"[bold green]✔ Done![/bold green]\n\n"
        f"[white]Articles collected:[/white] [bold bright_yellow]{len(all_articles)}[/bold bright_yellow]\n"
        f"[white]Sources:[/white] [cyan]{len(active_sources)}[/cyan]\n"
        f"[white]Language:[/white] [cyan]{args.lang.upper()}[/cyan]\n\n"
        f"[bold white]Output files:[/bold white]\n{file_list}\n\n"
        f"[dim]Logs → {LOG_DIR / 'bot.log'}[/dim]",
        title="[bold cyan]TechPulse — Summary[/bold cyan]",
        border_style="green",
        padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
