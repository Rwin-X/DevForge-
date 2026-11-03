"""TCP/UDP protocol simulator (scripted, deterministic) and encapsulation maths.

Pure logic: the GUI only renders the Step objects produced here."""

from __future__ import annotations

import math
from dataclasses import dataclass

M = 0xFFFFFFFF


@dataclass
class SimConfig:
    client_ip: str = "192.168.1.10"
    server_ip: str = "203.0.113.20"
    client_port: int = 49321
    server_port: int = 443
    c_isn: int = 1000
    s_isn: int = 5000
    c_len: int = 300       # request bytes (client -> server)
    s_len: int = 1200      # response bytes (server -> client)
    mss: int = 1460
    udp_server_port: int = 53


@dataclass
class Step:
    kind: str                # 'pkt' | 'lost' | 'note'
    direction: str           # 'c2s' | 's2c' | ''
    proto: str               # 'TCP' | 'UDP' | ''
    flags: str = ""
    seq: int | None = None
    ack: int | None = None
    seq_r: int | None = None
    ack_r: int | None = None
    length: int = 0
    win: int | None = None
    title: str = ""
    text: str = ""
    cstate: str = ""
    sstate: str = ""
    retrans: bool = False
    sport: int = 0
    dport: int = 0
    udp_len: int | None = None

    def label(self) -> str:
        """Short text drawn on the arrow."""
        if self.kind == "note":
            return self.title
        if self.proto == "UDP":
            return f"UDP  {self.length} B payload"
        parts = [f"[{self.flags}]"]
        if self.seq_r is not None:
            parts.append(f"seq={self.seq_r}")
        if self.ack_r is not None and "ACK" in self.flags:
            parts.append(f"ack={self.ack_r}")
        if self.length:
            parts.append(f"len={self.length}")
        return " ".join(parts)


class _Builder:
    def __init__(self, cfg: SimConfig, proto: str = "TCP", established: bool = False):
        self.cfg = cfg
        self.proto = proto
        self.steps: list[Step] = []
        self.sp = cfg.server_port if proto == "TCP" else cfg.udp_server_port
        self.cs = "CLOSED" if proto == "TCP" else "-"
        self.ss = "LISTEN" if proto == "TCP" else "-"
        self.cnext = cfg.c_isn & M
        self.snext = cfg.s_isn & M
        if established:
            self.cnext = (self.cnext + 1) & M
            self.snext = (self.snext + 1) & M
            self.cs = self.ss = "ESTABLISHED"
            self.add("note", "", title="ESTABLISHED",
                     text="This scenario starts from an open connection: the three-way handshake already happened, "
                          "so both sides know each other's sequence numbers.")

    def add(self, kind, direction, flags="", seq=None, ack=None, length=0, win=None, title="", text="",
            cs=None, ss=None, seq_r="auto", ack_r="auto", retrans=False, udp_len=None) -> Step:
        c = self.cfg
        if cs is not None:
            self.cs = cs
        if ss is not None:
            self.ss = ss
        if direction == "c2s":
            send_isn, recv_isn, sport, dport = c.c_isn, c.s_isn, c.client_port, self.sp
        elif direction == "s2c":
            send_isn, recv_isn, sport, dport = c.s_isn, c.c_isn, self.sp, c.client_port
        else:
            send_isn = recv_isn = sport = dport = 0
        if seq_r == "auto":
            seq_r = None if seq is None else (seq - send_isn) & M
        if ack_r == "auto":
            ack_r = None if ack is None else (ack - recv_isn) & M
        step = Step(kind=kind, direction=direction, proto=self.proto if kind != "note" else "",
                    flags=flags, seq=seq, ack=ack, seq_r=seq_r, ack_r=ack_r, length=length, win=win,
                    title=title, text=text, cstate=self.cs, sstate=self.ss, retrans=retrans,
                    sport=sport, dport=dport, udp_len=udp_len)
        self.steps.append(step)
        return step


# --------------------------------------------------------------------------
# TCP building blocks
# --------------------------------------------------------------------------
def _handshake(b: _Builder) -> None:
    c = b.cfg
    b.add("pkt", "c2s", "SYN", seq=b.cnext, win=65535, title="1. SYN", cs="SYN_SENT",
          text=f"The client opens the connection from ephemeral port {c.client_port} to port {b.sp}. "
               f"It picks an Initial Sequence Number (ISN = {c.c_isn}). SYN consumes one sequence number. "
               "No ACK flag yet because the client has nothing to acknowledge. The SYN also carries options (MSS, Window Scale, SACK, Timestamps).")
    b.cnext = (b.cnext + 1) & M
    b.add("pkt", "s2c", "SYN,ACK", seq=b.snext, ack=b.cnext, win=65535, title="2. SYN-ACK", ss="SYN_RCVD",
          text=f"The server acknowledges the client's SYN (ack = {c.c_isn} + 1 = {b.cnext}) and announces its own ISN "
               f"({c.s_isn}). It is now half-open (SYN_RCVD) and keeps this in its backlog: this is what a SYN flood fills up.")
    b.snext = (b.snext + 1) & M
    b.add("pkt", "c2s", "ACK", seq=b.cnext, ack=b.snext, win=65535, title="3. ACK", cs="ESTABLISHED", ss="ESTABLISHED",
          text=f"The client acknowledges the server's ISN (ack = {c.s_isn} + 1 = {b.snext}). Both sides are ESTABLISHED "
               "and may now send data. Parameters negotiated: MSS, window scaling, SACK.")


def _stream(b: _Builder, direction: str, nbytes: int) -> None:
    c = b.cfg
    nbytes = max(1, min(nbytes, c.mss * 6))
    segs = []
    remaining = nbytes
    while remaining > 0:
        n = min(c.mss, remaining)
        segs.append(n)
        remaining -= n
    who = "client" if direction == "c2s" else "server"
    for i, n in enumerate(segs):
        last = i == len(segs) - 1
        flags = "PSH,ACK" if last else "ACK"
        title = f"DATA {i + 1}/{len(segs)}" if len(segs) > 1 else "DATA"
        why = ("PSH asks the receiver to pass the data to the application immediately. " if last else
               "A full-size segment (MSS) is sent; the sender may keep sending while its window allows. ")
        if direction == "c2s":
            b.add("pkt", "c2s", flags, seq=b.cnext, ack=b.snext, length=n, win=65535, title=title,
                  text=f"The {who} sends {n} bytes starting at sequence number {b.cnext}. {why}")
            b.cnext = (b.cnext + n) & M
        else:
            b.add("pkt", "s2c", flags, seq=b.snext, ack=b.cnext, length=n, win=65535, title=title,
                  text=f"The {who} sends {n} bytes starting at sequence number {b.snext}. {why}")
            b.snext = (b.snext + n) & M
        if i % 2 == 1 or last:
            covered = "the last two segments" if i % 2 == 1 else "this segment"
            if direction == "c2s":
                b.add("pkt", "s2c", "ACK", seq=b.snext, ack=b.cnext, win=65535, title="ACK",
                      text=f"Cumulative acknowledgment: 'I received everything up to byte {b.cnext - 1}, send {b.cnext} next'. "
                           f"It covers {covered}. Receivers typically ACK every second segment (delayed ACK).")
            else:
                b.add("pkt", "c2s", "ACK", seq=b.cnext, ack=b.snext, win=65535, title="ACK",
                      text=f"Cumulative acknowledgment: 'I received everything up to byte {b.snext - 1}, send {b.snext} next'. "
                           f"It covers {covered}. Receivers typically ACK every second segment (delayed ACK).")


def _teardown(b: _Builder) -> None:
    b.add("pkt", "c2s", "FIN,ACK", seq=b.cnext, ack=b.snext, win=65535, title="1. FIN", cs="FIN_WAIT_1",
          text="The client has no more data and starts a graceful close. FIN consumes one sequence number. "
               "The connection is now half-closed: the client can still receive.")
    b.cnext = (b.cnext + 1) & M
    b.add("pkt", "s2c", "ACK", seq=b.snext, ack=b.cnext, win=65535, title="2. ACK", cs="FIN_WAIT_2", ss="CLOSE_WAIT",
          text="The server acknowledges the FIN. It may still have data to send; the application must call close() "
               "before the server sends its own FIN. (If it has nothing left, steps 2 and 3 are often merged into one FIN,ACK.)")
    b.add("pkt", "s2c", "FIN,ACK", seq=b.snext, ack=b.cnext, win=65535, title="3. FIN", ss="LAST_ACK",
          text="The server application closed its side, so the server sends its FIN.")
    b.snext = (b.snext + 1) & M
    b.add("pkt", "c2s", "ACK", seq=b.cnext, ack=b.snext, win=65535, title="4. ACK", cs="TIME_WAIT", ss="CLOSED",
          text="The client acknowledges the server's FIN and enters TIME_WAIT. The server is CLOSED immediately.")
    b.add("note", "", title="TIME_WAIT expires", cs="CLOSED",
          text="The client waits 2 x MSL (commonly 60 s, OS-dependent) so that late duplicate segments from this "
               "connection die out and the final ACK could be resent if lost. Then the port pair can be reused. "
               "Many sockets stuck in TIME_WAIT on a busy server is normal; many in CLOSE_WAIT means an application bug.")


# --------------------------------------------------------------------------
# TCP scenarios
# --------------------------------------------------------------------------
def build_handshake(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg)
    _handshake(b)
    return b.steps


def build_data(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg, established=True)
    _stream(b, "c2s", cfg.c_len)
    _stream(b, "s2c", cfg.s_len)
    return b.steps


def build_teardown(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg, established=True)
    _teardown(b)
    return b.steps


def build_loss(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg, established=True)
    n = max(1, min(cfg.c_len, cfg.mss))
    seq = b.cnext
    b.add("lost", "c2s", "PSH,ACK", seq=seq, ack=b.snext, length=n, win=65535, title="DATA (lost)",
          text=f"The client sends {n} bytes (seq {seq}). The segment is dropped on the way (congested router, bad link). "
               "Nobody tells the sender: it only learns from the absence of an ACK.")
    b.add("note", "", title="RTO expires",
          text="The retransmission timer (RTO, derived from measured round-trip times) runs out before an ACK arrives. "
               "With three duplicate ACKs TCP would use fast retransmit instead of waiting. Each further timeout doubles the RTO (exponential backoff) "
               "and the congestion window collapses.")
    b.add("pkt", "c2s", "PSH,ACK", seq=seq, ack=b.snext, length=n, win=65535, title="DATA (retransmit)", retrans=True,
          text=f"The same bytes are sent again with the SAME sequence number ({seq}). That is how the receiver recognizes the duplicate-free stream.")
    b.cnext = (b.cnext + n) & M
    b.add("pkt", "s2c", "ACK", seq=b.snext, ack=b.cnext, win=65535, title="ACK",
          text=f"The server acknowledges up to byte {b.cnext - 1}. The data is delivered intact and in order. "
               "UDP would have silently lost it.")
    return b.steps


def build_window(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg, established=True)
    seg = 1000
    for i in (1, 2):
        b.add("pkt", "c2s", "ACK", seq=b.cnext, ack=b.snext, length=seg, win=65535, title=f"DATA {i}",
              text=f"The client sends {seg} bytes. The server advertised a receive window of 2000 bytes earlier, so the client may have "
                   "at most 2000 unacknowledged bytes in flight.")
        b.cnext = (b.cnext + seg) & M
    b.add("pkt", "s2c", "ACK", seq=b.snext, ack=b.cnext, win=0, title="ACK, win=0",
          text="The server received 2000 bytes but its application has not read them: the buffer is full. "
               "It advertises Window = 0 (zero window). Flow control protects the receiver.")
    b.add("note", "", title="Sender stalls",
          text="The client must stop sending data. It starts a persist timer and periodically sends tiny window probes "
               "so a lost window update cannot deadlock the connection.")
    b.add("pkt", "s2c", "ACK", seq=b.snext, ack=b.cnext, win=2000, title="Window update",
          text="The application read the data, buffer space is free again. The server sends a window update: Window = 2000.")
    b.add("pkt", "c2s", "ACK", seq=b.cnext, ack=b.snext, length=seg, win=65535, title="DATA 3",
          text="The client resumes sending.")
    b.cnext = (b.cnext + seg) & M
    b.add("pkt", "s2c", "ACK", seq=b.snext, ack=b.cnext, win=2000, title="ACK",
          text=f"All {3 * seg} bytes are acknowledged. The sliding window moved forward by the acknowledged amount.")
    return b.steps


def build_refused(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg)
    b.ss = "CLOSED"
    b.add("pkt", "c2s", "SYN", seq=b.cnext, win=65535, title="SYN", cs="SYN_SENT",
          text=f"The client tries to connect to port {b.sp}, but nothing is listening there.")
    b.cnext = (b.cnext + 1) & M
    b.add("pkt", "s2c", "RST,ACK", seq=0, ack=b.cnext, seq_r=0, win=0, title="RST", cs="CLOSED",
          text="The server's OS answers immediately with RST,ACK. The client reports 'connection refused'. "
               "A port with a firewall DROP rule would not answer at all, so the client would time out instead: "
               "refused = closed port, timeout = filtered.")
    b.add("note", "", title="Connection refused",
          text="Closed port -> instant RST. Filtered port -> no reply (timeout, or an ICMP unreachable). "
               "Port scanners use exactly this difference to classify ports.")
    return b.steps


def build_full(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg)
    _handshake(b)
    _stream(b, "c2s", cfg.c_len)
    _stream(b, "s2c", cfg.s_len)
    _teardown(b)
    return b.steps


# --------------------------------------------------------------------------
# UDP scenarios
# --------------------------------------------------------------------------
def _udp_len(n: int) -> int:
    return 8 + n


def build_udp(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg, "UDP")
    q = max(1, min(cfg.c_len, 1472))
    r = max(1, min(cfg.s_len, 1472))
    b.add("pkt", "c2s", "", length=q, udp_len=_udp_len(q), title="Query",
          text=f"The client sends one datagram to port {b.sp} immediately: no handshake, no connection state. "
               f"UDP header = 8 bytes, so the length field is {_udp_len(q)}. The source port {cfg.client_port} is how the reply finds its way back.")
    b.add("pkt", "s2c", "", length=r, udp_len=_udp_len(r), title="Response",
          text=f"The server answers with one datagram (length {_udp_len(r)}) to the client's source port. "
               "There is no ACK: the response itself is the only confirmation, and only the application knows it is one.")
    b.add("note", "", title="No state kept",
          text="No connection was created and nothing needs closing. Each datagram is independent, keeps its boundaries and may be "
               "lost, duplicated or reordered. That is why DNS, DHCP, NTP, VoIP and streaming prefer it: lowest latency and overhead.")
    return b.steps


def build_udp_loss(cfg: SimConfig) -> list[Step]:
    b = _Builder(cfg, "UDP")
    q = max(1, min(cfg.c_len, 1472))
    r = max(1, min(cfg.s_len, 1472))
    b.add("lost", "c2s", "", length=q, udp_len=_udp_len(q), title="Query (lost)",
          text="The datagram is dropped in the network. UDP gives the sender no feedback at all.")
    b.add("note", "", title="Application timeout",
          text="Nothing arrives, and UDP does not retransmit. The APPLICATION must notice (a resolver waits a second or more) "
               "and decide to retry, use another server or give up. Reliability above UDP is the application's job (or QUIC's).")
    b.add("pkt", "c2s", "", length=q, udp_len=_udp_len(q), title="Query (app retry)", retrans=True,
          text="The application sends the same request again as a brand-new datagram.")
    b.add("pkt", "s2c", "", length=r, udp_len=_udp_len(r), title="Response",
          text="This time the datagram and its response both arrive.")
    return b.steps


SCENARIOS = [
    ("full", "Full TCP session", "TCP", build_full, "Handshake, request/response, teardown: the complete life of one connection."),
    ("handshake", "3-way handshake", "TCP", build_handshake, "SYN, SYN-ACK, ACK: ISNs, half-open state, ESTABLISHED."),
    ("data", "Data transfer", "TCP", build_data, "Sequence numbers, cumulative ACKs, MSS segmentation, PSH."),
    ("teardown", "Connection teardown", "TCP", build_teardown, "FIN/ACK in both directions, CLOSE_WAIT, LAST_ACK, TIME_WAIT."),
    ("loss", "Packet loss & retransmit", "TCP", build_loss, "Lost segment, RTO, retransmission with the same sequence number."),
    ("window", "Flow control (window)", "TCP", build_window, "Receive window, zero window, window update."),
    ("refused", "Closed port (RST)", "TCP", build_refused, "Why closed ports answer RST and filtered ports stay silent."),
    ("udp", "UDP exchange", "UDP", build_udp, "Query and response with no handshake and no ACK."),
    ("udp_loss", "UDP loss", "UDP", build_udp_loss, "A lost datagram: only the application can recover."),
]


def build_scenario(key: str, cfg: SimConfig) -> list[Step]:
    for k, _name, _proto, fn, _desc in SCENARIOS:
        if k == key:
            return fn(cfg)
    raise KeyError(key)


# --------------------------------------------------------------------------
# Encapsulation maths
# --------------------------------------------------------------------------
def _eth_frame(ip_total: int, vlan: bool) -> tuple[int, int]:
    """Return (frame bytes incl. FCS, padding)."""
    min_payload = 46 - (4 if vlan else 0)
    pad = max(0, min_payload - ip_total)
    return 14 + (4 if vlan else 0) + ip_total + pad + 4, pad


def encapsulate(payload: str, proto: str, src_ip: str, dst_ip: str, sport: int, dport: int,
                src_mac: str, dst_mac: str, vlan: int | None = None, mtu: int = 1500) -> dict:
    data = payload.encode("utf-8")
    n = len(data)
    tcp = proto == "TCP"
    mss = mtu - 40
    v = vlan is not None

    # Which bytes go into the first frame, and how many frames are needed.
    if tcp:
        first_payload = min(n, mss) if n else 0
        segs = max(1, math.ceil(n / mss)) if n else 1
        ip_totals = []
        remaining = n
        for _ in range(segs):
            chunk = min(remaining, mss)
            ip_totals.append(40 + chunk)
            remaining -= chunk
        l4_size = 20 + first_payload
        l3_size = ip_totals[0]
    else:
        total_udp = 8 + n
        frag = (mtu - 20) // 8 * 8
        if total_udp <= mtu - 20:
            ip_totals = [20 + total_udp]
        else:
            ip_totals = []
            remaining = total_udp
            while remaining > 0:
                chunk = min(frag, remaining)
                ip_totals.append(20 + chunk)
                remaining -= chunk
        first_payload = n
        l4_size = total_udp
        l3_size = ip_totals[0]

    frames = [_eth_frame(t, v) for t in ip_totals]
    frame0, pad0 = frames[0]
    wire_total = sum(f for f, _ in frames) + 20 * len(frames)   # preamble 7 + SFD 1 + IFG 12 per frame
    efficiency = (n / wire_total * 100) if wire_total else 0.0

    l4_name = "TCP" if tcp else "UDP"
    layers = [
        dict(layer=7, name="Application", pdu="Data", header=0, size=first_payload if tcp else n,
             fields=[("Payload", f"{n} bytes" + (f" (first segment carries {first_payload})" if tcp and n > mss else ""))]),
        dict(layer=4, name="Transport", pdu="Segment" if tcp else "Datagram", header=20 if tcp else 8, size=l4_size,
             fields=[("Protocol", l4_name), ("Source port", str(sport)), ("Destination port", str(dport))]
                    + ([("Flags", "PSH,ACK"), ("Header", "20 bytes + options")] if tcp else [("Length", str(8 + n))])),
        dict(layer=3, name="Network", pdu="Packet", header=20, size=l3_size,
             fields=[("Version / IHL", "4 / 5 (20 bytes)"), ("TTL", "64"), ("Protocol", "6 (TCP)" if tcp else "17 (UDP)"),
                     ("Source IP", src_ip), ("Destination IP", dst_ip), ("Total length", str(l3_size))]),
        dict(layer=2, name="Data Link", pdu="Frame", header=14 + (4 if v else 0), size=frame0,
             fields=[("Destination MAC", dst_mac), ("Source MAC", src_mac)]
                    + ([("802.1Q tag", f"VLAN {vlan}")] if v else [])
                    + [("EtherType", "0x0800 (IPv4)"), ("Padding", f"{pad0} bytes"), ("FCS (CRC-32)", "4 bytes")]),
        dict(layer=1, name="Physical", pdu="Bits", header=0, size=frame0 + 8,
             fields=[("Frame bits", str(frame0 * 8)), ("Preamble + SFD", "8 bytes"), ("Inter-frame gap", "12 bytes (idle)"),
                     ("On the wire", f"{frame0 + 20} bytes for the first frame")]),
    ]
    notes = []
    if len(frames) > 1:
        if tcp:
            notes.append(f"{n} bytes exceed one MSS ({mss}): TCP splits them into {len(frames)} segments, each in its own frame.")
        else:
            notes.append(f"The UDP datagram ({8 + n} bytes) exceeds the MTU ({mtu}): IP fragments it into {len(frames)} packets. "
                         "Losing any fragment loses the whole datagram. This is why apps keep UDP payloads small.")
    if pad0:
        notes.append(f"The frame is padded with {pad0} bytes to reach the 64-byte Ethernet minimum.")
    return {"layers": layers, "frames": len(frames), "frame_sizes": [f for f, _ in frames], "wire_total": wire_total,
            "efficiency": efficiency, "notes": notes, "mss": mss, "payload_bytes": n}
