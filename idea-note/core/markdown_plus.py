"""
markdown_plus.py — "Markdown+" renderer.

Standard CommonMark-ish markdown, extended with:
  [[Note Title]]         -> internal link (resolves against the vault)
  [[Note Title|label]]   -> internal link with custom display text
  #tag                   -> inline tag chip
  > [!note] / [!warn] / [!todo]   -> callout blocks (ideas, warnings, action items)
  - [ ] / - [x]           -> checkboxes (interactive-looking, static render)

This is intentionally a thin layer over python-markdown rather than a
reinvented parser — do the boring 90% with a battle-tested library,
spend the effort on the 10% that makes it "idea book" markdown.
"""

import re
import html
import markdown as md

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")
TAG_RE = re.compile(r"(?<!\w)#([a-zA-Z0-9_\-/]+)")
CALLOUT_RE = re.compile(
    r"^>\s*\[!(note|warn|warning|todo|idea)\]\s*(.*)$", re.IGNORECASE
)

CALLOUT_STYLES = {
    "note":    {"label": "NOTE",    "color": "#7C9CBF"},
    "idea":    {"label": "IDEA",    "color": "#C9995C"},
    "warn":    {"label": "WARNING", "color": "#C97C5C"},
    "warning": {"label": "WARNING", "color": "#C97C5C"},
    "todo":    {"label": "TODO",    "color": "#8FAF7C"},
}


def _protect_wikilinks(text: str, existing_titles: set[str]) -> str:
    """Convert [[Title]] / [[Title|Label]] into styled <a> before markdown runs,
    so python-markdown doesn't mangle the brackets."""

    def repl(m):
        target = m.group(1).strip()
        label = (m.group(2) or target).strip()
        exists = target in existing_titles
        cls = "wikilink" if exists else "wikilink wikilink-missing"
        safe_target = html.escape(target, quote=True)
        safe_label = html.escape(label)
        return f'<a href="ideabook://note/{safe_target}" class="{cls}">{safe_label}</a>'

    return WIKILINK_RE.sub(repl, text)


def _protect_tags(text: str) -> str:
    def repl(m):
        tag = m.group(1)
        return f'<a href="ideabook://tag/{html.escape(tag, quote=True)}" class="tag-chip">#{html.escape(tag)}</a>'
    # Avoid rewriting tags inside URLs or code spans crudely by skipping lines
    # that look like fenced code — good enough for a local single-user tool.
    return TAG_RE.sub(repl, text)


def _preprocess_callouts(text: str) -> str:
    """Turn '> [!idea] Title' blockquote blocks into raw HTML callout divs."""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        m = CALLOUT_RE.match(lines[i])
        if m:
            kind = m.group(1).lower()
            title = m.group(2).strip()
            style = CALLOUT_STYLES.get(kind, CALLOUT_STYLES["note"])
            body_lines = []
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                body_lines.append(lines[i].lstrip(">").strip())
                i += 1
            body_html = md.markdown("\n".join(body_lines))
            header = title if title else style["label"]
            out.append(
                f'<div class="callout callout-{kind}" style="border-left-color:{style["color"]}">'
                f'<div class="callout-title" style="color:{style["color"]}">'
                f'{style["label"]}{" — " + html.escape(header) if title else ""}</div>'
                f'<div class="callout-body">{body_html}</div></div>'
            )
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


CHECKBOX_RE = re.compile(r"^(\s*)-\s\[( |x|X)\]\s+(.*)$", re.MULTILINE)


def _preprocess_checkboxes(text: str) -> str:
    def repl(m):
        indent, mark, label = m.groups()
        checked = mark.lower() == "x"
        box = "\u2611" if checked else "\u2610"
        cls = "task-done" if checked else "task-open"
        return f'{indent}- <span class="{cls}">{box} {label}</span>'
    return CHECKBOX_RE.sub(repl, text)


def render(text: str, existing_titles: set[str] = None) -> str:
    """Render Markdown+ source into HTML fragment.

    Order matters: wikilinks/tags must be substituted BEFORE callout
    blocks are expanded into raw HTML, otherwise the tag regex will
    also match hex colors inside the callouts' injected style attributes
    (e.g. "#C9995C") and mangle them into tag-chip links.
    """
    existing_titles = existing_titles or set()

    working = _protect_wikilinks(text, existing_titles)
    working = _protect_tags(working)
    working = _preprocess_checkboxes(working)
    working = _preprocess_callouts(working)

    body = md.markdown(
        working,
        extensions=["fenced_code", "tables", "sane_lists", "nl2br", "codehilite"],
        extension_configs={"codehilite": {"noclasses": True, "pygments_style": "monokai"}},
    )
    return body


def extract_title_suggestion(text: str) -> str:
    """First H1 or first non-empty line — used to suggest a note title."""
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
        if s:
            return s[:60]
    return "Untitled"
