"""
__main__.py — Application entry point and top-level App shell.

Run with:
    python -m passvault
or via the convenience launcher:
    python run.py
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

from .storage import VaultPaths
from .theme import Palette
from .ui.login_screen import LoginScreen
from .ui.vault_screen import VaultScreen

# Lock the vault automatically after this many milliseconds of no
# keyboard/mouse activity. Set to None to disable auto-lock.
AUTO_LOCK_MS = 5 * 60 * 1000  # 5 minutes


class App(tk.Tk):
    def __init__(self, vault_dir: str | None = None):
        super().__init__()
        self.title("PassVault")
        self.geometry("920x580")
        self.minsize(760, 480)
        self.configure(bg=Palette.bg)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=Palette.bg)
        style.configure(
            "Vertical.TScrollbar",
            background=Palette.surface_alt,
            troughcolor=Palette.bg,
            bordercolor=Palette.bg,
            arrowcolor=Palette.text_dim,
        )

        self.paths = VaultPaths(vault_dir or os.getcwd())
        self.current_screen = None
        self._idle_after_id = None

        self.show_login()
        self._reset_idle_timer()
        # Any activity anywhere in the window resets the auto-lock clock.
        self.bind_all("<Any-KeyPress>", lambda e: self._reset_idle_timer(), add="+")
        self.bind_all("<Any-Button>", lambda e: self._reset_idle_timer(), add="+")
        self.bind_all("<Motion>", lambda e: self._reset_idle_timer(), add="+")

    # ---- screens ----

    def show_login(self):
        if self.current_screen:
            self.current_screen.destroy()
        self.current_screen = LoginScreen(self, self.paths, on_success=self.on_unlocked)
        self.current_screen.pack(fill="both", expand=True)

    def on_unlocked(self, fernet, master_password, entries):
        if self.current_screen:
            self.current_screen.destroy()
        self.current_screen = VaultScreen(self, self.paths, fernet, master_password, entries or [])
        self.current_screen.pack(fill="both", expand=True)

    # ---- auto-lock ----

    def _reset_idle_timer(self):
        if AUTO_LOCK_MS is None:
            return
        if self._idle_after_id is not None:
            self.after_cancel(self._idle_after_id)
        # Only arm the auto-lock while a vault is actually unlocked.
        if isinstance(self.current_screen, VaultScreen):
            self._idle_after_id = self.after(AUTO_LOCK_MS, self._lock_now)
        else:
            self._idle_after_id = None

    def _lock_now(self):
        if isinstance(self.current_screen, VaultScreen):
            self.show_login()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
