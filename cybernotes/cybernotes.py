#!/usr/bin/env python3
"""
CyberNotes — fast, minimal, IDLE-style notes editor for security study tracks.

Zero dependencies. Standard library only (tkinter).
Notes are stored as plain .md files under notes/<TRACK>/, so they stay
grep-able and diff-able in git.

    python3 cybernotes.py
"""

import os
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

APP_TITLE = "CyberNotes"
NOTES_ROOT = Path(__file__).resolve().parent / "notes"
TRACKS = ["General", "Network+", "Security+", "CEH", "OSCP"]

# devforge palette
BG_DARK = "#0a0e14"
BG_PANEL = "#0d1117"
BG_EDITOR = "#0a0e14"
FG_TEXT = "#c9d1d9"
ACCENT_GREEN = "#39ff88"
ACCENT_CYAN = "#39d5ff"
FG_DIM = "#5c6773"
SELECT_BG = "#1c2733"
BORDER = "#1c2733"

FONT_UI = ("Consolas", 10)
FONT_EDITOR = ("Consolas", 12)
if sys.platform == "darwin":
    FONT_UI = ("Menlo", 11)
    FONT_EDITOR = ("Menlo", 13)
elif sys.platform.startswith("linux"):
    FONT_UI = ("DejaVu Sans Mono", 10)
    FONT_EDITOR = ("DejaVu Sans Mono", 12)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class CyberNotes(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1000x650")
        self.minsize(700, 420)
        self.configure(bg=BG_DARK)

        self.current_path: Path | None = None
        self.dirty = False

        self._ensure_tracks()
        self._build_ui()
        self._bind_shortcuts()
        self._populate_tree()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- setup ---------------------------------------------------------

    def _ensure_tracks(self):
        NOTES_ROOT.mkdir(exist_ok=True)
        for track in TRACKS:
            (NOTES_ROOT / track).mkdir(exist_ok=True)

    def _build_ui(self):
        # top status bar: current file + save state
        self.status_bar = tk.Frame(self, bg=BG_PANEL, height=32)
        self.status_bar.pack(side=tk.TOP, fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_bar, text="no file open", bg=BG_PANEL, fg=FG_DIM,
            font=FONT_UI, anchor="w", padx=12,
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.Y)

        self.dirty_label = tk.Label(
            self.status_bar, text="", bg=BG_PANEL, fg=ACCENT_CYAN,
            font=FONT_UI, anchor="e", padx=12,
        )
        self.dirty_label.pack(side=tk.RIGHT, fill=tk.Y)

        # main split: tree | editor
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # -- left panel: track tree --------------------------------
        left = tk.Frame(body, bg=BG_PANEL, width=230)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        header = tk.Label(
            left, text="CYBERNOTES", bg=BG_PANEL, fg=ACCENT_GREEN,
            font=(FONT_UI[0], FONT_UI[1], "bold"), anchor="w", padx=12, pady=10,
        )
        header.pack(side=tk.TOP, fill=tk.X)

        tree_frame = tk.Frame(left, bg=BG_PANEL)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(4, 0))

        scrollbar = tk.Scrollbar(tree_frame, bg=BG_PANEL, troughcolor=BG_PANEL,
                                  bd=0, highlightthickness=0)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            tree_frame, bg=BG_PANEL, fg=FG_TEXT, font=FONT_UI,
            bd=0, highlightthickness=0, activestyle="none",
            selectbackground=SELECT_BG, selectforeground=ACCENT_GREEN,
            yscrollcommand=scrollbar.set,
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Double-Button-1>", self._on_select)

        # action buttons
        btn_frame = tk.Frame(left, bg=BG_PANEL)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=8, padx=8)

        self._make_button(btn_frame, "+ NEW", self._new_note, ACCENT_GREEN).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))
        self._make_button(btn_frame, "RENAME", self._rename_note, ACCENT_CYAN).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        self._make_button(btn_frame, "DELETE", self._delete_note, "#ff5c5c").pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        # -- right panel: editor --------------------------------------
        right = tk.Frame(body, bg=BG_EDITOR)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        edit_scroll = tk.Scrollbar(right, bg=BG_PANEL, troughcolor=BG_PANEL,
                                    bd=0, highlightthickness=0)
        edit_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.editor = tk.Text(
            right, bg=BG_EDITOR, fg=FG_TEXT, insertbackground=ACCENT_GREEN,
            font=FONT_EDITOR, bd=0, highlightthickness=0, wrap="word",
            undo=True, padx=16, pady=12, yscrollcommand=edit_scroll.set,
            selectbackground=SELECT_BG, selectforeground=ACCENT_CYAN,
        )
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        edit_scroll.config(command=self.editor.yview)
        self.editor.bind("<<Modified>>", self._on_modified)
        self.editor.config(state=tk.DISABLED)

    def _make_button(self, parent, text, command, color):
        btn = tk.Button(
            parent, text=text, command=command, bg=BG_PANEL, fg=color,
            activebackground=SELECT_BG, activeforeground=color,
            font=(FONT_UI[0], 8, "bold"), bd=1, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1, pady=4,
            cursor="hand2",
        )
        return btn

    def _bind_shortcuts(self):
        self.bind_all("<Control-s>", lambda e: self._save_note())
        self.bind_all("<Control-n>", lambda e: self._new_note())

    # -- tree / listbox population --------------------------------------

    def _populate_tree(self):
        """Flat list, grouped by track, showing TRACK/filename.md rows."""
        self.listbox.delete(0, tk.END)
        self._row_paths: list[Path | None] = []  # parallel index -> Path or None (header)

        for track in TRACKS:
            track_dir = NOTES_ROOT / track
            files = sorted(track_dir.glob("*.md"))

            self.listbox.insert(tk.END, f"  {track}")
            self._row_paths.append(None)
            idx = self.listbox.size() - 1
            self.listbox.itemconfig(idx, fg=ACCENT_CYAN)

            for f in files:
                self.listbox.insert(tk.END, f"    {f.stem}")
                self._row_paths.append(f)

        # reselect current file if still present
        if self.current_path and self.current_path in self._row_paths:
            idx = self._row_paths.index(self.current_path)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)

    def _selected_path(self) -> Path | None:
        sel = self.listbox.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx >= len(self._row_paths):
            return None
        return self._row_paths[idx]

    def _track_of_selection(self) -> str:
        """Return the track name a new note should land in, based on selection."""
        sel = self.listbox.curselection()
        if not sel:
            return TRACKS[0]
        idx = sel[0]
        path = self._row_paths[idx]
        if path is not None:
            return path.parent.name
        # header row selected -> its own text
        text = self.listbox.get(idx).strip()
        return text if text in TRACKS else TRACKS[0]

    # -- file ops ---------------------------------------------------------

    def _on_select(self, event=None):
        path = self._selected_path()
        if path is None:
            return
        if not self._confirm_discard_if_dirty():
            self._populate_tree()  # snap selection back
            return
        self._open_note(path)

    def _open_note(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Couldn't open file:\n{e}")
            return

        self.editor.config(state=tk.NORMAL)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", text)
        self.editor.edit_modified(False)
        self.editor.focus_set()

        self.current_path = path
        self.dirty = False
        self._update_status()

    def _new_note(self):
        if not self._confirm_discard_if_dirty():
            return

        track = self._track_of_selection()
        name = simpledialog.askstring(
            APP_TITLE, f"New note name in {track}:", parent=self,
        )
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if not name.endswith(".md"):
            name += ".md"
        stem = name[:-3]

        target = NOTES_ROOT / track / name
        if target.exists():
            messagebox.showwarning(APP_TITLE, f"'{name}' already exists in {track}.")
            return

        try:
            target.write_text(f"# {stem}\n\n", encoding="utf-8")
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Couldn't create file:\n{e}")
            return

        self._populate_tree()
        self._open_note(target)
        self.editor.mark_set(tk.INSERT, tk.END)

    def _save_note(self, event=None):
        if self.current_path is None:
            return "break"
        content = self.editor.get("1.0", "end-1c")
        try:
            self.current_path.write_text(content, encoding="utf-8")
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Couldn't save file:\n{e}")
            return "break"

        self.dirty = False
        self.editor.edit_modified(False)
        self._update_status(saved_flash=True)
        return "break"

    def _rename_note(self):
        path = self.current_path or self._selected_path()
        if path is None:
            messagebox.showinfo(APP_TITLE, "Select a note first.")
            return

        new_stem = simpledialog.askstring(
            APP_TITLE, "Rename to:", initialvalue=path.stem, parent=self,
        )
        if not new_stem:
            return
        new_stem = new_stem.strip()
        if not new_stem or new_stem == path.stem:
            return

        new_path = path.with_name(new_stem + ".md")
        if new_path.exists():
            messagebox.showwarning(APP_TITLE, f"'{new_path.name}' already exists.")
            return

        try:
            path.rename(new_path)
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Couldn't rename file:\n{e}")
            return

        was_current = (path == self.current_path)
        self._populate_tree()
        if was_current:
            self._open_note(new_path)

    def _delete_note(self):
        path = self.current_path or self._selected_path()
        if path is None:
            messagebox.showinfo(APP_TITLE, "Select a note first.")
            return

        if not messagebox.askyesno(
            APP_TITLE, f"Delete '{path.name}' from {path.parent.name}?\nThis cannot be undone.",
        ):
            return

        try:
            path.unlink()
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Couldn't delete file:\n{e}")
            return

        if path == self.current_path:
            self.current_path = None
            self.dirty = False
            self.editor.config(state=tk.NORMAL)
            self.editor.delete("1.0", tk.END)
            self.editor.config(state=tk.DISABLED)

        self._populate_tree()
        self._update_status()

    # -- state / status ----------------------------------------------------

    def _on_modified(self, event=None):
        if self.editor.edit_modified():
            self.dirty = True
            self._update_status()

    def _update_status(self, saved_flash=False):
        if self.current_path is None:
            self.status_label.config(text="no file open")
            self.dirty_label.config(text="")
            return

        rel = f"{self.current_path.parent.name}/{self.current_path.name}"
        self.status_label.config(text=rel)

        if saved_flash:
            self.dirty_label.config(text="saved", fg=ACCENT_GREEN)
        elif self.dirty:
            self.dirty_label.config(text="unsaved *", fg="#ffb84d")
        else:
            self.dirty_label.config(text="")

    def _confirm_discard_if_dirty(self) -> bool:
        """Returns True if it's OK to proceed (saved, discarded, or nothing to lose)."""
        if not self.dirty or self.current_path is None:
            return True
        answer = messagebox.askyesnocancel(
            APP_TITLE, f"Save changes to '{self.current_path.name}'?",
        )
        if answer is None:
            return False
        if answer:
            self._save_note()
        return True

    def _on_close(self):
        if self._confirm_discard_if_dirty():
            self.destroy()


def main():
    app = CyberNotes()
    app.mainloop()


if __name__ == "__main__":
    main()
