"""ui/widgets.py — Small reusable UI building blocks."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import Palette
from ..password_utils import StrengthResult


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable frame. Put widgets in `.inner`."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        canvas = tk.Canvas(self, bg=Palette.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def resize_inner(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", resize_inner)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class StrengthMeter(tk.Frame):
    """A small horizontal bar + label showing password strength."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Palette.surface, **kwargs)

        self.bar_bg = tk.Frame(self, bg=Palette.surface_alt, height=6)
        self.bar_bg.pack(fill="x", pady=(4, 2))

        self.bar_fill = tk.Frame(self.bar_bg, bg=Palette.strength_colors[0], height=6)
        self.bar_fill.place(relx=0, rely=0, relheight=1, relwidth=0)

        self.label = tk.Label(
            self, text="", font=(Palette.font_family, 8),
            fg=Palette.text_dim, bg=Palette.surface, anchor="w",
        )
        self.label.pack(fill="x")

    def update_strength(self, result: StrengthResult) -> None:
        fraction = (result.score + 1) / 5  # score 0..4 -> 0.2..1.0
        color = Palette.strength_colors[result.score]
        self.bar_fill.place(relx=0, rely=0, relheight=1, relwidth=fraction)
        self.bar_fill.config(bg=color)

        text = f"{result.label} · ~{result.entropy_bits:.0f} bits"
        if result.warnings:
            text += f" — {result.warnings[0]}"
        self.label.config(text=text, fg=color)

    def clear(self) -> None:
        self.bar_fill.place(relx=0, rely=0, relheight=1, relwidth=0)
        self.label.config(text="")


class Tag(tk.Frame):
    """A small rounded-looking pill for displaying a tag/category chip."""

    def __init__(self, parent, text: str, on_remove=None, **kwargs):
        super().__init__(parent, bg=Palette.surface_alt, **kwargs)
        pad_x = (8, 4) if on_remove else (8, 8)
        label = tk.Label(
            self, text=text, font=(Palette.font_family, 8),
            fg=Palette.text, bg=Palette.surface_alt,
        )
        label.pack(side="left", padx=pad_x, pady=3)

        if on_remove:
            close_btn = tk.Button(
                self, text="✕", font=(Palette.font_family, 7),
                fg=Palette.text_dim, bg=Palette.surface_alt,
                relief="flat", bd=0, cursor="hand2",
                command=on_remove,
            )
            close_btn.pack(side="left", padx=(0, 6))
