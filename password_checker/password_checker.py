import sys
import re
import random
import string
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QTimer, QPoint
)
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QFont,
    QBrush, QPainterPath, QCursor, QClipboard,
    QGuiApplication
)


# ══════════════════════════════════════════════════════════════
#  STRENGTH BAR  (animated gradient fill)
# ══════════════════════════════════════════════════════════════

class StrengthBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(6)
        self._fill  = 0.0
        self._score = 0
        self._anim  = QPropertyAnimation(self, b"fill")
        self._anim.setDuration(550)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def fill(self): return self._fill

    @fill.setter
    def fill(self, v):
        self._fill = v
        self.update()

    def set_score(self, score):
        self._score = score
        target = score / 5.0
        self._anim.stop()
        self._anim.setStartValue(self._fill)
        self._anim.setEndValue(target)
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        # track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0D1B2E"))
        tp = QPainterPath()
        tp.addRoundedRect(0, 0, w, h, r, r)
        p.drawPath(tp)

        if self._fill > 0.005:
            GRAD = [
                ("#FF3A3A", "#FF6B6B"),
                ("#FF3A3A", "#FF6B6B"),
                ("#FF8C00", "#FFA940"),
                ("#1A7FFF", "#00C2FF"),
                ("#00C2FF", "#00E5FF"),
                ("#00E5B0", "#00C2FF"),
            ]
            c1, c2 = GRAD[min(self._score, 5)]
            fw = int(w * self._fill)
            g = QLinearGradient(0, 0, fw, 0)
            g.setColorAt(0, QColor(c1))
            g.setColorAt(1, QColor(c2))
            p.setBrush(QBrush(g))
            fp = QPainterPath()
            fp.addRoundedRect(0, 0, fw, h, r, r)
            p.drawPath(fp)


# ══════════════════════════════════════════════════════════════
#  SEGMENTED STRENGTH  (5 dots / segments)
# ══════════════════════════════════════════════════════════════

class SegmentBar(QWidget):
    COLORS = ["#FF3A3A", "#FF3A3A", "#FF8C00", "#1A7FFF", "#00C2FF", "#00E5B0"]

    def __init__(self):
        super().__init__()
        self.setFixedHeight(6)
        self._score      = 0
        self._score_anim = 0.0          # must be set BEFORE QPropertyAnimation
        self._anim = QPropertyAnimation(self, b"score_anim")
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def score_anim(self): return self._score_anim

    @score_anim.setter
    def score_anim(self, v):
        self._score_anim = v
        self.update()

    def set_score(self, s):
        self._score = s
        self._anim.stop()
        self._anim.setStartValue(self._score_anim)
        self._anim.setEndValue(float(s))
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        n     = 5
        gap   = 6
        seg_w = (w - gap * (n - 1)) / n
        color = QColor(self.COLORS[min(self._score, 5)])
        frac  = self._score_anim / 5.0

        for i in range(n):
            x   = i * (seg_w + gap)
            seg_fill = min(1.0, max(0.0, (frac * n) - i))
            # background
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#0D1B2E"))
            bg = QPainterPath()
            bg.addRoundedRect(x, 0, seg_w, h, 3, 3)
            p.drawPath(bg)
            # fill
            if seg_fill > 0:
                fw = seg_w * seg_fill
                fg = QPainterPath()
                fg.addRoundedRect(x, 0, fw, h, 3, 3)
                c = QColor(color)
                c.setAlphaF(0.3 + 0.7 * seg_fill)
                p.setBrush(c)
                p.drawPath(fg)


# ══════════════════════════════════════════════════════════════
#  PILL BADGE
# ══════════════════════════════════════════════════════════════

class PillBadge(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self._active = False
        self.setFixedHeight(28)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self._refresh()

    def set_active(self, v):
        if v != self._active:
            self._active = v
            self._refresh()

    def _refresh(self):
        if self._active:
            self.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #0044BB, stop:1 #0088EE);
                    color: #E8F4FF;
                    border-radius: 14px;
                    padding: 0 14px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background: #0B1524;
                    color: #2A3D52;
                    border-radius: 14px;
                    border: 1px solid #162030;
                    padding: 0 14px;
                }
            """)


# ══════════════════════════════════════════════════════════════
#  CHECKLIST ROW
# ══════════════════════════════════════════════════════════════

class CheckRow(QWidget):
    def __init__(self, text):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._dot = QLabel("○")
        self._dot.setFont(QFont("Segoe UI", 11))
        self._dot.setFixedWidth(16)
        self._lbl = QLabel(text)
        self._lbl.setFont(QFont("Segoe UI", 10))
        lay.addWidget(self._dot)
        lay.addWidget(self._lbl)
        lay.addStretch()
        self.set_ok(False)

    def set_ok(self, ok: bool):
        if ok:
            self._dot.setText("●")
            self._dot.setStyleSheet("color: #00C2FF;")
            self._lbl.setStyleSheet("color: #5A8AB0;")
        else:
            self._dot.setText("○")
            self._dot.setStyleSheet("color: #1E2D3D;")
            self._lbl.setStyleSheet("color: #243040;")


# ══════════════════════════════════════════════════════════════
#  LOGIC
# ══════════════════════════════════════════════════════════════

COMMON = {
    "password","123456","password123","admin","letmein","qwerty","abc123",
    "monkey","master","login","welcome","dragon","pass","shadow","superman",
    "mustang","12345678","iloveyou","trustno1","sunshine","princess","1234567",
    "football","charlie","donald","batman","starwars","hello","freedom",
}

def entropy_bits(pw: str) -> float:
    cs = 0
    if re.search(r'[a-z]', pw): cs += 26
    if re.search(r'[A-Z]', pw): cs += 26
    if re.search(r'\d',    pw): cs += 10
    if re.search(r'[^a-zA-Z0-9]', pw): cs += 32
    if cs == 0: return 0.0
    import math
    return len(pw) * math.log2(cs)

def crack_time(pw: str) -> str:
    cs = 0
    if re.search(r'[a-z]', pw): cs += 26
    if re.search(r'[A-Z]', pw): cs += 26
    if re.search(r'\d',    pw): cs += 10
    if re.search(r'[^a-zA-Z0-9]', pw): cs += 32
    if cs == 0: return "–"
    import math
    combos   = cs ** len(pw)
    seconds  = (combos / 2) / 1e10   # 10B guesses/s GPU
    if seconds < 1:        return "Instant"
    if seconds < 60:       return f"{int(seconds)}s"
    if seconds < 3600:     return f"{int(seconds/60)}m"
    if seconds < 86400:    return f"{int(seconds/3600)}h"
    if seconds < 2592000:  return f"{int(seconds/86400)}d"
    if seconds < 31536000: return f"{int(seconds/2592000)} months"
    y = seconds / 31536000
    if y < 1e3:  return f"{int(y)} yrs"
    if y < 1e6:  return f"{int(y/1e3)}K yrs"
    if y < 1e9:  return f"{int(y/1e6)}M yrs"
    if y < 1e12: return f"{int(y/1e9)}B yrs"
    return "∞"

def score_password(pw: str):
    if not pw:
        return 0, 0.0
    if pw.lower() in COMMON:
        return 1, 20.0
    pts = 0
    if len(pw) >= 8:  pts += 1
    if len(pw) >= 12: pts += 1
    if re.search(r'[a-z]', pw) and re.search(r'[A-Z]', pw): pts += 1
    if re.search(r'\d', pw): pts += 1
    if re.search(r'[^a-zA-Z0-9]', pw): pts += 1
    return min(pts, 5), round(entropy_bits(pw), 1)

def generate_password(length=16) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        pw = ''.join(random.choices(chars, k=length))
        s, _ = score_password(pw)
        if s == 5:
            return pw


# ══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════

LABELS = ["", "Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
COLORS = ["", "#FF3A3A", "#FF6B35", "#1A7FFF", "#00C2FF", "#00E5B0"]

STYLE = """
QMainWindow, QWidget#root {
    background: #060D1A;
}
QWidget {
    font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: #070D1A;
    width: 4px;
    border-radius: 2px;
}
QScrollBar::handle:vertical {
    background: #1A2D45;
    border-radius: 2px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QLineEdit#pwd_input {
    background: #0B1728;
    border: 1.5px solid #162030;
    border-radius: 14px;
    color: #D6EEFF;
    font-size: 15px;
    padding: 13px 96px 13px 18px;
    letter-spacing: 0.8px;
    selection-background-color: #0044BB;
}
QLineEdit#pwd_input:focus {
    border: 1.5px solid #0066DD;
    background: #0D1E35;
}

QPushButton#eye_btn {
    background: transparent;
    border: none;
    color: #2A4060;
    font-size: 15px;
    padding: 0 6px;
}
QPushButton#eye_btn:hover { color: #0099FF; }

QPushButton#copy_btn {
    background: #0B1728;
    border: 1px solid #162030;
    border-radius: 9px;
    color: #2A4060;
    font-size: 11px;
    padding: 5px 10px;
}
QPushButton#copy_btn:hover {
    border: 1px solid #0066DD;
    color: #0099FF;
}

QPushButton#gen_btn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0044BB, stop:1 #0088EE);
    border: none;
    border-radius: 12px;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 600;
    padding: 10px 0;
}
QPushButton#gen_btn:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0055DD, stop:1 #0099FF);
}
QPushButton#gen_btn:pressed {
    background: #003399;
}

QPushButton#clear_btn {
    background: transparent;
    border: 1px solid #162030;
    border-radius: 9px;
    color: #1E2D40;
    font-size: 11px;
    padding: 5px 10px;
}
QPushButton#clear_btn:hover {
    border: 1px solid #FF3A3A44;
    color: #FF3A3A;
}

QFrame#card {
    background: #0A1624;
    border: 1px solid #132030;
    border-radius: 14px;
}
"""


class PasswordChecker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Password Strength Checker")
        self.setFixedSize(500, 660)
        self.setObjectName("root")
        self.setStyleSheet(STYLE)
        self._copy_timer = QTimer()
        self._copy_timer.setSingleShot(True)
        self._copy_timer.timeout.connect(self._reset_copy_btn)

        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # scroll area so nothing gets clipped
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("root")
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(32, 36, 32, 28)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────
        title = QLabel("Password Strength")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Light))
        title.setStyleSheet("color: #FFFFFF; letter-spacing: -0.3px;")
        root.addWidget(title)

        sub = QLabel("Analyze the security of your password in real time")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #1E3050; margin-top: 3px;")
        root.addWidget(sub)

        root.addSpacing(26)

        # ── Input field + overlay buttons ───────────────────────────────
        input_container = QWidget()
        input_container.setFixedHeight(52)
        input_container.setObjectName("root")

        self.pwd_input = QLineEdit(input_container)
        self.pwd_input.setObjectName("pwd_input")
        self.pwd_input.setPlaceholderText("Enter your password …")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Normal)   # visible by default
        self.pwd_input.setFixedHeight(52)
        self.pwd_input.setFixedWidth(436)
        self.pwd_input.textChanged.connect(self._on_change)

        # eye toggle
        self.eye_btn = QPushButton("●", input_container)
        self.eye_btn.setObjectName("eye_btn")
        self.eye_btn.setFixedSize(30, 30)
        self.eye_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.eye_btn.setToolTip("Toggle visibility")
        self.eye_btn.clicked.connect(self._toggle_vis)
        self.eye_btn.move(436 - 88, 11)

        # copy
        self.copy_btn = QPushButton("Copy", input_container)
        self.copy_btn.setObjectName("copy_btn")
        self.copy_btn.setFixedSize(46, 28)
        self.copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_btn.clicked.connect(self._copy)
        self.copy_btn.move(436 - 52, 12)

        root.addWidget(input_container)
        root.addSpacing(14)

        # ── Password display label ──────────────────────────────────────
        self.pwd_display = QLabel("")
        self.pwd_display.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        self.pwd_display.setStyleSheet(
            "color: #0066CC; letter-spacing: 2px; padding: 0 2px;"
        )
        self.pwd_display.setWordWrap(True)
        self.pwd_display.setMinimumHeight(20)
        root.addWidget(self.pwd_display)

        root.addSpacing(18)

        # ── Strength row ────────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)

        self.strength_lbl = QLabel("No password")
        self.strength_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.strength_lbl.setStyleSheet("color: #1E3050;")

        self.len_lbl = QLabel("")
        self.len_lbl.setFont(QFont("Segoe UI", 10))
        self.len_lbl.setStyleSheet("color: #162030;")
        self.len_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        row1.addWidget(self.strength_lbl)
        row1.addWidget(self.len_lbl)
        root.addLayout(row1)

        root.addSpacing(7)

        self.seg_bar = SegmentBar()
        root.addWidget(self.seg_bar)

        root.addSpacing(20)

        # ── Stats row  (Entropy | Crack Time) ──────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.entropy_card = self._make_stat_card("Entropy", "– bits")
        self.crack_card   = self._make_stat_card("Time to Crack", "–")
        stats_row.addWidget(self.entropy_card[0])
        stats_row.addWidget(self.crack_card[0])
        root.addLayout(stats_row)

        root.addSpacing(18)

        # ── Char-type pills ─────────────────────────────────────────────
        pills_lbl = QLabel("Character Types")
        pills_lbl.setFont(QFont("Segoe UI", 10))
        pills_lbl.setStyleSheet("color: #1E3050;")
        root.addWidget(pills_lbl)

        root.addSpacing(7)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(8)
        self.p_lower  = PillBadge("a – z")
        self.p_upper  = PillBadge("A – Z")
        self.p_digits = PillBadge("0 – 9")
        self.p_syms   = PillBadge("!@#$")
        for p in [self.p_lower, self.p_upper, self.p_digits, self.p_syms]:
            pills_row.addWidget(p)
        root.addLayout(pills_row)

        root.addSpacing(18)

        # ── Checklist ───────────────────────────────────────────────────
        checks_lbl = QLabel("Requirements")
        checks_lbl.setFont(QFont("Segoe UI", 10))
        checks_lbl.setStyleSheet("color: #1E3050;")
        root.addWidget(checks_lbl)

        root.addSpacing(8)

        self.checks = [
            CheckRow("At least 8 characters"),
            CheckRow("At least 12 characters  (recommended)"),
            CheckRow("Uppercase & lowercase letters"),
            CheckRow("Contains a number"),
            CheckRow("Contains a symbol  (!@#$…)"),
        ]
        for c in self.checks:
            root.addWidget(c)

        root.addSpacing(20)

        # ── Generate password ────────────────────────────────────────────
        gen_btn = QPushButton("⚡  Generate Strong Password")
        gen_btn.setObjectName("gen_btn")
        gen_btn.setFixedHeight(44)
        gen_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        gen_btn.clicked.connect(self._generate)
        root.addWidget(gen_btn)

        root.addSpacing(10)

        # Clear button
        clr_row = QHBoxLayout()
        clr_row.setAlignment(Qt.AlignmentFlag.AlignRight)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("clear_btn")
        clear_btn.setFixedSize(60, 28)
        clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        clear_btn.clicked.connect(lambda: self.pwd_input.clear())
        clr_row.addWidget(clear_btn)
        root.addLayout(clr_row)

        root.addSpacing(14)

        # ── Footer ───────────────────────────────────────────────────────
        footer = QLabel("GPU offline attack  ·  10 billion guesses / sec")
        footer.setFont(QFont("Segoe UI", 9))
        footer.setStyleSheet("color: #0D1C2E;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

    # ── stat card builder ────────────────────────────────────────────
    def _make_stat_card(self, title, value):
        card = QFrame()
        card.setObjectName("card")
        card.setFixedHeight(70)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(2)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 9))
        t.setStyleSheet("color: #1E3050;")
        v = QLabel(value)
        v.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        v.setStyleSheet("color: #0077CC;")
        lay.addWidget(t)
        lay.addWidget(v)
        return card, v   # return (widget, value_label)

    # ── toggle visibility ────────────────────────────────────────────
    def _toggle_vis(self):
        if self.pwd_input.echoMode() == QLineEdit.EchoMode.Normal:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setText("○")
            self.pwd_display.setText("")
        else:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setText("●")
            self._refresh_display(self.pwd_input.text())

    def _refresh_display(self, text):
        if self.pwd_input.echoMode() == QLineEdit.EchoMode.Normal and text:
            self.pwd_display.setText(text)
        else:
            self.pwd_display.setText("")

    # ── copy ─────────────────────────────────────────────────────────
    def _copy(self):
        t = self.pwd_input.text()
        if not t: return
        QGuiApplication.clipboard().setText(t)
        self.copy_btn.setText("✓")
        self.copy_btn.setStyleSheet(
            "QPushButton#copy_btn { background:#0B1728; border:1px solid #00CC7744;"
            "border-radius:9px; color:#00CC77; font-size:11px; padding:5px 10px; }"
        )
        self._copy_timer.start(1500)

    def _reset_copy_btn(self):
        self.copy_btn.setText("Copy")
        self.copy_btn.setStyleSheet("")

    # ── generate ─────────────────────────────────────────────────────
    def _generate(self):
        pw = generate_password(16)
        self.pwd_input.setText(pw)
        if self.pwd_input.echoMode() == QLineEdit.EchoMode.Password:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setText("●")

    # ── main update ──────────────────────────────────────────────────
    def _on_change(self, text):
        score, ent = score_password(text)
        ct = crack_time(text) if text else "–"

        self._refresh_display(text)
        self.seg_bar.set_score(score)

        if text:
            lbl = LABELS[score]
            col = COLORS[score]
            self.strength_lbl.setText(lbl)
            self.strength_lbl.setStyleSheet(f"color: {col}; font-weight:600;")
        else:
            self.strength_lbl.setText("No password")
            self.strength_lbl.setStyleSheet("color: #1E3050; font-weight:400;")

        self.len_lbl.setText(f"{len(text)} chars" if text else "")

        # entropy
        self.entropy_card[1].setText(f"{ent} bits" if text else "–")
        ent_col = (
            "#00E5B0" if ent >= 80 else
            "#00C2FF" if ent >= 60 else
            "#1A7FFF" if ent >= 40 else
            "#FF8C00" if ent >= 25 else
            "#FF3A3A"
        )
        self.entropy_card[1].setStyleSheet(f"color: {ent_col};")

        # crack time
        self.crack_card[1].setText(ct)
        crack_col = (
            "#00E5B0" if score >= 5 else
            "#00C2FF" if score >= 4 else
            "#1A7FFF" if score >= 3 else
            "#FF8C00" if score >= 2 else
            "#FF3A3A"
        )
        self.crack_card[1].setStyleSheet(f"color: {crack_col};")

        # pills
        self.p_lower.set_active (bool(re.search(r'[a-z]',        text)))
        self.p_upper.set_active (bool(re.search(r'[A-Z]',        text)))
        self.p_digits.set_active(bool(re.search(r'\d',           text)))
        self.p_syms.set_active  (bool(re.search(r'[^a-zA-Z0-9]',text)))

        # checklist
        self.checks[0].set_ok(len(text) >= 8)
        self.checks[1].set_ok(len(text) >= 12)
        self.checks[2].set_ok(
            bool(re.search(r'[a-z]', text)) and bool(re.search(r'[A-Z]', text))
        )
        self.checks[3].set_ok(bool(re.search(r'\d', text)))
        self.checks[4].set_ok(bool(re.search(r'[^a-zA-Z0-9]', text)))

        # common password warning
        if text.lower() in COMMON:
            self.strength_lbl.setText("⚠ Common Password")
            self.strength_lbl.setStyleSheet("color: #FF3A3A; font-weight:600;")


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = PasswordChecker()
    win.show()
    sys.exit(app.exec())
