"""Pages: Overview, Transport (TCP vs UDP + header diagrams), Simulator."""

from __future__ import annotations

import ipaddress
import random
import tkinter as tk
from tkinter import font as tkfont

from . import data, sim
from .ui import (T, Backdrop, Btn, KV, Seg, Table, Tabs, TextBox, card, check, combo, entry, flash, hairline,
                 label, mix, scale, wrap)


class Page:
    key = ""
    nav = ""
    eyebrow = ""
    title = ""
    sub = ""

    def __init__(self, app, parent):
        self.app, self.parent = app, parent
        self.build()

    def build(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass

    def para(self, parent, text, kind="small", pady=(0, 10), **kw) -> tk.Label:
        lb = label(parent, text, kind, **kw)
        lb.pack(fill="x", pady=pady)
        wrap(lb)
        return lb


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
class OverviewPage(Page):
    key, nav = "overview", "Overview"
    eyebrow, title = "Network+ study toolkit", "Overview"
    sub = "Learn it, calculate it, simulate it, test it. Every module works offline except the live tools."

    TILES = [
        ("transport", "Transport", "TCP vs UDP, bit-accurate header diagrams, flags, options and connection states."),
        ("sim", "Simulator", "Step through a TCP handshake, data transfer, loss, teardown and UDP exchanges."),
        ("subnet", "Subnetting", "Calculator with binary view, VLSM, splitting, summarization and host checks."),
        ("convert", "Converters", "IPv6, EUI-64, number bases, MAC formats, transfer time and TCP window maths."),
        ("ports", "Ports", "Searchable well-known ports and IP protocol numbers with secure alternatives."),
        ("osi", "OSI & Encapsulation", "The seven layers, PDUs, devices, and a live encapsulation builder."),
        ("reference", "Reference", "Cabling, Wi-Fi, DNS records, routing, commands, troubleshooting method."),
        ("live", "Live tools", "Real DNS queries, TCP port checker, system commands and a local socket lab."),
        ("drills", "Drills", "Generated subnetting, ports, OSI and concept questions with tracked accuracy."),
    ]

    def build(self) -> None:
        self.bd = Backdrop(self.parent, height=210)
        self.bd.pack(fill="x", pady=(0, 24))
        grid = tk.Frame(self.parent, bg=T["bg"])
        grid.pack(fill="x")
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="t")
        for i, (key, name, desc) in enumerate(self.TILES):
            self._tile(grid, i, key, name, desc)
        label(self.parent, "Exam domains", "lab").pack(anchor="w", pady=(30, 8))
        row = tk.Frame(self.parent, bg=T["bg"])
        row.pack(fill="x")
        for i, d in enumerate(("Networking Concepts", "Network Implementation", "Network Operations",
                               "Network Security", "Network Troubleshooting")):
            cell = card(row)
            cell.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            row.columnconfigure(i, weight=1, uniform="d")
            label(cell, f"0{i + 1}", "stat", fg=T.dim(.5)).pack(anchor="w", padx=14, pady=(10, 0))
            dl = label(cell, d, "small", fg=T["fg"])
            dl.pack(fill="x", padx=14, pady=(0, 12))
            wrap(dl, 28)
        self.para(self.parent, "Check CompTIA's current exam objectives for the authoritative list and weights. "
                  "This tool teaches the underlying concepts; it does not replace the objectives document.",
                  pady=(14, 0))

    def _tile(self, grid, i, key, name, desc) -> None:
        c = card(grid, cursor="hand2")
        c.grid(row=i // 3, column=i % 3, sticky="nsew", padx=(0 if i % 3 == 0 else 8, 0), pady=(0, 8))
        num = label(c, f"{i + 2:02d}", "lab")
        num.pack(anchor="w", padx=16, pady=(14, 2))
        ttl = label(c, name, "h3")
        ttl.pack(anchor="w", padx=16)
        dsc = label(c, desc, "small")
        dsc.pack(fill="x", padx=16, pady=(4, 16))
        wrap(dsc, 32)
        widgets = (c, num, ttl, dsc)

        def enter(_e):
            c.configure(highlightbackground=T["fg"])

        def leave(_e):
            c.configure(highlightbackground=T["line"])

        for w in widgets:
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
            w.bind("<Button-1>", lambda e, k=key: self.app.show(k))

    def on_show(self) -> None:
        self.bd.start()

    def on_hide(self) -> None:
        self.bd.stop()


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------
class TransportPage(Page):
    key, nav = "transport", "Transport"
    eyebrow, title = "Layer 4", "TCP / UDP"
    sub = "Two ways to move data between processes: guaranteed and ordered, or fast and fire-and-forget."

    def build(self) -> None:
        tabs = Tabs(self.parent)
        tabs.pack(fill="both", expand=True)
        self._compare(tabs.add("cmp", "TCP vs UDP"))
        self._headers(tabs.add("hdr", "Header diagrams"))
        self._flags(tabs.add("flags", "Flags & options"))
        self._states(tabs.add("states", "Connection states"))

    def _compare(self, f) -> None:
        Table(f, ["Property", "TCP", "UDP"], [150, 330, 330], data.TCP_UDP_COMPARE, height=10, detail=False,
              stretch=2).pack(fill="x")
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x", pady=(20, 0))
        for i, (head, body) in enumerate((
            ("Choose TCP when", "Every byte must arrive, in order, and a late answer is better than a wrong one: "
                                "web pages, file transfer, email, remote shells, database traffic."),
            ("Choose UDP when", "Fresh data beats complete data, or the app handles its own recovery: live voice and video, "
                                "games, DNS lookups, DHCP, NTP, SNMP, QUIC (HTTP/3)."),
            ("Exam trap", "DNS uses UDP for ordinary queries but TCP for zone transfers and responses too large for one datagram. "
                          "Ports belong to the transport protocol: TCP 80 and UDP 80 are different sockets."))):
            c = card(row)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            row.columnconfigure(i, weight=1, uniform="c")
            label(c, head, "lab").pack(anchor="w", padx=16, pady=(14, 6))
            bl = label(c, body, "small", fg=T["fg"])
            bl.pack(fill="x", padx=16, pady=(0, 16))
            wrap(bl, 32)

    # -- header diagrams -----------------------------------------------------
    def _headers(self, f) -> None:
        top = tk.Frame(f, bg=T["bg"])
        top.pack(fill="x")
        self.hseg = Seg(top, [("TCP", "TCP"), ("UDP", "UDP"), ("IPv4", "IPv4"), ("ICMP", "ICMP")], self._draw_header)
        self.hseg.pack(side="left")
        label(top, "Click any field.", "small").pack(side="left", padx=16)
        self.hc = tk.Canvas(f, bg=T["bg"], highlightthickness=0, height=420)
        self.hc.pack(fill="x", pady=(14, 0))
        self.hdetail = card(f)
        self.hdetail.pack(fill="x", pady=(10, 0))
        self.hd_title = label(self.hdetail, "", "h3")
        self.hd_title.pack(anchor="w", padx=16, pady=(12, 2))
        self.hd_text = label(self.hdetail, "Select a field in the diagram.", "small", fg=T["fg"])
        self.hd_text.pack(fill="x", padx=16, pady=(0, 14))
        wrap(self.hd_text, 32)
        self.sel = None
        self._draw_header("TCP")

    def _draw_header(self, key) -> None:
        c = self.hc
        c.delete("all")
        h = data.HEADERS[key]
        bw, rh, x0, y0 = 21, 46, 8, 52
        c.create_text(x0, 12, text=h["title"].upper(), anchor="w", fill=T["mut"], font=T.font("lab"))
        for b in (0, 8, 16, 24, 31):
            x = x0 + b * bw + (bw / 2 if b == 31 else 0)
            c.create_text(x + (0 if b else 0), 36, text=str(b), anchor="w" if b < 31 else "e", fill=T["mut"],
                          font=(T.mono, 8))
        f_small = tkfont.Font(family=T.sans, size=9)
        f_bold = tkfont.Font(family=T.sans, size=9, weight="bold")
        self.fields = {}
        self.sel = None
        for r, row in enumerate(h["rows"]):
            x = x0
            y = y0 + r * rh
            for i, (name, bits, short, desc) in enumerate(row):
                w = bits * bw
                payload = name.startswith("Data (") or name.startswith("Options")
                rect = c.create_rectangle(x, y, x + w, y + rh, outline=T["mut"] if not payload else T["line"],
                                          fill=T["card"], dash=(3, 3) if payload else None, width=1)
                text = name
                for cand in (name, short or name):
                    if f_bold.measure(cand) <= w - 8:
                        text = cand
                        break
                else:
                    text = short or ""
                    while text and f_bold.measure(text) > w - 4:
                        text = text[:-1]
                txt = c.create_text(x + w / 2, y + rh / 2 - (6 if bits > 1 else 0), text=text, fill=T["fg"],
                                    font=(T.sans, 9, "bold"))
                bit = c.create_text(x + w / 2, y + rh / 2 + 10, text=f"{bits} bit{'s' if bits > 1 else ''}"
                                    if bits > 1 and w > 52 else "", fill=T["mut"], font=(T.mono, 8))
                for item in (rect, txt, bit):
                    c.tag_bind(item, "<Button-1>", lambda e, k=(key, r, i): self._pick(k))
                    c.tag_bind(item, "<Enter>", lambda e: c.configure(cursor="hand2"))
                    c.tag_bind(item, "<Leave>", lambda e: c.configure(cursor=""))
                self.fields[(key, r, i)] = (rect, txt, bit, name, bits, desc)
                x += w
        total = y0 + len(h["rows"]) * rh + 10
        c.configure(height=total)
        self.hd_title.configure(text="")
        self.hd_text.configure(text="Select a field in the diagram.", fg=T["mut"])

    def _pick(self, k) -> None:
        c = self.hc
        if self.sel in self.fields:
            rect, txt, bit, *_ = self.fields[self.sel]
            c.itemconfigure(rect, fill=T["card"])
            c.itemconfigure(txt, fill=T["fg"])
            c.itemconfigure(bit, fill=T["mut"])
        rect, txt, bit, name, bits, desc = self.fields[k]
        c.itemconfigure(rect, fill=T["fg"])
        c.itemconfigure(txt, fill=T["bg"])
        c.itemconfigure(bit, fill=T["bg"])
        self.sel = k
        self.hd_title.configure(text=f"{name}   ·   {bits} bits")
        self.hd_text.configure(text=desc, fg=T["fg"])

    def _flags(self, f) -> None:
        label(f, "TCP flags", "lab").pack(anchor="w", pady=(0, 8))
        Table(f, ["Flag", "Name", "Meaning"], [80, 220, 560], data.TCP_FLAGS, height=8, detail=False).pack(fill="x")
        label(f, "Common flag combinations", "lab").pack(anchor="w", pady=(24, 8))
        Table(f, ["Segment", "Seen when"], [180, 700], [
            ("SYN", "Client opens a connection (also what a SYN port scan sends)."),
            ("SYN, ACK", "Server accepts: second step of the handshake. Port is open."),
            ("ACK", "Acknowledges data or completes the handshake. Sent on nearly every segment."),
            ("PSH, ACK", "Data the sender wants delivered to the application immediately."),
            ("FIN, ACK", "Graceful close of one direction."),
            ("RST", "Abort. Reply to a SYN on a closed port, or to a segment that belongs to no connection."),
            ("RST, ACK", "Abort that also acknowledges something (typical closed-port reply)."),
            ("none set (NULL) / FIN, PSH, URG (Xmas)", "Not normal traffic: used by scanners to probe firewalls."),
        ], height=8, detail=False).pack(fill="x")
        label(f, "TCP options (negotiated mainly in the SYN)", "lab").pack(anchor="w", pady=(24, 8))
        Table(f, ["Kind", "Option", "Purpose"], [60, 160, 700], data.TCP_OPTIONS, height=6, detail=False).pack(fill="x")

    def _states(self, f) -> None:
        left = tk.Frame(f, bg=T["bg"])
        left.pack(side="left", fill="both", expand=True)
        Table(left, ["State", "Meaning"], [140, 520], data.TCP_STATES, height=11, detail=False).pack(fill="x")
        right = card(f)
        right.pack(side="left", fill="y", padx=(16, 0), anchor="n")
        label(right, "Typical paths", "lab").pack(anchor="w", padx=16, pady=(14, 6))
        paths = ("Client open\n  CLOSED > SYN_SENT > ESTABLISHED\n\n"
                 "Server open\n  CLOSED > LISTEN > SYN_RCVD > ESTABLISHED\n\n"
                 "Active close (sends FIN first)\n  ESTABLISHED > FIN_WAIT_1 > FIN_WAIT_2\n  > TIME_WAIT > CLOSED\n\n"
                 "Passive close\n  ESTABLISHED > CLOSE_WAIT > LAST_ACK\n  > CLOSED\n\n"
                 "Troubleshooting\n  many SYN_RCVD    SYN flood suspected\n  many CLOSE_WAIT  application not closing\n"
                 "  many TIME_WAIT   normal on busy clients")
        label(right, paths, "monos", justify="left").pack(anchor="w", padx=16, pady=(0, 16))


# --------------------------------------------------------------------------
# Simulator
# --------------------------------------------------------------------------
class SimPage(Page):
    key, nav = "sim", "Simulator"
    eyebrow, title = "Interactive", "Packet Flow"
    sub = "Pick a scenario, then step through it. Each packet explains why it exists."

    def build(self) -> None:
        self.steps: list[sim.Step] = []
        self.idx = -1
        self.play_job = None
        self.scenario = "full"
        wrapper = tk.Frame(self.parent, bg=T["bg"])
        wrapper.pack(fill="both", expand=True)
        left = tk.Frame(wrapper, bg=T["bg"], width=290)
        left.pack(side="left", fill="y", anchor="n", padx=(0, 28))
        left.pack_propagate(False)
        right = tk.Frame(wrapper, bg=T["bg"])
        right.pack(side="left", fill="both", expand=True)

        label(left, "Scenario", "lab").pack(anchor="w", pady=(0, 6))
        self.scn = {}
        for k, name, proto, _fn, desc in sim.SCENARIOS:
            row = tk.Frame(left, bg=T["bg"], cursor="hand2")
            row.pack(fill="x")
            tag = label(row, proto, "lab", width=4)
            tag.pack(side="left")
            nm = label(row, name, "body")
            nm.pack(side="left", padx=(6, 0), pady=3)
            for w in (row, tag, nm):
                w.bind("<Button-1>", lambda e, kk=k: self.pick(kk))
            self.scn[k] = (nm, tag)
        self.scn_desc = label(left, "", "small")
        self.scn_desc.pack(fill="x", pady=(8, 0))
        wrap(self.scn_desc)
        hairline(left, pady=14)

        label(left, "Parameters", "lab").pack(anchor="w", pady=(0, 6))
        self.v = {n: tk.StringVar(value=str(val)) for n, val in (
            ("client_ip", "192.168.1.10"), ("server_ip", "203.0.113.20"), ("client_port", 49321),
            ("server_port", 443), ("c_isn", 1000), ("s_isn", 5000), ("c_len", 300), ("s_len", 1200))}
        form = tk.Frame(left, bg=T["bg"])
        form.pack(fill="x")
        for i, (n, text) in enumerate((("client_ip", "Client IP"), ("server_ip", "Server IP"),
                                       ("client_port", "Client port"), ("server_port", "Server port"),
                                       ("c_isn", "Client ISN"), ("s_isn", "Server ISN"),
                                       ("c_len", "Request bytes"), ("s_len", "Response bytes"))):
            label(form, text, "small").grid(row=i, column=0, sticky="w", pady=3)
            e = entry(form, self.v[n], width=15)
            e.grid(row=i, column=1, sticky="e", pady=3, ipady=2)
            e.bind("<Return>", lambda ev: self.apply())
        form.columnconfigure(1, weight=1)
        btns = tk.Frame(left, bg=T["bg"])
        btns.pack(fill="x", pady=(10, 0))
        Btn(btns, "Apply", self.apply, solid=True).pack(side="left")
        Btn(btns, "Random ISNs", self.randomize).pack(side="left", padx=8)
        self.rel = tk.BooleanVar(value=True)
        check(left, "Show relative sequence numbers", self.rel, self.refresh).pack(anchor="w", pady=(12, 0))
        self.msg = label(left, "", "small")
        self.msg.pack(fill="x", pady=(8, 0))
        wrap(self.msg)

        # right column: ladder canvas, controls, explanation
        cwrap = tk.Frame(right, bg=T["bg"], highlightthickness=1, highlightbackground=T["line"])
        cwrap.pack(fill="x")
        self.cv = tk.Canvas(cwrap, bg=T["bg"], highlightthickness=0, height=430)
        sb = tk.Scrollbar(cwrap, orient="vertical", command=self.cv.yview)
        from tkinter import ttk
        sb = ttk.Scrollbar(cwrap, orient="vertical", command=self.cv.yview, style="M.Vertical.TScrollbar")
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv._wheel_target = self.cv
        self.cv.bind("<Configure>", lambda e: self.refresh())

        ctl = tk.Frame(right, bg=T["bg"])
        ctl.pack(fill="x", pady=(12, 0))
        Btn(ctl, "‹  Back", self.back).pack(side="left")
        Btn(ctl, "Next  ›", self.next, solid=True).pack(side="left", padx=8)
        self.play_btn = Btn(ctl, "Play", self.toggle_play)
        self.play_btn.pack(side="left")
        Btn(ctl, "Reset", self.reset).pack(side="left", padx=8)
        self.speed = tk.DoubleVar(value=1.0)
        label(ctl, "Speed", "lab").pack(side="left", padx=(18, 6))
        scale(ctl, self.speed, 0.5, 3.0, length=110).pack(side="left")
        self.counter = label(ctl, "", "mono")
        self.counter.pack(side="right")

        self.info = card(right)
        self.info.pack(fill="x", pady=(12, 0))
        self.i_title = label(self.info, "", "h2")
        self.i_title.pack(anchor="w", padx=18, pady=(14, 2))
        self.i_text = label(self.info, "", "body", fg=T["fg"])
        self.i_text.pack(fill="x", padx=18, pady=(0, 10))
        wrap(self.i_text, 36)
        self.i_kv = tk.Frame(self.info, bg=T["card"])
        self.i_kv.pack(fill="x", padx=18, pady=(0, 14))
        self.pick("full")

    # -- scenario / parameters -----------------------------------------------
    def pick(self, key) -> None:
        self.scenario = key
        for k, (nm, tag) in self.scn.items():
            on = k == key
            nm.configure(fg=T["fg"] if on else T["mut"], font=(T.sans, 11, "bold" if on else "normal"))
            tag.configure(fg=T["fg"] if on else T["mut"])
        self.scn_desc.configure(text=next(d for k, _n, _p, _f, d in sim.SCENARIOS if k == key))
        self.apply()

    def _int(self, name, lo, hi, text) -> int:
        try:
            v = int(self.v[name].get().strip())
        except ValueError:
            raise ValueError(f"{text} must be a whole number.") from None
        if not lo <= v <= hi:
            raise ValueError(f"{text} must be between {lo} and {hi}.")
        return v

    def apply(self) -> None:
        try:
            cip, sip = self.v["client_ip"].get().strip(), self.v["server_ip"].get().strip()
            ipaddress.ip_address(cip)
            ipaddress.ip_address(sip)
            cfg = sim.SimConfig(
                client_ip=cip, server_ip=sip,
                client_port=self._int("client_port", 1, 65535, "Client port"),
                server_port=self._int("server_port", 1, 65535, "Server port"),
                c_isn=self._int("c_isn", 0, 0xFFFFFFFF, "Client ISN"),
                s_isn=self._int("s_isn", 0, 0xFFFFFFFF, "Server ISN"),
                c_len=self._int("c_len", 1, 8760, "Request bytes"),
                s_len=self._int("s_len", 1, 8760, "Response bytes"),
                udp_server_port=self._int("server_port", 1, 65535, "Server port"))
        except ValueError as e:
            self.msg.configure(text=f"—  {e}", fg=T["fg"])
            return
        self.msg.configure(text="")
        self.cfg = cfg
        self.stop_play()
        self.steps = sim.build_scenario(self.scenario, cfg)
        self.idx = -1
        self.refresh()

    def randomize(self) -> None:
        self.v["c_isn"].set(str(random.randrange(0, 2 ** 32)))
        self.v["s_isn"].set(str(random.randrange(0, 2 ** 32)))
        self.v["client_port"].set(str(random.randrange(49152, 65536)))
        self.apply()

    # -- playback ----------------------------------------------------------------
    def next(self) -> None:
        if self.idx < len(self.steps) - 1:
            self.idx += 1
            self.refresh(scroll=True)
        else:
            self.stop_play()

    def back(self) -> None:
        self.stop_play()
        if self.idx >= 0:
            self.idx -= 1
            self.refresh(scroll=True)

    def reset(self) -> None:
        self.stop_play()
        self.idx = -1
        self.refresh()
        self.cv.yview_moveto(0)

    def toggle_play(self) -> None:
        if self.play_job:
            self.stop_play()
            return
        if self.idx >= len(self.steps) - 1:
            self.idx = -1
        self.play_btn.set_text("Pause")
        self._tick()

    def _tick(self) -> None:
        if self.idx >= len(self.steps) - 1:
            self.stop_play()
            return
        self.next()
        self.play_job = self.parent.after(int(1500 / max(.5, self.speed.get())), self._tick)

    def stop_play(self) -> None:
        if self.play_job:
            try:
                self.parent.after_cancel(self.play_job)
            except tk.TclError:
                pass
            self.play_job = None
        try:
            self.play_btn.set_text("Play")
        except tk.TclError:
            pass

    def on_hide(self) -> None:
        self.stop_play()

    # -- drawing -----------------------------------------------------------------
    ROW = 58

    def refresh(self, *_a, scroll=False) -> None:
        c = self.cv
        c.delete("all")
        W = max(c.winfo_width(), 560)
        lx, rx = 150, W - 150
        cfg = self.cfg
        pad = 74
        total = pad + len(self.steps) * self.ROW + 20
        c.configure(scrollregion=(0, 0, W, max(total, 430)))
        # lifelines + headers
        for x, name, ip, port in ((lx, "Client", cfg.client_ip, cfg.client_port),
                                  (rx, "Server", cfg.server_ip,
                                   cfg.udp_server_port if self.scenario.startswith("udp") else cfg.server_port)):
            c.create_text(x, 16, text=name.upper(), fill=T["fg"], font=(T.sans, 10, "bold"))
            c.create_text(x, 34, text=f"{ip}:{port}", fill=T["mut"], font=(T.mono, 9))
            c.create_line(x, 50, x, max(total, 430), fill=T["line"], dash=(2, 4))
        shown = self.steps[:self.idx + 1]
        last_c = last_s = None
        for i, st in enumerate(shown):
            y = pad + i * self.ROW
            cur = i == self.idx
            col = T["fg"] if cur else T.dim(.5)
            if st.kind == "note":
                c.create_rectangle(lx + 24, y - 14, rx - 24, y + 18, outline=T["line"], fill=T["card"])
                c.create_text((lx + rx) / 2, y + 2, text=st.title, fill=col, font=(T.sans, 10, "bold"))
            else:
                x1, x2 = (lx, rx) if st.direction == "c2s" else (rx, lx)
                y2 = y + 24
                if st.kind == "lost":
                    xm = x1 + (x2 - x1) * .55
                    ym = y + 24 * .55
                    c.create_line(x1, y, xm, ym, fill=col, width=2 if cur else 1, dash=(5, 3))
                    c.create_line(xm - 7, ym - 7, xm + 7, ym + 7, fill=col, width=2)
                    c.create_line(xm - 7, ym + 7, xm + 7, ym - 7, fill=col, width=2)
                else:
                    c.create_line(x1, y, x2, y2, fill=col, width=2 if cur else 1, arrow="last", arrowshape=(10, 12, 4))
                label_txt = self._label(st)
                c.create_text((lx + rx) / 2, y - 7, text=label_txt, fill=col,
                              font=(T.mono, 9, "bold" if cur else "normal"))
                if st.retrans:
                    c.create_text((lx + rx) / 2, y + 36, text="retransmission", fill=col, font=(T.sans, 8))
            if st.cstate != last_c and st.kind != "lost":
                c.create_text(lx - 14, y + 8, text=st.cstate, anchor="e", fill=col, font=(T.mono, 9))
                last_c = st.cstate
            if st.sstate != last_s and st.kind != "lost":
                c.create_text(rx + 14, y + 8, text=st.sstate, anchor="w", fill=col, font=(T.mono, 9))
                last_s = st.sstate
        if scroll and self.idx >= 0:
            frac = max(0.0, (pad + self.idx * self.ROW - 220) / max(total, 1))
            c.yview_moveto(frac)
        self._info()

    def _label(self, st: sim.Step) -> str:
        if st.proto == "UDP":
            return f"UDP  {st.sport} > {st.dport}   {st.length} B"
        seq = st.seq_r if self.rel.get() else st.seq
        ack = st.ack_r if self.rel.get() else st.ack
        parts = [f"[{st.flags}]"]
        if seq is not None:
            parts.append(f"seq={seq}")
        if ack is not None and "ACK" in st.flags:
            parts.append(f"ack={ack}")
        if st.length:
            parts.append(f"len={st.length}")
        return " ".join(parts)

    def _info(self) -> None:
        n = len(self.steps)
        self.counter.configure(text=f"{max(self.idx + 1, 0)} / {n}")
        for w in self.i_kv.winfo_children():
            w.destroy()
        if self.idx < 0:
            self.i_title.configure(text="Ready")
            self.i_text.configure(text="Press Next to send the first packet, or Play to watch the whole scenario.")
            return
        st = self.steps[self.idx]
        self.i_title.configure(text=st.title)
        self.i_text.configure(text=st.text)
        if st.kind == "note":
            return
        rows = [("Direction", "Client > Server" if st.direction == "c2s" else "Server > Client"),
                ("Ports", f"{st.sport} > {st.dport}")]
        if st.proto == "TCP":
            rows += [("Flags", st.flags),
                     ("Sequence", f"{st.seq_r if self.rel.get() else st.seq}" + ("  (relative)" if self.rel.get() else "")),
                     ("Acknowledgment", "-" if st.ack is None or "ACK" not in st.flags else
                      f"{st.ack_r if self.rel.get() else st.ack}"),
                     ("Payload", f"{st.length} bytes"), ("Window", "-" if st.win is None else str(st.win)),
                     ("Client state", st.cstate), ("Server state", st.sstate)]
        else:
            rows += [("UDP length", f"{st.udp_len} bytes (8 header + {st.length} data)"),
                     ("Checksum", "present (optional in IPv4)"), ("State kept", "none")]
        for i, (k, v) in enumerate(rows):
            r, cidx = divmod(i, 4)
            cell = tk.Frame(self.i_kv, bg=T["card"])
            cell.grid(row=r, column=cidx, sticky="nw", padx=(0, 22), pady=(6, 0))
            label(cell, k, "lab", bg=T["card"]).pack(anchor="w")
            label(cell, v, "mono", bg=T["card"]).pack(anchor="w")
