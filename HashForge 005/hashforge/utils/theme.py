"""
HashForge Theme — Minimalist premium design.
Palette: off-white canvas, electric-blue accent (#2563EB),
slate neutrals, glass-card surfaces.
"""


class ThemeManager:
    # ── Palette ──────────────────────────────────────────────────────────────
    COLORS = {
        # Backgrounds
        "bg_base":        "#F8FAFC",
        "bg_surface":     "#FFFFFF",
        "bg_glass":       "rgba(255,255,255,0.70)",
        "bg_hover":       "#F1F5F9",
        "bg_active":      "#E0EAFF",
        "bg_input":       "#F8FAFC",

        # Borders
        "border_subtle":  "#E2E8F0",
        "border_focus":   "#2563EB",

        # Accent
        "accent":         "#2563EB",
        "accent_hover":   "#1D4ED8",
        "accent_light":   "#DBEAFE",
        "accent_text":    "#1E40AF",

        # Text
        "text_primary":   "#0F172A",
        "text_secondary": "#475569",
        "text_muted":     "#94A3B8",
        "text_on_accent": "#FFFFFF",

        # Status
        "success":        "#10B981",
        "success_bg":     "#D1FAE5",
        "error":          "#EF4444",
        "error_bg":       "#FEE2E2",
        "warning":        "#F59E0B",
        "warning_bg":     "#FEF3C7",

        # Dark overrides (applied when dark mode active)
        "dark_bg_base":      "#0D1117",
        "dark_bg_surface":   "#161B22",
        "dark_bg_glass":     "rgba(22,27,34,0.80)",
        "dark_bg_hover":     "#1C2333",
        "dark_bg_active":    "#1E3A5F",
        "dark_bg_input":     "#1C2333",
        "dark_border_subtle":"#30363D",
        "dark_text_primary": "#E6EDF3",
        "dark_text_secondary":"#8B949E",
        "dark_text_muted":   "#484F58",
    }

    def __init__(self, dark: bool = False):
        self.dark = dark

    def toggle(self):
        self.dark = not self.dark

    def c(self, key: str) -> str:
        if self.dark:
            dark_key = f"dark_{key}"
            if dark_key in self.COLORS:
                return self.COLORS[dark_key]
        return self.COLORS.get(key, "#000000")

    def get_stylesheet(self) -> str:
        c = self.COLORS
        if self.dark:
            bg_base        = c["dark_bg_base"]
            bg_surface     = c["dark_bg_surface"]
            bg_glass       = c["dark_bg_glass"]
            bg_hover       = c["dark_bg_hover"]
            bg_input       = c["dark_bg_input"]
            border_subtle  = c["dark_border_subtle"]
            text_primary   = c["dark_text_primary"]
            text_secondary = c["dark_text_secondary"]
            text_muted     = c["dark_text_muted"]
        else:
            bg_base        = c["bg_base"]
            bg_surface     = c["bg_surface"]
            bg_glass       = c["bg_glass"]
            bg_hover       = c["bg_hover"]
            bg_input       = c["bg_input"]
            border_subtle  = c["border_subtle"]
            text_primary   = c["text_primary"]
            text_secondary = c["text_secondary"]
            text_muted     = c["text_muted"]

        accent       = c["accent"]
        accent_hover = c["accent_hover"]
        accent_light = c["accent_light"]
        success      = c["success"]
        success_bg   = c["success_bg"]
        error        = c["error"]
        error_bg     = c["error_bg"]

        return f"""
/* ── Global ─────────────────────────────────────────────────────── */
QWidget {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
    color: {text_primary};
    background: transparent;
    border: none;
    outline: none;
}}

QMainWindow, QDialog {{
    background: {bg_base};
}}

QSplitter::handle {{
    background: {border_subtle};
    width: 1px;
    height: 1px;
}}

/* ── ScrollArea ──────────────────────────────────────────────────── */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {border_subtle};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {text_muted};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {border_subtle};
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {text_muted};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {{
    color: {text_primary};
    background: transparent;
}}
QLabel[role="heading"] {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: {text_primary};
}}
QLabel[role="subheading"] {{
    font-size: 13px;
    color: {text_secondary};
    font-weight: 400;
}}
QLabel[role="label"] {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {text_muted};
}}
QLabel[role="hash"] {{
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 12px;
    color: {text_primary};
    background: {bg_input};
    border: 1px solid {border_subtle};
    border-radius: 6px;
    padding: 8px 12px;
    letter-spacing: 0.5px;
}}
QLabel[status="success"] {{
    color: {success};
    font-weight: 600;
}}
QLabel[status="error"] {{
    color: {error};
    font-weight: 600;
}}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {{
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton[variant="primary"] {{
    background: {accent};
    color: #FFFFFF;
    border: none;
}}
QPushButton[variant="primary"]:hover {{
    background: {accent_hover};
}}
QPushButton[variant="primary"]:pressed {{
    background: {accent_hover};
    padding-top: 9px;
    padding-bottom: 7px;
}}
QPushButton[variant="primary"]:disabled {{
    background: {border_subtle};
    color: {text_muted};
}}

QPushButton[variant="ghost"] {{
    background: transparent;
    color: {text_secondary};
    border: 1px solid {border_subtle};
}}
QPushButton[variant="ghost"]:hover {{
    background: {bg_hover};
    color: {text_primary};
    border-color: {text_muted};
}}
QPushButton[variant="ghost"]:pressed {{
    background: {accent_light};
    color: {accent};
    border-color: {accent};
}}

QPushButton[variant="icon"] {{
    background: transparent;
    border: none;
    padding: 6px;
    border-radius: 6px;
    color: {text_muted};
}}
QPushButton[variant="icon"]:hover {{
    background: {bg_hover};
    color: {text_primary};
}}

QPushButton[variant="success"] {{
    background: {success_bg};
    color: {success};
    border: 1px solid {success};
}}
QPushButton[variant="danger"] {{
    background: transparent;
    color: {error};
    border: 1px solid {error};
}}
QPushButton[variant="danger"]:hover {{
    background: {error_bg};
}}

/* ── LineEdit / TextEdit ─────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {bg_input};
    border: 1px solid {border_subtle};
    border-radius: 8px;
    padding: 8px 12px;
    color: {text_primary};
    selection-background-color: {accent_light};
    selection-color: {accent};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {accent};
    background: {bg_surface};
}}
QLineEdit::placeholder {{
    color: {text_muted};
}}

/* ── CheckBox ────────────────────────────────────────────────────── */
QCheckBox {{
    spacing: 8px;
    color: {text_primary};
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid {border_subtle};
    background: {bg_surface};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
    image: none;
}}
QCheckBox::indicator:hover {{
    border-color: {accent};
}}

/* ── ProgressBar ─────────────────────────────────────────────────── */
QProgressBar {{
    background: {border_subtle};
    border-radius: 4px;
    height: 6px;
    border: none;
    text-align: center;
    color: transparent;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {accent}, stop:1 #60A5FA
    );
    border-radius: 4px;
}}

/* ── Tooltip ─────────────────────────────────────────────────────── */
QToolTip {{
    background: {text_primary};
    color: {bg_surface};
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Tab Widget ──────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {text_muted};
    padding: 8px 20px;
    border-bottom: 2px solid transparent;
    font-weight: 600;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {accent};
    border-bottom-color: {accent};
}}
QTabBar::tab:hover:!selected {{
    color: {text_primary};
}}
QTabBar::tab:focus {{
    outline: none;
}}

/* ── Menu ────────────────────────────────────────────────────────── */
QMenu {{
    background: {bg_surface};
    border: 1px solid {border_subtle};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 16px;
    border-radius: 6px;
    color: {text_primary};
}}
QMenu::item:selected {{
    background: {accent_light};
    color: {accent};
}}
QMenu::separator {{
    height: 1px;
    background: {border_subtle};
    margin: 4px 8px;
}}

/* ── StatusBar ───────────────────────────────────────────────────── */
QStatusBar {{
    background: {bg_surface};
    border-top: 1px solid {border_subtle};
    color: {text_muted};
    font-size: 11px;
    padding: 0 8px;
}}
"""
