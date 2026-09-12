"""ui/entry_dialog.py — Add/edit dialog for a single vault entry."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ..models import new_entry, update_entry, DEFAULT_CATEGORIES
from ..password_utils import generate_password, estimate_strength
from ..theme import Palette
from .widgets import StrengthMeter, Tag


class EntryDialog(tk.Toplevel):
    def __init__(self, parent, on_save, entry: dict | None = None, known_categories=None, known_tags=None):
        super().__init__(parent)
        self.on_save = on_save
        self.entry = entry or {}
        self.known_categories = known_categories or DEFAULT_CATEGORIES
        self.known_tags = known_tags or []
        self.tags: list[str] = list(self.entry.get("tags", []))

        self.title("Edit Entry" if entry else "New Entry")
        self.configure(bg=Palette.surface)
        self.geometry("440x640")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        def make_label(text):
            tk.Label(
                self, text=text, font=(Palette.font_family, 9, "bold"),
                fg=Palette.text_dim, bg=Palette.surface, anchor="w",
            ).pack(fill="x", padx=24, pady=(14, 2))

        def make_entry(var, show=None):
            e = tk.Entry(
                self, textvariable=var, show=show,
                font=(Palette.font_family, 12),
                bg=Palette.surface_alt, fg=Palette.text,
                insertbackground=Palette.text, relief="flat",
            )
            e.pack(fill="x", padx=24, ipady=8)
            return e

        self.name_var = tk.StringVar(value=self.entry.get("name", ""))
        self.username_var = tk.StringVar(value=self.entry.get("username", ""))
        self.password_var = tk.StringVar(value=self.entry.get("password", ""))
        self.url_var = tk.StringVar(value=self.entry.get("url", ""))
        self.category_var = tk.StringVar(value=self.entry.get("category", "General"))

        make_label("Name")
        name_entry = make_entry(self.name_var)
        name_entry.focus_set()

        make_label("Category")
        category_combo = ttk.Combobox(
            self, textvariable=self.category_var,
            values=self.known_categories, font=(Palette.font_family, 11),
        )
        category_combo.pack(fill="x", padx=24, ipady=4)

        make_label("Tags")
        tags_row = tk.Frame(self, bg=Palette.surface)
        tags_row.pack(fill="x", padx=24)

        self.tag_input_var = tk.StringVar()
        tag_entry = tk.Entry(
            tags_row, textvariable=self.tag_input_var,
            font=(Palette.font_family, 11),
            bg=Palette.surface_alt, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
        )
        tag_entry.pack(side="left", fill="x", expand=True, ipady=6)
        tag_entry.bind("<Return>", lambda e: self._add_tag())

        tk.Button(
            tags_row, text="Add", font=(Palette.font_family, 9),
            bg=Palette.surface_alt, fg=Palette.accent, relief="flat",
            cursor="hand2", command=self._add_tag,
        ).pack(side="left", padx=(6, 0))

        self.tags_container = tk.Frame(self, bg=Palette.surface)
        self.tags_container.pack(fill="x", padx=24, pady=(6, 0))
        self._render_tags()

        make_label("Username / Email")
        make_entry(self.username_var)

        make_label("Password")
        pw_row = tk.Frame(self, bg=Palette.surface)
        pw_row.pack(fill="x", padx=24)
        self.show_pw = False
        self.pw_entry = tk.Entry(
            pw_row, textvariable=self.password_var, show="•",
            font=(Palette.font_family, 12),
            bg=Palette.surface_alt, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
        )
        self.pw_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.password_var.trace_add("write", lambda *a: self._update_strength())

        tk.Button(
            pw_row, text="👁", font=(Palette.font_family, 10),
            bg=Palette.surface_alt, fg=Palette.text_dim, relief="flat",
            cursor="hand2", command=self.toggle_pw, width=3,
        ).pack(side="left", padx=(6, 0), fill="y")

        tk.Button(
            pw_row, text="⟳", font=(Palette.font_family, 10),
            bg=Palette.surface_alt, fg=Palette.accent, relief="flat",
            cursor="hand2", command=self.generate, width=3,
        ).pack(side="left", padx=(6, 0), fill="y")

        self.strength_meter = StrengthMeter(self)
        self.strength_meter.pack(fill="x", padx=24, pady=(4, 0))
        self._update_strength()

        make_label("Website / URL")
        make_entry(self.url_var)

        make_label("Notes")
        notes_frame = tk.Frame(self, bg=Palette.surface_alt)
        notes_frame.pack(fill="both", expand=True, padx=24, pady=(0, 4))
        self.notes_text = tk.Text(
            notes_frame, font=(Palette.font_family, 11),
            bg=Palette.surface_alt, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
            height=4, wrap="word", padx=8, pady=8,
        )
        self.notes_text.pack(fill="both", expand=True)
        self.notes_text.insert("1.0", self.entry.get("notes", ""))

        btn_row = tk.Frame(self, bg=Palette.surface)
        btn_row.pack(fill="x", padx=24, pady=16)

        tk.Button(
            btn_row, text="Cancel", font=(Palette.font_family, 10),
            bg=Palette.surface, fg=Palette.text_dim, relief="flat",
            cursor="hand2", command=self.destroy,
        ).pack(side="left")

        tk.Button(
            btn_row, text="Save", font=(Palette.font_family, 10, "bold"),
            bg=Palette.accent, fg="#0f1115", relief="flat",
            cursor="hand2", command=self.save, width=12, pady=6,
        ).pack(side="right")

    # ---- tags ----

    def _add_tag(self) -> None:
        val = self.tag_input_var.get().strip()
        if val and val not in self.tags:
            self.tags.append(val)
            self.tag_input_var.set("")
            self._render_tags()

    def _remove_tag(self, tag: str) -> None:
        self.tags = [t for t in self.tags if t != tag]
        self._render_tags()

    def _render_tags(self) -> None:
        for w in self.tags_container.winfo_children():
            w.destroy()
        for tag in self.tags:
            chip = Tag(self.tags_container, tag, on_remove=lambda t=tag: self._remove_tag(t))
            chip.pack(side="left", padx=(0, 6), pady=(0, 6))

    # ---- password ----

    def toggle_pw(self) -> None:
        self.show_pw = not self.show_pw
        self.pw_entry.config(show="" if self.show_pw else "•")

    def generate(self) -> None:
        self.password_var.set(generate_password())
        self.show_pw = True
        self.pw_entry.config(show="")

    def _update_strength(self) -> None:
        result = estimate_strength(self.password_var.get())
        self.strength_meter.update_strength(result)

    # ---- save ----

    def save(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Please give this entry a name.")
            return

        fields = dict(
            name=name,
            username=self.username_var.get().strip(),
            password=self.password_var.get(),
            url=self.url_var.get().strip(),
            notes=self.notes_text.get("1.0", "end-1c").strip(),
            category=self.category_var.get().strip() or "General",
            tags=self.tags,
        )

        if self.entry:
            result = update_entry(self.entry, **fields)
        else:
            result = new_entry(**fields)

        self.on_save(result)
        self.destroy()
