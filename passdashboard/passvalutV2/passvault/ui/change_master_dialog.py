"""ui/change_master_dialog.py — Change the vault's master password."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from ..crypto import make_fernet, decrypt_bytes, WrongPasswordError
from ..storage import VaultPaths, save_vault, generate_salt
from ..theme import Palette
from ..password_utils import estimate_strength
from .widgets import StrengthMeter


class ChangeMasterDialog(tk.Toplevel):
    """
    Re-encrypts the entire vault under a new master password.

    Flow:
      1. User confirms their CURRENT master password (defense against
         someone changing it on an unlocked, unattended session).
      2. User enters and confirms a NEW master password.
      3. A brand new random salt is generated and vault.salt is
         overwritten, then the vault is re-saved encrypted under a key
         derived from the new password + new salt.
    """

    def __init__(self, parent, paths: VaultPaths, current_fernet, current_password: str,
                 entries: list, on_changed):
        super().__init__(parent)
        self.paths = paths
        self.current_fernet = current_fernet
        self.current_password = current_password
        self.entries = entries
        self.on_changed = on_changed

        self.title("Change Master Password")
        self.configure(bg=Palette.surface)
        self.geometry("380x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        def label(text):
            tk.Label(
                self, text=text, font=(Palette.font_family, 9, "bold"),
                fg=Palette.text_dim, bg=Palette.surface, anchor="w",
            ).pack(fill="x", padx=24, pady=(16, 2))

        def pw_entry(var):
            e = tk.Entry(
                self, textvariable=var, show="•",
                font=(Palette.font_family, 12),
                bg=Palette.surface_alt, fg=Palette.text,
                insertbackground=Palette.text, relief="flat",
            )
            e.pack(fill="x", padx=24, ipady=8)
            return e

        label("Current master password")
        self.current_var = tk.StringVar()
        pw_entry(self.current_var)

        label("New master password")
        self.new_var = tk.StringVar()
        pw_entry(self.new_var)
        self.new_var.trace_add("write", lambda *a: self._update_strength())

        self.strength_meter = StrengthMeter(self)
        self.strength_meter.pack(fill="x", padx=24, pady=(2, 0))

        label("Confirm new password")
        self.confirm_var = tk.StringVar()
        pw_entry(self.confirm_var)

        self.error_label = tk.Label(
            self, text="", font=(Palette.font_family, 9),
            fg=Palette.danger, bg=Palette.surface,
        )
        self.error_label.pack(pady=(10, 4))

        btn_row = tk.Frame(self, bg=Palette.surface)
        btn_row.pack(fill="x", padx=24, pady=16, side="bottom")

        tk.Button(
            btn_row, text="Cancel", font=(Palette.font_family, 10),
            bg=Palette.surface, fg=Palette.text_dim, relief="flat",
            cursor="hand2", command=self.destroy,
        ).pack(side="left")

        tk.Button(
            btn_row, text="Change Password", font=(Palette.font_family, 10, "bold"),
            bg=Palette.accent, fg="#0f1115", relief="flat",
            cursor="hand2", command=self.submit, width=16, pady=6,
        ).pack(side="right")

    def _update_strength(self) -> None:
        self.strength_meter.update_strength(estimate_strength(self.new_var.get()))

    def submit(self) -> None:
        current = self.current_var.get()
        new = self.new_var.get()
        confirm = self.confirm_var.get()

        if current != self.current_password:
            self.error_label.config(text="Current password is incorrect.")
            return
        if len(new) < 8:
            self.error_label.config(text="New password must be at least 8 characters.")
            return
        if new != confirm:
            self.error_label.config(text="New passwords do not match.")
            return
        if new == current:
            self.error_label.config(text="New password must differ from the current one.")
            return

        new_salt = generate_salt()
        new_fernet = make_fernet(new, new_salt)

        # Persist new salt, then re-save the vault under the new key.
        with open(self.paths.salt_file, "wb") as f:
            f.write(new_salt)
        save_vault(new_fernet, self.paths, self.entries)

        messagebox.showinfo("Success", "Master password changed successfully.")
        self.on_changed(new_fernet, new)
        self.destroy()
