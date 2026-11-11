"""Palette constants and the single application stylesheet.

One accent color only. Hover states change the fill, never the hue.
"""

BG_BASE = "#121214"
BG_ELEVATED = "#1a1a1e"
BG_SUNKEN = "#0c0c0e"
BG_HOVER = "#202024"
BG_SELECT = "#23272b"
BORDER = "#2a2a2f"
TEXT_PRIMARY = "#e8e8ea"
TEXT_SECONDARY = "#8a8a92"
TEXT_TERTIARY = "#5a5a62"
ACCENT = "#5ee0c0"
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
    QLabel, QCheckBox {{ background-color: transparent; }}
    QScrollArea {{ border: none; }}

    QWidget#rootContainer {{ border: 1px solid {BORDER}; }}
    QWidget#titleBar {{
        background-color: {BG_ELEVATED};
        border: none;
        border-bottom: 1px solid {BORDER};
    }}
    QLabel#titleLabel {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
    QFrame#sidebar {{
        background-color: {BG_ELEVATED};
        border: none;
        border-right: 1px solid {BORDER};
    }}
    QWidget#statusStrip {{ background-color: {BG_ELEVATED}; border-top: 1px solid {BORDER}; }}
    QLabel#statusText {{ color: {TEXT_TERTIARY}; font-size: 11px; }}

    QFrame#elevatedPanel {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QLabel#brandLabel {{
        font-family: {FONT_MONO};
        color: {ACCENT};
        font-size: 13px;
        letter-spacing: 2px;
    }}
    QLabel#pageTitle {{ font-size: 20px; font-weight: 600; }}
    QLabel#secondaryLabel {{ color: {TEXT_SECONDARY}; }}
    QLabel#tertiaryLabel {{ color: {TEXT_TERTIARY}; font-size: 11px; }}
    QLabel#monoLabel {{ font-family: {FONT_MONO}; color: {TEXT_PRIMARY}; }}
    QLabel#statValue {{ font-family: {FONT_MONO}; font-size: 26px; color: {TEXT_PRIMARY}; }}
    QLabel#statTitle {{ color: {TEXT_SECONDARY}; font-size: 11px; }}
    QLabel#noticeLabel {{ color: {TEXT_SECONDARY}; }}
    QLabel#noticeLabel[level="error"] {{ color: {DANGER}; }}
    QLabel#noticeLabel[level="ok"] {{ color: {ACCENT}; }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 7px 14px;
        color: {TEXT_PRIMARY};
    }}
    QPushButton:hover {{ background-color: {BG_HOVER}; }}
    QPushButton:pressed {{ background-color: {BG_SUNKEN}; }}
    QPushButton:disabled {{ color: {TEXT_TERTIARY}; background-color: {BG_BASE}; }}
    QPushButton#primaryAction {{ border: 1px solid {ACCENT}; color: {ACCENT}; }}
    QPushButton#primaryAction:disabled {{ border: 1px solid {BORDER}; color: {TEXT_TERTIARY}; }}
    QPushButton#destructiveAction {{ border: 1px solid {DANGER}; color: {DANGER}; }}
    QPushButton#destructiveAction:disabled {{ border: 1px solid {BORDER}; color: {TEXT_TERTIARY}; }}
    QPushButton:checked {{ color: {ACCENT}; border: 1px solid {ACCENT}; }}
    QPushButton::menu-indicator {{ width: 0px; }}

    QPushButton#navButton {{
        text-align: left;
        border: none;
        border-left: 2px solid transparent;
        border-radius: 0px;
        padding: 11px 18px;
        background-color: transparent;
        color: {TEXT_SECONDARY};
    }}
    QPushButton#navButton:hover {{ background-color: {BG_HOVER}; }}
    QPushButton#navButton:checked {{
        color: {ACCENT};
        border: none;
        border-left: 2px solid {ACCENT};
        background-color: {BG_HOVER};
    }}
    QPushButton#windowControl, QPushButton#closeControl {{
        border: none; background-color: transparent; padding: 0px;
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        color: {TEXT_PRIMARY};
        selection-background-color: {BG_SELECT};
        selection-color: {TEXT_PRIMARY};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
    QDoubleSpinBox:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        selection-background-color: {BG_SELECT};
        selection-color: {TEXT_PRIMARY};
        outline: 0;
    }}

    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {BORDER}; border-radius: 4px;
        background-color: {BG_SUNKEN};
    }}
    QCheckBox::indicator:checked {{ background-color: {ACCENT}; border: 1px solid {ACCENT}; }}

    QGroupBox {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 12px;
        margin-top: 14px;
        padding: 18px 14px 14px 14px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: {TEXT_SECONDARY};
        background-color: {BG_BASE};
    }}

    QTableWidget {{
        background-color: {BG_BASE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        gridline-color: transparent;
        selection-background-color: {BG_SELECT};
        selection-color: {TEXT_PRIMARY};
        outline: 0;
    }}
    QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid #1c1c20; }}
    QHeaderView::section {{
        background-color: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 6px 8px;
        font-size: 11px;
    }}
    QTableCornerButton::section {{ background-color: {BG_ELEVATED}; border: none; }}

    QProgressBar {{
        border: 1px solid {BORDER}; border-radius: 4px;
        background-color: {BG_SUNKEN}; max-height: 6px; color: transparent;
    }}
    QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 3px; }}

    QSplitter::handle {{ background-color: {BORDER}; }}
    QSplitter::handle:vertical {{ height: 1px; }}

    QMenu {{
        background-color: {BG_ELEVATED}; border: 1px solid {BORDER}; padding: 4px;
    }}
    QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
    QMenu::item:selected {{ background-color: {BG_SELECT}; }}
    QToolTip {{
        background-color: {BG_ELEVATED}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER};
    }}

    QScrollBar:vertical {{ background-color: {BG_BASE}; width: 10px; border: none; }}
    QScrollBar::handle:vertical {{
        background-color: {BORDER}; border-radius: 5px; min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{ background-color: {BG_BASE}; height: 10px; border: none; }}
    QScrollBar::handle:horizontal {{
        background-color: {BORDER}; border-radius: 5px; min-width: 24px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    """
