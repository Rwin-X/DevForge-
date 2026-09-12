"""ui/vault_screen.py — The main unlocked vault view."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from ..models import all_categories, all_tags
from ..password_utils import find_reused_passwords, find_weak_entries
from ..storage import VaultPaths, save_vault
from ..theme import Palette
from .entry_dialog import EntryDialog
from .change_master_dialog import ChangeMasterDialog
from .export_import_dialog import ExportDialog, ImportDialog
from .security_dashboard import SecurityDashboard
from .widgets import ScrollableFrame, Tag


class VaultScreen(tk.Frame):
    def __init__(self, master, paths: VaultPaths, fernet, master_password: str, entries: list):
        super().__init__(master, bg=Palette.bg)
        self.paths = paths
        self.fernet = fernet
        self.master_password = master_password
        self.entries = entries
        self.selected_id = None
        self.revealed = set()
        self.active_category = None  # None = "All"
        self.active_tag = None

        self.build_layout()
        self.refresh_list()

    # ---- layout ----

    def build_layout(self):
        top_bar = tk.Frame(self, bg=Palette.surface, height=56)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        tk.Label(
            top_bar, text="PassVault", font=(Palette.font_family, 15, "bold"),
            fg=Palette.text, bg=Palette.surface,
        ).pack(side="left", padx=20)

        tk.Button(
            top_bar, text="+  New Entry", font=(Palette.font_family, 10, "bold"),
            bg=Palette.accent, fg="#0f1115", relief="flat",
            cursor="hand2", command=self.new_entry, padx=14, pady=6,
        ).pack(side="right", padx=(0, 20))

        tk.Button(
            top_bar, text="⋮ Menu", font=(Palette.font_family, 10),
            bg=Palette.surface_alt, fg=Palette.text, relief="flat",
            cursor="hand2", command=self.open_menu, padx=12, pady=6,
        ).pack(side="right", padx=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_list())
        search_entry = tk.Entry(
            top_bar, textvariable=self.search_var,
            font=(Palette.font_family, 11),
            bg=Palette.surface_alt, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
            width=26,
        )
        search_entry.pack(side="right", padx=(0, 12), ipady=6)

        # Category filter bar
        filter_bar = tk.Frame(self, bg=Palette.bg)
        filter_bar.pack(fill="x", side="top", padx=20, pady=(10, 0))
        self.filter_bar = filter_bar

        body = tk.Frame(self, bg=Palette.bg)
        body.pack(fill="both", expand=True)

        list_panel = tk.Frame(body, bg=Palette.bg, width=280)
        list_panel.pack(side="left", fill="y")
        list_panel.pack_propagate(False)

        self.scroll_frame = ScrollableFrame(list_panel)
        self.scroll_frame.pack(fill="both", expand=True)

        divider = tk.Frame(body, bg=Palette.border, width=1)
        divider.pack(side="left", fill="y")

        self.detail_panel = tk.Frame(body, bg=Palette.bg)
        self.detail_panel.pack(side="left", fill="both", expand=True)

        self.show_empty_detail()
        self.render_filter_bar()

    def render_filter_bar(self):
        for w in self.filter_bar.winfo_children():
            w.destroy()

        categories = all_categories(self.entries)
        chip_bg_active = Palette.accent
        chip_fg_active = "#0f1115"

        def make_chip(label, is_active, on_click):
            chip = tk.Label(
                self.filter_bar, text=label, font=(Palette.font_family, 9),
                fg=chip_fg_active if is_active else Palette.text_dim,
                bg=chip_bg_active if is_active else Palette.surface_alt,
                padx=10, pady=4, cursor="hand2",
            )
            chip.pack(side="left", padx=(0, 6))
            chip.bind("<Button-1>", lambda e: on_click())

        make_chip("All", self.active_category is None, lambda: self.set_category(None))
        for cat in categories:
            make_chip(cat, self.active_category == cat, lambda c=cat: self.set_category(c))

    def set_category(self, category):
        self.active_category = category
        self.render_filter_bar()
        self.refresh_list()

    def show_empty_detail(self):
        for w in self.detail_panel.winfo_children():
            w.destroy()
        tk.Label(
            self.detail_panel, text="Select an entry or create a new one",
            font=(Palette.font_family, 11), fg=Palette.text_dim, bg=Palette.bg,
        ).place(relx=0.5, rely=0.5, anchor="center")

    # ---- menu ----

    def open_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=Palette.surface, fg=Palette.text,
                        activebackground=Palette.accent, activeforeground="#0f1115",
                        relief="flat", bd=0)
        menu.add_command(label="Security Check", command=self.open_security_dashboard)
        menu.add_separator()
        menu.add_command(label="Export…", command=self.open_export)
        menu.add_command(label="Import…", command=self.open_import)
        menu.add_separator()
        menu.add_command(label="Change Master Password…", command=self.open_change_password)

        try:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def open_security_dashboard(self):
        SecurityDashboard(self, self.entries, on_select_entry=self.select_entry)

    def open_export(self):
        ExportDialog(self, self.entries)

    def open_import(self):
        def handle_import(new_entries):
            self.entries.extend(new_entries)
            self.persist()
            self.render_filter_bar()
            self.refresh_list()

        ImportDialog(self, on_import=handle_import)

    def open_change_password(self):
        def handle_changed(new_fernet, new_password):
            self.fernet = new_fernet
            self.master_password = new_password

        ChangeMasterDialog(
            self, self.paths, self.fernet, self.master_password,
            self.entries, on_changed=handle_changed,
        )

    # ---- list ----

    def refresh_list(self):
        for w in self.scroll_frame.inner.winfo_children():
            w.destroy()

        query = self.search_var.get().lower().strip()
        weak_ids = set(find_weak_entries(self.entries))
        reused = find_reused_passwords(self.entries)
        reused_ids = {eid for ids in reused.values() for eid in ids}

        filtered = [
            e for e in self.entries
            if (query in e["name"].lower()
                or query in e.get("username", "").lower()
                or query in e.get("url", "").lower()
                or any(query in t.lower() for t in e.get("tags", [])))
            and (self.active_category is None or e.get("category") == self.active_category)
        ]
        filtered.sort(key=lambda e: e["name"].lower())

        if not filtered:
            empty_text = "No entries yet" if not query and not self.active_category else "No matches"
            tk.Label(
                self.scroll_frame.inner, text=empty_text,
                font=(Palette.font_family, 10), fg=Palette.text_dim, bg=Palette.bg,
            ).pack(pady=20)
            return

        for e in filtered:
            flags = []
            if e["id"] in weak_ids:
                flags.append("weak")
            if e["id"] in reused_ids:
                flags.append("reused")
            self.build_list_item(e, flags)

    def build_list_item(self, entry, flags):
        is_selected = entry["id"] == self.selected_id
        bg = Palette.surface_alt if is_selected else Palette.bg

        item = tk.Frame(self.scroll_frame.inner, bg=bg, cursor="hand2")
        item.pack(fill="x")

        inner = tk.Frame(item, bg=bg)
        inner.pack(fill="x", padx=16, pady=10)

        title_row = tk.Frame(inner, bg=bg)
        title_row.pack(fill="x")

        name_lbl = tk.Label(
            title_row, text=entry["name"], font=(Palette.font_family, 11, "bold"),
            fg=Palette.text, bg=bg, anchor="w",
        )
        name_lbl.pack(side="left")

        if flags:
            dot_color = Palette.danger if "reused" in flags else Palette.warning
            tk.Label(
                title_row, text="●", font=(Palette.font_family, 8),
                fg=dot_color, bg=bg,
            ).pack(side="right")

        sub = entry.get("username") or entry.get("url") or ""
        sub_lbl = tk.Label(
            inner, text=sub, font=(Palette.font_family, 9),
            fg=Palette.text_dim, bg=bg, anchor="w",
        )
        sub_lbl.pack(fill="x")

        cat_lbl = tk.Label(
            inner, text=entry.get("category", "General"), font=(Palette.font_family, 8),
            fg=Palette.accent, bg=bg, anchor="w",
        )
        cat_lbl.pack(fill="x", pady=(2, 0))

        sep = tk.Frame(self.scroll_frame.inner, bg=Palette.border, height=1)
        sep.pack(fill="x")

        for widget in (item, inner, name_lbl, sub_lbl, title_row, cat_lbl):
            widget.bind("<Button-1>", lambda e, eid=entry["id"]: self.select_entry(eid))

    # ---- detail ----

    def select_entry(self, entry_id):
        self.selected_id = entry_id
        self.refresh_list()
        entry = next((e for e in self.entries if e["id"] == entry_id), None)
        if not entry:
            self.show_empty_detail()
            return

        for w in self.detail_panel.winfo_children():
            w.destroy()

        wrapper = tk.Frame(self.detail_panel, bg=Palette.bg)
        wrapper.pack(fill="both", expand=True, padx=36, pady=28)

        header = tk.Frame(wrapper, bg=Palette.bg)
        header.pack(fill="x", pady=(0, 4))

        tk.Label(
            header, text=entry["name"], font=(Palette.font_family, 20, "bold"),
            fg=Palette.text, bg=Palette.bg, anchor="w",
        ).pack(side="left")

        actions = tk.Frame(header, bg=Palette.bg)
        actions.pack(side="right")

        tk.Button(
            actions, text="Edit", font=(Palette.font_family, 9),
            bg=Palette.surface_alt, fg=Palette.text, relief="flat",
            cursor="hand2", padx=12, pady=5,
            command=lambda: self.edit_entry(entry),
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            actions, text="Delete", font=(Palette.font_family, 9),
            bg=Palette.surface_alt, fg=Palette.danger, relief="flat",
            cursor="hand2", padx=12, pady=5,
            command=lambda: self.delete_entry(entry),
        ).pack(side="left")

        meta_row = tk.Frame(wrapper, bg=Palette.bg)
        meta_row.pack(fill="x", pady=(4, 16))
        tk.Label(
            meta_row, text=entry.get("category", "General"),
            font=(Palette.font_family, 9), fg=Palette.accent, bg=Palette.bg,
        ).pack(side="left")

        for tag in entry.get("tags", []):
            Tag(meta_row, tag).pack(side="left", padx=(8, 0))

        def field_row(label, value, secret=False):
            row = tk.Frame(wrapper, bg=Palette.surface)
            row.pack(fill="x", pady=(0, 10))
            content = tk.Frame(row, bg=Palette.surface)
            content.pack(fill="x", padx=16, pady=10)

            tk.Label(
                content, text=label, font=(Palette.font_family, 8, "bold"),
                fg=Palette.text_dim, bg=Palette.surface, anchor="w",
            ).pack(fill="x")

            display_value = value or "—"
            if secret and value and entry["id"] not in self.revealed:
                display_value = "•" * min(len(value), 24)

            tk.Label(
                content, text=display_value, font=(Palette.font_family, 12),
                fg=Palette.text, bg=Palette.surface, anchor="w",
            ).pack(fill="x", pady=(2, 0))

            if not value:
                return row

            btn_row = tk.Frame(content, bg=Palette.surface)
            btn_row.pack(fill="x", pady=(6, 0))

            def copy_val():
                self.clipboard_clear()
                self.clipboard_append(value)
                copy_btn.config(text="Copied ✓", fg=Palette.success)
                self.after(1200, lambda: copy_btn.config(text="Copy", fg=Palette.accent))

            copy_btn = tk.Button(
                btn_row, text="Copy", font=(Palette.font_family, 8),
                bg=Palette.surface, fg=Palette.accent, relief="flat",
                cursor="hand2", command=copy_val,
            )
            copy_btn.pack(side="left")

            if secret:
                def toggle_reveal():
                    if entry["id"] in self.revealed:
                        self.revealed.discard(entry["id"])
                    else:
                        self.revealed.add(entry["id"])
                    self.select_entry(entry["id"])

                tk.Button(
                    btn_row, text="Hide" if entry["id"] in self.revealed else "Show",
                    font=(Palette.font_family, 8),
                    bg=Palette.surface, fg=Palette.text_dim, relief="flat",
                    cursor="hand2", command=toggle_reveal,
                ).pack(side="left", padx=(12, 0))

            return row

        field_row("USERNAME / EMAIL", entry.get("username", ""))
        field_row("PASSWORD", entry.get("password", ""), secret=True)
        field_row("WEBSITE", entry.get("url", ""))

        history = entry.get("history", [])
        if history:
            hist_frame = tk.Frame(wrapper, bg=Palette.surface)
            hist_frame.pack(fill="x", pady=(0, 10))
            hist_inner = tk.Frame(hist_frame, bg=Palette.surface)
            hist_inner.pack(fill="x", padx=16, pady=10)
            tk.Label(
                hist_inner, text=f"PASSWORD HISTORY ({len(history)})",
                font=(Palette.font_family, 8, "bold"), fg=Palette.text_dim, bg=Palette.surface,
                anchor="w",
            ).pack(fill="x")
            for h in reversed(history[-5:]):
                masked = "•" * min(len(h["password"]), 16) if h["password"] else "(empty)"
                tk.Label(
                    hist_inner, text=masked, font=(Palette.font_family, 9),
                    fg=Palette.text_dim, bg=Palette.surface, anchor="w",
                ).pack(fill="x", pady=(4, 0))

        notes = entry.get("notes", "")
        notes_box = tk.Frame(wrapper, bg=Palette.surface)
        notes_box.pack(fill="both", expand=True, pady=(0, 10))
        notes_content = tk.Frame(notes_box, bg=Palette.surface)
        notes_content.pack(fill="both", expand=True, padx=16, pady=10)
        tk.Label(
            notes_content, text="NOTES", font=(Palette.font_family, 8, "bold"),
            fg=Palette.text_dim, bg=Palette.surface, anchor="w",
        ).pack(fill="x")
        tk.Label(
            notes_content, text=notes or "—", font=(Palette.font_family, 11),
            fg=Palette.text, bg=Palette.surface, anchor="nw",
            justify="left", wraplength=520,
        ).pack(fill="both", expand=True, pady=(4, 0))

    # ---- actions ----

    def new_entry(self):
        EntryDialog(
            self, on_save=self.add_entry,
            known_categories=all_categories(self.entries),
            known_tags=all_tags(self.entries),
        )

    def add_entry(self, entry):
        self.entries.append(entry)
        self.persist()
        self.render_filter_bar()
        self.refresh_list()
        self.select_entry(entry["id"])

    def edit_entry(self, entry):
        def save_edit(updated):
            idx = next(i for i, e in enumerate(self.entries) if e["id"] == entry["id"])
            self.entries[idx] = updated
            self.persist()
            self.render_filter_bar()
            self.refresh_list()
            self.select_entry(updated["id"])

        EntryDialog(
            self, on_save=save_edit, entry=entry,
            known_categories=all_categories(self.entries),
            known_tags=all_tags(self.entries),
        )

    def delete_entry(self, entry):
        if not messagebox.askyesno(
            "Delete entry", f"Delete '{entry['name']}'? This cannot be undone."
        ):
            return
        self.entries = [e for e in self.entries if e["id"] != entry["id"]]
        self.selected_id = None
        self.persist()
        self.render_filter_bar()
        self.refresh_list()
        self.show_empty_detail()

    def persist(self):
        save_vault(self.fernet, self.paths, self.entries)
