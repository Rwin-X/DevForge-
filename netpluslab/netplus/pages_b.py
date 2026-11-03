"""Pages: Subnetting, Converters, Ports, OSI & Encapsulation."""

from __future__ import annotations

import tkinter as tk

from . import data, sim
from . import subnet as sn
from .pages_a import Page
from .ui import (T, Btn, InputText, KV, Seg, Table, Tabs, TextBox, ToolPanel, card, combo, entry, flash, hairline,
                 label, mix, scale, wrap)


def _fmt(n) -> str:
    return f"{n:,}"


# --------------------------------------------------------------------------
# Subnetting
# --------------------------------------------------------------------------
class SubnetPage(Page):
    key, nav = "subnet", "Subnetting"
    eyebrow, title = "Layer 3 addressing", "Subnetting"
    sub = "Type an address and mask in any form: 192.168.1.77/26, 192.168.1.77 /26 or 192.168.1.77 255.255.255.192."

    def build(self) -> None:
        tabs = Tabs(self.parent)
        tabs.pack(fill="both", expand=True)
        self._calc(tabs.add("calc", "Calculator"))
        self._vlsm(tabs.add("vlsm", "VLSM"))
        self._split(tabs.add("split", "Split"))
        self._summ(tabs.add("sum", "Summarize"))
        self._same(tabs.add("same", "Same subnet?"))
        self._cidr(tabs.add("cidr", "CIDR table"))

    # -- calculator --------------------------------------------------------------
    def _calc(self, f) -> None:
        top = tk.Frame(f, bg=T["bg"])
        top.pack(fill="x")
        label(top, "Address / mask", "lab").grid(row=0, column=0, sticky="w")
        self.cv_in = tk.StringVar(value="192.168.1.77/26")
        e = entry(top, self.cv_in, width=34)
        e.grid(row=1, column=0, sticky="w", ipady=4)
        label(top, "Prefix", "lab").grid(row=0, column=1, sticky="w", padx=(24, 0))
        self.prefix_var = tk.IntVar(value=26)
        self.slider = scale(top, self.prefix_var, 0, 32, command=self._slide, length=300)
        self.slider.grid(row=1, column=1, padx=(24, 0), sticky="w")
        self.plabel = label(top, "/26", "stat")
        self.plabel.grid(row=1, column=2, padx=(14, 0))
        self.err = label(f, "", "small")
        self.err.pack(fill="x", pady=(10, 0))
        self.bin_cv = tk.Canvas(f, bg=T["bg"], highlightthickness=0, height=170)
        self.bin_cv.pack(fill="x", pady=(8, 8))
        self.kv = KV(f)
        self.kv.pack(fill="x")
        self._busy = False
        self.cv_in.trace_add("write", lambda *a: self._calc_now())
        self._calc_now()

    def _slide(self, v) -> None:
        if self._busy:
            return
        try:
            ip = sn.parse_ip_and_prefix(self.cv_in.get())[0]
        except sn.NetError:
            return
        self._busy = True
        self.cv_in.set(f"{ip}/{int(float(v))}")
        self._busy = False

    def _calc_now(self) -> None:
        try:
            ip, p, _ = sn.parse_ip_and_prefix(self.cv_in.get())
            d = sn.describe_ipv4(ip, p)
        except sn.NetError as e:
            self.err.configure(text=f"—  {e}", fg=T["fg"])
            return
        self.err.configure(text="")
        self._busy = True
        self.prefix_var.set(p)
        self._busy = False
        self.plabel.configure(text=f"/{p}")
        self._draw_bits(d)
        net_bits = d["prefix"]
        self.kv.set([
            ("Address", d["ip"]), ("Subnet mask", d["mask"]), ("Prefix length", f"/{d['prefix']}"),
            ("Wildcard mask", d["wildcard"]), ("##", "This subnet"),
            ("Network address", f"{d['network_address']}"), ("Broadcast address", d["broadcast"]),
            ("First usable host", d["first"]), ("Last usable host", d["last"]),
            ("Usable hosts", _fmt(d["usable"])), ("Total addresses", _fmt(d["total"])),
            ("Network / host bits", f"{net_bits} / {d['host_bits']}"),
            ("Next network", d["next_network"] or "none (end of address space)"),
            ("Previous network", d["prev_network"] or "none (start of address space)"),
            ("##", "About the address"), ("Class (classful)", d["class"]), ("Type", d["type"]),
            ("This address is a", d["host_role"]),
        ])

    def _draw_bits(self, d) -> None:
        c = self.bin_cv
        c.delete("all")
        cw, ch, gap, x0 = 20, 26, 12, 112
        rows = [("Address", d["ip_bin"]), ("Mask", d["mask_bin"]), ("Network", d["net_bin"]), ("Broadcast", d["bcast_bin"])]
        p = d["prefix"]
        for r, (name, bits) in enumerate(rows):
            y = 26 + r * (ch + 8)
            c.create_text(0, y + ch / 2, text=name.upper(), anchor="w", fill=T["mut"], font=T.font("lab"))
            idx = 0
            x = x0
            for ch_ in bits:
                if ch_ == ".":
                    x += gap
                    continue
                net = idx < p
                c.create_rectangle(x, y, x + cw, y + ch, fill=T["fg"] if net else T["card"],
                                   outline=T["fg"] if net else T["line"])
                c.create_text(x + cw / 2, y + ch / 2, text=ch_, fill=T["bg"] if net else T["fg"], font=(T.mono, 10))
                x += cw
                idx += 1
        # dividing marker
        mx = x0 + p * cw + (p // 8 - (1 if p % 8 == 0 and p else 0)) * gap if p else x0
        if 0 < p < 32:
            c.create_line(mx, 18, mx, 26 + 4 * (ch + 8), fill=T["fg"], width=2)
        c.create_text(x0, 8, text="NETWORK BITS (filled)  ·  HOST BITS (outline)", anchor="w", fill=T["mut"],
                      font=T.font("lab"))

    # -- VLSM --------------------------------------------------------------------
    def _vlsm(self, f) -> None:
        self.para(f, "Allocate the largest subnet first, then smaller ones, each aligned to its own block size. "
                  "This avoids gaps and overlaps. One line per subnet: name, then the hosts it needs.")
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x")
        left = tk.Frame(row, bg=T["bg"])
        left.pack(side="left", anchor="n")
        label(left, "Base network", "lab").pack(anchor="w", pady=(0, 4))
        self.vl_base = tk.StringVar(value="192.168.1.0/24")
        entry(left, self.vl_base, width=26).pack(anchor="w", ipady=3)
        label(left, "Requirements", "lab").pack(anchor="w", pady=(12, 4))
        self.vl_req = InputText(left, height=7, width=26)
        self.vl_req.pack(anchor="w")
        self.vl_req.set("Sales 50\nHR 25\nIT 10\nWAN link 2")
        Btn(left, "Calculate", self._vlsm_run, solid=True).pack(anchor="w", pady=(12, 0))
        right = tk.Frame(row, bg=T["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(26, 0))
        self.vl_err = label(right, "", "small")
        self.vl_err.pack(fill="x")
        self.vl_bar = tk.Canvas(right, bg=T["bg"], highlightthickness=0, height=56)
        self.vl_bar.pack(fill="x", pady=(0, 10))
        self.vl_tbl = Table(right, ["Name", "Need", "Block", "Mask", "Network", "First host", "Last host", "Broadcast", "Spare"],
                            [100, 50, 60, 120, 130, 120, 120, 120, 50], height=7, detail=False, stretch=7)
        self.vl_tbl.pack(fill="x")
        self.vl_free = label(right, "", "small")
        self.vl_free.pack(fill="x", pady=(10, 0))
        wrap(self.vl_free)
        self._vlsm_run()

    def _vlsm_run(self) -> None:
        reqs = []
        for line in self.vl_req.get().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.rsplit(None, 1)
            try:
                if len(parts) == 1:
                    reqs.append((f"LAN {len(reqs) + 1}", int(parts[0])))
                else:
                    reqs.append((parts[0], int(parts[1])))
            except ValueError:
                self.vl_err.configure(text=f"—  Line '{line}': the last word must be a host count.", fg=T["fg"])
                return
        try:
            r = sn.vlsm(self.vl_base.get(), reqs)
        except sn.NetError as e:
            self.vl_err.configure(text=f"—  {e}", fg=T["fg"])
            self.vl_tbl.set_rows([])
            self.vl_bar.delete("all")
            self.vl_free.configure(text="")
            return
        self.vl_err.configure(text="")
        self.vl_tbl.set_rows([(a["name"], a["required"], f"/{a['prefix']}", a["mask"], a["network"], a["first"], a["last"],
                               a["broadcast"], a["spare"]) for a in r["allocations"]])
        self.vl_free.configure(text=(f"Used {_fmt(r['used'])} of {_fmt(r['total'])} addresses ({r['utilization']:.0%}).  "
                                     + ("Free: " + ",  ".join(map(str, r["free"])) if r["free"] else "No free space left.")))
        self._vlsm_bar(r)

    def _vlsm_bar(self, r) -> None:
        c = self.vl_bar
        c.delete("all")
        c.update_idletasks()
        W = max(c.winfo_width(), 400) - 2
        total = r["total"]
        x = 1
        base = int(r["base"].network_address)
        segs = [(int(a["network"].network_address) - base, a["size"], a["name"], True) for a in r["allocations"]]
        segs += [(int(n.network_address) - base, n.num_addresses, "free", False) for n in r["free"]]
        for off, size, name, used in sorted(segs):
            x0 = 1 + off / total * W
            x1 = 1 + (off + size) / total * W
            c.create_rectangle(x0, 6, x1, 40, fill=T["fg"] if used else T["card"], outline=T["bg"] if used else T["line"])
            if x1 - x0 > 46:
                c.create_text((x0 + x1) / 2, 23, text=name if len(name) * 7 < x1 - x0 else name[:max(1, int((x1 - x0) / 7))],
                              fill=T["bg"] if used else T["mut"], font=(T.sans, 9, "bold" if used else "normal"))
        c.create_text(1, 50, text=str(r["base"].network_address), anchor="w", fill=T["mut"], font=(T.mono, 8))
        c.create_text(W, 50, text=str(r["base"].broadcast_address), anchor="e", fill=T["mut"], font=(T.mono, 8))

    # -- split -------------------------------------------------------------------
    def _split(self, f) -> None:
        self.para(f, "Divide one network into equal subnets, either by how many subnets you need or by how many hosts each must hold.")
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x")
        self.sp_base = tk.StringVar(value="192.168.10.0/24")
        self.sp_val = tk.StringVar(value="5")
        for i, (name, w) in enumerate((("Network", None), ("Split by", None), ("Value", None))):
            label(row, name, "lab").grid(row=0, column=i, sticky="w", padx=(0, 18))
        entry(row, self.sp_base, width=22).grid(row=1, column=0, sticky="w", padx=(0, 18), ipady=3)
        self.sp_mode = Seg(row, [("subnets", "Subnets"), ("hosts", "Hosts per subnet")], lambda k: self._split_run())
        self.sp_mode.grid(row=1, column=1, sticky="w", padx=(0, 18))
        entry(row, self.sp_val, width=10).grid(row=1, column=2, sticky="w", ipady=3)
        self.sp_base.trace_add("write", lambda *a: self._split_run())
        self.sp_val.trace_add("write", lambda *a: self._split_run())
        self.sp_info = label(f, "", "small")
        self.sp_info.pack(fill="x", pady=(12, 8))
        wrap(self.sp_info)
        self.sp_tbl = Table(f, ["#", "Network", "First host", "Last host", "Broadcast"], [50, 170, 150, 150, 150],
                            height=10, detail=False, stretch=4)
        self.sp_tbl.pack(fill="x")
        self._split_run()

    def _split_run(self) -> None:
        try:
            r = sn.split_network(self.sp_base.get(), self.sp_mode.get(), int(self.sp_val.get()))
        except (sn.NetError, ValueError) as e:
            self.sp_info.configure(text=f"—  {e if isinstance(e, sn.NetError) else 'Value must be a whole number.'}", fg=T["fg"])
            self.sp_tbl.set_rows([])
            return
        self.sp_info.configure(
            text=f"{r['base']} becomes {_fmt(r['count'])} subnets of /{r['new_prefix']} ({r['mask']}), borrowing {r['borrowed']} bit(s). "
                 f"Each holds {_fmt(r['usable'])} usable hosts." + (f"  Showing the first {len(r['rows'])}." if r["truncated"] else ""),
            fg=T["fg"])
        self.sp_tbl.set_rows([(i + 1, x["network"], x["first"], x["last"], x["broadcast"]) for i, x in enumerate(r["rows"])])

    # -- summarize ---------------------------------------------------------------
    def _summ(self, f) -> None:
        self.para(f, "Route summarization: find the smallest single prefix covering several networks. "
                  "It is exact only when the networks are contiguous and aligned; otherwise the summary also covers addresses you do not own.")
        self.su_in = InputText(f, height=6, width=30)
        self.su_in.pack(anchor="w")
        self.su_in.set("192.168.0.0/24\n192.168.1.0/24\n192.168.2.0/24\n192.168.3.0/24")
        Btn(f, "Summarize", self._summ_run, solid=True).pack(anchor="w", pady=(10, 0))
        self.su_err = label(f, "", "small")
        self.su_err.pack(fill="x", pady=(8, 0))
        self.su_kv = KV(f)
        self.su_kv.pack(fill="x", pady=(6, 0))
        self._summ_run()

    def _summ_run(self) -> None:
        try:
            r = sn.summarize(self.su_in.get().splitlines())
        except sn.NetError as e:
            self.su_err.configure(text=f"—  {e}", fg=T["fg"])
            self.su_kv.set([])
            return
        self.su_err.configure(text="")
        self.su_kv.set([
            ("Summary route", r["supernet"]),
            ("Exact match", "Yes: the summary covers exactly your networks" if r["exact"]
             else f"No: {_fmt(r['wasted'])} extra addresses are covered"),
            ("Minimal list", ",  ".join(map(str, r["collapsed"]))),
            ("Addresses in your networks", _fmt(r["covered"])),
            ("Addresses in the summary", _fmt(r["supernet"].num_addresses)),
            ("Mask", sn.prefix_to_mask(r["supernet"].prefixlen)),
        ])

    # -- same subnet ---------------------------------------------------------------
    def _same(self, f) -> None:
        def fn(v):
            r = sn.compare_hosts(v["a"], v["b"], v["mask"], v["gw"])
            a, b = r["a"], r["b"]
            rows = [("Verdict", "SAME subnet: delivered directly on the LAN (ARP)" if r["same"]
                     else "DIFFERENT subnets: traffic must go through a router"),
                    ("Host A network", a["network"]), ("Host B network", b["network"]),
                    ("Usable range A", f"{a['first']} - {a['last']}")]
            if r["gateway"]:
                rows.append(("Gateway network", r["gateway"]["network"]))
            rows.append(("Problems", "\n".join(r["problems"]) if r["problems"] else "none found"))
            return rows
        ToolPanel(f, [dict(key="a", label="Host A", default="192.168.1.10", width=18),
                      dict(key="b", label="Host B", default="192.168.1.130", width=18),
                      dict(key="mask", label="Mask or prefix", default="255.255.255.128", width=18),
                      dict(key="gw", label="Gateway (optional)", default="192.168.1.1", width=18)], fn,
                  intro="The classic troubleshooting check: two hosts cannot talk, so are they even on the same network, "
                        "and is the default gateway reachable from each?").pack(fill="x")

    def _cidr(self, f) -> None:
        Table(f, ["Prefix", "Mask", "Wildcard", "Addresses", "Usable", "Block / octet"],
              [70, 140, 120, 130, 130, 200], sn.cidr_table(), height=16, detail=False, stretch=5).pack(fill="x")


# --------------------------------------------------------------------------
# Converters
# --------------------------------------------------------------------------
class ConvertPage(Page):
    key, nav = "convert", "Converters"
    eyebrow, title = "Maths & formats", "Converters"
    sub = "Results update as you type. Click any value to copy it."

    def build(self) -> None:
        tabs = Tabs(self.parent)
        tabs.pack(fill="both", expand=True)
        P = lambda key, name, inputs, fn, intro="": ToolPanel(tabs.add(key, name), inputs, fn, intro).pack(fill="x")  # noqa: E731

        def v6(v):
            d = sn.describe_ipv6(v["ip"])
            rows = [("Compressed", d["compressed"]), ("Expanded", d["exploded"]), ("Type", d["type"]), ("Scope", d["scope"]),
                    ("Prefix length", f"/{d['prefix']}"), ("Network", d["network"]), ("Interface ID (low 64 bits)", d["interface_id"]),
                    ("Looks like EUI-64", "Yes (ff:fe in the middle)" if d["eui64_hint"] else "No"),
                    ("Solicited-node multicast", d["solicited_node"]), ("Reverse DNS name", d["reverse"])]
            if d["slash64s"] is not None:
                rows.insert(6, ("/64 subnets inside", _fmt(d["slash64s"])))
            return rows
        P("v6", "IPv6", [dict(key="ip", label="IPv6 address[/prefix]", default="2001:0db8:0000:0000:0000:ff00:0042:8329/64", width=46)], v6,
          "Compression rules: drop leading zeros in each group, and replace ONE run of all-zero groups with '::'.")

        def e64(v):
            r = sn.eui64(v["mac"], v["prefix"])
            return [("MAC address", r["mac"]), ("Step 1", "Split the MAC in half and insert FF:FE in the middle"),
                    ("Step 2", f"Flip bit 7 (universal/local) of the first byte: {r['flipped_first']}"),
                    ("Interface ID", r["interface_id"]), ("Resulting address", r["address"])]
        P("e64", "EUI-64", [dict(key="mac", label="MAC address", default="00:1A:2B:3C:4D:5E", width=22),
                            dict(key="prefix", label="Prefix (/64)", default="fe80::/64", width=26)], e64,
          "SLAAC can build the interface ID from the MAC. Modern OSes often use random (privacy) IDs instead.")

        def bases(v):
            n = sn.parse_int(v["n"])
            f = sn.base_forms(n)
            rows = [("Decimal", f["dec"]), ("Binary", f["bin"]), ("Hexadecimal", f["hex"]), ("Octal", f["oct"]), ("Bits needed", f["bits"])]
            if n <= 255:
                rows.append(("As dotted mask octet", f"{n}" + ("" if f"{n:08b}".rstrip("0").count("0") == 0 else "   (not a valid mask octet)")))
            return rows
        P("base", "Number bases", [dict(key="n", label="Number (255, 0xFF, 0b1111_1111, 0o377)", default="192", width=30)], bases)

        def v4(v):
            f = sn.ipv4_forms(v["ip"])
            return [("Dotted decimal", f["dotted"]), ("Octets", f["octets"]), ("Binary", f["binary"]), ("Hexadecimal", f["hex"]),
                    ("32-bit integer", f["integer"])]
        P("v4", "IPv4 forms", [dict(key="ip", label="Dotted, binary, hex or integer", default="192.168.0.1", width=40)], v4)

        def mac(v):
            m = sn.mac_forms(v["mac"])
            return [("Colon (Linux, Wireshark)", m["colon"]), ("Hyphen (Windows)", m["hyphen"]), ("Cisco dotted", m["cisco"]),
                    ("Plain hex", m["plain"]), ("OUI (vendor prefix)", m["oui"]), ("NIC-specific part", m["nic"]),
                    ("Delivery", m["cast"]), ("Administration", m["admin"]), ("Broadcast", "Yes" if m["broadcast"] else "No")]
        P("mac", "MAC address", [dict(key="mac", label="MAC (any separator)", default="00-1A-2B-3C-4D-5E", width=24)], mac,
          "The OUI identifies the manufacturer in public IEEE registries. Bit 0 of the first byte = multicast, bit 1 = locally administered.")

        def tt(v):
            try:
                size, speed, eff = float(v["size"]), float(v["speed"]), float(v["eff"])
            except ValueError:
                raise sn.NetError("Size, speed and efficiency must be numbers.") from None
            r = sn.transfer_time(size, v["su"], speed, v["bu"], eff)
            return [("Ideal time (100% of line rate)", r["ideal_h"]), (f"Realistic time ({eff:g}% efficiency)", r["real_h"]),
                    ("Effective throughput", f"{r['mbytes_s']:.2f} MB/s"), ("Data size in bits", _fmt(int(r["bits"])))]
        P("time", "Transfer time", [dict(key="size", label="Size", default="4.7", width=10),
                                    dict(key="su", label="Unit", default="GB", width=6, choices=sn.SIZE_UNITS),
                                    dict(key="speed", label="Link speed", default="100", width=10),
                                    dict(key="bu", label="Unit", default="Mbps", width=7, choices=sn.SPEED_UNITS),
                                    dict(key="eff", label="Efficiency %", default="90", width=8)], tt,
          "Bytes vs bits is the classic trap: file sizes are in bytes, link speeds in bits per second (divide by 8).")

        def win(v):
            try:
                bw, rtt, w = float(v["bw"]), float(v["rtt"]), float(v["win"])
            except ValueError:
                raise sn.NetError("All values must be numbers.") from None
            r = sn.tcp_window_math(bw, rtt, w)
            return [("Bandwidth-delay product", f"{r['bdp_bytes']:,.0f} bytes  ({r['bdp_kb']:,.1f} KiB)"),
                    ("Throughput cap from window", f"{r['window_cap_mbps']:.2f} Mbps  (window / RTT)"),
                    ("Achievable throughput", f"{r['achievable_mbps']:.2f} Mbps"),
                    ("Window is the bottleneck", "Yes: window too small to fill the pipe" if r["limited"] else "No: the link is the limit"),
                    ("Needs window scaling (>64 KiB)", "Yes" if r["needs_scaling"] else "No")]
        P("win", "TCP window", [dict(key="bw", label="Bandwidth (Mbps)", default="1000", width=12),
                                dict(key="rtt", label="RTT (ms)", default="50", width=10),
                                dict(key="win", label="Receive window (bytes)", default="65535", width=14)], win,
          "A sender can have at most one window of unacknowledged data in flight per round trip, so throughput <= window / RTT. "
          "Long fat networks need the window scale option.")


# --------------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------------
class PortsPage(Page):
    key, nav = "ports", "Ports"
    eyebrow, title = "Reference", "Ports & Protocols"
    sub = "Search by number, service or keyword. Select a row for the full note."

    def build(self) -> None:
        tabs = Tabs(self.parent)
        tabs.pack(fill="both", expand=True)
        f = tabs.add("ports", "Well-known ports")
        bar = tk.Frame(f, bg=T["bg"])
        bar.pack(fill="x", pady=(0, 12))
        self.q = tk.StringVar()
        label(bar, "Search", "lab").pack(side="left", padx=(0, 10))
        e = entry(bar, self.q, width=32)
        e.pack(side="left", ipady=4)
        self.proto = Seg(bar, [("all", "All"), ("TCP", "TCP"), ("UDP", "UDP")], lambda k: self._filter())
        self.proto.pack(side="left", padx=14)
        self.count = label(bar, "", "small")
        self.count.pack(side="left")
        rows = [(p, t, s, d, sec, n) for p, t, s, d, sec, n in data.PORTS]
        self.tbl = Table(f, ["Port", "Proto", "Service", "Description", "Secure alternative", "Note"],
                         [70, 90, 170, 330, 230, 10], rows, height=15, stretch=3)
        self.tbl.tree.column("Note", width=0, minwidth=0, stretch=False)
        self.tbl.pack(fill="x")
        self.q.trace_add("write", lambda *a: self._filter())
        self._filter()
        rg = tk.Frame(f, bg=T["bg"])
        rg.pack(fill="x", pady=(20, 0))
        for i, (name, rng, text) in enumerate((
                ("Well-known", "0 - 1023", "Assigned to standard services. Servers need elevated privileges on Unix to bind here."),
                ("Registered", "1024 - 49151", "Registered with IANA for specific applications (databases, VPNs, games)."),
                ("Dynamic / ephemeral", "49152 - 65535", "Picked by clients as temporary source ports. Linux uses 32768-60999 by default."))):
            c = card(rg)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            rg.columnconfigure(i, weight=1, uniform="r")
            label(c, name, "lab").pack(anchor="w", padx=16, pady=(14, 2))
            label(c, rng, "stat").pack(anchor="w", padx=16)
            tl = label(c, text, "small")
            tl.pack(fill="x", padx=16, pady=(4, 14))
            wrap(tl, 32)
        g = tabs.add("ip", "IP protocol numbers")
        self.para(g, "The IPv4 'Protocol' (IPv6 'Next Header') field says what the packet carries. TCP and UDP are only two of many: "
                  "routing protocols and tunnels ride directly on IP and have no ports at all.")
        Table(g, ["Number", "Name", "Description"], [90, 150, 640], data.IP_PROTOCOLS, height=13, detail=False).pack(fill="x")

    def _filter(self) -> None:
        pr = self.proto.get()

        def extra(r):
            return pr == "all" or pr in r[1].split("/")
        n = self.tbl.filter(self.q.get(), extra)
        self.count.configure(text=f"{n} result{'s' if n != 1 else ''}")


# --------------------------------------------------------------------------
# OSI & encapsulation
# --------------------------------------------------------------------------
class OsiPage(Page):
    key, nav = "osi", "OSI & Encapsulation"
    eyebrow, title = "Models", "OSI Model"
    sub = "Seven layers, what each one adds, and what the wire really carries."

    def build(self) -> None:
        tabs = Tabs(self.parent)
        tabs.pack(fill="both", expand=True)
        self._layers(tabs.add("layers", "Layers"))
        self._encap(tabs.add("encap", "Encapsulation builder"))

    def _layers(self, f) -> None:
        row = tk.Frame(f, bg=T["bg"])
        row.pack(fill="x")
        left = tk.Frame(row, bg=T["bg"], width=330)
        left.pack(side="left", anchor="n")
        self.cells = {}
        for o in data.OSI:
            c = tk.Frame(left, bg=T["card"], highlightthickness=1, highlightbackground=T["line"], cursor="hand2")
            c.pack(fill="x", pady=(0, 4))
            num = label(c, str(o["n"]), "stat", bg=T["card"], width=2)
            num.pack(side="left", padx=(14, 6), pady=6)
            col = tk.Frame(c, bg=T["card"])
            col.pack(side="left", fill="x", expand=True)
            nm = label(col, o["name"], "h3", bg=T["card"])
            nm.pack(anchor="w", pady=(7, 0))
            pdu = label(col, o["pdu"], "small", bg=T["card"])
            pdu.pack(anchor="w", pady=(0, 7))
            ws = (c, num, col, nm, pdu)
            for w in ws:
                w.bind("<Button-1>", lambda e, n=o["n"]: self._select(n))
            self.cells[o["n"]] = (c, ws)
        for t in data.OSI_MNEMONICS:
            label(left, t, "small").pack(anchor="w", pady=(10, 0))
        right = tk.Frame(row, bg=T["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(28, 0))
        self.o_title = label(right, "", "h2")
        self.o_title.pack(anchor="w", pady=(0, 8))
        self.o_kv = KV(right, label_w=130, wrap_px=520)
        self.o_kv.pack(fill="x")
        self.o_sel = None
        self._select(4)

    def _select(self, n) -> None:
        if self.o_sel:
            c, ws = self.cells[self.o_sel]
            for w in ws:
                w.configure(bg=T["card"])
            ws[1].configure(fg=T["fg"])
            ws[3].configure(fg=T["fg"])
            ws[4].configure(fg=T["mut"])
        c, ws = self.cells[n]
        for w in ws:
            w.configure(bg=T["fg"])
        for w in (ws[1], ws[3], ws[4]):
            w.configure(fg=T["bg"])
        self.o_sel = n
        o = next(x for x in data.OSI if x["n"] == n)
        self.o_title.configure(text=f"Layer {n}  ·  {o['name']}")
        self.o_kv.set([("Function", o["function"]), ("PDU", o["pdu"]), ("Protocols", o["protocols"]), ("Devices", o["devices"]),
                       ("TCP/IP layer", o["tcpip"]), ("Example", o["example"])])

    # -- encapsulation -----------------------------------------------------------
    def _encap(self, f) -> None:
        self.para(f, "Type a payload and watch each layer wrap it. Sizes are real: 20-byte TCP header (no options), 20-byte IPv4 header, "
                  "14-byte Ethernet header (+4 for an 802.1Q tag), 4-byte FCS, 64-byte minimum frame, and 20 bytes of preamble/gap on the wire.")
        self.ev = {k: tk.StringVar(value=v) for k, v in (
            ("payload", "GET / HTTP/1.1"), ("src_ip", "192.168.1.10"), ("dst_ip", "203.0.113.20"), ("sport", "49321"),
            ("dport", "80"), ("src_mac", "00:1A:2B:3C:4D:5E"), ("dst_mac", "00:50:56:AA:BB:CC"), ("vlan", ""), ("mtu", "1500"))}
        form = tk.Frame(f, bg=T["bg"])
        form.pack(fill="x")
        label(form, "Protocol", "lab").grid(row=0, column=0, sticky="w")
        self.e_proto = Seg(form, [("TCP", "TCP"), ("UDP", "UDP")], lambda k: self._encap_run())
        self.e_proto.grid(row=1, column=0, sticky="w", padx=(0, 18), pady=(0, 8))
        specs = [("payload", "Payload text", 28), ("src_ip", "Source IP", 15), ("dst_ip", "Destination IP", 15),
                 ("sport", "Src port", 7), ("dport", "Dst port", 7), ("src_mac", "Source MAC", 18),
                 ("dst_mac", "Destination MAC", 18), ("vlan", "VLAN ID (optional)", 8), ("mtu", "MTU", 6)]
        for i, (k, name, w) in enumerate(specs):
            r, c = divmod(i, 5)
            cell = tk.Frame(form, bg=T["bg"])
            cell.grid(row=2 + r, column=c, sticky="w", padx=(0, 18), pady=(0, 8))
            label(cell, name, "lab").pack(anchor="w", pady=(0, 3))
            entry(cell, self.ev[k], width=w).pack(anchor="w", ipady=3)
            self.ev[k].trace_add("write", lambda *a: self._encap_soon())
        self.e_err = label(f, "", "small")
        self.e_err.pack(fill="x", pady=(6, 0))
        self.e_cv = tk.Canvas(f, bg=T["bg"], highlightthickness=0, height=300)
        self.e_cv.pack(fill="x", pady=(4, 6))
        self.e_cv.bind("<Configure>", lambda e: self._encap_soon())
        self.e_stats = label(f, "", "small", fg=T["fg"])
        self.e_stats.pack(fill="x")
        wrap(self.e_stats)
        self.e_tbl = Table(f, ["Layer", "Field", "Value"], [190, 190, 400], height=10, detail=False)
        self.e_tbl.pack(fill="x", pady=(10, 0))
        self._job = None
        self._encap_run()

    def _encap_soon(self) -> None:
        if self._job:
            self.parent.after_cancel(self._job)
        self._job = self.parent.after(160, self._encap_run)

    def _encap_run(self) -> None:
        self._job = None
        v = {k: x.get().strip() if k != "payload" else x.get() for k, x in self.ev.items()}
        try:
            for k in ("sport", "dport", "mtu"):
                int(v[k])
            sport, dport, mtu = int(v["sport"]), int(v["dport"]), int(v["mtu"])
            if not (0 <= sport <= 65535 and 0 <= dport <= 65535):
                raise sn.NetError("Ports must be 0-65535.")
            if not 68 <= mtu <= 9216:
                raise sn.NetError("MTU must be between 68 and 9216.")
            sn.parse_ipv4(v["src_ip"])
            sn.parse_ipv4(v["dst_ip"])
            sn.parse_mac(v["src_mac"])
            sn.parse_mac(v["dst_mac"])
            vlan = None
            if v["vlan"]:
                vlan = int(v["vlan"])
                if not 1 <= vlan <= 4094:
                    raise sn.NetError("VLAN ID must be 1-4094.")
            if len(v["payload"].encode()) > 20000:
                raise sn.NetError("Keep the payload under 20,000 bytes.")
        except sn.NetError as e:
            self.e_err.configure(text=f"—  {e}", fg=T["fg"])
            return
        except ValueError:
            self.e_err.configure(text="—  Ports, MTU and VLAN must be whole numbers.", fg=T["fg"])
            return
        self.e_err.configure(text="")
        r = sim.encapsulate(v["payload"], self.e_proto.get(), v["src_ip"], v["dst_ip"], sport, dport,
                            sn.mac_forms(v["src_mac"])["colon"], sn.mac_forms(v["dst_mac"])["colon"], vlan, mtu)
        self._encap_draw(r)
        txt = (f"Payload {r['payload_bytes']} B  >  {r['frames']} frame(s) of {', '.join(map(str, r['frame_sizes']))} B  ·  "
               f"{r['wire_total']} B on the wire  ·  payload efficiency {r['efficiency']:.1f}%")
        if r["notes"]:
            txt += "\n" + "\n".join(r["notes"])
        self.e_stats.configure(text=txt)
        rows = []
        for L in r["layers"]:
            for k, val in L["fields"]:
                rows.append((f"{L['layer']}  {L['name']}  ({L['pdu']})", k, val))
        self.e_tbl.set_rows(rows)

    def _encap_draw(self, r) -> None:
        c = self.e_cv
        c.delete("all")
        W = max(c.winfo_width(), 700)
        lw, rw = 190, 150
        avail = W - lw - rw
        layers = r["layers"]
        top = max(L["size"] for L in layers)
        sc = avail / top
        rh = 46
        for i, L in enumerate(layers):
            y = 4 + i * (rh + 8)
            c.create_text(0, y + 12, text=f"{L['layer']}  {L['name'].upper()}", anchor="w", fill=T["fg"], font=T.font("lab"))
            c.create_text(0, y + 30, text=L["pdu"], anchor="w", fill=T["mut"], font=(T.sans, 9))
            hdr = 8 if L["layer"] == 1 else L["header"]
            size = L["size"]
            x = lw
            trailer = 4 if L["layer"] == 2 else 0
            parts = []
            if hdr:
                parts.append((hdr, "hdr", {1: "Preamble+SFD", 2: "Eth hdr", 3: "IP hdr", 4: "TCP hdr" if self.e_proto.get() == "TCP" else "UDP hdr"}.get(L["layer"], "hdr")))
            body = size - hdr - trailer
            if body > 0:
                parts.append((body, "body", "Data" if L["layer"] == 7 else "payload" if L["layer"] != 1 else "frame"))
            if trailer:
                parts.append((trailer, "hdr", "FCS"))
            for nbytes, kind, name in parts:
                w = max(nbytes * sc, 3)
                c.create_rectangle(x, y, x + w, y + rh, fill=T["fg"] if kind == "hdr" else T["card"],
                                   outline=T["bg"] if kind == "hdr" else T["line"])
                if w > 44:
                    c.create_text(x + w / 2, y + rh / 2 - 7, text=name, fill=T["bg"] if kind == "hdr" else T["fg"],
                                  font=(T.sans, 9, "bold"))
                    c.create_text(x + w / 2, y + rh / 2 + 9, text=f"{nbytes} B", fill=T["bg"] if kind == "hdr" else T["mut"],
                                  font=(T.mono, 8))
                x += w
            c.create_text(x + 10, y + rh / 2, text=f"{size} B", anchor="w", fill=T["mut"], font=(T.mono, 10))
        c.configure(height=4 + len(layers) * (rh + 8))
