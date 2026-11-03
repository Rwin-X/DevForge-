"""Pages: Reference, Live tools, Drills."""

from __future__ import annotations

import ipaddress
import queue
import random
import threading
import time
import tkinter as tk

from . import data, netio, quiz
from .pages_a import Page
from .subnet import NetError
from .ui import (T, Btn, KV, Seg, Table, Tabs, TextBox, card, combo, entry, flash, hairline, label, scale, wrap)


# --------------------------------------------------------------------------
# Reference
# --------------------------------------------------------------------------
class ReferencePage(Page):
    key, nav = "reference", "Reference"
    eyebrow, title = "Cheat sheets", "Reference"
    sub = "Compact tables for the facts you are expected to know cold."

    def build(self) -> None:
        wrapper = tk.Frame(self.parent, bg=T["bg"])
        wrapper.pack(fill="both", expand=True)
        left = tk.Frame(wrapper, bg=T["bg"], width=210)
        left.pack(side="left", fill="y", anchor="n", padx=(0, 28))
        right = tk.Frame(wrapper, bg=T["bg"])
        right.pack(side="left", fill="both", expand=True)
        self.items = {}
        for key, name, *_ in data.REFERENCE:
            lb = label(left, name, "body", cursor="hand2")
            lb.pack(anchor="w", pady=4)
            lb.bind("<Button-1>", lambda e, k=key: self.show(k))
            self.items[key] = lb
        self.head = label(right, "", "h2")
        self.head.pack(anchor="w", pady=(0, 10))
        self.holder = tk.Frame(right, bg=T["bg"])
        self.holder.pack(fill="x")
        self.note = label(right, "", "small")
        self.note.pack(fill="x", pady=(12, 0))
        wrap(self.note)
        self.cur = None
        self.show(data.REFERENCE[0][0])

    def show(self, key) -> None:
        for k, lb in self.items.items():
            on = k == key
            lb.configure(fg=T["fg"] if on else T["mut"], font=(T.sans, 11, "bold" if on else "normal"))
        for w in self.holder.winfo_children():
            w.destroy()
        _k, name, cols, rows, note = next(r for r in data.REFERENCE if r[0] == key)
        self.head.configure(text=name)
        widths = []
        for i, c in enumerate(cols):
            longest = max([len(c)] + [len(r[i]) for r in rows])
            widths.append(min(max(90, longest * 8 + 20), 340 if i < len(cols) - 1 else 600))
        Table(self.holder, cols, widths, rows, height=min(max(len(rows), 6), 14), detail=True).pack(fill="x")
        self.note.configure(text=note)


# --------------------------------------------------------------------------
# Live tools
# --------------------------------------------------------------------------
def hexdump(b: bytes) -> str:
    lines = []
    for i in range(0, len(b), 16):
        chunk = b[i:i + 16]
        hx = " ".join(f"{x:02x}" for x in chunk).ljust(47)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"{i:04x}  {hx}  {asc}")
    return "\n".join(lines)


COMMAND_HINTS = {
    "ping": "Reply times show latency; 'Request timed out' means no ICMP echo reply (host down, or ICMP filtered). TTL hints at the OS and hop count.",
    "traceroute": "Each line is a router. '* * *' means that hop did not answer (often a firewall, not necessarily a fault). Look for where latency jumps or the path stops.",
    "nslookup": "Shows which DNS server answered and what records it returned. 'Non-authoritative answer' means it came from a cache.",
    "ipconfig": "Check IP, mask, gateway and DNS. 169.254.x.x = DHCP failed. A wrong subnet or missing gateway explains most 'cannot reach X' tickets.",
    "arp": "IP-to-MAC mappings the host has learned. Two IPs with the same MAC, or a gateway MAC that suddenly changes, can indicate ARP poisoning.",
    "route": "The routing table: the longest matching prefix wins; 0.0.0.0/0 is the default route. No default route = no off-subnet traffic.",
    "netstat": "Active connections and listeners with their TCP states. Many SYN_RECV suggests a SYN flood; many CLOSE_WAIT suggests an application bug.",
    "hostname": "The name this machine uses on the network.",
}


class LivePage(Page):
    key, nav = "live", "Live tools"
    eyebrow, title = "Real network", "Live Tools"
    sub = "These send real packets. Use them on networks and hosts you own or are authorized to test."

    def build(self) -> None:
        tabs = Tabs(self.parent)
        tabs.pack(fill="both", expand=True)
        self._dns(tabs.add("dns", "DNS query"))
        self._ports(tabs.add("scan", "Port check"))
        self._cmd(tabs.add("cmd", "Commands"))
        self._lab(tabs.add("lab", "Socket lab"))

    def alive(self) -> bool:
        try:
            return bool(self.parent.winfo_exists())
        except tk.TclError:
            return False

    # -- DNS -----------------------------------------------------------------------
    def _dns(self, f) -> None:
        self.para(f, "A hand-built DNS client: the query below is assembled byte by byte and sent over UDP port 53 "
                  "(TCP only if the answer is truncated). Enter an IP address to get a reverse (PTR) lookup.")
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x")
        self.dn = tk.StringVar(value="example.com")
        self.dt = tk.StringVar(value="A")
        self.ds = tk.StringVar(value=netio.system_resolvers()[0])
        for i, (name, w, var, kind) in enumerate((("Name or IP", 28, self.dn, "e"), ("Type", 7, self.dt, "c"),
                                                  ("DNS server", 20, self.ds, "e"))):
            cell = tk.Frame(row, bg=T["bg"])
            cell.grid(row=0, column=i, padx=(0, 18), sticky="w")
            label(cell, name, "lab").pack(anchor="w", pady=(0, 3))
            if kind == "c":
                combo(cell, list(netio.QTYPES), var, width=w).pack(anchor="w", ipady=2)
            else:
                e = entry(cell, var, width=w)
                e.pack(anchor="w", ipady=3)
                e.bind("<Return>", lambda ev: self.dns_go())
        self.dbtn = Btn(row, "Query", self.dns_go, solid=True)
        self.dbtn.grid(row=0, column=3, sticky="s")
        self.d_status = label(f, "", "small")
        self.d_status.pack(fill="x", pady=(10, 0))
        self.d_kv = KV(f, label_w=150)
        self.d_kv.pack(fill="x", pady=(4, 0))
        self.d_tbl = Table(f, ["Name", "Type", "TTL", "Data"], [220, 70, 80, 420], height=6, detail=False)
        self.d_tbl.pack(fill="x", pady=(10, 0))
        label(f, "Query packet on the wire", "lab").pack(anchor="w", pady=(18, 6))
        self.d_hex = TextBox(f, height=6)
        self.d_hex.pack(fill="x")

    def dns_go(self) -> None:
        name, qt, srv = self.dn.get().strip(), self.dt.get(), self.ds.get().strip() or None
        try:
            if not name:
                raise NetError("Enter a name or an IP address.")
            try:
                ipaddress.ip_address(name)
                name, qt = netio.reverse_name(name), "PTR"
            except ValueError:
                pass
            q = netio.build_dns_query(name, qt)
        except NetError as e:
            self.d_status.configure(text=f"—  {e}", fg=T["fg"])
            return
        self.d_hex.set(f"{len(q)} bytes  ·  ID {q[0]:02x}{q[1]:02x}, flags 0100 (recursion desired), 1 question\n\n{hexdump(q)}")
        self.d_status.configure(text=f"Querying {srv or netio.system_resolvers()[0]} for {name} {qt} ...", fg=T["mut"])
        self.dbtn.set_enabled(False)
        self.app.run_bg(lambda: netio.dns_query(name, qt, srv, 3.0), self._dns_done)

    def _dns_done(self, kind, val) -> None:
        if not self.alive():
            return
        self.dbtn.set_enabled(True)
        if kind == "err":
            self.d_status.configure(text=f"—  {val}", fg=T["fg"])
            self.d_kv.set([])
            self.d_tbl.set_rows([])
            return
        r = val
        self.d_status.configure(text="")
        flags = [n for n, on in (("AA authoritative", r["aa"]), ("TC truncated", r["tc"]), ("RD recursion desired", r["rd"]),
                                 ("RA recursion available", r["ra"])) if on]
        self.d_kv.set([("Server", r["server"]), ("Transport", r["transport"]), ("Response code", r["rcode"]),
                       ("Round trip", f"{r['rtt_ms']:.1f} ms"), ("Sizes", f"query {r['query_size']} B  ·  response {r['size']} B"),
                       ("Header flags", ", ".join(flags) or "none"),
                       ("Records", f"{len(r['answers'])} answer, {len(r['authority'])} authority, {len(r['additional'])} additional")])
        rows = [(n, t, ttl, d) for n, t, ttl, d in r["answers"]]
        rows += [(n, t + " (auth)", ttl, d) for n, t, ttl, d in r["authority"]]
        self.d_tbl.set_rows(rows or [("-", "-", "-", f"No records ({r['rcode']})")])

    # -- port check ------------------------------------------------------------------
    def _ports(self, f) -> None:
        self.para(f, "TCP connect check. open = handshake completed; closed = the host answered RST (nothing listening); "
                  "filtered = no answer (firewall dropping, or host unreachable). Only test hosts you are authorized to test.")
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x")
        self.ph = tk.StringVar(value="127.0.0.1")
        self.pp = tk.StringVar(value="22, 53, 80, 443, 3389")
        self.pt = tk.StringVar(value="0.8")
        for i, (name, w, var) in enumerate((("Host", 26, self.ph), ("Ports (list or range)", 30, self.pp), ("Timeout s", 6, self.pt))):
            cell = tk.Frame(row, bg=T["bg"])
            cell.grid(row=0, column=i, padx=(0, 18), sticky="w")
            label(cell, name, "lab").pack(anchor="w", pady=(0, 3))
            e = entry(cell, var, width=w)
            e.pack(anchor="w", ipady=3)
            e.bind("<Return>", lambda ev: self.scan_go())
        self.sbtn = Btn(row, "Check", self.scan_go, solid=True)
        self.sbtn.grid(row=0, column=3, sticky="s")
        self.sstop = Btn(row, "Stop", self.scan_stop)
        self.sstop.grid(row=0, column=4, sticky="s", padx=8)
        self.s_status = label(f, "", "small")
        self.s_status.pack(fill="x", pady=(10, 6))
        self.s_tbl = Table(f, ["Port", "Service", "State", "Time"], [80, 220, 120, 120], height=9, detail=False, stretch=3)
        self.s_tbl.pack(fill="x")
        self._stop = threading.Event()
        self._prog = (0, 0)
        self._scanning = False

    def scan_go(self) -> None:
        if self._scanning:
            return
        try:
            ports = netio.parse_ports(self.pp.get())
            tmo = float(self.pt.get())
            if not 0.1 <= tmo <= 10:
                raise NetError("Timeout must be between 0.1 and 10 seconds.")
            host = self.ph.get().strip()
            netio.resolve_host(host)
        except NetError as e:
            self.s_status.configure(text=f"—  {e}", fg=T["fg"])
            return
        except ValueError:
            self.s_status.configure(text="—  Timeout must be a number.", fg=T["fg"])
            return
        self._stop.clear()
        self._scanning = True
        self._prog = (0, len(ports))
        self.sbtn.set_enabled(False)
        self.s_tbl.set_rows([])
        self.app.run_bg(lambda: netio.scan_ports(host, ports, tmo, 100, self._stop,
                                                 lambda d, n: setattr(self, "_prog", (d, n))), self._scan_done)
        self._scan_tick()

    def _scan_tick(self) -> None:
        if self._scanning and self.alive():
            d, n = self._prog
            self.s_status.configure(text=f"Checking ... {d} / {n}", fg=T["mut"])
            self.parent.after(150, self._scan_tick)

    def scan_stop(self) -> None:
        self._stop.set()

    def _scan_done(self, kind, val) -> None:
        self._scanning = False
        if not self.alive():
            return
        self.sbtn.set_enabled(True)
        if kind == "err":
            self.s_status.configure(text=f"—  {val}", fg=T["fg"])
            return
        res = val["results"]
        rows = [(p, netio.service_name(p) or "-", st, f"{ms:.0f} ms" if st != "filtered" else "timeout") for p, (st, ms) in res.items()]
        self.s_tbl.set_rows(rows)
        o = sum(1 for s, _ in res.values() if s == "open")
        c = sum(1 for s, _ in res.values() if s == "closed")
        fl = sum(1 for s, _ in res.values() if s == "filtered")
        self.s_status.configure(text=f"{val['host']} ({val['ip']}):  {o} open  ·  {c} closed  ·  {fl} filtered"
                                + ("   (stopped early)" if val["stopped"] else ""), fg=T["fg"])

    # -- commands --------------------------------------------------------------------
    def _cmd(self, f) -> None:
        self.para(f, "Runs the operating system's own diagnostic tools (no shell, input is validated) and streams the output.")
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x")
        keys = list(netio.COMMANDS)
        self.cc = tk.StringVar(value="ping")
        self.ch = tk.StringVar(value="example.com")
        cell = tk.Frame(row, bg=T["bg"])
        cell.grid(row=0, column=0, padx=(0, 18))
        label(cell, "Command", "lab").pack(anchor="w", pady=(0, 3))
        cb = combo(cell, keys, self.cc, width=14)
        cb.pack(anchor="w", ipady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self._cmd_hint(), add="+")
        cell = tk.Frame(row, bg=T["bg"])
        cell.grid(row=0, column=1, padx=(0, 18))
        label(cell, "Host (when needed)", "lab").pack(anchor="w", pady=(0, 3))
        e = entry(cell, self.ch, width=28)
        e.pack(anchor="w", ipady=3)
        e.bind("<Return>", lambda ev: self.cmd_go())
        self.cbtn = Btn(row, "Run", self.cmd_go, solid=True)
        self.cbtn.grid(row=0, column=2, sticky="s")
        self.cstop = Btn(row, "Stop", lambda: self._cstop.set())
        self.cstop.grid(row=0, column=3, sticky="s", padx=8)
        self.c_hint = label(f, "", "small", fg=T["fg"])
        self.c_hint.pack(fill="x", pady=(12, 8))
        wrap(self.c_hint)
        self.c_out = TextBox(f, height=16)
        self.c_out.pack(fill="x")
        self._cstop = threading.Event()
        self._cq: queue.Queue = queue.Queue()
        self._crun = False
        self._cmd_hint()

    def _cmd_hint(self) -> None:
        self.c_hint.configure(text=COMMAND_HINTS.get(self.cc.get(), ""))

    def cmd_go(self) -> None:
        if self._crun:
            return
        try:
            argv = netio.build_command(self.cc.get(), self.ch.get())
        except NetError as e:
            self.c_out.set(f"—  {e}")
            return
        self.c_out.set("$ " + " ".join(argv) + "\n")
        self._cstop.clear()
        self._crun = True
        self.cbtn.set_enabled(False)

        def work():
            try:
                rc = netio.run_command(argv, lambda s: self._cq.put(("line", s)), self._cstop, 90)
                self._cq.put(("end", rc))
            except OSError as e:
                self._cq.put(("line", f"error: {e}"))
                self._cq.put(("end", -1))

        threading.Thread(target=work, daemon=True).start()
        self._cmd_poll()

    def _cmd_poll(self) -> None:
        if not self.alive():
            return
        try:
            while True:
                kind, val = self._cq.get_nowait()
                if kind == "line":
                    self.c_out.add(val + "\n")
                else:
                    self.c_out.add(f"\n[finished, exit code {val}]\n", "m")
                    self._crun = False
                    self.cbtn.set_enabled(True)
                    return
        except queue.Empty:
            pass
        self.parent.after(60, self._cmd_poll)

    # -- socket lab --------------------------------------------------------------------
    def _lab(self, f) -> None:
        self.para(f, "A real TCP and UDP echo server on your own machine (127.0.0.1). Send messages and compare what each protocol does: "
                  "TCP connects, delivers and closes; UDP just sends, and a lost datagram is simply gone.")
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x")
        self.lp = tk.StringVar(value="5050")
        self.lm = tk.StringVar(value="hello network")
        self.ll = tk.IntVar(value=0)
        cell = tk.Frame(row, bg=T["bg"])
        cell.grid(row=0, column=0, padx=(0, 18))
        label(cell, "Port", "lab").pack(anchor="w", pady=(0, 3))
        entry(cell, self.lp, width=8).pack(anchor="w", ipady=3)
        self.lstart = Btn(row, "Start server", self.lab_toggle, solid=True)
        self.lstart.grid(row=0, column=1, sticky="s", padx=(0, 24))
        cell = tk.Frame(row, bg=T["bg"])
        cell.grid(row=0, column=2, padx=(0, 18))
        self.lloss = label(cell, "UDP packet loss: 0%", "lab")
        self.lloss.pack(anchor="w", pady=(0, 3))
        scale(cell, self.ll, 0, 100, command=self._loss, length=190).pack(anchor="w")
        row2 = tk.Frame(f, bg=T["bg"])
        row2.pack(fill="x", pady=(14, 0))
        cell = tk.Frame(row2, bg=T["bg"])
        cell.pack(side="left", padx=(0, 18))
        label(cell, "Message", "lab").pack(anchor="w", pady=(0, 3))
        entry(cell, self.lm, width=34).pack(anchor="w", ipady=3)
        Btn(row2, "Send via TCP", lambda: self._send("tcp")).pack(side="left", pady=(18, 0))
        Btn(row2, "Send via UDP", lambda: self._send("udp")).pack(side="left", padx=8, pady=(18, 0))
        Btn(row2, "UDP with 3 app retries", lambda: self._send("udp3")).pack(side="left", pady=(18, 0))
        Btn(row2, "Clear", lambda: self.l_out.clear()).pack(side="left", padx=8, pady=(18, 0))
        self.l_out = TextBox(f, height=14)
        self.l_out.pack(fill="x", pady=(14, 0))
        self.l_out.text.tag_configure("srv", foreground=T["mut"])
        self._lab_poll()
        self._lab_sync()

    def _lab_sync(self) -> None:
        self.lstart.set_text("Stop server" if self.app.lab.running else "Start server")

    def _port(self) -> int:
        try:
            port = int(self.lp.get())
        except ValueError:
            raise NetError("Port must be a whole number.") from None
        if not 1024 <= port <= 65535:
            raise NetError("Use a port between 1024 and 65535.")
        return port

    def lab_toggle(self) -> None:
        lab = self.app.lab
        if lab.running:
            lab.stop()
        else:
            try:
                lab.port = self._port()
                lab.udp_loss = self.ll.get() / 100
                lab.start()
            except NetError as e:
                self.l_out.add(f"—  {e}\n")
        self._lab_sync()

    def _loss(self, v) -> None:
        self.lloss.configure(text=f"UDP packet loss: {int(float(v))}%")
        self.app.lab.udp_loss = float(v) / 100

    def _send(self, how) -> None:
        msg = self.lm.get()
        if not msg:
            return
        try:
            port = self._port()
        except NetError as e:
            self.l_out.add(f"—  {e}\n")
            return
        lab = self.app.lab
        if not lab.running:
            self.l_out.add("(server is not running: expect 'refused' for TCP and 'no reply' / 'unreachable' for UDP)\n", "m")

        def work():
            if how == "tcp":
                netio.tcp_client("127.0.0.1", port, msg, 2.0, emit=lab.log)
            elif how == "udp":
                netio.udp_client("127.0.0.1", port, msg, 0.8, 1, emit=lab.log)
            else:
                netio.udp_client("127.0.0.1", port, msg, 0.6, 3, emit=lab.log)
        threading.Thread(target=work, daemon=True).start()

    def _lab_poll(self) -> None:
        if not self.alive():
            return
        try:
            while True:
                ts, who, text = self.app.lab.events.get_nowait()
                self.l_out.add(f"{ts}  {who:<6}  {text}\n", "srv" if who == "SERVER" else None)
        except queue.Empty:
            pass
        self.parent.after(100, self._lab_poll)


# --------------------------------------------------------------------------
# Drills
# --------------------------------------------------------------------------
class DrillsPage(Page):
    key, nav = "drills", "Drills"
    eyebrow, title = "Practice", "Drills"
    sub = "Endless generated questions. Accuracy per topic is saved locally so you can see what to revise."

    def build(self) -> None:
        self.q: quiz.Question | None = None
        self.answered = False
        top = tk.Frame(self.parent, bg=T["bg"])
        top.pack(fill="x")
        self.mode = Seg(top, [("mixed", "Mixed"), ("subnet", "Subnetting"), ("ports", "Ports"), ("osi", "OSI"),
                              ("concepts", "Concepts")], lambda k: self.new_q())
        self.mode.pack(side="left")
        self.stat = label(top, "", "mono")
        self.stat.pack(side="right")
        self.card = card(self.parent)
        self.card.pack(fill="x", pady=(16, 0))
        self.tag = label(self.card, "", "lab", bg=T["card"])
        self.tag.pack(anchor="w", padx=22, pady=(18, 4))
        self.prompt = label(self.card, "", "h2", bg=T["card"])
        self.prompt.pack(fill="x", padx=22)
        wrap(self.prompt, 44)
        self.answer_area = tk.Frame(self.card, bg=T["card"])
        self.answer_area.pack(fill="x", padx=22, pady=(16, 6))
        self.fb = label(self.card, "", "h3", bg=T["card"])
        self.fb.pack(fill="x", padx=22)
        self.expl = label(self.card, "", "small", bg=T["card"], fg=T["fg"])
        self.expl.pack(fill="x", padx=22, pady=(4, 8))
        wrap(self.expl, 44)
        bar = tk.Frame(self.card, bg=T["card"])
        bar.pack(fill="x", padx=22, pady=(0, 18))
        self.submit_btn = Btn(bar, "Check", self.submit, solid=True)
        self.submit_btn.pack(side="left")
        self.next_btn = Btn(bar, "Next  ›", self.new_q)
        self.next_btn.pack(side="left", padx=8)
        label(self.parent, "Accuracy by topic", "lab").pack(anchor="w", pady=(24, 8))
        self.tbl = Table(self.parent, ["Topic", "Correct", "Answered", "Accuracy"], [200, 100, 100, 100], height=6,
                         detail=False, stretch=3)
        self.tbl.pack(fill="x")
        Btn(self.parent, "Reset statistics", self.reset_stats).pack(anchor="w", pady=(12, 0))
        self.session = [0, 0]
        self.streak = 0
        self.rng = random.Random()
        self.parent.winfo_toplevel().bind("<Return>", self._enter, add="+")
        self.new_q()

    def _enter(self, _e=None) -> None:
        try:
            if not self.parent.winfo_exists() or self.app.current != "drills":
                return
        except tk.TclError:
            return
        if self.answered:
            self.new_q()
        elif self.q and self.q.kind == "text":
            self.submit()

    def new_q(self, *_a) -> None:
        self.q = quiz.make_question(self.mode.get(), self.rng)
        self.answered = False
        for w in self.answer_area.winfo_children():
            w.destroy()
        self.tag.configure(text=self.q.tag)
        self.prompt.configure(text=self.q.prompt)
        self.fb.configure(text="")
        self.expl.configure(text="")
        self.next_btn.set_enabled(False)
        self.submit_btn.set_enabled(True)
        if self.q.kind == "text":
            self.var = tk.StringVar()
            self.ent = entry(self.answer_area, self.var, width=26)
            self.ent.pack(anchor="w", ipady=5)
            self.ent.focus_set()
            if self.q.placeholder:
                label(self.answer_area, f"format: {self.q.placeholder}", "small", bg=T["card"]).pack(anchor="w", pady=(4, 0))
            self.submit_btn.pack(side="left")
        else:
            self.submit_btn.pack_forget()
            self.choice_btns = []
            for i, ch in enumerate(self.q.choices):
                b = tk.Frame(self.answer_area, bg=T["card"], highlightthickness=1, highlightbackground=T["line"], cursor="hand2")
                b.pack(fill="x", pady=3)
                num = label(b, str(i + 1), "mono", bg=T["card"], fg=T["mut"], width=3)
                num.pack(side="left", padx=(10, 0), pady=7)
                tx = label(b, ch, "body", bg=T["card"])
                tx.pack(side="left", pady=7, fill="x")
                for w in (b, num, tx):
                    w.bind("<Button-1>", lambda e, c=ch: self.choose(c))
                    w.bind("<Enter>", lambda e, bb=b: None if self.answered else bb.configure(highlightbackground=T["fg"]))
                    w.bind("<Leave>", lambda e, bb=b: None if self.answered else bb.configure(highlightbackground=T["line"]))
                self.choice_btns.append((ch, b, num, tx))
        self._refresh_stats()

    def choose(self, ch) -> None:
        if not self.answered:
            self._grade(ch)

    def submit(self) -> None:
        if self.answered or not self.q or self.q.kind != "text":
            return
        if not self.var.get().strip():
            return
        self._grade(self.var.get())

    def _grade(self, given) -> None:
        q = self.q
        ok = quiz.check(q, given)
        self.answered = True
        self.session[1] += 1
        self.session[0] += ok
        self.streak = self.streak + 1 if ok else 0
        self.fb.configure(text="Correct." if ok else f"Not quite.  Answer: {q.answer}")
        self.expl.configure(text=q.explanation)
        self.next_btn.set_enabled(True)
        self.submit_btn.set_enabled(False)
        if q.kind == "mc":
            for ch, b, num, tx in self.choice_btns:
                right, picked = ch == q.answer, ch == given
                if right:
                    for w in (b, num, tx):
                        w.configure(bg=T["fg"])
                    num.configure(fg=T["bg"])
                    tx.configure(fg=T["bg"], font=(T.sans, 11, "bold"))
                elif picked:
                    tx.configure(font=(T.sans, 11, "overstrike"), fg=T["mut"])
                b.configure(highlightbackground=T["fg"] if right else T["line"])
        st = self.app.settings.setdefault("stats", {})
        rec = st.setdefault(q.tag, [0, 0])
        rec[0] += ok
        rec[1] += 1
        self.app.save_settings()
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        right, total = self.session
        self.stat.configure(text=f"session {right}/{total}   streak {self.streak}")
        st = self.app.settings.get("stats", {})
        rows = [(k, v[0], v[1], f"{v[0] / v[1]:.0%}") for k, v in sorted(st.items(), key=lambda kv: kv[1][0] / max(kv[1][1], 1)) if v[1]]
        self.tbl.set_rows(rows or [("No answers yet", "-", "-", "-")])

    def reset_stats(self) -> None:
        self.app.settings["stats"] = {}
        self.app.save_settings()
        self.session = [0, 0]
        self.streak = 0
        self._refresh_stats()
        flash("Statistics reset")
