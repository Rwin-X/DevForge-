"""QSS palette and stylesheet for the Pulse Qt window."""
BG, FG, LINE, MUTED = "#0a0a0a", "#f2f2f0", "#252525", "#77776f"

QSS = """
QWidget { background: %BG%; color: %FG%; font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 12px; }
QPushButton { border: 1px solid %LINE%; border-radius: 8px; padding: 8px 16px; }
QPushButton:hover { border-color: %FG%; }
QPushButton#primary { background: %FG%; color: %BG%; border-color: %FG%; }
QLabel#muted { color: %MUTED%; }
QSlider::groove:horizontal { height: 2px; background: %LINE%; }
QSlider::sub-page:horizontal { background: %FG%; }
QSlider::handle:horizontal { background: %FG%; width: 8px; height: 8px; margin: -3px 0; border-radius: 0; }
"""
for _k, _v in (("%BG%", BG), ("%FG%", FG), ("%LINE%", LINE), ("%MUTED%", MUTED)):
    QSS = QSS.replace(_k, _v)
