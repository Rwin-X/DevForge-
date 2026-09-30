"""Centralized QSS stylesheet and palette constants.

Swap ACCENT to change the whole app's single accent color; never
introduce a second accent color alongside it. Every widget file
imports these constants instead of re-typing hex values.
"""

BG_BASE = "#121214"
BG_ELEVATED = "#1a1a1e"
BG_SUNKEN = "#0c0c0e"
BORDER = "#2a2a2f"
BORDER_FOCUS = "#3a3a40"
TEXT_PRIMARY = "#e8e8ea"
TEXT_SECONDARY = "#8a8a92"
TEXT_TERTIARY = "#5a5a62"
ACCENT = "#5b8cff"
ACCENT_DIM = "#3a5bb0"
DANGER = "#c0524a"

FONT_UI = "Inter, -apple-system, Segoe UI, sans-serif"
FONT_MONO = "JetBrains Mono, Consolas, monospace"


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

    QLabel#appTitle {{
        font-weight: 600;
        font-size: 13px;
        color: {TEXT_PRIMARY};
    }}

    QLabel#appTagline {{
        color: {TEXT_TERTIARY};
        font-size: 10px;
        letter-spacing: 1px;
    }}

    QWidget#elevatedPanel {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QWidget#sunkenPanel {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QTabBar::tab {{
        background: transparent;
        color: {TEXT_SECONDARY};
        padding: 8px 4px;
        margin-right: 22px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 11px;
    }}

    QTabBar::tab:selected {{
        color: {TEXT_PRIMARY};
        border-bottom: 2px solid {ACCENT};
    }}

    QTabWidget::pane {{
        border: none;
        border-top: 1px solid {BORDER};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 7px 10px;
        color: {TEXT_PRIMARY};
        selection-background-color: {ACCENT_DIM};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {ACCENT};
    }}

    QLineEdit:disabled, QTextEdit:disabled {{
        color: {TEXT_TERTIARY};
    }}

    QLineEdit#monoField, QTextEdit#monoField, QPlainTextEdit#monoField {{
        font-family: {FONT_MONO};
        font-size: 12.5px;
    }}

    QComboBox {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 7px 12px;
        color: {TEXT_PRIMARY};
        min-width: 200px;
    }}

    QComboBox:hover {{
        border: 1px solid {BORDER_FOCUS};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT_DIM};
        color: {TEXT_PRIMARY};
        outline: none;
        padding: 4px;
    }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 8px 16px;
        color: {TEXT_PRIMARY};
    }}

    QPushButton:hover {{
        background-color: #202024;
    }}

    QPushButton:pressed {{
        background-color: {BG_SUNKEN};
    }}

    QPushButton:disabled {{
        color: {TEXT_TERTIARY};
        border: 1px solid {BORDER};
    }}

    QPushButton#primaryAction {{
        background-color: {ACCENT};
        border: 1px solid {ACCENT};
        color: #0c0c0e;
        font-weight: 600;
    }}

    QPushButton#primaryAction:hover {{
        background-color: #6f99ff;
    }}

    QPushButton#ghostAction {{
        background: transparent;
        border: none;
        color: {TEXT_SECONDARY};
        padding: 4px 8px;
    }}

    QPushButton#ghostAction:hover {{
        color: {TEXT_PRIMARY};
    }}

    QPushButton#destructiveAction {{
        border: 1px solid {DANGER};
        color: {DANGER};
        background: transparent;
    }}

    QPushButton#destructiveAction:hover {{
        background-color: rgba(192, 82, 74, 0.12);
    }}

    QPushButton#segmentButton {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 6px 16px;
        color: {TEXT_SECONDARY};
        font-size: 11px;
    }}

    QPushButton#segmentButton:checked {{
        background-color: {ACCENT};
        color: #0c0c0e;
        font-weight: 600;
    }}

    QLabel#secondaryLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}

    QLabel#tertiaryLabel {{
        color: {TEXT_TERTIARY};
        font-size: 11px;
    }}

    QLabel#fieldLabel {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}

    QLabel#monoLabel {{
        font-family: {FONT_MONO};
        color: {TEXT_PRIMARY};
    }}

    QLabel#errorLabel {{
        color: {DANGER};
        font-size: 12px;
    }}

    QLabel#descriptionLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}

    QFrame#hairline {{
        background-color: {BORDER};
        max-height: 1px;
        min-height: 1px;
    }}

    QScrollBar:vertical {{
        background-color: {BG_BASE};
        width: 10px;
        border: none;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background-color: {BORDER};
        border-radius: 5px;
        min-height: 24px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {BG_BASE};
        height: 10px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {BORDER};
        border-radius: 5px;
        min-width: 24px;
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    QListWidget {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 4px;
        outline: none;
    }}

    QListWidget::item {{
        border-radius: 8px;
        padding: 10px;
    }}

    QListWidget::item:hover {{
        background-color: {BG_ELEVATED};
    }}

    QListWidget::item:selected {{
        background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
    }}

    QProgressBar {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 6px;
        text-align: center;
        color: {TEXT_SECONDARY};
        height: 8px;
    }}

    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: 5px;
    }}

    QCheckBox {{
        spacing: 8px;
        color: {TEXT_PRIMARY};
    }}

    QToolTip {{
        background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        padding: 4px 8px;
        border-radius: 4px;
    }}
    """
