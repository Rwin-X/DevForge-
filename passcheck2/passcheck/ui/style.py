"""Centralized QSS stylesheet and palette constants for passcheck.

Palette matches the established dark/minimal convention. Swap ACCENT
to change the app's single accent color; the meter colors below are
semantic (weak/fair/strong) and intentionally separate from ACCENT.
"""

BG_BASE = "#121214"
BG_ELEVATED = "#1a1a1e"
BG_SUNKEN = "#0c0c0e"
BORDER = "#2a2a2f"
TEXT_PRIMARY = "#e8e8ea"
TEXT_SECONDARY = "#8a8a92"
TEXT_TERTIARY = "#5a5a62"
ACCENT = "#5ee0c0"
DANGER = "#c0524a"

FONT_UI = "Inter, -apple-system, Segoe UI, sans-serif"
FONT_MONO = "JetBrains Mono, Consolas, monospace"

# Strength-level colors, from very weak to very strong.
LEVEL_COLORS = {
    0: "#c0524a",  # very weak
    1: "#c98a4a",  # weak
    2: "#c9b84a",  # fair
    3: "#7fc94a",  # strong
    4: "#5ee0c0",  # very strong
}


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG_BASE};
        color: {TEXT_PRIMARY};
        font-family: {FONT_UI};
        font-size: 13px;
    }}

    QWidget#titleBar {{
        background-color: {BG_ELEVATED};
        border-bottom: 1px solid {BORDER};
    }}

    QWidget#elevatedPanel {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QLineEdit {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 10px 12px;
        color: {TEXT_PRIMARY};
        font-family: {FONT_MONO};
        font-size: 14px;
    }}

    QLineEdit:focus {{
        border: 1px solid {ACCENT};
    }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 8px 14px;
        color: {TEXT_PRIMARY};
    }}

    QPushButton:hover {{
        background-color: #202024;
    }}

    QPushButton:pressed {{
        background-color: {BG_SUNKEN};
    }}

    QPushButton#primaryAction {{
        border: 1px solid {ACCENT};
        color: {ACCENT};
    }}

    QLabel#secondaryLabel {{
        color: {TEXT_SECONDARY};
    }}

    QLabel#tertiaryLabel {{
        color: {TEXT_TERTIARY};
        font-size: 11px;
    }}

    QLabel#monoLabel {{
        font-family: {FONT_MONO};
        color: {TEXT_PRIMARY};
    }}

    QLabel#issueLabel {{
        color: {DANGER};
        font-size: 12px;
    }}

    QLabel#suggestionLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}

    QListWidget {{
        background-color: transparent;
        border: none;
        font-size: 12px;
    }}

    QListWidget::item {{
        padding: 2px 0px;
    }}
    """
