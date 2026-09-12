"""ui/login_screen.py — Master password entry / vault creation screen."""

from __future__ import annotations

import tkinter as tk

from ..crypto import make_fernet, WrongPasswordError
from ..storage import VaultPaths, load_or_create_salt, load_vault, save_vault
from ..theme import Palette
from ..password_utils import estimate_strength
from .widgets import StrengthMeter


class LoginScreen(tk.Frame):
    def __init__(self, master, paths: VaultPaths, on_success):
        super().__init__(master, bg=Palette.bg)
        self.paths = paths
        self.on_success = on_success
        self.salt = load_or_create_salt(paths)
        self.is_new = not paths.exists()

        container = tk.Frame(self, bg=Palette.bg)
        container.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            container, text="PassVault", font=(Palette.font_family, 28, "bold"),
            fg=Palette.text, bg=Palette.bg,
        ).pack(pady=(0, 4))

        subtitle_text = (
            "Create a master password to start your vault"
            if self.is_new else "Enter your master password to unlock"
        )
        tk.Label(
            container, text=subtitle_text, font=(Palette.font_family, 11),
            fg=Palette.text_dim, bg=Palette.bg,
        ).pack(pady=(0, 28))

        self.pw_var = tk.StringVar()
        entry = tk.Entry(
            container, textvariable=self.pw_var, show="•",
            font=(Palette.font_family, 13), bg=Palette.surface, fg=Palette.text,
            insertbackground=Palette.text, relief="flat", width=30, justify="center",
        )
        entry.pack(ipady=10, pady=(0, 8))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self.submit())

        if self.is_new:
            self.pw_var.trace_add("write", lambda *a: self._update_strength())

            self.strength_meter = StrengthMeter(container)
            self.strength_meter.pack(fill="x", pady=(0, 8))

            tk.Label(
                container, text="Confirm password", font=(Palette.font_family, 9),
                fg=Palette.text_dim, bg=Palette.bg, anchor="w",
            ).pack(fill="x")

            self.pw_confirm_var = tk.StringVar()
            confirm_entry = tk.Entry(
                container, textvariable=self.pw_confirm_var, show="•",
                font=(Palette.font_family, 13), bg=Palette.surface, fg=Palette.text,
                insertbackground=Palette.text, relief="flat", width=30, justify="center",
            )
            confirm_entry.pack(ipady=10, pady=(0, 8))
            confirm_entry.bind("<Return>", lambda e: self.submit())

        self.error_label = tk.Label(
            container, text="", font=(Palette.font_family, 9),
            fg=Palette.danger, bg=Palette.bg,
        )
        self.error_label.pack(pady=(4, 12))

        btn_text = "Create Vault" if self.is_new else "Unlock"
        tk.Button(
            container, text=btn_text, font=(Palette.font_family, 12, "bold"),
            bg=Palette.accent, fg="#0f1115", activebackground=Palette.accent_dim,
            activeforeground=Palette.text, relief="flat", cursor="hand2",
            width=24, pady=8, command=self.submit,
        ).pack(pady=(4, 0))

        if self.is_new:
            tk.Label(
                container,
                text="⚠ There is no password recovery.\nIf you forget this, your data is unrecoverable.",
                font=(Palette.font_family, 9), fg=Palette.text_dim, bg=Palette.bg,
                justify="center",
            ).pack(pady=(20, 0))

    def _update_strength(self) -> None:
        result = estimate_strength(self.pw_var.get())
        self.strength_meter.update_strength(result)

    def submit(self) -> None:
        pw = self.pw_var.get()
        if not pw:
            self.error_label.config(text="Please enter a master password.")
            return

        if self.is_new:
            confirm = self.pw_confirm_var.get()
            if len(pw) < 8:
                self.error_label.config(text="Use at least 8 characters.")
                return
            if pw != confirm:
                self.error_label.config(text="Passwords do not match.")
                return
            fernet = make_fernet(pw, self.salt)
            save_vault(fernet, self.paths, [])
            self.on_success(fernet, pw, [])
        else:
            fernet = make_fernet(pw, self.salt)
            try:
                entries = load_vault(fernet, self.paths)
            except WrongPasswordError:
                self.error_label.config(text="Incorrect master password.")
                return
            self.on_success(fernet, pw, entries)
