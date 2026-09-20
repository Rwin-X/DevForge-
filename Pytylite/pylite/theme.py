"""Colours, fonts and the Qt stylesheet. Everything visual lives here."""

from string import Template

from PyQt6.QtGui import QColor, QFont, QPalette

# --- Surfaces -------------------------------------------------------------
BG = "#1e1e1e"            # editor
BG_CHROME = "#181818"     # window, tab bar, status bar
BG_ALT = "#252526"        # menus
TERM_BG = "#181818"       # terminal panel
BORDER = "#2b2b2b"
HOVER = "#2a2d2e"
CURRENT_LINE = "#262626"
SELECTION = "#264f78"
ACCENT = "#3b9eff"

# --- Text -----------------------------------------------------------------
FG = "#d4d4d4"
FG_DIM = "#8b8b8b"
LINE_NO = "#5a5a5a"
LINE_NO_ACTIVE = "#c6c6c6"

# --- Syntax (VS Code "Dark+" inspired) ------------------------------------
SYNTAX = {
    "keyword": "#569cd6",
    "control": "#c586c0",
    "string": "#ce9178",
    "comment": "#6a9955",
    "number": "#b5cea8",
    "function": "#dcdcaa",
    "class": "#4ec9b0",
    "variable": "#9cdcfe",
    "decorator": "#dcdcaa",
}

# --- Terminal -------------------------------------------------------------
TERM_ERR = "#f48771"
TERM_OK = "#89d185"
TERM_INFO = "#8b8b8b"
TERM_INPUT = "#4fc1ff"

MONO_FAMILIES = [
    "JetBrains Mono",
    "Fira Code",
    "Cascadia Code",
    "Ubuntu Mono",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "monospace",
]


def mono_font(size: int = 13) -> QFont:
    font = QFont()
    font.setFamilies(MONO_FAMILIES)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    font.setPointSize(size)
    return font


def build_palette() -> QPalette:
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG_CHROME,
        QPalette.ColorRole.WindowText: FG,
        QPalette.ColorRole.Base: BG,
        QPalette.ColorRole.AlternateBase: BG_ALT,
        QPalette.ColorRole.Text: FG,
        QPalette.ColorRole.Button: "#2d2d30",
        QPalette.ColorRole.ButtonText: FG,
        QPalette.ColorRole.ToolTipBase: BG_ALT,
        QPalette.ColorRole.ToolTipText: FG,
        QPalette.ColorRole.PlaceholderText: FG_DIM,
        QPalette.ColorRole.Highlight: SELECTION,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.Link: ACCENT,
    }
    for role, color in roles.items():
        p.setColor(role, QColor(color))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(FG_DIM))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(FG_DIM))
    return p


_QSS = Template(
    """
QMainWindow, QDialog { background: $BG_CHROME; }
QToolTip { background: $BG_ALT; color: $FG; border: 1px solid $BORDER; padding: 3px; }

QMenuBar { background: $BG_CHROME; color: $FG_DIM; padding: 2px 6px; }
QMenuBar::item { background: transparent; padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background: $HOVER; color: $FG; }
QMenu { background: $BG_ALT; color: $FG; border: 1px solid $BORDER; padding: 4px; }
QMenu::item { padding: 5px 28px 5px 14px; border-radius: 4px; }
QMenu::item:selected { background: $SELECTION; }
QMenu::item:disabled { color: $FG_DIM; }
QMenu::separator { height: 1px; background: $BORDER; margin: 4px 8px; }

QTabWidget::pane { border: 0; }
QTabBar { background: $BG_CHROME; qproperty-drawBase: 0; }
QTabBar::tab {
    background: $BG_CHROME; color: $FG_DIM;
    padding: 7px 6px 7px 14px; border-top: 2px solid transparent; min-width: 70px;
}
QTabBar::tab:selected { background: $BG; color: $FG; border-top: 2px solid $ACCENT; }
QTabBar::tab:hover:!selected { color: $FG; }
QToolButton#tabClose {
    border: 0; background: transparent; color: $FG_DIM;
    padding: 0px 5px 2px 5px; font-size: 15px; border-radius: 4px;
}
QToolButton#tabClose:hover { background: #3a3a3a; color: $FG; }

QStatusBar { background: $BG_CHROME; color: $FG_DIM; border-top: 1px solid $BORDER; }
QStatusBar::item { border: 0; }
QStatusBar QLabel { color: $FG_DIM; padding: 0 8px; }

QSplitter::handle { background: $BORDER; }
QSplitter::handle:vertical { height: 1px; }

QPlainTextEdit { background: $BG; color: $FG; border: 0; selection-background-color: $SELECTION; selection-color: #ffffff; }
QPlainTextEdit#termOutput { background: $TERM_BG; }

QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #3a3a3a; border-radius: 4px; min-height: 32px; margin: 2px 2px; }
QScrollBar::handle:horizontal { background: #3a3a3a; border-radius: 4px; min-width: 32px; margin: 2px 2px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #4d4d4d; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QWidget#runPanel { background: $TERM_BG; }
QLabel#panelTitle { color: $FG_DIM; font-size: 10px; font-weight: bold; padding-left: 4px; }
QLabel#panelStatus { color: $FG_DIM; font-size: 11px; padding-right: 6px; }
QLabel#prompt { color: $ACCENT; padding-left: 10px; background: $TERM_BG; }
QPushButton#flat { background: transparent; color: $FG_DIM; border: 0; padding: 3px 9px; border-radius: 4px; }
QPushButton#flat:hover { background: $HOVER; color: $FG; }
QPushButton#flat:disabled { color: #4a4a4a; }
QLineEdit#termInput {
    background: $TERM_BG; color: $FG; border: 0; padding: 7px 8px;
    selection-background-color: $SELECTION;
}
"""
)


def stylesheet() -> str:
    return _QSS.substitute(
        BG=BG, BG_CHROME=BG_CHROME, BG_ALT=BG_ALT, TERM_BG=TERM_BG, BORDER=BORDER,
        HOVER=HOVER, SELECTION=SELECTION, ACCENT=ACCENT, FG=FG, FG_DIM=FG_DIM,
    )
