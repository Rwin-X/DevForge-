"""Theme and minimal widget kit for NET+ LAB (Tkinter / ttk, stdlib only).

Design language: monochrome, hairline borders, one oversized display headline, tiny uppercase
eyebrow labels. No hue anywhere: every colour derives from the --bg / --fg pair."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

PALETTES = {
    "dark": dict(bg="#0a0a0a", fg="#f2f2f0", mut="#8a8a82", line="#252525", card="#111111", soft="#181818"),
    "light": dict(bg="#f6f6f4", fg="#0c0c0c", mut="#76766f", line="#d9d9d5", card="#ffffff", soft="#ecece8"),
}


def _rgb(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def mix(a: str, b: str, t: float) -> str:
    """`a` at opacity t over `b` (canvas has no alpha, so we blend by hand)."""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x * t + y * (1 - t)) for x, y in zip(ra, rb))


SIZES = {
    "display": (44, "bold"), "h2": (18, "bold"), "h3": (12, "bold"), "body": (11, "normal"),
    "small": (10, "normal"), "lab": (9, "bold"), "stat": (26, "normal"),
    "mono": (11, "normal"), "monos": (10, "normal"), "monob": (11, "bold"),
}


class _Theme:
    name = "dark"
    c = PALETTES["dark"]
    sans = "Helvetica"
    mono = "Courier"

    def set(self, name: str) -> None:
        self.name, self.c = name, PALETTES[name]

    def __getitem__(self, k: str) -> str:
        return self.c[k]

    def dim(self, t: float) -> str:
        return mix(self.c["fg"], self.c["bg"], t)

    def font(self, kind: str):
        size, weight = SIZES[kind]
        fam = self.mono if kind.startswith("mono") else self.sans
        return (fam, size, weight)


T = _Theme()
_flash = lambda msg: None  # noqa: E731  (replaced by the app)


def set_flash(fn) -> None:
    global _flash
    _flash = fn


def flash(msg: str) -> None:
    _flash(msg)


def init_fonts(root: tk.Misc) -> None:
    fams = {f.lower(): f for f in tkfont.families(root)}
    for cand in ("Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Noto Sans",
                 "DejaVu Sans", "Arial", "Helvetica"):
        if cand.lower() in fams:
            T.sans = fams[cand.lower()]
            break
    for cand in ("JetBrains Mono", "Cascadia Mono", "Consolas", "SF Mono", "Menlo", "DejaVu Sans Mono",
                 "Liberation Mono", "Courier New"):
        if cand.lower() in fams:
            T.mono = fams[cand.lower()]
            break


def apply_style(root: tk.Tk) -> None:
    c = T.c
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure("Treeview", background=c["card"], fieldbackground=c["card"], foreground=c["fg"], borderwidth=0,
                 rowheight=28, font=(T.sans, 10), relief="flat")
    st.configure("Treeview.Heading", background=c["bg"], foreground=c["mut"], font=(T.sans, 9, "bold"),
                 relief="flat", borderwidth=0, padding=(8, 7), bordercolor=c["line"], lightcolor=c["bg"],
                 darkcolor=c["bg"])
    st.map("Treeview", background=[("selected", c["fg"])], foreground=[("selected", c["bg"])])
    st.map("Treeview.Heading", background=[("active", c["soft"])])
    st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    st.configure("M.TCombobox", fieldbackground=c["card"], background=c["card"], foreground=c["fg"],
                 arrowcolor=c["fg"], bordercolor=c["line"], lightcolor=c["line"], darkcolor=c["line"],
                 selectbackground=c["card"], selectforeground=c["fg"], padding=5)
    st.map("M.TCombobox", fieldbackground=[("readonly", c["card"])], foreground=[("readonly", c["fg"])],
           bordercolor=[("focus", c["fg"])], selectbackground=[("readonly", c["card"])],
           selectforeground=[("readonly", c["fg"])], background=[("active", c["card"])])
    for orient in ("Vertical", "Horizontal"):
        st.configure(f"M.{orient}.TScrollbar", troughcolor=c["bg"], background=c["line"], bordercolor=c["bg"],
                     arrowcolor=c["line"], lightcolor=c["line"], darkcolor=c["line"], gripcount=0, arrowsize=8)
        st.map(f"M.{orient}.TScrollbar", background=[("active", c["mut"])], arrowcolor=[("active", c["mut"])])
    root.option_add("*TCombobox*Listbox.background", c["card"])
    root.option_add("*TCombobox*Listbox.foreground", c["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", c["fg"])
    root.option_add("*TCombobox*Listbox.selectForeground", c["bg"])
    root.option_add("*TCombobox*Listbox.font", (T.sans, 10))
    root.configure(bg=c["bg"])


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------
def _bg(parent) -> str:
    try:
        return parent.cget("bg")
    except tk.TclError:
        return T["bg"]


def label(parent, text="", kind="body", fg=None, bg=None, **kw) -> tk.Label:
    if kind == "lab":
        text = text.upper()
    color = fg or (T["mut"] if kind in ("lab", "small") else T["fg"])
    return tk.Label(parent, text=text, font=T.font(kind), fg=color, bg=bg or _bg(parent),
                    anchor=kw.pop("anchor", "w"), justify=kw.pop("justify", "left"), **kw)


def wrap(lbl: tk.Label, pad: int = 0) -> tk.Label:
    """Keep a label's wraplength in sync with its parent's width."""
    parent = lbl.nametowidget(lbl.winfo_parent())
    parent.bind("<Configure>", lambda e: lbl.configure(wraplength=max(160, e.width - pad)), add="+")
    return lbl


def hairline(parent, color=None, pady=0) -> tk.Frame:
    f = tk.Frame(parent, height=1, bg=color or T["line"])
    f.pack(fill="x", pady=pady)
    return f


def card(parent, **kw) -> tk.Frame:
    return tk.Frame(parent, bg=T["card"], highlightthickness=1, highlightbackground=T["line"], **kw)


class Btn(tk.Frame):
    def __init__(self, parent, text, command, solid=False, padx=14, pady=6):
        super().__init__(parent, bg=_bg(parent), highlightthickness=1,
                         highlightbackground=T["fg"] if solid else T["line"])
        self.command, self.solid, self.enabled = command, solid, True
        self.lbl = tk.Label(self, text=text, font=(T.sans, 10, "bold" if solid else "normal"),
                            fg=T["bg"] if solid else T["fg"], bg=T["fg"] if solid else _bg(parent),
                            padx=padx, pady=pady, cursor="hand2")
        self.lbl.pack()
        for w in (self, self.lbl):
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", self._click)

    def _enter(self, _e):
        if self.enabled:
            self.configure(highlightbackground=T["fg"])

    def _leave(self, _e):
        self.configure(highlightbackground=T["fg"] if self.solid else T["line"])

    def _click(self, _e):
        if self.enabled and self.command:
            self.command()

    def set_text(self, text: str) -> None:
        self.lbl.configure(text=text)

    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        self.lbl.configure(fg=(T["bg"] if self.solid else T["fg"]) if on else T["mut"],
                           cursor="hand2" if on else "arrow")


def entry(parent, var=None, width=24, mono=True, **kw) -> tk.Entry:
    e = tk.Entry(parent, textvariable=var, width=width, font=T.font("mono" if mono else "body"),
                 bg=T["card"], fg=T["fg"], insertbackground=T["fg"], relief="flat", highlightthickness=1,
                 highlightbackground=T["line"], highlightcolor=T["fg"], selectbackground=T["fg"],
                 selectforeground=T["bg"], disabledbackground=T["soft"], **kw)
    return e


def combo(parent, values, var, width=14) -> ttk.Combobox:
    cb = ttk.Combobox(parent, values=list(values), textvariable=var, width=width, state="readonly",
                      style="M.TCombobox", font=(T.sans, 10))
    cb.bind("<<ComboboxSelected>>", lambda e: cb.selection_clear(), add="+")
    return cb


def check(parent, text, var, command=None) -> tk.Checkbutton:
    return tk.Checkbutton(parent, text=text, variable=var, command=command, font=(T.sans, 10), fg=T["fg"],
                          bg=_bg(parent), activebackground=_bg(parent), activeforeground=T["fg"],
                          selectcolor=T["card"], highlightthickness=0, bd=0, cursor="hand2")


class Slider(tk.Canvas):
    """Monochrome slider (tk.Scale paints its handle with the widget background, which vanishes on a flat theme)."""

    def __init__(self, parent, var, lo, hi, command=None, length=220):
        super().__init__(parent, width=length, height=24, bg=_bg(parent), highlightthickness=0, cursor="hand2")
        self.var, self.lo, self.hi, self.command, self.length = var, lo, hi, command, length
        self.integer = isinstance(var, tk.IntVar)
        self._tr = var.trace_add("write", lambda *a: self._draw())
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Destroy>", lambda e: self._cleanup())
        self._draw()

    def _cleanup(self) -> None:
        try:
            self.var.trace_remove("write", self._tr)
        except (tk.TclError, ValueError):
            pass

    def _x(self) -> float:
        try:
            v = float(self.var.get())
        except (tk.TclError, ValueError):
            v = self.lo
        return 8 + (min(max(v, self.lo), self.hi) - self.lo) / (self.hi - self.lo) * (self.length - 16)

    def _draw(self) -> None:
        self.delete("all")
        x = self._x()
        self.create_line(8, 12, self.length - 8, 12, fill=T["line"], width=2)
        self.create_line(8, 12, x, 12, fill=T["fg"], width=2)
        self.create_rectangle(x - 5, 5, x + 5, 19, fill=T["fg"], outline=T["bg"])

    def _drag(self, e) -> None:
        frac = min(max((e.x - 8) / max(self.length - 16, 1), 0.0), 1.0)
        v = self.lo + frac * (self.hi - self.lo)
        if self.integer:
            v = int(round(v))
        if float(self.var.get()) != v:
            self.var.set(v)
            if self.command:
                self.command(v)


def scale(parent, var, lo, hi, command=None, length=220) -> Slider:
    return Slider(parent, var, lo, hi, command, length)


class Seg(tk.Frame):
    """Segmented single-choice control."""

    def __init__(self, parent, options, command=None, value=None):
        super().__init__(parent, bg=_bg(parent), highlightthickness=1, highlightbackground=T["line"])
        self.command, self.cells, self.value = command, {}, None
        for key, text in options:
            lb = tk.Label(self, text=text, font=(T.sans, 10), padx=12, pady=5, cursor="hand2",
                          bg=T["card"], fg=T["fg"])
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, k=key: self.set(k))
            self.cells[key] = lb
        self.set(value if value is not None else options[0][0], fire=False)

    def set(self, key, fire=True) -> None:
        self.value = key
        for k, lb in self.cells.items():
            on = k == key
            lb.configure(bg=T["fg"] if on else T["card"], fg=T["bg"] if on else T["fg"],
                         font=(T.sans, 10, "bold" if on else "normal"))
        if fire and self.command:
            self.command(key)

    def get(self):
        return self.value


class Tabs(tk.Frame):
    """Underline tab bar; `add(key, text)` returns the content frame."""

    def __init__(self, parent, on_change=None):
        bg = _bg(parent)
        super().__init__(parent, bg=bg)
        self.on_change, self.items, self.cur = on_change, {}, None
        self.bar = tk.Frame(self, bg=bg)
        self.bar.pack(fill="x")
        hairline(self)
        self.holder = tk.Frame(self, bg=bg)
        self.holder.pack(fill="both", expand=True, pady=(18, 0))

    def add(self, key, text) -> tk.Frame:
        bg = _bg(self)
        frame = tk.Frame(self.holder, bg=bg)
        cell = tk.Frame(self.bar, bg=bg, cursor="hand2")
        cell.pack(side="left", padx=(0, 24))
        lb = label(cell, text, "lab")
        lb.pack(pady=(0, 7))
        ul = tk.Frame(cell, height=2, bg=bg)
        ul.pack(fill="x")
        for w in (cell, lb, ul):
            w.bind("<Button-1>", lambda e, k=key: self.select(k))
        self.items[key] = (frame, lb, ul)
        if self.cur is None:
            self.select(key)
        return frame

    def select(self, key) -> None:
        if self.cur == key:
            return
        if self.cur is not None:
            f, lb, ul = self.items[self.cur]
            f.pack_forget()
            lb.configure(fg=T["mut"])
            ul.configure(bg=_bg(self))
        f, lb, ul = self.items[key]
        f.pack(fill="both", expand=True)
        lb.configure(fg=T["fg"])
        ul.configure(bg=T["fg"])
        self.cur = key
        if self.on_change:
            self.on_change(key)


class ScrollFrame(tk.Frame):
    """Vertically scrolling container. Put children into `.inner`."""

    def __init__(self, parent):
        super().__init__(parent, bg=_bg(parent))
        self.canvas = tk.Canvas(self, bg=_bg(parent), highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="M.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=_bg(parent))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.canvas._wheel_target = self.canvas

    def _on_scroll(self, lo, hi):
        self.vsb.set(lo, hi)
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.vsb.pack_forget()
        elif not self.vsb.winfo_ismapped():
            self.vsb.pack(side="right", fill="y", before=self.canvas)

    def to_top(self):
        self.canvas.yview_moveto(0)


def install_wheel(root: tk.Tk) -> None:
    """One global wheel handler: scroll the nearest scrollable ancestor."""

    def handler(e):
        try:
            w = root.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        while w is not None:
            if isinstance(w, (tk.Text, ttk.Treeview, tk.Listbox, ttk.Combobox)):
                return
            tgt = getattr(w, "_wheel_target", None)
            if tgt is not None:
                if e.num == 4 or getattr(e, "delta", 0) > 0:
                    tgt.yview_scroll(-3, "units")
                else:
                    tgt.yview_scroll(3, "units")
                return
            w = w.master

    root.bind_all("<MouseWheel>", handler)
    root.bind_all("<Button-4>", handler)
    root.bind_all("<Button-5>", handler)


class TextBox(tk.Frame):
    """Read-only text area with scrollbar and a few monochrome tags."""

    def __init__(self, parent, height=10, mono=True, wrap_mode="word"):
        super().__init__(parent, bg=T["card"], highlightthickness=1, highlightbackground=T["line"])
        self.text = tk.Text(self, height=height, wrap=wrap_mode, font=T.font("monos" if mono else "body"),
                            bg=T["card"], fg=T["fg"], relief="flat", bd=0, padx=12, pady=10,
                            insertbackground=T["fg"], selectbackground=T["fg"], selectforeground=T["bg"],
                            highlightthickness=0, spacing1=1, spacing3=1, state="disabled")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview, style="M.Vertical.TScrollbar")
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure("b", font=(T.mono if mono else T.sans, SIZES["monos"][0], "bold"))
        self.text.tag_configure("m", foreground=T["mut"])
        self.text.tag_configure("h", font=(T.sans, 12, "bold"), spacing1=6)

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def add(self, s: str, tag: str | None = None) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", s, tag or ())
        self.text.configure(state="disabled")
        self.text.see("end")

    def set(self, s: str) -> None:
        self.clear()
        self.add(s)
        self.text.see("1.0")


class InputText(tk.Frame):
    """Editable multi-line input in the same style."""

    def __init__(self, parent, height=6, width=40):
        super().__init__(parent, bg=T["card"], highlightthickness=1, highlightbackground=T["line"])
        self.text = tk.Text(self, height=height, width=width, wrap="none", font=T.font("mono"), bg=T["card"],
                            fg=T["fg"], relief="flat", bd=0, padx=10, pady=8, insertbackground=T["fg"],
                            selectbackground=T["fg"], selectforeground=T["bg"], highlightthickness=0, undo=True)
        self.text.pack(fill="both", expand=True)
        self.text.bind("<FocusIn>", lambda e: self.configure(highlightbackground=T["fg"]))
        self.text.bind("<FocusOut>", lambda e: self.configure(highlightbackground=T["line"]))

    def get(self) -> str:
        return self.text.get("1.0", "end").strip("\n")

    def set(self, s: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", s)


class KV(tk.Frame):
    """Label / value grid with hairline separators. Click a value to copy it."""

    def __init__(self, parent, label_w=170, wrap_px=620):
        super().__init__(parent, bg=_bg(parent))
        self.label_w, self.wrap_px = label_w, wrap_px
        self.values: list[tk.Label] = []
        self.columnconfigure(1, weight=1)
        self.bind("<Configure>", self._rewrap)

    def _rewrap(self, e) -> None:
        px = max(180, e.width - self.label_w - 30)
        for v in self.values:
            v.configure(wraplength=px)

    def set(self, rows) -> None:
        for w in self.winfo_children():
            w.destroy()
        self.values = []
        r = 0
        for k, v in rows:
            if k == "##":
                label(self, v, "lab").grid(row=r, column=0, columnspan=2, sticky="w", pady=(16, 6))
                r += 1
                continue
            tk.Frame(self, height=1, bg=T["line"]).grid(row=r, column=0, columnspan=2, sticky="ew")
            r += 1
            label(self, k, "small", width=0).grid(row=r, column=0, sticky="nw", padx=(0, 18), pady=6)
            self.grid_columnconfigure(0, minsize=self.label_w)
            val = label(self, str(v), "mono", wraplength=max(180, (self.winfo_width() or self.wrap_px + self.label_w) - self.label_w - 30),
                        cursor="hand2")
            val.grid(row=r, column=1, sticky="nw", pady=5)
            self.values.append(val)
            val.bind("<Button-1>", lambda e, s=str(v): self._copy(s))
            r += 1
        tk.Frame(self, height=1, bg=T["line"]).grid(row=r, column=0, columnspan=2, sticky="ew")

    def _copy(self, s: str) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(s)
            flash(f"Copied  {s[:60]}")
        except tk.TclError:
            pass


class Table(tk.Frame):
    """Treeview wrapper: filtering plus a full-text detail strip for the selected row."""

    def __init__(self, parent, columns, widths=None, rows=(), height=10, detail=True, stretch=None):
        super().__init__(parent, bg=_bg(parent))
        self.columns, self.all_rows, self.detail_on = list(columns), [], detail
        box = tk.Frame(self, bg=T["card"], highlightthickness=1, highlightbackground=T["line"])
        box.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(box, columns=self.columns, show="headings", height=height, selectmode="browse")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview, style="M.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        widths = widths or [140] * len(self.columns)
        stretch = len(self.columns) - 1 if stretch is None else stretch
        for i, (c, w) in enumerate(zip(self.columns, widths)):
            self.tree.heading(c, text=c.upper(), anchor="w")
            self.tree.column(c, width=w, minwidth=40, anchor="w", stretch=(i == stretch))
        self.tree.tag_configure("odd", background=T["card"])
        self.tree.tag_configure("even", background=T["soft"])
        self.detail = None
        if detail:
            self.detail = label(self, "Select a row for the full text.", "small", wraplength=900)
            self.detail.pack(fill="x", pady=(10, 0))
            wrap(self.detail)
            self.tree.bind("<<TreeviewSelect>>", self._select)
        self.set_rows(rows)

    def set_rows(self, rows) -> None:
        self.all_rows = [tuple(map(str, r)) for r in rows]
        self._fill(self.all_rows)

    def _fill(self, rows) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            self.tree.insert("", "end", values=r, tags=("even" if i % 2 else "odd",))

    def filter(self, text: str, extra=None) -> int:
        t = text.strip().lower()
        rows = [r for r in self.all_rows if (not t or any(t in c.lower() for c in r)) and (extra is None or extra(r))]
        self._fill(rows)
        return len(rows)

    def _select(self, _e=None) -> None:
        sel = self.tree.selection()
        if not sel or self.detail is None:
            return
        vals = self.tree.item(sel[0], "values")
        self.detail.configure(text="   ·   ".join(f"{c}: {v}" for c, v in zip(self.columns, vals) if v and v != "-"),
                              fg=T["fg"])


class ToolPanel(tk.Frame):
    """Generic live calculator: labelled inputs on the left, KV results below. Recomputes as you type."""

    def __init__(self, parent, inputs, fn, intro="", button=None, live=True):
        super().__init__(parent, bg=_bg(parent))
        self.fn, self.vars, self.live = fn, {}, live
        if intro:
            lb = label(self, intro, "small")
            lb.pack(fill="x", pady=(0, 14))
            wrap(lb)
        form = tk.Frame(self, bg=_bg(self))
        form.pack(fill="x")
        for i, spec in enumerate(inputs):
            var = tk.StringVar(value=str(spec.get("default", "")))
            self.vars[spec["key"]] = var
            cell = tk.Frame(form, bg=_bg(self))
            cell.grid(row=0, column=i, sticky="nw", padx=(0, 18), pady=(0, 6))
            label(cell, spec["label"], "lab").pack(anchor="w", pady=(0, 4))
            if spec.get("choices"):
                w = combo(cell, spec["choices"], var, width=spec.get("width", 12))
            else:
                w = entry(cell, var, width=spec.get("width", 24))
                w.bind("<Return>", lambda e: self.run())
            w.pack(anchor="w", ipady=3)
            if live:
                var.trace_add("write", lambda *a: self._soon())
        if button:
            Btn(form, button, self.run, solid=True).grid(row=0, column=len(inputs), sticky="sw", pady=(0, 6))
        self.err = label(self, "", "small")
        self.err.pack(fill="x", pady=(10, 0))
        self.kv = KV(self)
        self.kv.pack(fill="x", pady=(6, 0))
        self._job = None
        self.after(30, self.run)

    def _soon(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(180, self.run)

    def values(self) -> dict:
        return {k: v.get() for k, v in self.vars.items()}

    def run(self) -> None:
        self._job = None
        try:
            rows = self.fn(self.values())
        except Exception as e:  # NetError and parse errors alike
            self.err.configure(text=f"—  {e}", fg=T["fg"])
            self.kv.set([])
            return
        self.err.configure(text="")
        self.kv.set(rows)


class Backdrop(tk.Canvas):
    """Lightweight ambient network graph: drifting nodes, faint links, packets travelling along links.
    ~30 fps, a few dozen items, redraw only while visible."""

    def __init__(self, parent, height=230, nodes=26):
        super().__init__(parent, height=height, bg=_bg(parent), highlightthickness=1,
                         highlightbackground=T["line"], bd=0)
        import random
        self.rnd = random.Random(7)
        self.n = nodes
        self.pts = []
        self.packets = []
        self.job = None
        self.running = False
        self.bind("<Configure>", self._resize)
        self.w = self.h = 1

    def _resize(self, e) -> None:
        self.w, self.h = max(e.width, 2), max(e.height, 2)
        if not self.pts:
            self.pts = [[self.rnd.random() * self.w, self.rnd.random() * self.h,
                         (self.rnd.random() - .5) * .35, (self.rnd.random() - .5) * .35] for _ in range(self.n)]

    def start(self) -> None:
        if not self.running:
            self.running = True
            self._tick()

    def stop(self) -> None:
        self.running = False
        if self.job:
            try:
                self.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None

    def _tick(self) -> None:
        if not self.running or not self.winfo_exists():
            return
        w, h = self.w, self.h
        for p in self.pts:
            p[0] += p[2]
            p[1] += p[3]
            if p[0] < 0 or p[0] > w:
                p[2] *= -1
            if p[1] < 0 or p[1] > h:
                p[3] *= -1
        self.delete("all")
        links = []
        R = 150
        for i in range(len(self.pts)):
            for j in range(i + 1, len(self.pts)):
                a, b = self.pts[i], self.pts[j]
                d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5
                if d < R:
                    links.append((i, j, d))
                    self.create_line(a[0], a[1], b[0], b[1], fill=T.dim(.04 + .22 * (1 - d / R)))
        if links and len(self.packets) < 5 and self.rnd.random() < .06:
            i, j, _ = self.rnd.choice(links)
            self.packets.append([i, j, 0.0])
        keep = []
        for pk in self.packets:
            pk[2] += .018
            if pk[2] < 1:
                a, b = self.pts[pk[0]], self.pts[pk[1]]
                x, y = a[0] + (b[0] - a[0]) * pk[2], a[1] + (b[1] - a[1]) * pk[2]
                self.create_rectangle(x - 2, y - 2, x + 2, y + 2, fill=T["fg"], outline="")
                keep.append(pk)
        self.packets = keep
        for p in self.pts:
            self.create_oval(p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2, fill=T.dim(.55), outline="")
        self.job = self.after(33, self._tick)
