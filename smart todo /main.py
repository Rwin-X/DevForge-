import customtkinter as ctk
import json
import os

# ── Config ─────────────────────────────────────────────────────────
TASKS_FILE      = "tasks.json"
APP_TITLE       = "Smart Todo"
WIN_W, WIN_H    = 460, 660

# ── Palette ────────────────────────────────────────────────────────
BG       = "#0C0C0E"   # near-black background
SURFACE  = "#141416"   # card surface
BORDER   = "#222226"   # subtle borders
ACCENT   = "#7C6EF7"   # violet accent
ACCENT_H = "#6557E8"   # hover state
T_HI     = "#EEEEF4"   # primary text
T_MID    = "#888899"   # secondary / placeholders
T_DONE   = "#4A4A5C"   # completed task text

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SmartTodo(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(380, 500)
        self.configure(fg_color=BG)

        self.tasks: list[dict] = []
        self._build_ui()
        self._load()

    # ── UI Construction ─────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ─────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=28, pady=(32, 0))

        ctk.CTkLabel(
            hdr, text="Smart Todo",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=T_HI,
        ).pack(side="left")

        self.count_lbl = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont(size=12),
            text_color=T_MID,
        )
        self.count_lbl.pack(side="right", pady=(5, 0))

        # ── Thin progress bar ───────────────────────────────────────
        self.progress = ctk.CTkProgressBar(
            self, height=2, corner_radius=2,
            fg_color=BORDER, progress_color=ACCENT,
        )
        self.progress.set(0)
        self.progress.pack(fill="x", padx=28, pady=(10, 22))

        # ── Input card ─────────────────────────────────────────────
        inp_card = ctk.CTkFrame(
            self, fg_color=SURFACE,
            corner_radius=14, border_width=1, border_color=BORDER,
        )
        inp_card.pack(fill="x", padx=28)

        self.entry = ctk.CTkEntry(
            inp_card,
            placeholder_text="What needs to be done?",
            font=ctk.CTkFont(size=14),
            fg_color="transparent", border_width=0,
            text_color=T_HI, placeholder_text_color=T_MID,
            height=48,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(16, 6), pady=5)
        self.entry.bind("<Return>", lambda _: self._add())

        ctk.CTkButton(
            inp_card, text="Add",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_H,
            text_color="#FFFFFF", corner_radius=10,
            width=68, height=38,
            command=self._add,
        ).pack(side="right", padx=(0, 6), pady=5)

        # ── Section row ────────────────────────────────────────────
        sec = ctk.CTkFrame(self, fg_color="transparent")
        sec.pack(fill="x", padx=28, pady=(18, 8))

        self.section_lbl = ctk.CTkLabel(
            sec, text="TASKS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=T_MID,
        )
        self.section_lbl.pack(side="left")

        # ── Scrollable task list ────────────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color="#32323A",
        )
        self.list_frame.pack(fill="both", expand=True, padx=28, pady=(0, 28))

    # ── Task Logic ──────────────────────────────────────────────────

    def _add(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.tasks.append({"text": text, "done": False})
        self.entry.delete(0, "end")
        self._refresh()
        self._save()

    def _delete(self, idx: int):
        self.tasks.pop(idx)
        self._refresh()
        self._save()

    def _toggle(self, idx: int):
        self.tasks[idx]["done"] = not self.tasks[idx]["done"]
        self._refresh()
        self._save()

    # ── Rendering ───────────────────────────────────────────────────

    def _refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        total = len(self.tasks)
        done  = sum(1 for t in self.tasks if t["done"])

        # Empty state
        if total == 0:
            self.count_lbl.configure(text="")
            self.section_lbl.configure(text="TASKS")
            self.progress.set(0)
            ctk.CTkLabel(
                self.list_frame,
                text="Nothing here yet.\nAdd your first task above ↑",
                font=ctk.CTkFont(size=13),
                text_color=T_MID, justify="center",
            ).pack(pady=52)
            return

        # Update header meta
        self.count_lbl.configure(text=f"{done} of {total} done")
        self.section_lbl.configure(text=f"TASKS  ·  {total}")
        self.progress.set(done / total)

        for i, task in enumerate(self.tasks):
            self._make_row(i, task)

    def _make_row(self, idx: int, task: dict):
        row = ctk.CTkFrame(
            self.list_frame, fg_color=SURFACE,
            corner_radius=12, border_width=1, border_color=BORDER,
        )
        row.pack(fill="x", pady=(0, 7))
        row.columnconfigure(1, weight=1)

        # Checkbox
        var = ctk.BooleanVar(value=task["done"])
        ctk.CTkCheckBox(
            row, text="", variable=var,
            command=lambda i=idx: self._toggle(i),
            fg_color=ACCENT, hover_color=ACCENT_H,
            border_color="#3E3E52",
            checkmark_color="#FFFFFF",
            width=20, height=20,
        ).grid(row=0, column=0, padx=(14, 10), pady=14, sticky="w")

        # Task label (dim when done)
        ctk.CTkLabel(
            row,
            text=task["text"],
            font=ctk.CTkFont(size=14),
            text_color=T_DONE if task["done"] else T_HI,
            anchor="w", justify="left",
            wraplength=280,
        ).grid(row=0, column=1, sticky="ew", pady=14)

        # Delete button
        ctk.CTkButton(
            row, text="✕",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color="#222228",
            text_color=T_MID,
            width=30, height=30,
            corner_radius=8,
            command=lambda i=idx: self._delete(i),
        ).grid(row=0, column=2, padx=(4, 10), pady=10)

    # ── Persistence ─────────────────────────────────────────────────

    def _save(self):
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, indent=2, ensure_ascii=False)

    def _load(self):
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.tasks = data
            except (json.JSONDecodeError, ValueError):
                self.tasks = []
        self._refresh()


# ── Entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    app = SmartTodo()
    app.mainloop()
