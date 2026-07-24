"""
Chat Personality Analyzer
=========================
Main CLI entry point.

Usage:
    python analyzer.py chat.txt
    python analyzer.py chat.txt --speaker "Alice"
    python analyzer.py chat.txt --no-ai
    python analyzer.py --paste          (read from stdin)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# ── Rich / Colorama ────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table
    from rich.text import Text
    from rich import box
    from rich.columns import Columns
    from rich.rule import Rule
    from rich.padding import Padding
    _HAS_RICH = True
except ImportError:
    # Stub so rest of file doesn't get NameError
    class _Stub:
        def __getattr__(self, name):
            return None
    Console = Panel = Progress = Table = Text = Columns = Rule = Padding = None
    box = _Stub()
    SpinnerColumn = BarColumn = TaskProgressColumn = TextColumn = TimeElapsedColumn = None
    _HAS_RICH = False

try:
    import colorama
    colorama.init(autoreset=True)
    _HAS_COLORAMA = True
except ImportError:
    _HAS_COLORAMA = False

from config import APP_NAME, APP_VERSION, REPORTS_DIR, OPENAI_API_KEY
from parser import parse_file, parse_text, ParsedConversation
from personality_engine import analyze, AnalysisResult
from report_generator import generate_all

# ─── Console setup ─────────────────────────────────────────────────────────────

console = Console() if _HAS_RICH else None

def _print(msg: str, style: str = "") -> None:
    if _HAS_RICH and console:
        console.print(msg, style=style)
    else:
        # Strip basic rich markup for plain output
        import re as _re
        clean = _re.sub(r"\[/?[a-zA-Z0-9 #_]+\]", "", msg)
        print(clean)


def _rule(title: str = "") -> None:
    if _HAS_RICH and console:
        console.print(Rule(title, style="dim cyan"))
    else:
        print(f"\n{'─' * 60}  {title}")


# ─── Banner ───────────────────────────────────────────────────────────────────

def _show_banner() -> None:
    if not _HAS_RICH:
        print(f"\n  {'=' * 50}")
        print(f"  🧠  {APP_NAME} v{APP_VERSION}")
        print(f"  All processing is local · No data stored")
        print(f"  {'=' * 50}\n")
        return

    banner = Text()
    banner.append("  🧠  ", style="bold")
    banner.append(APP_NAME, style="bold #00D4AA")
    banner.append(f"  v{APP_VERSION}", style="dim")

    console.print(
        Panel(
            banner,
            subtitle="[dim]All processing is local  ·  No data stored[/dim]",
            border_style="#2A2E45",
            padding=(0, 2),
        )
    )


# ─── Progress helpers ─────────────────────────────────────────────────────────

class StepProgress:
    """Thin wrapper that shows a spinner while work happens."""

    def __init__(self) -> None:
        self._progress = None
        self._task = None
        self._steps: list[str] = []

    def __enter__(self):
        if _HAS_RICH:
            self._progress = Progress(
                SpinnerColumn(style="#00D4AA"),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            )
            self._progress.__enter__()
            self._task = self._progress.add_task("Starting …", total=None)
        return self

    def update(self, msg: str) -> None:
        self._steps.append(msg)
        if _HAS_RICH and self._progress and self._task is not None:
            self._progress.update(self._task, description=f"[cyan]{msg}[/cyan]")
        else:
            print(f"  … {msg}")

    def __exit__(self, *args):
        if _HAS_RICH and self._progress:
            self._progress.__exit__(*args)


# ─── Display helpers ──────────────────────────────────────────────────────────

def _score_bar(score: float, width: int = 20) -> str:
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _score_color(score: float) -> str:
    if score >= 80:
        return "#00D4AA"
    if score >= 60:
        return "#4ECDC4"
    if score >= 40:
        return "#FFE66D"
    if score >= 20:
        return "#FF8C69"
    return "#FF6B6B"


def _show_conversation_summary(conv: ParsedConversation) -> None:
    _rule("Conversation Overview")

    if _HAS_RICH:
        table = Table(show_header=True, header_style="bold #00D4AA", box=box.SIMPLE_HEAVY)
        table.add_column("Speaker", style="bold white")
        table.add_column("Messages", justify="right")
        table.add_column("Words", justify="right")
        table.add_column("Avg Length", justify="right")
        table.add_column("Questions", justify="right")
        table.add_column("Emojis", justify="right")

        for sp, st in conv.stats.items():
            is_target = sp == conv.target_speaker
            style = "bold #00D4AA" if is_target else "dim"
            name = f"⟹  {sp}" if is_target else sp
            table.add_row(
                name,
                str(st.message_count),
                f"{st.total_words:,}",
                f"{st.avg_message_length:.1f}w",
                str(st.question_count),
                str(st.emoji_count),
                style=style,
            )
        console.print(table)
        console.print(
            f"  [dim]Format detected:[/dim] [bold]{conv.format_detected}[/bold]  "
            f"[dim]·  Analysing:[/dim] [bold #00D4AA]{conv.target_speaker}[/bold #00D4AA]"
        )
    else:
        print(f"  {'Speaker':<20} {'Msgs':>6} {'Words':>8} {'Avg':>6} {'Q':>4} {'Emoji':>6}")
        print(f"  {'-'*52}")
        for sp, st in conv.stats.items():
            marker = " <--" if sp == conv.target_speaker else ""
            print(f"  {sp:<20} {st.message_count:>6} {st.total_words:>8,} {st.avg_message_length:>5.1f}w {st.question_count:>4} {st.emoji_count:>6}{marker}")
        print(f"\n  Format: {conv.format_detected} | Analysing: {conv.target_speaker}")


def _show_scores(result: AnalysisResult) -> None:
    _rule("Personality Scores")

    if not _HAS_RICH:
        for trait, score in result.scores.as_dict().items():
            bar = _score_bar(score)
            print(f"  {trait:25s} {score:5.1f}  {bar}")
        return

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))  # type: ignore[arg-type]
    table.add_column("Trait", style="bold white", width=22)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Bar", width=22)
    table.add_column("Level", width=10)

    labels = {
        "curiosity": "Curiosity",
        "confidence": "Confidence",
        "friendliness": "Friendliness",
        "analytical_thinking": "Analytical",
        "creativity": "Creativity",
        "emotional_expression": "Emotional Expr.",
        "leadership": "Leadership",
        "social_engagement": "Social Engagement",
    }
    for key, score in result.scores.as_dict().items():
        color = _score_color(score)
        bar = _score_bar(score, 18)
        level = (
            "Very High" if score >= 80 else
            "High" if score >= 65 else
            "Moderate" if score >= 45 else
            "Low" if score >= 25 else "Very Low"
        )
        table.add_row(
            labels.get(key, key),
            f"[bold {color}]{score:.0f}[/bold {color}]",
            f"[{color}]{bar}[/{color}]",
            f"[dim]{level}[/dim]",
        )
    console.print(table)


def _show_topics(result: AnalysisResult) -> None:
    if not result.topics:
        return
    _rule("Detected Interests")
    if not _HAS_RICH:
        for t in result.topics[:6]:
            bar = _score_bar(t.confidence, 15)
            print(f"  {t.topic:<20} {t.confidence:5.0f}%  {bar}  ({t.mention_count} mentions)")
        return

    renderables = []
    for t in result.topics[:8]:
        color = _score_color(t.confidence)
        bar = _score_bar(t.confidence, 10)
        renderables.append(
            Panel(
                f"[bold {color}]{t.confidence:.0f}%[/bold {color}]\n"
                f"[dim]{bar}[/dim]\n"
                f"[dim]{t.mention_count} mentions[/dim]",
                title=f"[bold]{t.topic}[/bold]",
                border_style=color,
                width=18,
                padding=(0, 1),
            )
        )
    console.print(Columns(renderables, equal=False, expand=False))


def _show_insights(result: AnalysisResult) -> None:
    _rule("AI Insights" if result.ai_available else "Insights (Rule-Based)")

    if _HAS_RICH:
        console.print(
            Panel(
                result.ai_insights.personality_summary,
                title="[bold #00D4AA]Personality Summary[/bold #00D4AA]",
                border_style="#2A2E45",
                padding=(1, 2),
            )
        )
        console.print(
            Panel(
                result.ai_insights.communication_profile,
                title="[bold #7B61FF]Communication Profile[/bold #7B61FF]",
                border_style="#2A2E45",
                padding=(1, 2),
            )
        )
        s_text = Text()
        for s in result.ai_insights.strengths:
            s_text.append(f"✅ {s}\n", style="#7EFFA0")
        w_text = Text()
        for w in result.ai_insights.weaknesses:
            w_text.append(f"⚠️  {w}\n", style="#FFB86C")
        console.print(
            Columns([
                Panel(s_text, title="[bold #7EFFA0]Strengths[/bold #7EFFA0]", border_style="#2A2E45", padding=(1, 2)),
                Panel(w_text, title="[bold #FFB86C]Growth Areas[/bold #FFB86C]", border_style="#2A2E45", padding=(1, 2)),
            ])
        )
        console.print(
            Panel(
                result.ai_insights.final_assessment,
                title="[bold white]Final Assessment[/bold white]",
                border_style="dim",
                padding=(1, 2),
            )
        )
    else:
        sep = "─" * 60
        print(f"\n  PERSONALITY SUMMARY\n  {sep}")
        print(f"  {result.ai_insights.personality_summary}\n")
        print(f"  COMMUNICATION PROFILE\n  {sep}")
        print(f"  {result.ai_insights.communication_profile}\n")
        print(f"  STRENGTHS\n  {sep}")
        for s in result.ai_insights.strengths:
            print(f"  ✅ {s}")
        print(f"\n  GROWTH AREAS\n  {sep}")
        for w in result.ai_insights.weaknesses:
            print(f"  ⚠️  {w}")
        print(f"\n  FINAL ASSESSMENT\n  {sep}")
        print(f"  {result.ai_insights.final_assessment}")


def _show_report_paths(paths: dict) -> None:
    _rule("Reports Saved")
    if _HAS_RICH:
        table = Table(show_header=False, box=box.SIMPLE)  # type: ignore[arg-type]
        table.add_column("Format", style="bold #00D4AA", width=10)
        table.add_column("Path", style="white")
        for fmt, path in paths.items():
            table.add_row(fmt.upper(), str(path))
        console.print(table)
        console.print(
            f"\n  💡 [dim]Open [bold]reports/report.html[/bold] in your browser for the full interactive report.[/dim]"
        )
    else:
        for fmt, path in paths.items():
            print(f"  {fmt.upper():10s}  {path}")
        print("\n  Tip: Open reports/report.html in your browser for the full interactive report.")


# ─── Argument parsing ─────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="analyzer",
        description=f"{APP_NAME} — analyze a chat file and generate a personality profile.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyzer.py chat.txt
  python analyzer.py telegram_export.txt --speaker "Alice"
  python analyzer.py whatsapp.txt --no-ai
  python analyzer.py --paste < conversation.txt
  cat chat.txt | python analyzer.py --paste
        """,
    )
    ap.add_argument(
        "file",
        nargs="?",
        help="Path to the chat file (.txt)",
    )
    ap.add_argument(
        "--speaker",
        "-s",
        help="Name of the person to analyse (auto-detected if omitted)",
    )
    ap.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI analysis and use rule-based scoring only",
    )
    ap.add_argument(
        "--paste",
        "-p",
        action="store_true",
        help="Read conversation from stdin instead of a file",
    )
    ap.add_argument(
        "--output",
        "-o",
        default="report",
        help="Base name for output report files (default: report)",
    )
    ap.add_argument(
        "--open",
        action="store_true",
        help="Open the HTML report in the default browser when done",
    )
    return ap


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = _build_parser()
    args = ap.parse_args()

    _show_banner()

    # ── Input ──────────────────────────────────────────────────────────────────
    if args.paste:
        _print("\n[dim]Reading from stdin … (paste your chat and press Ctrl+D / Ctrl+Z)[/dim]")
        raw = sys.stdin.read()
        if not raw.strip():
            _print("[bold red]Error:[/bold red] No input received from stdin.", "red")
            return 1
        try:
            conv = parse_text(raw)
        except ValueError as e:
            _print(f"[bold red]Parse error:[/bold red] {e}")
            return 1
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            _print(f"[bold red]Error:[/bold red] File not found: {path}")
            return 1
        _print(f"\n[dim]Loading:[/dim] [bold]{path}[/bold]")
        try:
            conv = parse_file(path)
        except ValueError as e:
            _print(f"[bold red]Parse error:[/bold red] {e}")
            return 1
    else:
        ap.print_help()
        return 0

    # ── Speaker override ────────────────────────────────────────────────────────
    if args.speaker:
        # Find closest match (case-insensitive)
        needle = args.speaker.lower()
        match = next(
            (sp for sp in conv.speakers if sp.lower() == needle),
            None,
        )
        if match is None:
            _print(
                f"[yellow]Warning:[/yellow] Speaker '{args.speaker}' not found. "
                f"Available: {', '.join(conv.speakers)}. Using auto-detected target."
            )
        else:
            conv.target_speaker = match

    # ── Warn if AI disabled or no key ───────────────────────────────────────────
    if args.no_ai:
        os.environ["OPENAI_API_KEY"] = ""
    elif not OPENAI_API_KEY:
        _print(
            "[yellow]ℹ️  No OPENAI_API_KEY found.[/yellow] "
            "Using rule-based analysis only.  "
            "Set the env variable for AI-powered insights.",
        )

    # ── Show conversation summary ───────────────────────────────────────────────
    _show_conversation_summary(conv)

    # ── Run analysis ────────────────────────────────────────────────────────────
    _print("")
    result: AnalysisResult | None = None

    with StepProgress() as sp:
        def _tick(msg: str) -> None:
            sp.update(msg)

        try:
            result = analyze(conv, speaker=conv.target_speaker, progress_callback=_tick)
        except Exception as e:
            _print(f"[bold red]Analysis error:[/bold red] {e}")
            return 1

    if result is None:
        _print("[bold red]Analysis returned no result.[/bold red]")
        return 1

    # ── Display ─────────────────────────────────────────────────────────────────
    _show_scores(result)
    _show_topics(result)
    _show_insights(result)

    # ── Generate reports ─────────────────────────────────────────────────────────
    _print("\n[dim]Generating reports …[/dim]")
    paths = generate_all(result, conv, base_name=args.output)
    _show_report_paths(paths)

    # ── Open browser ─────────────────────────────────────────────────────────────
    if args.open:
        import webbrowser
        webbrowser.open(paths["html"].resolve().as_uri())

    _print("\n[bold #00D4AA]✓ Done.[/bold #00D4AA]  All data processed locally — no conversation data was stored.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
