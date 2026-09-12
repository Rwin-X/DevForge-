"""ui/export_import_dialog.py — Export and import vault data."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, filedialog

from .. import storage
from ..crypto import WrongPasswordError
from ..theme import Palette


class ExportDialog(tk.Toplevel):
    def __init__(self, parent, entries: list, on_export_done=None):
        super().__init__(parent)
        self.entries = entries
        self.on_export_done = on_export_done

        self.title("Export Vault")
        self.configure(bg=Palette.surface)
        self.geometry("420x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self, text="Export", font=(Palette.font_family, 15, "bold"),
            fg=Palette.text, bg=Palette.surface,
        ).pack(padx=24, pady=(20, 4), anchor="w")

        tk.Label(
            self,
            text="Encrypted export stays protected by a password of your\nchoice. Plaintext export is unencrypted — only use it to\nmigrate to another tool, and delete the file afterwards.",
            font=(Palette.font_family, 9), fg=Palette.text_dim, bg=Palette.surface,
            justify="left",
        ).pack(padx=24, pady=(0, 16), anchor="w")

        # --- Encrypted export ---
        enc_frame = tk.Frame(self, bg=Palette.surface_alt)
        enc_frame.pack(fill="x", padx=24, pady=(0, 12))
        enc_inner = tk.Frame(enc_frame, bg=Palette.surface_alt)
        enc_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(
            enc_inner, text="🔒 Encrypted export (.pvexport)",
            font=(Palette.font_family, 10, "bold"), fg=Palette.text, bg=Palette.surface_alt,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            enc_inner, text="Recommended. Set a password to protect the file.",
            font=(Palette.font_family, 8), fg=Palette.text_dim, bg=Palette.surface_alt,
            anchor="w",
        ).pack(fill="x", pady=(2, 8))

        self.export_pw_var = tk.StringVar()
        tk.Entry(
            enc_inner, textvariable=self.export_pw_var, show="•",
            font=(Palette.font_family, 11), bg=Palette.surface, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
        ).pack(fill="x", ipady=6, pady=(0, 8))

        tk.Button(
            enc_inner, text="Export Encrypted…", font=(Palette.font_family, 9, "bold"),
            bg=Palette.accent, fg="#0f1115", relief="flat", cursor="hand2",
            command=self.export_encrypted, pady=6,
        ).pack(fill="x")

        # --- Plaintext export ---
        plain_frame = tk.Frame(self, bg=Palette.surface_alt)
        plain_frame.pack(fill="x", padx=24)
        plain_inner = tk.Frame(plain_frame, bg=Palette.surface_alt)
        plain_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(
            plain_inner, text="⚠ Plaintext export (.json / .csv)",
            font=(Palette.font_family, 10, "bold"), fg=Palette.warning, bg=Palette.surface_alt,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            plain_inner, text="Unencrypted. Anyone with the file can read every password.",
            font=(Palette.font_family, 8), fg=Palette.text_dim, bg=Palette.surface_alt,
            anchor="w",
        ).pack(fill="x", pady=(2, 8))

        btn_row = tk.Frame(plain_inner, bg=Palette.surface_alt)
        btn_row.pack(fill="x")
        tk.Button(
            btn_row, text="Export as JSON", font=(Palette.font_family, 9),
            bg=Palette.surface, fg=Palette.text, relief="flat", cursor="hand2",
            command=lambda: self.export_plaintext("json"), pady=6,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(
            btn_row, text="Export as CSV", font=(Palette.font_family, 9),
            bg=Palette.surface, fg=Palette.text, relief="flat", cursor="hand2",
            command=lambda: self.export_plaintext("csv"), pady=6,
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

    def export_encrypted(self) -> None:
        pw = self.export_pw_var.get()
        if len(pw) < 6:
            messagebox.showwarning("Weak password", "Use at least 6 characters for the export password.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pvexport",
            filetypes=[("PassVault Export", "*.pvexport")],
            title="Save encrypted export",
        )
        if not path:
            return
        storage.export_encrypted(self.entries, pw, path)
        messagebox.showinfo("Export complete", f"Encrypted export saved to:\n{path}")
        if self.on_export_done:
            self.on_export_done()

    def export_plaintext(self, fmt: str) -> None:
        proceed = messagebox.askyesno(
            "Export unencrypted?",
            "This file will contain every password in PLAIN TEXT.\n\n"
            "Anyone who opens it can read all your credentials.\n"
            "Continue?",
            icon="warning",
        )
        if not proceed:
            return

        ext = ".json" if fmt == "json" else ".csv"
        filetypes = [("JSON", "*.json")] if fmt == "json" else [("CSV", "*.csv")]
        path = filedialog.asksaveasfilename(
            defaultextension=ext, filetypes=filetypes, title="Save plaintext export",
        )
        if not path:
            return

        if fmt == "json":
            storage.export_plaintext_json(self.entries, path)
        else:
            storage.export_plaintext_csv(self.entries, path)

        messagebox.showinfo(
            "Export complete",
            f"Unencrypted export saved to:\n{path}\n\nDelete this file when you're done with it.",
        )
        if self.on_export_done:
            self.on_export_done()


class ImportDialog(tk.Toplevel):
    def __init__(self, parent, on_import):
        super().__init__(parent)
        self.on_import = on_import

        self.title("Import Vault")
        self.configure(bg=Palette.surface)
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self, text="Import", font=(Palette.font_family, 15, "bold"),
            fg=Palette.text, bg=Palette.surface,
        ).pack(padx=24, pady=(20, 4), anchor="w")

        tk.Label(
            self,
            text="Imported entries are added to your current vault.\nExisting entries are not overwritten.",
            font=(Palette.font_family, 9), fg=Palette.text_dim, bg=Palette.surface,
            justify="left",
        ).pack(padx=24, pady=(0, 16), anchor="w")

        tk.Label(
            self, text="Encrypted export password (if importing .pvexport)",
            font=(Palette.font_family, 8, "bold"), fg=Palette.text_dim, bg=Palette.surface,
            anchor="w",
        ).pack(fill="x", padx=24)

        self.import_pw_var = tk.StringVar()
        tk.Entry(
            self, textvariable=self.import_pw_var, show="•",
            font=(Palette.font_family, 11), bg=Palette.surface_alt, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
        ).pack(fill="x", padx=24, ipady=6, pady=(4, 16))

        tk.Button(
            self, text="Choose File to Import…", font=(Palette.font_family, 10, "bold"),
            bg=Palette.accent, fg="#0f1115", relief="flat", cursor="hand2",
            command=self.choose_file, pady=8,
        ).pack(fill="x", padx=24)

        self.error_label = tk.Label(
            self, text="", font=(Palette.font_family, 9),
            fg=Palette.danger, bg=Palette.surface,
        )
        self.error_label.pack(pady=(10, 0))

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("All supported", "*.pvexport *.json *.csv"),
                ("PassVault Export", "*.pvexport"),
                ("JSON", "*.json"),
                ("CSV", "*.csv"),
            ],
            title="Choose file to import",
        )
        if not path:
            return

        try:
            if path.endswith(".pvexport"):
                pw = self.import_pw_var.get()
                if not pw:
                    self.error_label.config(text="Enter the export's password first.")
                    return
                entries = storage.import_encrypted(pw, path)
            elif path.endswith(".json"):
                entries = storage.import_plaintext_json(path)
            elif path.endswith(".csv"):
                entries = storage.import_plaintext_csv(path)
            else:
                self.error_label.config(text="Unsupported file type.")
                return
        except WrongPasswordError:
            self.error_label.config(text="Incorrect export password.")
            return
        except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
            self.error_label.config(text=f"Could not read file: {exc}")
            return

        self.on_import(entries)
        messagebox.showinfo("Import complete", f"Imported {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")
        self.destroy()
