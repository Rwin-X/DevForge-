#!/usr/bin/env python3
"""
LOC Counter — GUI utility to scan a folder and count lines of code
per language / file extension.

Run with:
    python3 loc_counter_gui.py

Requires only the Python standard library (tkinter ships with most
standard CPython installs — on Debian/Ubuntu you may need:
    sudo apt install python3-tk
).
"""

import os
import threading
import queue
import csv
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from counter_core import (
    scan_directory,
    LANGUAGE_EXTENSIONS,
    DEFAULT_EXCLUDED_DIRS,
)

# --------------------------------------------------------------------------
# Theme — dark / monochrome / phosphor accent, JetBrains Mono where available
# --------------------------------------------------------------------------
BG_DARKEST = "#0a0a0a"
BG_DARK = "#111318"
BG_PANEL = "#161a20"
BG_INPUT = "#1c2028"
FG_PRIMARY = "#d4d8dd"
FG_DIM = "#6b7280"
ACCENT = "#00ff9c"        # phosphor green
ACCENT_DIM = "#0a3d2c"
ACCENT_CYAN = "#00d4ff"
BORDER = "#2a2f38"
ERROR_COLOR = "#ff5c5c"

MONO_CANDIDATES = ["JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"]


def pick_mono_font(root: tk.Tk) -> str:
    import tkinter.font as tkfont
    available = set(tkfont.families(root))
    for name in MONO_CANDIDATES:
        if name in available:
            return name
    return "Courier"


class LOCCounterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LOC COUNTER // devforge")
        self.root.geometry("980x680")
        self.root.minsize(760, 520)
        self.root.configure(bg=BG_DARKEST)

        self.mono_font = pick_mono_font(root)

        self.selected_dir = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="IDLE — select a folder to begin")
        self.recursive_var = tk.BooleanVar(value=True)
        self.skip_junk_var = tk.BooleanVar(value=True)

        self.lang_vars: dict[str, tk.BooleanVar] = {
            lang: tk.BooleanVar(value=True) for lang in sorted(LANGUAGE_EXTENSIONS.keys())
        }

        self._scan_thread: threading.Thread | None = None
        self._result_queue: "queue.Queue" = queue.Queue()
        self._last_scan_result = None  # ScanResult, kept for export

        self._build_style()
        self._build_layout()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "TFrame", background=BG_DARK,
        )
        style.configure(
            "Panel.TFrame", background=BG_PANEL,
        )
        style.configure(
            "TLabel", background=BG_DARK, foreground=FG_PRIMARY,
            font=(self.mono_font, 10),
        )
        style.configure(
            "Header.TLabel", background=BG_DARKEST, foreground=ACCENT,
            font=(self.mono_font, 15, "bold"),
        )
        style.configure(
            "Dim.TLabel", background=BG_DARK, foreground=FG_DIM,
            font=(self.mono_font, 9),
        )
        style.configure(
            "Status.TLabel", background=BG_DARKEST, foreground=ACCENT_CYAN,
            font=(self.mono_font, 9),
        )
        style.configure(
            "TButton",
            background=BG_INPUT, foreground=ACCENT,
            font=(self.mono_font, 10, "bold"),
            borderwidth=1, focusthickness=0, padding=8,
        )
        style.map(
            "TButton",
            background=[("active", ACCENT_DIM), ("pressed", ACCENT_DIM)],
            foreground=[("active", ACCENT)],
        )
        style.configure(
            "Accent.TButton",
            background=ACCENT_DIM, foreground=ACCENT,
            font=(self.mono_font, 11, "bold"), padding=10,
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT), ("pressed", ACCENT)],
            foreground=[("active", BG_DARKEST), ("pressed", BG_DARKEST)],
        )
        style.configure(
            "TCheckbutton",
            background=BG_PANEL, foreground=FG_PRIMARY,
            font=(self.mono_font, 9),
        )
        style.map(
            "TCheckbutton",
            background=[("active", BG_PANEL)],
            foreground=[("active", ACCENT)],
        )
        style.configure(
            "TEntry",
            fieldbackground=BG_INPUT, foreground=FG_PRIMARY,
            insertcolor=ACCENT, borderwidth=1,
        )
        style.configure(
            "Treeview",
            background=BG_INPUT, fieldbackground=BG_INPUT, foreground=FG_PRIMARY,
            font=(self.mono_font, 10), rowheight=26, borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=BG_PANEL, foreground=ACCENT,
            font=(self.mono_font, 10, "bold"), borderwidth=1,
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT_DIM)],
            foreground=[("selected", ACCENT)],
        )
        style.configure("TPanedwindow", background=BG_DARKEST)
        style.configure("Vertical.TScrollbar", background=BG_PANEL, troughcolor=BG_DARK, arrowcolor=ACCENT)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        # ---- Header bar ----
        header = tk.Frame(self.root, bg=BG_DARKEST, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header, text="LOC COUNTER", bg=BG_DARKEST, fg=ACCENT,
            font=(self.mono_font, 16, "bold"),
        ).pack(side="left", padx=(18, 4), pady=10)
        tk.Label(
            header, text="// devforge utility", bg=BG_DARKEST, fg=FG_DIM,
            font=(self.mono_font, 10),
        ).pack(side="left", pady=10)

        # ---- Main body: left config panel + right results panel ----
        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=14, pady=(10, 0))

        left = tk.Frame(body, bg=BG_PANEL, width=260)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True)

        self._build_left_panel(left)
        self._build_right_panel(right)

        # ---- Status bar ----
        status_bar = tk.Frame(self.root, bg=BG_DARKEST, height=30)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        tk.Label(
            status_bar, textvariable=self.status_text, bg=BG_DARKEST, fg=ACCENT_CYAN,
            font=(self.mono_font, 9), anchor="w",
        ).pack(side="left", padx=14, fill="x", expand=True)

    def _build_left_panel(self, parent: tk.Frame):
        pad = {"padx": 14, "pady": (12, 4)}

        tk.Label(parent, text="TARGET FOLDER", bg=BG_PANEL, fg=FG_DIM,
                 font=(self.mono_font, 9, "bold")).pack(anchor="w", **pad)

        path_row = tk.Frame(parent, bg=BG_PANEL)
        path_row.pack(fill="x", padx=14)
        entry = tk.Entry(
            path_row, textvariable=self.selected_dir, bg=BG_INPUT, fg=FG_PRIMARY,
            insertbackground=ACCENT, relief="flat", font=(self.mono_font, 9),
        )
        entry.pack(side="left", fill="x", expand=True, ipady=4)

        ttk.Button(parent, text="BROWSE…", command=self._browse_folder).pack(
            fill="x", padx=14, pady=(6, 14)
        )

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=14, pady=4)

        tk.Label(parent, text="OPTIONS", bg=BG_PANEL, fg=FG_DIM,
                 font=(self.mono_font, 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))

        ttk.Checkbutton(
            parent, text="Skip junk dirs (.git, node_modules, venv…)",
            variable=self.skip_junk_var,
        ).pack(anchor="w", padx=14, pady=2)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=14, pady=8)

        lang_header_row = tk.Frame(parent, bg=BG_PANEL)
        lang_header_row.pack(fill="x", padx=14)
        tk.Label(lang_header_row, text="LANGUAGES", bg=BG_PANEL, fg=FG_DIM,
                 font=(self.mono_font, 9, "bold")).pack(side="left")
        tk.Button(
            lang_header_row, text="all", command=self._select_all_langs,
            bg=BG_PANEL, fg=ACCENT_CYAN, relief="flat", font=(self.mono_font, 8, "underline"),
            activebackground=BG_PANEL, activeforeground=ACCENT, cursor="hand2",
        ).pack(side="right", padx=2)
        tk.Button(
            lang_header_row, text="none", command=self._select_no_langs,
            bg=BG_PANEL, fg=ACCENT_CYAN, relief="flat", font=(self.mono_font, 8, "underline"),
            activebackground=BG_PANEL, activeforeground=ACCENT, cursor="hand2",
        ).pack(side="right", padx=2)

        # Scrollable checklist of languages
        lang_canvas_frame = tk.Frame(parent, bg=BG_PANEL)
        lang_canvas_frame.pack(fill="both", expand=True, padx=14, pady=(4, 8))

        canvas = tk.Canvas(lang_canvas_frame, bg=BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(lang_canvas_frame, orient="vertical", command=canvas.yview)
        scroll_inner = tk.Frame(canvas, bg=BG_PANEL)

        scroll_inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for lang in sorted(self.lang_vars.keys()):
            ttk.Checkbutton(
                scroll_inner, text=f"{lang}", variable=self.lang_vars[lang],
            ).pack(anchor="w", pady=1)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=14, pady=4)

        self.scan_button = ttk.Button(
            parent, text="▶ RUN SCAN", style="Accent.TButton", command=self._start_scan
        )
        self.scan_button.pack(fill="x", padx=14, pady=(8, 14))

    def _build_right_panel(self, parent: tk.Frame):
        # Summary strip
        self.summary_frame = tk.Frame(parent, bg=BG_DARK)
        self.summary_frame.pack(fill="x", pady=(0, 8))
        self._render_summary_placeholder()

        # Results table
        table_frame = tk.Frame(parent, bg=BG_DARK)
        table_frame.pack(fill="both", expand=True)

        columns = ("language", "files", "code", "blank", "total")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "language": "LANGUAGE",
            "files": "FILES",
            "code": "CODE LINES",
            "blank": "BLANK LINES",
            "total": "TOTAL LINES",
        }
        widths = {"language": 220, "files": 90, "code": 130, "blank": 130, "total": 130}
        for col in columns:
            self.tree.heading(col, text=headings[col], command=lambda c=col: self._sort_tree(c))
            self.tree.column(col, width=widths[col], anchor="center" if col != "language" else "w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Bottom action row (export, errors)
        bottom_row = tk.Frame(parent, bg=BG_DARK)
        bottom_row.pack(fill="x", pady=(8, 0))

        self.export_button = ttk.Button(
            bottom_row, text="EXPORT CSV", command=self._export_csv, state="disabled"
        )
        self.export_button.pack(side="left")

        self.errors_button = ttk.Button(
            bottom_row, text="VIEW ERRORS (0)", command=self._show_errors, state="disabled"
        )
        self.errors_button.pack(side="left", padx=8)

    def _render_summary_placeholder(self):
        for w in self.summary_frame.winfo_children():
            w.destroy()
        tk.Label(
            self.summary_frame, text="No scan run yet.", bg=BG_DARK, fg=FG_DIM,
            font=(self.mono_font, 10),
        ).pack(anchor="w")

    def _render_summary(self, totals: dict):
        for w in self.summary_frame.winfo_children():
            w.destroy()

        cards = [
            ("FILES SCANNED", totals["files"]),
            ("CODE LINES", totals["code_lines"]),
            ("BLANK LINES", totals["blank_lines"]),
            ("TOTAL LINES", totals["total_lines"]),
        ]
        for label, value in cards:
            card = tk.Frame(self.summary_frame, bg=BG_PANEL, padx=16, pady=10)
            card.pack(side="left", padx=(0, 8), fill="y")
            tk.Label(
                card, text=f"{value:,}", bg=BG_PANEL, fg=ACCENT,
                font=(self.mono_font, 18, "bold"),
            ).pack(anchor="w")
            tk.Label(
                card, text=label, bg=BG_PANEL, fg=FG_DIM,
                font=(self.mono_font, 8),
            ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select folder to scan")
        if path:
            self.selected_dir.set(path)

    def _select_all_langs(self):
        for v in self.lang_vars.values():
            v.set(True)

    def _select_no_langs(self):
        for v in self.lang_vars.values():
            v.set(False)

    def _start_scan(self):
        target = self.selected_dir.get().strip()
        if not target:
            messagebox.showwarning("No folder selected", "Choose a folder first.")
            return
        if not os.path.isdir(target):
            messagebox.showerror("Invalid folder", f"Not a directory:\n{target}")
            return

        selected_languages = {lang for lang, v in self.lang_vars.items() if v.get()}
        if not selected_languages:
            messagebox.showwarning("No languages selected", "Select at least one language.")
            return

        if self._scan_thread and self._scan_thread.is_alive():
            return  # scan already running

        self.scan_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.errors_button.configure(state="disabled")
        self.status_text.set(f"SCANNING {target} …")

        excluded_dirs = DEFAULT_EXCLUDED_DIRS if self.skip_junk_var.get() else set()

        self._scan_thread = threading.Thread(
            target=self._run_scan_worker,
            args=(target, selected_languages, excluded_dirs),
            daemon=True,
        )
        self._scan_thread.start()
        self.root.after(100, self._poll_scan_queue)

    def _run_scan_worker(self, target, selected_languages, excluded_dirs):
        try:
            result = scan_directory(
                target, selected_languages=selected_languages, excluded_dirs=excluded_dirs
            )
            self._result_queue.put(("done", result))
        except Exception as e:
            self._result_queue.put(("error", str(e)))

    def _poll_scan_queue(self):
        try:
            kind, payload = self._result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_scan_queue)
            return

        self.scan_button.configure(state="normal")

        if kind == "error":
            self.status_text.set(f"ERROR: {payload}")
            messagebox.showerror("Scan failed", payload)
            return

        result = payload
        self._last_scan_result = result
        self._populate_results(result)

    def _populate_results(self, result):
        for row in self.tree.get_children():
            self.tree.delete(row)

        by_lang = result.by_language()
        for lang, stats in sorted(by_lang.items(), key=lambda kv: -kv[1]["code_lines"]):
            self.tree.insert(
                "", "end",
                values=(lang, stats["files"], stats["code_lines"], stats["blank_lines"], stats["total_lines"]),
            )

        totals = result.grand_total()
        self._render_summary(totals)

        n_errors = len(result.errors)
        self.errors_button.configure(text=f"VIEW ERRORS ({n_errors})")
        self.errors_button.configure(state="normal" if n_errors else "disabled")
        self.export_button.configure(state="normal" if result.files else "disabled")

        self.status_text.set(
            f"DONE — {totals['files']} files, {totals['code_lines']:,} code lines "
            f"({totals['total_lines']:,} total) — {datetime.now().strftime('%H:%M:%S')}"
        )

    def _sort_tree(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            items.sort(key=lambda t: float(t[0]), reverse=True)
        except ValueError:
            items.sort(key=lambda t: t[0].lower())
        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)

    def _show_errors(self):
        if not self._last_scan_result or not self._last_scan_result.errors:
            return
        win = tk.Toplevel(self.root)
        win.title("Scan errors")
        win.configure(bg=BG_DARK)
        win.geometry("640x360")
        text = tk.Text(
            win, bg=BG_INPUT, fg=ERROR_COLOR, font=(self.mono_font, 9),
            wrap="word", insertbackground=ACCENT,
        )
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", "\n".join(self._last_scan_result.errors))
        text.configure(state="disabled")

    def _export_csv(self):
        if not self._last_scan_result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="loc_report.csv",
            title="Export report as CSV",
        )
        if not path:
            return

        by_lang = self._last_scan_result.by_language()
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["language", "files", "code_lines", "blank_lines", "total_lines"])
                for lang, stats in sorted(by_lang.items(), key=lambda kv: -kv[1]["code_lines"]):
                    writer.writerow([lang, stats["files"], stats["code_lines"], stats["blank_lines"], stats["total_lines"]])
                total = self._last_scan_result.grand_total()
                writer.writerow(["TOTAL", total["files"], total["code_lines"], total["blank_lines"], total["total_lines"]])
            self.status_text.set(f"EXPORTED → {path}")
        except OSError as e:
            messagebox.showerror("Export failed", str(e))


def main():
    root = tk.Tk()
    try:
        root.iconname("LOC Counter")
    except tk.TclError:
        pass
    LOCCounterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
