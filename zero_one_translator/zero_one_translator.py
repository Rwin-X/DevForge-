import tkinter as tk
from tkinter import ttk
import threading
import time

# ─── Color Palette ──────────────────────────────────────────────────────────
BG         = "#000000"
SURFACE    = "#080808"
PANEL      = "#0a0a0a"
BORDER     = "#1a2e1a"
GREEN      = "#00ff41"
GREEN_DIM  = "#005514"
GREEN_DARK = "#002208"
GREEN_MID  = "#00aa2a"
TEXT_DIM   = "#3a5c3a"
WHITE      = "#e8ffe8"

FONT_MONO  = ("Courier New", 11)
FONT_MONO_LG = ("Courier New", 13)
FONT_MONO_SM = ("Courier New", 9)
FONT_TITLE = ("Courier New", 16, "bold")
FONT_LABEL = ("Courier New", 9)

MODE_TEXT_TO_BIN = "text → binary"
MODE_BIN_TO_TEXT = "binary → text"


class ZeroOneTranslator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZERO-ONE TRANSLATOR")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(640, 460)

        self.mode = tk.StringVar(value=MODE_TEXT_TO_BIN)
        self._animating = False

        self._build_ui()
        self._center_window(760, 520)

    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # ── outer frame with green border ──
        outer = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        inner = tk.Frame(outer, bg=BG)
        inner.pack(fill="both", expand=True)

        # ── header ──
        header = tk.Frame(inner, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 6))

        tk.Label(
            header, text="[ ZERO-ONE TRANSLATOR ]",
            font=FONT_TITLE, fg=GREEN, bg=BG
        ).pack(side="left")

        # version tag
        tk.Label(
            header, text="v1.0",
            font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG
        ).pack(side="right", pady=6)

        # ── thin separator ──
        tk.Frame(inner, bg=GREEN_DIM, height=1).pack(fill="x", padx=20)

        # ── mode bar ──
        mode_bar = tk.Frame(inner, bg=BG)
        mode_bar.pack(fill="x", padx=20, pady=(10, 4))

        tk.Label(
            mode_bar, text="MODE:", font=FONT_LABEL, fg=TEXT_DIM, bg=BG
        ).pack(side="left", padx=(0, 8))

        self.mode_label = tk.Label(
            mode_bar,
            textvariable=self.mode,
            font=("Courier New", 10, "bold"),
            fg=GREEN, bg=BG
        )
        self.mode_label.pack(side="left")

        # reverse toggle button
        self.toggle_btn = tk.Button(
            mode_bar,
            text="⇄  REVERSE",
            font=FONT_MONO_SM,
            fg=BG,
            bg=GREEN,
            activebackground=GREEN_MID,
            activeforeground=BG,
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._toggle_mode
        )
        self.toggle_btn.pack(side="right")

        # ── panels ──
        panels = tk.Frame(inner, bg=BG)
        panels.pack(fill="both", expand=True, padx=20, pady=(6, 0))
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(2, weight=1)
        panels.rowconfigure(0, weight=1)

        # input panel
        self.input_panel = self._build_panel(panels, "INPUT", editable=True)
        self.input_panel.grid(row=0, column=0, sticky="nsew")

        # center divider with arrow
        mid = tk.Frame(panels, bg=BG, width=48)
        mid.grid(row=0, column=1, sticky="ns", padx=4)

        self.arrow_label = tk.Label(
            mid, text="→", font=("Courier New", 20, "bold"),
            fg=GREEN_DIM, bg=BG
        )
        self.arrow_label.place(relx=0.5, rely=0.5, anchor="center")

        # output panel
        self.output_panel = self._build_panel(panels, "OUTPUT", editable=False)
        self.output_panel.grid(row=0, column=2, sticky="nsew")

        # store text widgets
        self.input_text  = self.input_panel._text
        self.output_text = self.output_panel._text

        # bind input changes
        self.input_text.bind("<KeyRelease>", self._on_type)

        # ── bottom bar ──
        tk.Frame(inner, bg=GREEN_DIM, height=1).pack(fill="x", padx=20, pady=(10, 0))

        bottom = tk.Frame(inner, bg=BG)
        bottom.pack(fill="x", padx=20, pady=(6, 14))

        self.status_var = tk.StringVar(value="ready.")
        tk.Label(
            bottom, textvariable=self.status_var,
            font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG
        ).pack(side="left")

        # action buttons
        btn_frame = tk.Frame(bottom, bg=BG)
        btn_frame.pack(side="right")

        self._ghost_btn(btn_frame, "CLEAR", self._clear).pack(side="left", padx=(0, 6))
        self._ghost_btn(btn_frame, "COPY OUTPUT", self._copy_output).pack(side="left")

    def _build_panel(self, parent, title: str, editable: bool) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL, bd=0)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # panel header
        hdr = tk.Frame(frame, bg=GREEN_DARK)
        hdr.grid(row=0, column=0, sticky="ew")

        tk.Label(
            hdr, text=f"  {title}",
            font=FONT_LABEL, fg=GREEN_MID, bg=GREEN_DARK,
            pady=5
        ).pack(side="left")

        # text widget
        txt = tk.Text(
            frame,
            font=FONT_MONO_LG,
            fg=GREEN,
            bg=SURFACE,
            insertbackground=GREEN,
            selectbackground=GREEN_DIM,
            selectforeground=WHITE,
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            wrap="word",
            state="normal" if editable else "disabled",
            highlightthickness=0,
            spacing3=2,
        )
        txt.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # scrollbar
        sb = tk.Scrollbar(frame, command=txt.yview, bg=BG, troughcolor=BG,
                          activebackground=GREEN_DIM, width=6, bd=0)
        sb.grid(row=1, column=1, sticky="ns")
        txt.configure(yscrollcommand=sb.set)

        frame._text = txt
        return frame

    def _ghost_btn(self, parent, label: str, cmd) -> tk.Button:
        return tk.Button(
            parent, text=label,
            font=FONT_MONO_SM,
            fg=GREEN_MID,
            bg=BG,
            activebackground=GREEN_DARK,
            activeforeground=GREEN,
            relief="flat",
            bd=0,
            padx=8, pady=3,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=GREEN_DIM,
            command=cmd
        )

    # ── Logic ────────────────────────────────────────────────────────────────

    def _on_type(self, event=None):
        raw = self.input_text.get("1.0", "end-1c")
        result = self._translate(raw)
        self._set_output(result)
        char_count = len(raw)
        self.status_var.set(f"chars: {char_count}  |  {self._mode_short()}")

    def _translate(self, text: str) -> str:
        if not text.strip():
            return ""
        if self.mode.get() == MODE_TEXT_TO_BIN:
            return self._text_to_binary(text)
        else:
            return self._binary_to_text(text)

    @staticmethod
    def _text_to_binary(text: str) -> str:
        parts = []
        for ch in text:
            parts.append(format(ord(ch), "08b"))
        return " ".join(parts)

    @staticmethod
    def _binary_to_text(binary: str) -> str:
        tokens = binary.strip().split()
        result = []
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue
            if all(c in "01" for c in tok) and len(tok) >= 1:
                try:
                    result.append(chr(int(tok, 2)))
                except ValueError:
                    result.append("?")
            else:
                result.append("?")
        return "".join(result)

    def _set_output(self, text: str):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.configure(state="disabled")

    def _toggle_mode(self):
        if self._animating:
            return

        # swap mode
        if self.mode.get() == MODE_TEXT_TO_BIN:
            self.mode.set(MODE_BIN_TO_TEXT)
        else:
            self.mode.set(MODE_TEXT_TO_BIN)

        # swap content
        old_output = self.output_text.get("1.0", "end-1c")
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", old_output)

        self._animate_arrow()
        self._on_type()

    def _animate_arrow(self):
        self._animating = True
        frames = ["←", "↔", "→", "↔", "←", "↔", "→"]
        delay = 60

        def step(i):
            if i < len(frames):
                self.arrow_label.configure(text=frames[i], fg=GREEN)
                self.after(delay, lambda: step(i + 1))
            else:
                self.arrow_label.configure(text="→", fg=GREEN_DIM)
                self._animating = False

        step(0)

    def _clear(self):
        self.input_text.delete("1.0", "end")
        self._set_output("")
        self.status_var.set("cleared.")

    def _copy_output(self):
        text = self.output_text.get("1.0", "end-1c")
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_var.set("output copied to clipboard.")
            self.after(1800, lambda: self.status_var.set("ready."))
        else:
            self.status_var.set("nothing to copy.")

    def _mode_short(self) -> str:
        if self.mode.get() == MODE_TEXT_TO_BIN:
            return "text → binary"
        return "binary → text"


if __name__ == "__main__":
    app = ZeroOneTranslator()
    app.mainloop()
