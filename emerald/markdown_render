"""
markdown_render.py

Renders note content to HTML for the Preview tab. Uses the 'markdown'
package if it's installed (nicer output for tables, fenced code, etc.),
and otherwise falls back to a small hand-rolled renderer so the app
still works with zero extra dependencies. Either way, [[Wiki Links]]
are converted into clickable in-app links (note:<id>) before the rest
of the markdown is processed, and links to notes that don't exist yet
are shown in a distinct "broken link" style.
"""

from __future__ import annotations

import html
import re

from note_store import NoteStore, WIKILINK_PATTERN

CSS = """
<style>
body {
    background-color: #0e1512;
    color: #d7ffe9;
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 10.5pt;
    line-height: 1.55;
    padding: 4px 6px;
}
h1, h2, h3, h4 { color: #39ff9f; font-weight: 600; }
h1 { font-size: 1.5em; border-bottom: 1px solid #223129; padding-bottom: 4px; }
h2 { font-size: 1.25em; }
h3 { font-size: 1.1em; }
a.wikilink { color: #39ff9f; text-decoration: none; border-bottom: 1px dotted #39ff9f; }
a.wikilink:hover { color: #6cffc0; }
a.wikilink.broken { color: #ff6b6b; border-bottom: 1px dotted #ff6b6b; }
code { background-color: #16201b; padding: 1px 5px; border-radius: 3px; color: #9fd9bb; }
pre { background-color: #0b0e0d; border: 1px solid #223129; padding: 10px; border-radius: 4px; overflow-x: auto; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #2c4839; margin-left: 0; padding-left: 12px; color: #9fd9bb; }
ul, ol { margin-left: 1.2em; }
hr { border: none; border-top: 1px solid #223129; }
table { border-collapse: collapse; }
th, td { border: 1px solid #223129; padding: 4px 8px; }
</style>
"""


def _wikilinks_to_html(text: str, store: NoteStore) -> str:
    def replace(match: re.Match) -> str:
        raw_target = match.group(1).strip()
        full = match.group(0)
        alias_match = re.search(r"\|([^\]]+)\]\]$", full)
        display = alias_match.group(1).strip() if alias_match else raw_target
        exists = store.note_exists(raw_target)
        css_class = "wikilink" if exists else "wikilink broken"
        target_escaped = html.escape(raw_target)
        display_escaped = html.escape(display)
        return f'<a class="{css_class}" href="note:{target_escaped}">{display_escaped}</a>'

    return WIKILINK_PATTERN.sub(replace, text)


def _fallback_markdown(text: str) -> str:
    """Minimal markdown -> HTML for when the 'markdown' package isn't installed."""
    lines = text.split("\n")
    html_lines = []
    in_code_block = False
    in_list = False

    for line in lines:
        if line.strip().startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
            else:
                html_lines.append("<pre><code>")
            in_code_block = not in_code_block
            continue

        if in_code_block:
            html_lines.append(html.escape(line))
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.*)", line)
        if heading_match:
            level = len(heading_match.group(1))
            html_lines.append(f"<h{level}>{heading_match.group(2)}</h{level}>")
            continue

        list_match = re.match(r"^\s*[-*]\s+(.*)", line)
        if list_match:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{list_match.group(1)}</li>")
            continue
        elif in_list:
            html_lines.append("</ul>")
            in_list = False

        if line.strip() == "":
            html_lines.append("<br/>")
            continue

        # inline emphasis
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"\*(.+?)\*", r"<i>\1</i>", line)
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        html_lines.append(f"<p>{line}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def render_markdown_html(content: str, store: NoteStore) -> str:
    # Protect wiki links from being mangled by the markdown parser by
    # converting them to real HTML anchors first (they're inert to the
    # markdown package since they don't look like markdown syntax).
    with_links = _wikilinks_to_html(content, store)

    try:
        import markdown as md_lib  # optional dependency

        body = md_lib.markdown(
            with_links, extensions=["fenced_code", "tables", "sane_lists"]
        )
    except ImportError:
        body = _fallback_markdown(with_links)

    return f"<html><head>{CSS}</head><body>{body}</body></html>"
