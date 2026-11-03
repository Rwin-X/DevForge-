"""Application shell: sidebar navigation, page header, theme switching, settings, background jobs."""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path

from . import APP_NAME, __version__
from . import netio, ui
from .pages_a import OverviewPage, SimPage, TransportPage
from .pages_b import ConvertPage, OsiPage, PortsPage, SubnetPage
from .pages_c import DrillsPage, LivePage, ReferencePage
from .ui import T, ScrollFrame, hairline, label

PAGES = [OverviewPage, TransportPage, SimPage, SubnetPage, ConvertPage, PortsPage, OsiPage, ReferencePage, LivePage,
         DrillsPage]
SETTINGS_PATH = Path.home() / ".netplus_lab.json"


class App:
    def __init__(self, theme: str | None = None, start: str = "overview"):
        self.settings = self._load()
        self.lab = netio.EchoLab()  # lives in the app so it survives theme rebuilds
        self.current = None
        self.pages: dict[str, object] = {}
        self.sf: dict[str, ScrollFrame] = {}
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}  ·  Network+ toolkit")
        self.root.geometry("1280x820")
        self.root.minsize(1060, 680)
        ui.init_fonts(self.root)
        T.set(theme or self.settings.get("theme", "dark"))
        ui.set_flash(self.flash)
        ui.install_wheel(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._flash_job = None
        self.build(start)

    # -- settings ------------------------------------------------------------------
    @staticmethod
    def _load() -> dict:
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save_settings(self) -> None:
        try:
            SETTINGS_PATH.write_text(json.dumps(self.settings, indent=1), encoding="utf-8")
        except OSError:
            pass

    # -- layout ----------------------------------------------------------------------
    def build(self, start: str) -> None:
        for w in self.root.winfo_children():
            w.destroy()
        self.pages.clear()
        self.sf.clear()
        ui.apply_style(self.root)
        self.root.configure(bg=T["bg"])
        shell = tk.Frame(self.root, bg=T["bg"])
        shell.pack(fill="both", expand=True)

        side = tk.Frame(shell, bg=T["bg"], width=232)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(shell, width=1, bg=T["line"]).pack(side="left", fill="y")
        brand = tk.Frame(side, bg=T["bg"])
        brand.pack(fill="x", padx=24, pady=(28, 30))
        tk.Label(brand, text="NET+", font=(T.sans, 20, "bold"), fg=T["fg"], bg=T["bg"]).pack(side="left")
        tk.Label(brand, text=" LAB", font=(T.sans, 20), fg=T["mut"], bg=T["bg"]).pack(side="left")
        self.nav_items = {}
        for i, cls in enumerate(PAGES):
            row = tk.Frame(side, bg=T["bg"], cursor="hand2")
            row.pack(fill="x")
            bar = tk.Frame(row, width=2, bg=T["bg"])
            bar.pack(side="left", fill="y")
            num = label(row, f"{i + 1:02d}", "lab", bg=T["bg"], width=3)
            num.pack(side="left", padx=(22, 0), pady=8)
            nm = label(row, cls.nav, "body", bg=T["bg"])
            nm.pack(side="left", pady=8)
            for w in (row, num, nm, bar):
                w.bind("<Button-1>", lambda e, k=cls.key: self.show(k))
            self.nav_items[cls.key] = (bar, num, nm)
        tk.Frame(side, bg=T["bg"]).pack(fill="both", expand=True)
        foot = tk.Frame(side, bg=T["bg"])
        foot.pack(fill="x", padx=24, pady=(0, 22))
        ui.Btn(foot, "Light mode" if T.name == "dark" else "Dark mode", self.toggle_theme).pack(anchor="w")
        label(foot, f"v{__version__}  ·  stdlib only", "small").pack(anchor="w", pady=(10, 0))

        main = tk.Frame(shell, bg=T["bg"])
        main.pack(side="left", fill="both", expand=True)
        head = tk.Frame(main, bg=T["bg"])
        head.pack(fill="x", padx=40, pady=(30, 0))
        self.eyebrow = label(head, "", "lab")
        self.eyebrow.pack(anchor="w")
        self.title = label(head, "", "display")
        self.title.pack(anchor="w", pady=(6, 4))
        self.subtitle = label(head, "", "small")
        self.subtitle.pack(fill="x", pady=(0, 18))
        ui.wrap(self.subtitle)
        tk.Frame(main, height=1, bg=T["fg"]).pack(fill="x", padx=40)       # the one strong rule
        self.body = tk.Frame(main, bg=T["bg"])
        self.body.pack(fill="both", expand=True, padx=(40, 0))
        status = tk.Frame(main, bg=T["bg"])
        status.pack(fill="x", side="bottom")
        hairline(status)
        self.status = label(status, "Click any result value to copy it.", "small")
        self.status.pack(anchor="e", padx=40, pady=6)
        self.current = None
        self.show(start)

    def show(self, key: str) -> None:
        if self.current == key:
            return
        if self.current in self.pages:
            self.pages[self.current].on_hide()
            self.sf[self.current].pack_forget()
        cls = next(c for c in PAGES if c.key == key)
        if key not in self.pages:
            sf = ScrollFrame(self.body)
            self.sf[key] = sf
            inner = tk.Frame(sf.inner, bg=T["bg"])
            inner.pack(fill="both", expand=True, padx=(0, 40), pady=(26, 40))
            self.pages[key] = cls(self, inner)
        self.sf[key].pack(fill="both", expand=True)
        self.sf[key].to_top()
        self.current = key
        self.eyebrow.configure(text=cls.eyebrow.upper())
        self.title.configure(text=cls.title)
        self.subtitle.configure(text=cls.sub)
        for k, (bar, num, nm) in self.nav_items.items():
            on = k == key
            bar.configure(bg=T["fg"] if on else T["bg"])
            num.configure(fg=T["fg"] if on else T["mut"])
            nm.configure(fg=T["fg"] if on else T["mut"], font=(T.sans, 11, "bold" if on else "normal"))
        self.pages[key].on_show()

    def toggle_theme(self) -> None:
        for p in self.pages.values():
            try:
                p.on_hide()
            except tk.TclError:
                pass
        T.set("light" if T.name == "dark" else "dark")
        self.settings["theme"] = T.name
        self.save_settings()
        cur = self.current or "overview"
        self.build(cur)

    # -- helpers ---------------------------------------------------------------------
    def flash(self, msg: str) -> None:
        try:
            self.status.configure(text=msg, fg=T["fg"])
            if self._flash_job:
                self.root.after_cancel(self._flash_job)
            self._flash_job = self.root.after(2500, lambda: self.status.configure(text="Click any result value to copy it.", fg=T["mut"]))
        except tk.TclError:
            pass

    def run_bg(self, fn, done) -> None:
        """Run fn in a worker thread; call done('ok'|'err', value) on the Tk thread."""
        q: queue.Queue = queue.Queue()

        def work():
            try:
                q.put(("ok", fn()))
            except Exception as e:  # report every failure to the UI instead of dying silently
                q.put(("err", e))

        threading.Thread(target=work, daemon=True).start()

        def poll():
            try:
                kind, val = q.get_nowait()
            except queue.Empty:
                self.root.after(60, poll)
                return
            try:
                done(kind, val)
            except tk.TclError:
                pass       # the page was rebuilt (theme switch) while the job ran

        self.root.after(60, poll)

    def close(self) -> None:
        try:
            self.lab.stop()
        finally:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    App().run()
