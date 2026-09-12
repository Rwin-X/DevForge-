"""
PassVault — A minimal, secure, local password manager.

Security design:
- Your master password is NEVER stored anywhere.
- A random salt is generated once and saved (salt is not secret).
- The master password + salt are run through PBKDF2-HMAC-SHA256
  (390,000 iterations) to derive an encryption key.
- All vault data is encrypted at rest with Fernet (AES-128-CBC + HMAC).
- If you forget your master password, the vault CANNOT be recovered.
  This is by design — there are no backdoors.

Run:
    python passvault.py

Data files (created next to this script):
    vault.dat   -> encrypted database (unreadable without master password)
    vault.salt  -> random salt (not secret, but required to derive the key)
"""

import base64
import hashlib
import json
import os
import secrets
import string
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

APP_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_FILE = os.path.join(APP_DIR, "vault.dat")
SALT_FILE = os.path.join(APP_DIR, "vault.salt")

KDF_ITERATIONS = 390_000


# --------------------------------------------------------------------------
# Crypto helpers
# --------------------------------------------------------------------------

def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from the master password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def load_or_create_salt() -> bytes:
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, "rb") as f:
            return f.read()
    salt = secrets.token_bytes(16)
    with open(SALT_FILE, "wb") as f:
        f.write(salt)
    return salt


def vault_exists() -> bool:
    return os.path.exists(VAULT_FILE)


def load_vault(fernet: Fernet) -> list:
    """Load and decrypt the vault. Raises InvalidToken on wrong password."""
    if not vault_exists():
        return []
    with open(VAULT_FILE, "rb") as f:
        encrypted = f.read()
    if not encrypted:
        return []
    decrypted = fernet.decrypt(encrypted)
    return json.loads(decrypted.decode("utf-8"))


def save_vault(fernet: Fernet, entries: list) -> None:
    data = json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
    encrypted = fernet.encrypt(data)
    with open(VAULT_FILE, "wb") as f:
        f.write(encrypted)


def generate_password(length: int = 20, use_symbols: bool = True) -> str:
    alphabet = string.ascii_letters + string.digits
    if use_symbols:
        alphabet += "!@#$%^&*()-_=+[]{}"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# --------------------------------------------------------------------------
# Color palette — minimal, calm, dark theme
# --------------------------------------------------------------------------

class Palette:
    bg = "#0f1115"
    surface = "#161920"
    surface_alt = "#1c2029"
    border = "#262b36"
    text = "#e8eaed"
    text_dim = "#8b92a3"
    accent = "#6ea8fe"
    accent_dim = "#3d5a8a"
    danger = "#e56b6b"
    success = "#5fbf8a"
    font_family = "Helvetica"


# --------------------------------------------------------------------------
# Scrollable frame helper
# --------------------------------------------------------------------------

class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        canvas = tk.Canvas(self, bg=Palette.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def resize_inner(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", resize_inner)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


# --------------------------------------------------------------------------
# Login / Setup screen
# --------------------------------------------------------------------------

class LoginScreen(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master, bg=Palette.bg)
        self.on_success = on_success
        self.salt = load_or_create_salt()
        self.is_new = not vault_exists()

        container = tk.Frame(self, bg=Palette.bg)
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(
            container,
            text="PassVault",
            font=(Palette.font_family, 28, "bold"),
            fg=Palette.text,
            bg=Palette.bg,
        )
        title.pack(pady=(0, 4))

        subtitle_text = (
            "Create a master password to start your vault"
            if self.is_new
            else "Enter your master password to unlock"
        )
        subtitle = tk.Label(
            container,
            text=subtitle_text,
            font=(Palette.font_family, 11),
            fg=Palette.text_dim,
            bg=Palette.bg,
        )
        subtitle.pack(pady=(0, 28))

        self.pw_var = tk.StringVar()
        entry = tk.Entry(
            container,
            textvariable=self.pw_var,
            show="•",
            font=(Palette.font_family, 13),
            bg=Palette.surface,
            fg=Palette.text,
            insertbackground=Palette.text,
            relief="flat",
            width=30,
            justify="center",
        )
        entry.pack(ipady=10, pady=(0, 8))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self.submit())

        if self.is_new:
            self.pw_confirm_var = tk.StringVar()

            confirm_label = tk.Label(
                container,
                text="Confirm password",
                font=(Palette.font_family, 9),
                fg=Palette.text_dim,
                bg=Palette.bg,
                anchor="w",
            )
            confirm_label.pack(fill="x")
            entry2 = tk.Entry(
                container,
                textvariable=self.pw_confirm_var,
                show="•",
                font=(Palette.font_family, 13),
                bg=Palette.surface,
                fg=Palette.text,
                insertbackground=Palette.text,
                relief="flat",
                width=30,
                justify="center",
            )
            entry2.pack(ipady=10, pady=(0, 8))
            entry2.bind("<Return>", lambda e: self.submit())
            self.confirm_entry = entry2

        self.error_label = tk.Label(
            container,
            text="",
            font=(Palette.font_family, 9),
            fg=Palette.danger,
            bg=Palette.bg,
        )
        self.error_label.pack(pady=(4, 12))

        btn_text = "Create Vault" if self.is_new else "Unlock"
        unlock_btn = tk.Button(
            container,
            text=btn_text,
            font=(Palette.font_family, 12, "bold"),
            bg=Palette.accent,
            fg="#0f1115",
            activebackground=Palette.accent_dim,
            activeforeground=Palette.text,
            relief="flat",
            cursor="hand2",
            width=24,
            pady=8,
            command=self.submit,
        )
        unlock_btn.pack(pady=(4, 0))

        if self.is_new:
            note = tk.Label(
                container,
                text="⚠ There is no password recovery.\nIf you forget this, your data is unrecoverable.",
                font=(Palette.font_family, 9),
                fg=Palette.text_dim,
                bg=Palette.bg,
                justify="center",
            )
            note.pack(pady=(20, 0))

    def submit(self):
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
            key = derive_key(pw, self.salt)
            fernet = Fernet(key)
            save_vault(fernet, [])
            self.on_success(fernet)
        else:
            key = derive_key(pw, self.salt)
            fernet = Fernet(key)
            try:
                entries = load_vault(fernet)
            except (InvalidToken, Exception):
                self.error_label.config(text="Incorrect master password.")
                return
            self.on_success(fernet, entries)


# --------------------------------------------------------------------------
# Entry editor dialog
# --------------------------------------------------------------------------

class EntryDialog(tk.Toplevel):
    def __init__(self, parent, on_save, entry=None):
        super().__init__(parent)
        self.on_save = on_save
        self.entry = entry or {}
        self.title("Edit Entry" if entry else "New Entry")
        self.configure(bg=Palette.surface)
        self.geometry("420x460")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 24, "pady": (14, 4)}

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

        make_label("Name")
        name_entry = make_entry(self.name_var)
        name_entry.focus_set()

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

        toggle_btn = tk.Button(
            pw_row, text="👁", font=(Palette.font_family, 10),
            bg=Palette.surface_alt, fg=Palette.text_dim, relief="flat",
            cursor="hand2", command=self.toggle_pw, width=3,
        )
        toggle_btn.pack(side="left", padx=(6, 0), fill="y")

        gen_btn = tk.Button(
            pw_row, text="⟳", font=(Palette.font_family, 10),
            bg=Palette.surface_alt, fg=Palette.accent, relief="flat",
            cursor="hand2", command=self.generate, width=3,
        )
        gen_btn.pack(side="left", padx=(6, 0), fill="y")

        make_label("Website / URL")
        make_entry(self.url_var)

        make_label("Notes")
        notes_frame = tk.Frame(self, bg=Palette.surface_alt)
        notes_frame.pack(fill="both", expand=True, padx=24, pady=(0, 4))
        self.notes_text = tk.Text(
            notes_frame, font=(Palette.font_family, 11),
            bg=Palette.surface_alt, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
            height=5, wrap="word", padx=8, pady=8,
        )
        self.notes_text.pack(fill="both", expand=True)
        self.notes_text.insert("1.0", self.entry.get("notes", ""))

        btn_row = tk.Frame(self, bg=Palette.surface)
        btn_row.pack(fill="x", padx=24, pady=16)

        cancel_btn = tk.Button(
            btn_row, text="Cancel", font=(Palette.font_family, 10),
            bg=Palette.surface, fg=Palette.text_dim, relief="flat",
            cursor="hand2", command=self.destroy,
        )
        cancel_btn.pack(side="left")

        save_btn = tk.Button(
            btn_row, text="Save", font=(Palette.font_family, 10, "bold"),
            bg=Palette.accent, fg="#0f1115", relief="flat",
            cursor="hand2", command=self.save, width=12, pady=6,
        )
        save_btn.pack(side="right")

    def toggle_pw(self):
        self.show_pw = not self.show_pw
        self.pw_entry.config(show="" if self.show_pw else "•")

    def generate(self):
        self.password_var.set(generate_password())
        self.show_pw = True
        self.pw_entry.config(show="")

    def save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Please give this entry a name.")
            return
        result = {
            "id": self.entry.get("id") or secrets.token_hex(8),
            "name": name,
            "username": self.username_var.get().strip(),
            "password": self.password_var.get(),
            "url": self.url_var.get().strip(),
            "notes": self.notes_text.get("1.0", "end-1c").strip(),
            "created": self.entry.get("created", time.time()),
            "updated": time.time(),
        }
        self.on_save(result)
        self.destroy()


# --------------------------------------------------------------------------
# Main vault view
# --------------------------------------------------------------------------

class VaultScreen(tk.Frame):
    def __init__(self, master, fernet: Fernet, entries: list):
        super().__init__(master, bg=Palette.bg)
        self.fernet = fernet
        self.entries = entries
        self.selected_id = None
        self.revealed = set()

        self.build_layout()
        self.refresh_list()

    # ---- layout ----

    def build_layout(self):
        # Top bar
        top_bar = tk.Frame(self, bg=Palette.surface, height=56)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        title = tk.Label(
            top_bar, text="PassVault", font=(Palette.font_family, 15, "bold"),
            fg=Palette.text, bg=Palette.surface,
        )
        title.pack(side="left", padx=20)

        add_btn = tk.Button(
            top_bar, text="+  New Entry", font=(Palette.font_family, 10, "bold"),
            bg=Palette.accent, fg="#0f1115", relief="flat",
            cursor="hand2", command=self.new_entry, padx=14, pady=6,
        )
        add_btn.pack(side="right", padx=20)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_list())
        search_entry = tk.Entry(
            top_bar, textvariable=self.search_var,
            font=(Palette.font_family, 11),
            bg=Palette.surface_alt, fg=Palette.text,
            insertbackground=Palette.text, relief="flat",
            width=30,
        )
        search_entry.pack(side="right", padx=(0, 12), ipady=6)
        search_placeholder = tk.Label(
            top_bar, text="🔍", font=(Palette.font_family, 10),
            fg=Palette.text_dim, bg=Palette.surface,
        )

        # Body: split list / detail
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

    def show_empty_detail(self):
        for w in self.detail_panel.winfo_children():
            w.destroy()
        label = tk.Label(
            self.detail_panel,
            text="Select an entry or create a new one",
            font=(Palette.font_family, 11),
            fg=Palette.text_dim, bg=Palette.bg,
        )
        label.place(relx=0.5, rely=0.5, anchor="center")

    # ---- list ----

    def refresh_list(self):
        for w in self.scroll_frame.inner.winfo_children():
            w.destroy()

        query = self.search_var.get().lower().strip()
        filtered = [
            e for e in self.entries
            if query in e["name"].lower()
            or query in e.get("username", "").lower()
            or query in e.get("url", "").lower()
        ]
        filtered.sort(key=lambda e: e["name"].lower())

        if not filtered:
            empty = tk.Label(
                self.scroll_frame.inner,
                text="No entries yet" if not query else "No matches",
                font=(Palette.font_family, 10),
                fg=Palette.text_dim, bg=Palette.bg,
            )
            empty.pack(pady=20)
            return

        for e in filtered:
            self.build_list_item(e)

    def build_list_item(self, entry):
        is_selected = entry["id"] == self.selected_id
        bg = Palette.surface_alt if is_selected else Palette.bg

        item = tk.Frame(self.scroll_frame.inner, bg=bg, cursor="hand2")
        item.pack(fill="x")

        inner = tk.Frame(item, bg=bg)
        inner.pack(fill="x", padx=16, pady=10)

        name_lbl = tk.Label(
            inner, text=entry["name"], font=(Palette.font_family, 11, "bold"),
            fg=Palette.text, bg=bg, anchor="w",
        )
        name_lbl.pack(fill="x")

        sub = entry.get("username") or entry.get("url") or ""
        sub_lbl = tk.Label(
            inner, text=sub, font=(Palette.font_family, 9),
            fg=Palette.text_dim, bg=bg, anchor="w",
        )
        sub_lbl.pack(fill="x")

        sep = tk.Frame(self.scroll_frame.inner, bg=Palette.border, height=1)
        sep.pack(fill="x")

        for widget in (item, inner, name_lbl, sub_lbl):
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
        header.pack(fill="x", pady=(0, 20))

        tk.Label(
            header, text=entry["name"], font=(Palette.font_family, 20, "bold"),
            fg=Palette.text, bg=Palette.bg, anchor="w",
        ).pack(side="left")

        actions = tk.Frame(header, bg=Palette.bg)
        actions.pack(side="right")

        edit_btn = tk.Button(
            actions, text="Edit", font=(Palette.font_family, 9),
            bg=Palette.surface_alt, fg=Palette.text, relief="flat",
            cursor="hand2", padx=12, pady=5,
            command=lambda: self.edit_entry(entry),
        )
        edit_btn.pack(side="left", padx=(0, 8))

        del_btn = tk.Button(
            actions, text="Delete", font=(Palette.font_family, 9),
            bg=Palette.surface_alt, fg=Palette.danger, relief="flat",
            cursor="hand2", padx=12, pady=5,
            command=lambda: self.delete_entry(entry),
        )
        del_btn.pack(side="left")

        def field_row(label, value, secret=False, key="username"):
            row = tk.Frame(wrapper, bg=Palette.surface, cursor="hand2" if value else "arrow")
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

            val_lbl = tk.Label(
                content, text=display_value, font=(Palette.font_family, 12),
                fg=Palette.text, bg=Palette.surface, anchor="w",
            )
            val_lbl.pack(fill="x", pady=(2, 0))

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

                reveal_btn = tk.Button(
                    btn_row,
                    text="Hide" if entry["id"] in self.revealed else "Show",
                    font=(Palette.font_family, 8),
                    bg=Palette.surface, fg=Palette.text_dim, relief="flat",
                    cursor="hand2", command=toggle_reveal,
                )
                reveal_btn.pack(side="left", padx=(12, 0))

            return row

        field_row("USERNAME / EMAIL", entry.get("username", ""))
        field_row("PASSWORD", entry.get("password", ""), secret=True)
        field_row("WEBSITE", entry.get("url", ""))

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
        EntryDialog(self, on_save=self.add_entry)

    def add_entry(self, entry):
        self.entries.append(entry)
        self.persist()
        self.refresh_list()
        self.select_entry(entry["id"])

    def edit_entry(self, entry):
        def save_edit(updated):
            idx = next(i for i, e in enumerate(self.entries) if e["id"] == entry["id"])
            self.entries[idx] = updated
            self.persist()
            self.refresh_list()
            self.select_entry(updated["id"])

        EntryDialog(self, on_save=save_edit, entry=entry)

    def delete_entry(self, entry):
        if not messagebox.askyesno(
            "Delete entry", f"Delete '{entry['name']}'? This cannot be undone."
        ):
            return
        self.entries = [e for e in self.entries if e["id"] != entry["id"]]
        self.selected_id = None
        self.persist()
        self.refresh_list()
        self.show_empty_detail()

    def persist(self):
        save_vault(self.fernet, self.entries)


# --------------------------------------------------------------------------
# App shell
# --------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PassVault")
        self.geometry("880x560")
        self.minsize(720, 480)
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

        self.current_screen = None
        self.show_login()

    def show_login(self):
        if self.current_screen:
            self.current_screen.destroy()
        self.current_screen = LoginScreen(self, on_success=self.on_unlocked)
        self.current_screen.pack(fill="both", expand=True)

    def on_unlocked(self, fernet, entries=None):
        if self.current_screen:
            self.current_screen.destroy()
        self.current_screen = VaultScreen(self, fernet, entries or [])
        self.current_screen.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = App()
    app.mainloop()
