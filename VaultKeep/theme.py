"""
theme.py

Minimal dark theme in white/blue for VaultKeep.
Single source of truth for the stylesheet + palette so widgets stay
visually consistent.
"""

# Palette -------------------------------------------------------------
BG_DARKEST = "#0B0F14"
BG_BASE = "#10151C"
BG_PANEL = "#151B24"
BG_ELEVATED = "#1B222D"
BORDER = "#242C38"
BORDER_FOCUS = "#3FA7FF"

TEXT_PRIMARY = "#F2F5F8"
TEXT_SECONDARY = "#8C97A6"
TEXT_MUTED = "#5C6572"

BLUE = "#3FA7FF"
BLUE_HOVER = "#5FB8FF"
BLUE_PRESSED = "#2E86D9"
BLUE_SOFT = "#1E2A38"

DANGER = "#E74C3C"
SUCCESS = "#2ECC71"
WARNING = "#F1C40F"

FONT_FAMILY = "Segoe UI, Inter, -apple-system, Helvetica Neue, Arial, sans-serif"
MONO_FAMILY = "JetBrains Mono, Consolas, Menlo, monospace"

STYLESHEET = f"""
* {{
    font-family: {FONT_FAMILY};
    outline: none;
}}

QMainWindow, QDialog, QWidget#root {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    color: {TEXT_PRIMARY};
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QLabel[role="secondary"] {{
    color: {TEXT_SECONDARY};
}}

QLabel[role="muted"] {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}

QLabel[role="heading"] {{
    color: {TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 600;
}}

QLabel[role="brand"] {{
    color: {TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QFrame#sidebar {{
    background-color: {BG_DARKEST};
    border-right: 1px solid {BORDER};
}}

QFrame#panel {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#card {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#hline {{
    background-color: {BORDER};
    max-height: 1px;
    min-height: 1px;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 12px;
    color: {TEXT_PRIMARY};
    selection-background-color: {BLUE};
    selection-color: {BG_DARKEST};
    font-size: 13px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {BORDER_FOCUS};
}}

QLineEdit:disabled {{
    color: {TEXT_MUTED};
}}

QLineEdit[echoMode="2"] {{
    font-family: {MONO_FAMILY};
    letter-spacing: 1px;
}}

QPushButton {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 16px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    border: 1px solid {BLUE};
    color: {BLUE_HOVER};
}}

QPushButton:pressed {{
    background-color: {BLUE_SOFT};
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
}}

QPushButton#primary {{
    background-color: {BLUE};
    border: 1px solid {BLUE};
    color: {BG_DARKEST};
    font-weight: 600;
}}

QPushButton#primary:hover {{
    background-color: {BLUE_HOVER};
    border: 1px solid {BLUE_HOVER};
}}

QPushButton#primary:pressed {{
    background-color: {BLUE_PRESSED};
    border: 1px solid {BLUE_PRESSED};
}}

QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {DANGER};
    color: {DANGER};
}}

QPushButton#danger:hover {{
    background-color: {DANGER};
    color: {BG_DARKEST};
}}

QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {TEXT_SECONDARY};
}}

QPushButton#ghost:hover {{
    color: {BLUE_HOVER};
    border: 1px solid transparent;
    background: transparent;
}}

QPushButton#navItem {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 14px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QPushButton#navItem:hover {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
}}

QPushButton#navItem:checked {{
    background-color: {BLUE_SOFT};
    color: {BLUE};
    font-weight: 600;
}}

QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 8px;
    color: {TEXT_PRIMARY};
}}

QListWidget::item:selected {{
    border: 1px solid {BLUE};
    background-color: {BG_ELEVATED};
}}

QListWidget::item:hover {{
    border: 1px solid {BORDER_FOCUS};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QProgressBar {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 5px;
    height: 8px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    border-radius: 5px;
}}

QComboBox {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 10px;
    color: {TEXT_PRIMARY};
}}

QComboBox:hover {{
    border: 1px solid {BLUE};
}}

QComboBox QAbstractItemView {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
    selection-background-color: {BLUE_SOFT};
    selection-color: {BLUE};
    outline: none;
}}

QCheckBox {{
    color: {TEXT_SECONDARY};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {BORDER};
    background: {BG_ELEVATED};
}}

QCheckBox::indicator:checked {{
    background: {BLUE};
    border: 1px solid {BLUE};
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {BLUE};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::sub-page:horizontal {{
    background: {BLUE};
    border-radius: 2px;
}}

QToolTip {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    padding: 6px 8px;
    border-radius: 6px;
}}

QMenu {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px;
    color: {TEXT_PRIMARY};
}}

QMenu::item {{
    padding: 8px 20px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: {BLUE_SOFT};
    color: {BLUE};
}}

QStatusBar {{
    background-color: {BG_DARKEST};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    font-size: 11px;
}}

QSplitter::handle {{
    background-color: {BORDER};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {BLUE};
    border-bottom: 2px solid {BLUE};
}}
"""
