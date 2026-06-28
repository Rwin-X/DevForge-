import tkinter as tk
import math, random, time

# ══════════════════════════════════════════════════════════════════
#  PALETTE  —  "phosphor terminal" theme
# ══════════════════════════════════════════════════════════════════
BG         = "#07090a"   # near-black with slight blue-grey tint
SURFACE    = "#0b0e10"
CARD       = "#0f1214"
ACCENT     = "#39ff14"   # neon phosphor green
ACCENT_MID = "#1a7a06"
ACCENT_DIM = "#0d3d03"
ACCENT_LO  = "#081e02"
PHOSPHOR   = "#b5ffb0"   # bright highlight green
MUTED      = "#2a4228"
GHOST      = "#162014"
WHITE      = "#dfffd8"

MONO       = "Courier New"

# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def text_to_binary(text: str) -> str:
    return " ".join(format(ord(c), "08b") for c in text)

def binary_to_text(binary: str) -> str:
    out = []
    for tok in binary.strip().split():
        tok = tok.strip()
        if tok and all(b in "01" for b in tok):
            try:
                out.append(chr(int(tok, 2)))
            except ValueError:
                out.append("·")
        elif tok:
            out.append("·")
    return "".join(out)


# ══════════════════════════════════════════════════════════════════
#  SCANLINE CANVAS  — decorative live binary rain strip
# ══════════════════════════════════════════════════════════════════

class BinaryRain(tk.Canvas):
    COL_W = 14
    ROWS  = 5

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, highlightthickness=0, **kw)
        self._cols = []
        self._ids  = []
        self._running = False
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        self.after(50, self._rebuild)

    def _rebuild(self):
        self.delete("all")
        self._ids = []
        w = self.winfo_width()
        if w < 10:
            return
        ncols = max(1, w // self.COL_W)
        for ci in range(ncols):
            x = ci * self.COL_W + self.COL_W // 2
            col = []
            for ri in range(self.ROWS):
                y = ri * 13 + 8
                iid = self.create_text(
                    x, y, text=str(random.randint(0, 1)),
                    font=(MONO, 8), fill=ACCENT_DIM, anchor="center"
                )
                col.append(iid)
            self._ids.append(col)
        if not self._running:
            self._running = True
            self._tick()

    def _tick(self):
        t = time.time()
        for ci, col in enumerate(self._ids):
            phase = t * 2.5 + ci * 0.37
            brightness = (math.sin(phase) + 1) / 2
            for ri, iid in enumerate(col):
                row_phase = phase + ri * 0.6
                val = int(time.time() * (3 + ci % 3) + ri) % 2
                alpha = max(0, math.sin(row_phase))
                if alpha > 0.7:
                    fill = ACCENT_MID
                elif alpha > 0.3:
                    fill = ACCENT_DIM
                else:
                    fill = ACCENT_LO
                try:
                    self.itemconfigure(iid, text=str(val), fill=fill)
                except Exception:
                    pass
        self.after(120, self._tick)


# ══════════════════════════════════════════════════════════════════
#  PILL TOGGLE  — mode switch widget
# ══════════════════════════════════════════════════════════════════

class PillToggle(tk.Canvas):
    W, H, R = 180, 30, 15

    def __init__(self, parent, on_toggle, **kw):
        super().__init__(
            parent, width=self.W, height=self.H,
            bg=BG, highlightthickness=0, cursor="hand2", **kw
        )
        self._mode = 0   # 0 = text→bin, 1 = bin→text
        self._cb   = on_toggle
        self._anim = 0.0
        self._draw()
        self.bind("<Button-1>", self._click)

    def _rounded_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1+r, y1,  x2-r, y1,
            x2,   y1,  x2,   y1+r,
            x2,   y2-r,x2,   y2,
            x2-r, y2,  x1+r, y2,
            x1,   y2,  x1,   y2-r,
            x1,   y1+r,x1,   y1,
            x1+r, y1,
        ]
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete("all")
        # track
        self._rounded_rect(0, 0, self.W, self.H, self.R,
                            fill=GHOST, outline=ACCENT_DIM, width=1)
        # labels
        self.create_text(self.W//4, self.H//2,
                         text="TEXT", font=(MONO, 8, "bold"),
                         fill=PHOSPHOR if self._mode == 0 else MUTED)
        self.create_text(3*self.W//4, self.H//2,
                         text="BINARY", font=(MONO, 8, "bold"),
                         fill=PHOSPHOR if self._mode == 1 else MUTED)
        # thumb
        pad = 3
        tw  = self.W // 2 - pad * 2
        tx  = pad + (self._mode * (self.W // 2))
        self._rounded_rect(tx, pad, tx+tw, self.H-pad, self.R-pad,
                            fill=ACCENT_MID, outline=ACCENT, width=1)
        # indicator text on thumb
        label = "→ BIN" if self._mode == 0 else "← TXT"
        self.create_text(tx + tw//2, self.H//2,
                         text=label, font=(MONO, 7, "bold"),
                         fill=ACCENT)

    def _click(self, _e=None):
        self._mode = 1 - self._mode
        self._draw()
        self._cb(self._mode)

    def get_mode(self):
        return self._mode


# ══════════════════════════════════════════════════════════════════
#  STYLED TEXT PANEL
# ══════════════════════════════════════════════════════════════════

class Panel(tk.Frame):
    def __init__(self, parent, label: str, editable: bool, **kw):
        super().__init__(parent, bg=CARD, **kw)
        self.editable = editable

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── header bar ──
        hdr = tk.Frame(self, bg=ACCENT_LO, height=32)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr.grid_propagate(False)

        # left accent stripe
        tk.Frame(hdr, bg=ACCENT, width=3, height=32).pack(side="left")

        tk.Label(hdr, text=f"  {label}", font=(MONO, 8, "bold"),
                 fg=ACCENT, bg=ACCENT_LO).pack(side="left", pady=6)

        # char counter on right
        self._counter = tk.StringVar(value="0 chars")
        tk.Label(hdr, textvariable=self._counter, font=(MONO, 7),
                 fg=MUTED, bg=ACCENT_LO).pack(side="right", padx=10)

        # ── text area ──
        self.text = tk.Text(
            self,
            font=(MONO, 12),
            fg=PHOSPHOR if editable else ACCENT,
            bg=SURFACE,
            insertbackground=ACCENT,
            selectbackground=ACCENT_DIM,
            selectforeground=WHITE,
            relief="flat", bd=0,
            padx=16, pady=14,
            wrap="word",
            state="normal" if editable else "disabled",
            highlightthickness=0,
            spacing1=2, spacing3=4,
            undo=True,
        )
        self.text.grid(row=1, column=0, sticky="nsew")

        # thin scrollbar
        sb = tk.Scrollbar(self, orient="vertical",
                          command=self.text.yview,
                          bg=CARD, troughcolor=CARD,
                          activebackground=ACCENT_DIM,
                          bd=0, width=5, relief="flat")
        sb.grid(row=1, column=1, sticky="ns")
        self.text.configure(yscrollcommand=sb.set)

        # bottom line accent
        tk.Frame(self, bg=ACCENT_DIM, height=1).grid(row=2, column=0,
                                                       columnspan=2, sticky="ew")

        if editable:
            self.text.bind("<KeyRelease>", self._update_counter)

    def _update_counter(self, _e=None):
        n = len(self.get())
        self._counter.set(f"{n} chars")

    def get(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set(self, val: str):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", val)
        if not self.editable:
            self.text.configure(state="disabled")
        n = len(val)
        self._counter.set(f"{n} chars")

    def clear(self):
        self.set("")


# ══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════

class ZeroOneTranslator(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("ZERO-ONE  //  BINARY TRANSLATOR")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(700, 520)
        self._mode = 0   # 0=text→bin  1=bin→text

        self._build()
        self._center(820, 580)

    # ── layout ───────────────────────────────────────────────────

    def _build(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True, padx=0, pady=0)

        # ── top bar ──────────────────────────────────────────────
        top = tk.Frame(root, bg=GHOST, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)

        # left accent line
        tk.Frame(top, bg=ACCENT, width=4).pack(side="left", fill="y")

        title_block = tk.Frame(top, bg=GHOST)
        title_block.pack(side="left", padx=18, pady=8)

        tk.Label(title_block, text="ZERO-ONE", font=(MONO, 17, "bold"),
                 fg=ACCENT, bg=GHOST).pack(anchor="w")
        tk.Label(title_block, text="binary translator", font=(MONO, 7),
                 fg=MUTED, bg=GHOST).pack(anchor="w")

        # pill toggle — right side of header
        toggle_wrap = tk.Frame(top, bg=GHOST)
        toggle_wrap.pack(side="right", padx=20)

        tk.Label(toggle_wrap, text="MODE", font=(MONO, 7),
                 fg=MUTED, bg=GHOST).pack(anchor="e")
        self._pill = PillToggle(toggle_wrap, self._on_mode_change)
        self._pill.pack()

        # ── binary rain strip ────────────────────────────────────
        rain = BinaryRain(root, height=38)
        rain.pack(fill="x")

        # thin separator line
        tk.Frame(root, bg=ACCENT_DIM, height=1).pack(fill="x")

        # ── panels row ───────────────────────────────────────────
        panels = tk.Frame(root, bg=BG)
        panels.pack(fill="both", expand=True, padx=14, pady=(14, 0))
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(2, weight=1)
        panels.rowconfigure(0, weight=1)

        self._inp = Panel(panels, "INPUT", editable=True)
        self._inp.grid(row=0, column=0, sticky="nsew")
        self._inp.text.bind("<KeyRelease>", self._translate)

        # ── center column ────────────────────────────────────────
        mid = tk.Frame(panels, bg=BG, width=60)
        mid.grid(row=0, column=1, sticky="ns")
        mid.grid_propagate(False)

        # convert button — vertical center
        self._arrow_cv = tk.Canvas(mid, width=44, height=44,
                                   bg=BG, highlightthickness=0)
        self._arrow_cv.place(relx=0.5, rely=0.5, anchor="center")
        self._draw_arrow_btn(idle=True)
        self._arrow_cv.bind("<Enter>",  lambda e: self._draw_arrow_btn(idle=False))
        self._arrow_cv.bind("<Leave>",  lambda e: self._draw_arrow_btn(idle=True))
        self._arrow_cv.bind("<Button-1>", self._swap_contents)

        # ── output panel ─────────────────────────────────────────
        self._out = Panel(panels, "OUTPUT", editable=False)
        self._out.grid(row=0, column=2, sticky="nsew")

        # ── status bar ───────────────────────────────────────────
        tk.Frame(root, bg=ACCENT_DIM, height=1).pack(fill="x", padx=14, pady=(12, 0))

        bar = tk.Frame(root, bg=BG, height=34)
        bar.pack(fill="x", padx=14, pady=(4, 10))

        self._status = tk.StringVar(value="  ·  ready")
        tk.Label(bar, textvariable=self._status, font=(MONO, 8),
                 fg=MUTED, bg=BG, anchor="w").pack(side="left", fill="x", expand=True)

        # action buttons
        for lbl, cmd in [("CLEAR", self._clear), ("COPY", self._copy)]:
            b = tk.Button(bar, text=lbl, font=(MONO, 8, "bold"),
                          fg=ACCENT_MID, bg=BG,
                          activebackground=GHOST, activeforeground=ACCENT,
                          relief="flat", bd=0, padx=10, pady=4,
                          cursor="hand2",
                          highlightthickness=1, highlightbackground=ACCENT_DIM,
                          command=cmd)
            b.pack(side="right", padx=(6, 0))

    # ── arrow button on canvas ────────────────────────────────────

    def _draw_arrow_btn(self, idle: bool):
        cv = self._arrow_cv
        cv.delete("all")
        outline = ACCENT if not idle else ACCENT_DIM
        fill_bg = ACCENT_LO if not idle else GHOST
        # circle
        cv.create_oval(2, 2, 42, 42, fill=fill_bg, outline=outline, width=1)
        # arrow symbol
        sym = "→" if self._mode == 0 else "←"
        cv.create_text(22, 22, text=sym,
                       font=(MONO, 14, "bold"),
                       fill=ACCENT if not idle else ACCENT_MID)

    # ── logic ─────────────────────────────────────────────────────

    def _translate(self, _e=None):
        raw = self._inp.get()
        if not raw.strip():
            self._out.clear()
            self._status.set("  ·  ready")
            return
        if self._mode == 0:
            result = text_to_binary(raw)
            bits   = len(result.replace(" ", ""))
            self._status.set(f"  ·  {len(raw)} chars  →  {bits} bits")
        else:
            result = binary_to_text(raw)
            self._status.set(f"  ·  decoded  →  {len(result)} chars")
        self._out.set(result)

    def _on_mode_change(self, mode: int):
        self._mode = mode
        self._draw_arrow_btn(idle=True)
        self._translate()

    def _swap_contents(self, _e=None):
        # swap input ↔ output, flip mode
        old_out = self._out.get()
        self._inp.clear()
        self._inp.text.insert("1.0", old_out)
        self._inp._update_counter()
        self._pill._click()          # flip pill (triggers _on_mode_change)

    def _clear(self):
        self._inp.clear()
        self._out.clear()
        self._status.set("  ·  cleared")

    def _copy(self):
        txt = self._out.get()
        if txt.strip():
            self.clipboard_clear()
            self.clipboard_append(txt)
            self._status.set("  ·  copied to clipboard")
            self.after(2000, lambda: self._status.set("  ·  ready"))
        else:
            self._status.set("  ·  nothing to copy")

    def _center(self, w, h):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")


# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = ZeroOneTranslator()
    app.mainloop()
