"""ui/security_dashboard.py — A window summarizing vault password health."""

from __future__ import annotations

import tkinter as tk

from ..password_utils import find_reused_passwords, find_weak_entries, estimate_strength
from ..theme import Palette
from .widgets import ScrollableFrame


class SecurityDashboard(tk.Toplevel):
    def __init__(self, parent, entries: list, on_select_entry):
        super().__init__(parent)
        self.entries = entries
        self.on_select_entry = on_select_entry
        self.by_id = {e["id"]: e for e in entries}

        self.title("Security Check")
        self.configure(bg=Palette.bg)
        self.geometry("460x560")
        self.transient(parent)

        header = tk.Frame(self, bg=Palette.bg)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(
            header, text="Security Check", font=(Palette.font_family, 16, "bold"),
            fg=Palette.text, bg=Palette.bg,
        ).pack(anchor="w")

        reused = find_reused_passwords(entries)
        weak_ids = set(find_weak_entries(entries))
        reused_ids = {eid for ids in reused.values() for eid in ids}

        total = len(entries)
        healthy = total - len(weak_ids | reused_ids)

        summary = tk.Frame(self, bg=Palette.surface)
        summary.pack(fill="x", padx=24, pady=(0, 16))
        summary_inner = tk.Frame(summary, bg=Palette.surface)
        summary_inner.pack(fill="x", padx=16, pady=14)

        self._stat_row(summary_inner, "Total entries", str(total), Palette.text)
        self._stat_row(summary_inner, "Weak passwords", str(len(weak_ids)), Palette.danger if weak_ids else Palette.success)
        self._stat_row(summary_inner, "Reused passwords", str(len(reused_ids)), Palette.danger if reused_ids else Palette.success)
        self._stat_row(summary_inner, "Looking good", str(healthy), Palette.success)

        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        if not weak_ids and not reused_ids:
            tk.Label(
                scroll.inner, text="✓ No weak or reused passwords found.",
                font=(Palette.font_family, 10), fg=Palette.success, bg=Palette.bg,
            ).pack(pady=20)
            return

        if weak_ids:
            self._section_title(scroll.inner, "Weak Passwords")
            for eid in weak_ids:
                entry = self.by_id.get(eid)
                if entry:
                    result = estimate_strength(entry.get("password", ""))
                    self._issue_row(scroll.inner, entry, result.label)

        if reused:
            self._section_title(scroll.inner, "Reused Passwords")
            for pw, ids in reused.items():
                names = [self.by_id[i]["name"] for i in ids if i in self.by_id]
                for eid in ids:
                    entry = self.by_id.get(eid)
                    if entry:
                        other_names = ", ".join(n for n in names if n != entry["name"]) or "another entry"
                        self._issue_row(scroll.inner, entry, f"Shared with {other_names}")

    def _stat_row(self, parent, label, value, color):
        row = tk.Frame(parent, bg=Palette.surface)
        row.pack(fill="x", pady=3)
        tk.Label(
            row, text=label, font=(Palette.font_family, 10),
            fg=Palette.text_dim, bg=Palette.surface, anchor="w",
        ).pack(side="left")
        tk.Label(
            row, text=value, font=(Palette.font_family, 10, "bold"),
            fg=color, bg=Palette.surface, anchor="e",
        ).pack(side="right")

    def _section_title(self, parent, text):
        tk.Label(
            parent, text=text, font=(Palette.font_family, 10, "bold"),
            fg=Palette.text_dim, bg=Palette.bg, anchor="w",
        ).pack(fill="x", pady=(12, 6))

    def _issue_row(self, parent, entry, detail):
        row = tk.Frame(parent, bg=Palette.surface, cursor="hand2")
        row.pack(fill="x", pady=(0, 6))
        inner = tk.Frame(row, bg=Palette.surface)
        inner.pack(fill="x", padx=14, pady=10)

        tk.Label(
            inner, text=entry["name"], font=(Palette.font_family, 10, "bold"),
            fg=Palette.text, bg=Palette.surface, anchor="w",
        ).pack(fill="x")
        tk.Label(
            inner, text=detail, font=(Palette.font_family, 8),
            fg=Palette.warning, bg=Palette.surface, anchor="w",
        ).pack(fill="x")

        def go():
            self.on_select_entry(entry["id"])
            self.destroy()

        for w in (row, inner):
            w.bind("<Button-1>", lambda e: go())
