"""
theme.py — the visual identity of Idea Book.

Palette:
  #161616  base (near-black, not pure — pure black kills depth)
  #1C1C1C  raised surface (sidebar, panels)
  #232323  hover / active surface
  #2A2A2A  borders, hairlines
  #E8E6E1  warm paper-white text (not cold #FFFFFF)
  #9A9791  secondary text
  #605D58  tertiary / placeholder text
  #C9995C  accent — desaturated amber, used sparingly (selection, links, pins)

Type: system UI font for chrome, monospace for the editor surface itself —
the editor should feel like an instrument, the chrome should disappear.
"""

ACCENT = "#C9995C"
BG_BASE = "#161616"
BG_RAISED = "#1C1C1C"
BG_HOVER = "#232323"
BORDER = "#2A2A2A"
TEXT_PRIMARY = "#E8E6E1"
TEXT_SECONDARY = "#9A9791"
TEXT_TERTIARY = "#605D58"

STYLESHEET = f"""
* {{
    font-family: -apple-system, "SF Pro Text", "Segoe UI", sans-serif;
    color: {TEXT_PRIMARY};
    outline: none;
}}

QMainWindow, QWidget#root {{
    background-color: {BG_BASE};
}}

/* ---------- Titlebar ---------- */
QWidget#titlebar {{
    background-color: {BG_RAISED};
    border-bottom: 1px solid {BORDER};
}}
QLabel#titlebarLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#trafficDot {{
    border-radius: 6px;
    min-width: 12px; max-width: 12px;
    min-height: 12px; max-height: 12px;
    border: none;
}}

/* ---------- Sidebar ---------- */
QWidget#sidebar {{
    background-color: {BG_RAISED};
    border-right: 1px solid {BORDER};
}}
QLabel#sidebarHeader {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 12px 14px 4px 14px;
}}
QListWidget {{
    background: transparent;
    border: none;
    font-size: 13px;
    padding: 4px 6px;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: 6px;
    margin: 1px 0px;
    color: {TEXT_PRIMARY};
}}
QListWidget::item:selected {{
    background-color: {BG_HOVER};
    color: {ACCENT};
}}
QListWidget::item:hover:!selected {{
    background-color: #1F1F1F;
}}

/* ---------- Editor ---------- */
QPlainTextEdit#editor {{
    background-color: {BG_BASE};
    border: none;
    font-family: "SF Mono", "JetBrains Mono", Consolas, monospace;
    font-size: 14px;
    line-height: 1.6;
    padding: 28px 36px;
    selection-background-color: #3A2E1E;
    selection-color: {TEXT_PRIMARY};
}}

/* ---------- Preview ---------- */
QTextBrowser#preview {{
    background-color: {BG_BASE};
    border: none;
    padding: 28px 36px;
    font-size: 14px;
}}

/* ---------- Search / Input ---------- */
QLineEdit {{
    background-color: {BG_HOVER};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
    margin: 8px 10px;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}

/* ---------- Toolbar buttons ---------- */
QPushButton#toolBtn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
    padding: 5px 12px;
}}
QPushButton#toolBtn:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}
QPushButton#toolBtn:checked {{
    background-color: #2E2620;
    color: {ACCENT};
}}

/* ---------- Splitter ---------- */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3A3A3A;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4A4A4A;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ---------- Status bar ---------- */
QWidget#statusbar {{
    background-color: {BG_RAISED};
    border-top: 1px solid {BORDER};
}}
QLabel#statusLabel {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
    padding: 4px 12px;
}}

/* ---------- Menu ---------- */
QMenu {{
    background-color: #202020;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 5px;
    font-size: 13px;
}}
QMenu::item:selected {{
    background-color: {BG_HOVER};
    color: {ACCENT};
}}
"""

PREVIEW_CSS = f"""
<style>
body {{
    color: {TEXT_PRIMARY};
    font-family: -apple-system, "SF Pro Text", sans-serif;
    font-size: 14px;
    line-height: 1.65;
}}
h1, h2, h3 {{
    color: {TEXT_PRIMARY};
    font-weight: 600;
    border-bottom: 1px solid {BORDER};
    padding-bottom: 6px;
}}
a.wikilink {{
    color: {ACCENT};
    text-decoration: none;
    border-bottom: 1px dotted {ACCENT};
}}
a.wikilink-missing {{
    color: {TEXT_TERTIARY};
    border-bottom: 1px dashed {TEXT_TERTIARY};
}}
a.tag-chip {{
    color: #8FAF7C;
    text-decoration: none;
    background-color: #1E241C;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 12px;
}}
code {{
    background-color: {BG_HOVER};
    padding: 2px 5px;
    border-radius: 4px;
    font-family: "SF Mono", monospace;
    font-size: 12.5px;
}}
pre {{
    background-color: {BG_HOVER};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px;
    overflow-x: auto;
}}
blockquote {{
    border-left: 3px solid {BORDER};
    margin: 8px 0;
    padding-left: 12px;
    color: {TEXT_SECONDARY};
}}
.callout {{
    border-left: 3px solid {ACCENT};
    background-color: {BG_HOVER};
    border-radius: 6px;
    padding: 10px 14px;
    margin: 12px 0;
}}
.callout-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}}
.callout-body {{
    color: {TEXT_PRIMARY};
    font-size: 13.5px;
}}
table {{
    border-collapse: collapse;
    width: 100%;
}}
.task-done {{
    color: {TEXT_TERTIARY};
    text-decoration: line-through;
}}
.task-open {{
    color: {TEXT_PRIMARY};
}}
th, td {{
    border: 1px solid {BORDER};
    padding: 6px 10px;
    text-align: left;
}}
</style>
"""
