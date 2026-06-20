#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  CYBER_NEWS // Real-time Security Intelligence Aggregator
═══════════════════════════════════════════════════════════════════


Usage:
    python3 cyber_news.py                  # 
    python3 cyber_news.py --limit 5        # 
    python3 cyber_news.py --output report.md
    python3 cyber_news.py --sources krebs,thehackernews
"""

import sys
import subprocess
import argparse
import re
import html
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ─────────────────────────────────────────────────────────────────
# Dependency bootstrap — auto-install rich if missing, no failure
# if network is unavailable (falls back to plain text rendering).
# ─────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "rich", "--break-system-packages", "-q"],
            check=True, capture_output=True, timeout=30
        )
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.live import Live
        from rich.text import Text
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        from rich import box
        RICH_AVAILABLE = True
    except Exception:
        RICH_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────
# Source registry — well-known, reputable infosec RSS feeds
# ─────────────────────────────────────────────────────────────────
SOURCES = {
    "krebs":          {"name": "Krebs on Security",      "url": "https://krebsonsecurity.com/feed/"},
    "thehackernews":  {"name": "The Hacker News",          "url": "https://feeds.feedburner.com/TheHackersNews"},
    "bleepingcomputer":{"name": "BleepingComputer",        "url": "https://www.bleepingcomputer.com/feed/"},
    "darkreading":    {"name": "Dark Reading",             "url": "https://www.darkreading.com/rss.xml"},
    "threatpost":     {"name": "Threatpost",               "url": "https://threatpost.com/feed/"},
    "schneier":       {"name": "Schneier on Security",     "url": "https://www.schneier.com/feed/atom/"},
    "securityweek":   {"name": "SecurityWeek",             "url": "https://www.securityweek.com/feed/"},
    "cisa":           {"name": "CISA Advisories",          "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml"},
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 12

# Tags that hint at higher severity — purely heuristic, for visual emphasis
CRITICAL_HINTS = re.compile(
    r"\b(zero[\s-]?day|exploit(ed)?|ransomware|critical|rce|breach|"
    r"vulnerab(le|ility)|cve-\d{4}|patch (now|immediately)|active(ly)? exploit)",
    re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────────
# Feed fetching & parsing (stdlib only — no feedparser dependency)
# ─────────────────────────────────────────────────────────────────
def fetch_feed(key, source):
    """Fetch and parse a single RSS/Atom feed. Returns (key, items, error)."""
    try:
        req = Request(source["url"], headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
        items = parse_feed_xml(raw, source["name"])
        return key, items, None
    except (URLError, HTTPError) as e:
        return key, [], f"network error: {e}"
    except ET.ParseError as e:
        return key, [], f"malformed XML: {e}"
    except Exception as e:
        return key, [], f"{type(e).__name__}: {e}"


def parse_feed_xml(raw_bytes, source_name):
    """Parse RSS 2.0 or Atom XML into a normalized list of dicts."""
    items = []
    root = ET.fromstring(raw_bytes)

    # RSS 2.0: <rss><channel><item>...
    for item in root.findall(".//item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        pub = _text(item.find("pubDate"))
        desc = _text(item.find("description"))
        items.append(_normalize(title, link, pub, desc, source_name))

    # Atom: <feed><entry>...
    if not items:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns):
            title = _text(entry.find("a:title", ns))
            link_el = entry.find("a:link", ns)
            link = link_el.get("href") if link_el is not None else ""
            pub = _text(entry.find("a:updated", ns)) or _text(entry.find("a:published", ns))
            desc = _text(entry.find("a:summary", ns)) or _text(entry.find("a:content", ns))
            items.append(_normalize(title, link, pub, desc, source_name))

    return items


def _text(el):
    return el.text.strip() if el is not None and el.text else ""


def _normalize(title, link, pub, desc, source_name):
    clean_desc = html.unescape(re.sub(r"<[^>]+>", "", desc or "")).strip()
    clean_desc = re.sub(r"\s+", " ", clean_desc)[:280]

    dt = None
    if pub:
        try:
            dt = parsedate_to_datetime(pub)
        except Exception:
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except Exception:
                dt = None

    return {
        "title": html.unescape(title or "(no title)").strip(),
        "link": link or "",
        "published": dt,
        "published_raw": pub or "",
        "summary": clean_desc,
        "source": source_name,
        "is_critical": bool(CRITICAL_HINTS.search((title or "") + " " + (desc or ""))),
    }


def fetch_all(selected_sources, limit_per_source, console=None, progress_cb=None):
    """Fetch all selected feeds concurrently, yielding results as they arrive."""
    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=min(8, len(selected_sources)) or 1) as pool:
        futures = {
            pool.submit(fetch_feed, key, src): key
            for key, src in selected_sources.items()
        }
        for future in as_completed(futures):
            key, items, err = future.result()
            name = selected_sources[key]["name"]
            if err:
                errors[key] = err
                if progress_cb:
                    progress_cb(name, 0, ok=False, err=err)
            else:
                items = items[:limit_per_source]
                results[key] = items
                if progress_cb:
                    progress_cb(name, len(items), ok=True, err=None)

    return results, errors


# ─────────────────────────────────────────────────────────────────
# Terminal rendering (rich, cyberpunk theme) — falls back to plain
# ─────────────────────────────────────────────────────────────────
def run_with_rich(selected_sources, limit_per_source, output_path):
    console = Console()

    banner = Text()
    banner.append("▓▓▓ ", style="bold magenta")
    banner.append("CYBER_NEWS", style="bold bright_green")
    banner.append(" // SECURITY INTEL AGGREGATOR ", style="bold bright_cyan")
    banner.append("▓▓▓", style="bold magenta")
    console.print(Panel(banner, border_style="bright_magenta", box=box.DOUBLE))
    console.print(f"[dim]target sources: {len(selected_sources)} | limit/source: {limit_per_source} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    all_results = {}
    errors = {}

    with Progress(
        SpinnerColumn(style="bright_green"),
        TextColumn("[bright_cyan]{task.fields[label]}"),
        BarColumn(complete_style="bright_magenta"),
        TextColumn("[bright_green]{task.fields[status]}"),
        console=console,
        transient=False,
    ) as progress:
        tasks = {
            key: progress.add_task("", total=1, label=src["name"].ljust(22), status="[yellow]connecting...")
            for key, src in selected_sources.items()
        }

        def cb(name, count, ok, err):
            for key, src in selected_sources.items():
                if src["name"] == name:
                    if ok:
                        progress.update(tasks[key], completed=1, status=f"[bright_green]✓ {count} items")
                    else:
                        progress.update(tasks[key], completed=1, status=f"[bold red]✗ failed")
                    break

        all_results, errors = fetch_all(selected_sources, limit_per_source, console, cb)

    console.print()

    total_items = sum(len(v) for v in all_results.values())
    critical_count = sum(1 for v in all_results.values() for item in v if item["is_critical"])

    summary = Table.grid(padding=(0, 2))
    summary.add_row("[bold]Total stories:[/bold]", f"[bright_green]{total_items}[/bright_green]")
    summary.add_row("[bold]Flagged high-severity:[/bold]", f"[bold red]{critical_count}[/bold red]")
    summary.add_row("[bold]Sources reached:[/bold]", f"[bright_cyan]{len(all_results)}/{len(selected_sources)}[/bright_cyan]")
    console.print(Panel(summary, title="[bold]// SUMMARY[/bold]", border_style="green", box=box.ROUNDED))
    console.print()

    # Print stories grouped by source, flagging critical ones
    for key, items in all_results.items():
        if not items:
            continue
        source_name = selected_sources[key]["name"]
        console.print(f"[bold bright_magenta]┌─[/bold bright_magenta] [bold bright_white on grey15] {source_name} [/bold bright_white on grey15]")
        for item in items:
            tag = "[bold red]⚠ CRITICAL[/bold red] " if item["is_critical"] else ""
            console.print(f"[bright_magenta]│[/bright_magenta]  {tag}[bright_white]{item['title']}[/bright_white]")
            if item["published"]:
                console.print(f"[bright_magenta]│[/bright_magenta]  [dim]   {item['published'].strftime('%Y-%m-%d %H:%M')} · [link={item['link']}]{item['link']}[/link][/dim]")
            console.print("[bright_magenta]│[/bright_magenta]")
        console.print("[bold bright_magenta]└─[/bold bright_magenta]\n")

    if errors:
        console.print("[bold red]// ERRORS[/bold red]")
        for key, err in errors.items():
            console.print(f"  [red]✗ {selected_sources[key]['name']}: {err}[/red]")
        console.print()

    return all_results, errors, total_items, critical_count


def run_plain(selected_sources, limit_per_source):
    print("=" * 60)
    print("  CYBER_NEWS // SECURITY INTEL AGGREGATOR")
    print("=" * 60)
    print(f"sources: {len(selected_sources)} | limit/source: {limit_per_source} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def cb(name, count, ok, err):
        if ok:
            print(f"  [OK]   {name:<22} {count} items")
        else:
            print(f"  [FAIL] {name:<22} {err}")

    all_results, errors = fetch_all(selected_sources, limit_per_source, None, cb)

    total_items = sum(len(v) for v in all_results.values())
    critical_count = sum(1 for v in all_results.values() for item in v if item["is_critical"])
    print(f"\nTotal: {total_items} stories | Flagged: {critical_count} | Sources OK: {len(all_results)}/{len(selected_sources)}\n")

    for key, items in all_results.items():
        if not items:
            continue
        name = selected_sources[key]["name"]
        print(f"\n-- {name} --")
        for item in items:
            tag = "[CRITICAL] " if item["is_critical"] else ""
            print(f"  {tag}{item['title']}")
            print(f"     {item['link']}")

    return all_results, errors, total_items, critical_count


# ─────────────────────────────────────────────────────────────────
# Markdown report generation
# ─────────────────────────────────────────────────────────────────
def build_markdown(all_results, selected_sources, errors, total_items, critical_count):
    now = datetime.now()
    lines = []
    lines.append(f"# 🛡️ Cyber Security Daily Digest")
    lines.append("")
    lines.append(f"> Generated `{now.strftime('%Y-%m-%d %H:%M:%S')}` · "
                  f"**{total_items}** stories · "
                  f"**{critical_count}** flagged high-severity · "
                  f"**{len(all_results)}/{len(selected_sources)}** sources reached")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of contents
    lines.append("## 📑 Contents")
    lines.append("")
    for key, items in all_results.items():
        if items:
            anchor = selected_sources[key]["name"].lower().replace(" ", "-")
            lines.append(f"- [{selected_sources[key]['name']}](#{anchor}) ({len(items)})")
    lines.append("")
    lines.append("---")
    lines.append("")

    for key, items in all_results.items():
        if not items:
            continue
        source = selected_sources[key]
        lines.append(f"## {source['name']}")
        lines.append("")
        for item in items:
            flag = "🔴 **[HIGH SEVERITY]** " if item["is_critical"] else ""
            date_str = item["published"].strftime("%Y-%m-%d %H:%M") if item["published"] else "n/a"
            lines.append(f"### {flag}{item['title']}")
            lines.append("")
            lines.append(f"- 🕒 `{date_str}`")
            lines.append(f"- 🔗 [{item['link']}]({item['link']})")
            if item["summary"]:
                lines.append("")
                lines.append(f"> {item['summary']}{'…' if len(item['summary']) >= 280 else ''}")
            lines.append("")
        lines.append("---")
        lines.append("")

    if errors:
        lines.append("## ⚠️ Fetch Errors")
        lines.append("")
        for key, err in errors.items():
            lines.append(f"- **{selected_sources[key]['name']}**: `{err}`")
        lines.append("")

    lines.append(f"<sub>Generated by `cyber_news.py` · {now.isoformat()}</sub>")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Cybersecurity RSS news aggregator → Markdown digest")
    parser.add_argument("--limit", type=int, default=8, help="max stories per source (default: 8)")
    parser.add_argument("--output", type=str, default=None, help="output markdown path (default: cyber_digest_YYYY-MM-DD.md)")
    parser.add_argument("--sources", type=str, default=None, help="comma-separated source keys (default: all). Available: " + ", ".join(SOURCES.keys()))
    parser.add_argument("--no-rich", action="store_true", help="force plain text output (skip rich UI)")
    args = parser.parse_args()

    if args.sources:
        keys = [k.strip() for k in args.sources.split(",") if k.strip()]
        selected = {k: SOURCES[k] for k in keys if k in SOURCES}
        unknown = [k for k in keys if k not in SOURCES]
        if unknown:
            print(f"[!] Unknown source keys ignored: {', '.join(unknown)}")
        if not selected:
            print("[!] No valid sources selected. Aborting.")
            sys.exit(1)
    else:
        selected = SOURCES

    output_path = args.output or f"cyber_digest_{datetime.now().strftime('%Y-%m-%d')}.md"

    use_rich = RICH_AVAILABLE and not args.no_rich
    if use_rich:
        all_results, errors, total_items, critical_count = run_with_rich(selected, args.limit, output_path)
    else:
        all_results, errors, total_items, critical_count = run_plain(selected, args.limit)

    md = build_markdown(all_results, selected, errors, total_items, critical_count)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    if use_rich:
        console = Console()
        console.print(Panel(f"[bold bright_green]✓ Digest saved →[/bold bright_green] [bold white]{output_path}[/bold white]",
                             border_style="bright_green", box=box.ROUNDED))
    else:
        print(f"\n✓ Digest saved → {output_path}")


if __name__ == "__main__":
    main()
