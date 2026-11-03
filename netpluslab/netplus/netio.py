"""Real network operations (stdlib only): DNS client, TCP port checker, system command runner, echo lab.

Everything here is GUI-free and safe to import headless. Blocking calls are meant to run in worker threads."""

from __future__ import annotations

import errno
import ipaddress
import os
import platform
import queue
import random
import re
import shutil
import socket
import struct
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .data import PORTS
from .subnet import NetError

# --------------------------------------------------------------------------
# DNS client (RFC 1035) - shows what really travels in UDP/53
# --------------------------------------------------------------------------
QTYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12, "MX": 15, "TXT": 16, "AAAA": 28, "SRV": 33}
QTYPE_NAMES = {v: k for k, v in QTYPES.items()}
RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED"}


def build_dns_query(name: str, qtype: str = "A", qid: int | None = None, recursion: bool = True) -> bytes:
    if qtype not in QTYPES:
        raise NetError(f"Unsupported record type '{qtype}'.")
    qid = random.randrange(0, 65536) if qid is None else qid
    flags = 0x0100 if recursion else 0
    header = struct.pack("!HHHHHH", qid, flags, 1, 0, 0, 0)
    qname = b""
    for label in name.strip(".").split("."):
        if not label:
            raise NetError("Invalid DNS name.")
        try:
            enc = label.encode("idna")
        except UnicodeError:
            raise NetError("Invalid DNS label (empty, too long, or not encodable).") from None
        if len(enc) > 63:
            raise NetError("A DNS label may be at most 63 characters.")
        qname += bytes([len(enc)]) + enc
    qname += b"\x00"
    return header + qname + struct.pack("!HH", QTYPES[qtype], 1)


def _read_name(data: bytes, off: int) -> tuple[str, int]:
    labels = []
    jumped = False
    end = off
    hops = 0
    while True:
        if off >= len(data):
            raise NetError("Malformed DNS response (name overruns message).")
        length = data[off]
        if length == 0:
            off += 1
            break
        if length & 0xC0 == 0xC0:
            if off + 1 >= len(data):
                raise NetError("Malformed DNS response (bad pointer).")
            ptr = ((length & 0x3F) << 8) | data[off + 1]
            if not jumped:
                end = off + 2
            off = ptr
            jumped = True
            hops += 1
            if hops > 32:
                raise NetError("Malformed DNS response (pointer loop).")
            continue
        off += 1
        labels.append(data[off:off + length].decode("ascii", "replace"))
        off += length
    if not jumped:
        end = off
    return (".".join(labels) or "."), end


def parse_dns_response(data: bytes) -> dict:
    if len(data) < 12:
        raise NetError("DNS response too short.")
    qid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", data[:12])
    off = 12
    questions = []
    for _ in range(qd):
        name, off = _read_name(data, off)
        qt, qc = struct.unpack("!HH", data[off:off + 4])
        off += 4
        questions.append((name, QTYPE_NAMES.get(qt, str(qt))))

    def read_rrs(count):
        nonlocal off
        out = []
        for _ in range(count):
            name, off = _read_name(data, off)
            rtype, rclass, ttl, rdlen = struct.unpack("!HHIH", data[off:off + 10])
            off += 10
            rd_start = off
            rdata = data[off:off + rdlen]
            off += rdlen
            out.append((name, QTYPE_NAMES.get(rtype, str(rtype)), ttl, _format_rdata(data, rtype, rd_start, rdata)))
        return out

    answers = read_rrs(an)
    authority = read_rrs(ns)
    additional = read_rrs(ar)
    return {
        "id": qid, "qr": bool(flags & 0x8000), "opcode": (flags >> 11) & 0xF, "aa": bool(flags & 0x0400),
        "tc": bool(flags & 0x0200), "rd": bool(flags & 0x0100), "ra": bool(flags & 0x0080),
        "rcode": RCODES.get(flags & 0xF, str(flags & 0xF)), "questions": questions,
        "answers": answers, "authority": authority, "additional": additional,
    }


def _format_rdata(msg: bytes, rtype: int, start: int, rdata: bytes) -> str:
    try:
        if rtype == 1 and len(rdata) == 4:
            return str(ipaddress.IPv4Address(rdata))
        if rtype == 28 and len(rdata) == 16:
            return str(ipaddress.IPv6Address(rdata))
        if rtype in (2, 5, 12):
            return _read_name(msg, start)[0]
        if rtype == 15:
            pref = struct.unpack("!H", rdata[:2])[0]
            return f"{pref} {_read_name(msg, start + 2)[0]}"
        if rtype == 16:
            parts, i = [], 0
            while i < len(rdata):
                ln = rdata[i]
                parts.append(rdata[i + 1:i + 1 + ln].decode("utf-8", "replace"))
                i += 1 + ln
            return " ".join(f'"{p}"' for p in parts)
        if rtype == 6:
            mname, o = _read_name(msg, start)
            rname, o = _read_name(msg, o)
            serial, refresh, retry, expire, minimum = struct.unpack("!IIIII", msg[o:o + 20])
            return f"{mname} {rname} serial={serial} refresh={refresh} retry={retry} expire={expire} min={minimum}"
        if rtype == 33:
            prio, weight, port = struct.unpack("!HHH", rdata[:6])
            return f"{prio} {weight} {port} {_read_name(msg, start + 6)[0]}"
    except (struct.error, ValueError, NetError):
        pass
    return rdata.hex()


def system_resolvers() -> list[str]:
    out = []
    try:
        with open("/etc/resolv.conf", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"\s*nameserver\s+(\S+)", line)
                if m:
                    out.append(m.group(1))
    except OSError:
        pass
    return out or ["1.1.1.1", "8.8.8.8"]


def dns_query(name: str, qtype: str = "A", server: str | None = None, timeout: float = 3.0) -> dict:
    """Send a real DNS query over UDP (falling back to TCP when truncated)."""
    server = (server or system_resolvers()[0]).strip()
    query = build_dns_query(name, qtype)
    qid = struct.unpack("!H", query[:2])[0]
    try:
        infos = socket.getaddrinfo(server, 53, type=socket.SOCK_DGRAM)
    except socket.gaierror:
        raise NetError(f"Cannot resolve DNS server '{server}'.") from None
    family, _t, _p, _c, addr = infos[0]
    transport = "UDP"
    t0 = time.perf_counter()
    with socket.socket(family, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        try:
            s.sendto(query, addr)
            while True:
                data, peer = s.recvfrom(4096)
                if len(data) >= 2 and struct.unpack("!H", data[:2])[0] == qid:
                    break
        except socket.timeout:
            raise NetError(f"No answer from {server} within {timeout:g} s (UDP/53 may be blocked).") from None
        except OSError as e:
            raise NetError(f"Network error talking to {server}: {e}") from None
    result = parse_dns_response(data)
    if result["tc"]:
        transport = "TCP (response was truncated over UDP)"
        try:
            with socket.create_connection((server, 53), timeout=timeout) as ts:
                ts.settimeout(timeout)
                ts.sendall(struct.pack("!H", len(query)) + query)
                hdr = _recv_exact(ts, 2)
                data = _recv_exact(ts, struct.unpack("!H", hdr)[0])
            result = parse_dns_response(data)
        except (OSError, NetError) as e:
            raise NetError(f"TCP fallback failed: {e}") from None
    result.update({"server": server, "transport": transport, "rtt_ms": (time.perf_counter() - t0) * 1000,
                   "size": len(data), "query_size": len(query)})
    return result


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise NetError("Connection closed early.")
        buf += chunk
    return buf


def reverse_name(ip_text: str) -> str:
    try:
        return ipaddress.ip_address(ip_text.strip()).reverse_pointer
    except ValueError:
        raise NetError(f"'{ip_text.strip()}' is not a valid IP address.") from None


# --------------------------------------------------------------------------
# TCP port checker
# --------------------------------------------------------------------------
_SERVICE = {}
for _p, _t, _s, *_rest in PORTS:
    _SERVICE.setdefault(_p, _s)


def service_name(port: int) -> str:
    return _SERVICE.get(port, "")


MAX_PORTS = 1024


def parse_ports(text: str) -> list[int]:
    ports: set[int] = set()
    for part in re.split(r"[,\s]+", text.strip()):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise NetError(f"'{part}' is not a port or range. Use e.g. 22,80,443 or 1-1024.")
        lo = int(m.group(1))
        hi = int(m.group(2) or lo)
        if lo > hi:
            lo, hi = hi, lo
        if lo < 1 or hi > 65535:
            raise NetError("Ports must be between 1 and 65535.")
        ports.update(range(lo, hi + 1))
        if len(ports) > MAX_PORTS:
            raise NetError(f"At most {MAX_PORTS} ports per run.")
    if not ports:
        raise NetError("Enter at least one port.")
    return sorted(ports)


def resolve_host(host: str) -> tuple[int, str]:
    host = host.strip()
    if not host:
        raise NetError("Enter a hostname or IP address.")
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise NetError(f"Cannot resolve '{host}'.") from None
    fam, _t, _p, _c, addr = infos[0]
    return fam, addr[0]


def tcp_check(family: int, ip: str, port: int, timeout: float) -> tuple[str, float]:
    """Return ('open'|'closed'|'filtered', rtt_ms)."""
    t0 = time.perf_counter()
    s = socket.socket(family, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        return "open", (time.perf_counter() - t0) * 1000
    except ConnectionRefusedError:
        return "closed", (time.perf_counter() - t0) * 1000
    except (socket.timeout, TimeoutError):
        return "filtered", timeout * 1000
    except OSError as e:
        if e.errno == errno.ECONNREFUSED or getattr(e, "winerror", None) == 10061:
            return "closed", (time.perf_counter() - t0) * 1000
        return "filtered", (time.perf_counter() - t0) * 1000
    finally:
        s.close()


def scan_ports(host: str, ports: list[int], timeout: float = 0.8, workers: int = 100,
               stop: threading.Event | None = None, progress=None) -> dict:
    family, ip = resolve_host(host)
    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 200))) as pool:
        futures = {pool.submit(tcp_check, family, ip, p, timeout): p for p in ports}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                results[p] = fut.result()
            except Exception:
                results[p] = ("filtered", 0.0)
            done += 1
            if progress:
                progress(done, len(ports))
            if stop is not None and stop.is_set():
                for f in futures:
                    f.cancel()
                break
    return {"host": host, "ip": ip, "results": dict(sorted(results.items())), "stopped": bool(stop and stop.is_set())}


# --------------------------------------------------------------------------
# System command runner (allow-listed, no shell)
# --------------------------------------------------------------------------
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-:]{0,252}$")
_SYS = platform.system()

# key -> (label, needs_host, [argv templates in order of preference])
COMMANDS = {
    "ping": ("ping", True, {
        "Windows": [["ping", "-n", "4", "{h}"]],
        "default": [["ping", "-c", "4", "{h}"]]}),
    "traceroute": ("traceroute", True, {
        "Windows": [["tracert", "-d", "-h", "20", "{h}"]],
        "default": [["traceroute", "-n", "-m", "20", "{h}"], ["tracepath", "-n", "{h}"]]}),
    "nslookup": ("nslookup", True, {"default": [["nslookup", "{h}"]]}),
    "ipconfig": ("IP configuration", False, {
        "Windows": [["ipconfig", "/all"]],
        "Darwin": [["ifconfig"]],
        "default": [["ip", "addr"], ["ifconfig", "-a"]]}),
    "arp": ("ARP cache", False, {
        "Windows": [["arp", "-a"]],
        "default": [["ip", "neigh"], ["arp", "-a"]]}),
    "route": ("Routing table", False, {
        "Windows": [["route", "print"]],
        "Darwin": [["netstat", "-rn"]],
        "default": [["ip", "route"], ["netstat", "-rn"]]}),
    "netstat": ("Connections", False, {
        "Windows": [["netstat", "-ano"]],
        "Darwin": [["netstat", "-an"]],
        "default": [["ss", "-tun"], ["netstat", "-tun"]]}),
    "hostname": ("Hostname", False, {"default": [["hostname"]]}),
}


def build_command(key: str, host: str = "") -> list[str]:
    if key not in COMMANDS:
        raise NetError("Unknown command.")
    _label, needs_host, table = COMMANDS[key]
    templates = table.get(_SYS, table["default"])
    if needs_host:
        host = host.strip()
        if not _HOST_RE.match(host):
            raise NetError("Enter a valid hostname or IP address (letters, digits, '.', '-', ':').")
    for tpl in templates:
        if shutil.which(tpl[0]):
            return [a.replace("{h}", host) for a in tpl]
    raise NetError(f"'{templates[0][0]}' is not installed on this system.")


def run_command(argv: list[str], on_line, stop: threading.Event | None = None, timeout: float = 90.0) -> int:
    """Run argv (no shell), stream output lines to on_line. Returns the exit code (-1 on timeout/stop)."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            errors="replace", bufsize=1, creationflags=flags)
    deadline = time.monotonic() + timeout

    def watchdog():
        while proc.poll() is None:
            if (stop is not None and stop.is_set()) or time.monotonic() > deadline:
                try:
                    proc.kill()
                except OSError:
                    pass
                return
            time.sleep(0.2)

    threading.Thread(target=watchdog, daemon=True).start()
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            on_line(line.rstrip("\n"))
    finally:
        proc.stdout.close()
        proc.wait()
    return proc.returncode


# --------------------------------------------------------------------------
# Local socket lab: real TCP and UDP echo server + clients on loopback
# --------------------------------------------------------------------------
class EchoLab:
    def __init__(self, port: int = 5050, udp_loss: float = 0.0, host: str = "127.0.0.1"):
        self.host, self.port, self.udp_loss = host, port, udp_loss
        self.events: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._tcp = self._udp = None
        self._threads: list[threading.Thread] = []
        self.running = False

    def log(self, who: str, text: str) -> None:
        self.events.put((time.strftime("%H:%M:%S"), who, text))

    def start(self) -> None:
        if self.running:
            return
        try:
            tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp.bind((self.host, self.port))
            tcp.listen(8)
            tcp.settimeout(0.2)
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.bind((self.host, self.port))
            udp.settimeout(0.2)
        except OSError as e:
            for s in (locals().get("tcp"), locals().get("udp")):
                if s:
                    s.close()
            raise NetError(f"Cannot bind {self.host}:{self.port}: {e}") from None
        self._tcp, self._udp = tcp, udp
        self._stop.clear()
        self.running = True
        for target in (self._tcp_loop, self._udp_loop):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            self._threads.append(t)
        self.log("SERVER", f"TCP listening on {self.host}:{self.port}  (state LISTEN)")
        self.log("SERVER", f"UDP bound on {self.host}:{self.port}  (no listen, no accept: just recvfrom)")

    def stop(self) -> None:
        if not self.running:
            return
        self._stop.set()
        for t in self._threads:
            t.join(timeout=1.0)
        for s in (self._tcp, self._udp):
            if s:
                s.close()
        self._threads.clear()
        self.running = False
        self.log("SERVER", "Stopped.")

    def _tcp_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, addr = self._tcp.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.log("SERVER", f"TCP accept() from {addr[0]}:{addr[1]}  (handshake complete, new connected socket)")
            threading.Thread(target=self._tcp_conn, args=(conn, addr), daemon=True).start()

    def _tcp_conn(self, conn: socket.socket, addr) -> None:
        conn.settimeout(0.5)
        with conn:
            while not self._stop.is_set():
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    self.log("SERVER", f"TCP peer {addr[1]} sent FIN (recv returned 0 bytes)")
                    break
                self.log("SERVER", f"TCP recv {len(data)} B from :{addr[1]} -> echoing")
                try:
                    conn.sendall(b"ECHO: " + data)
                except OSError:
                    break

    def _udp_loop(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._udp.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            if random.random() < self.udp_loss:
                self.log("SERVER", f"UDP datagram {len(data)} B from :{addr[1]} DROPPED (simulated loss {self.udp_loss:.0%}), no reply")
                continue
            self.log("SERVER", f"UDP datagram {len(data)} B from :{addr[1]} -> echoing (no connection involved)")
            try:
                self._udp.sendto(b"ECHO: " + data, addr)
            except OSError:
                pass


def tcp_client(host: str, port: int, message: str, timeout: float = 2.0, emit=None) -> list[tuple[str, str]]:
    """Real TCP exchange. `emit(who, text)` is called as events happen; the list is also returned."""
    out: list[tuple[str, str]] = []

    def note(text: str) -> None:
        out.append(("CLIENT", text))
        if emit:
            emit("CLIENT", text)

    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            t1 = time.perf_counter()
            local = s.getsockname()
            note(f"TCP connect() ok in {(t1 - t0) * 1000:.2f} ms  (SYN, SYN-ACK, ACK) from ephemeral port {local[1]}")
            s.sendall(message.encode())
            note(f"TCP send {len(message.encode())} B")
            s.settimeout(timeout)
            t2 = time.perf_counter()
            data = s.recv(4096)
            note(f"TCP reply {len(data)} B in {(time.perf_counter() - t2) * 1000:.2f} ms: {data.decode(errors='replace')!r}")
        note("TCP close() sent FIN")
    except ConnectionRefusedError:
        note(f"TCP connect refused (RST): nothing is listening on {host}:{port}")
    except socket.timeout:
        note("TCP timed out")
    except OSError as e:
        note(f"TCP error: {e}")
    return out


def udp_client(host: str, port: int, message: str, timeout: float = 1.0, tries: int = 1, emit=None) -> list[tuple[str, str]]:
    """Real UDP exchange with optional application-level retries (UDP itself never retries)."""
    out: list[tuple[str, str]] = []

    def note(text: str) -> None:
        out.append(("CLIENT", text))
        if emit:
            emit("CLIENT", text)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        for attempt in range(1, tries + 1):
            t0 = time.perf_counter()
            try:
                s.sendto(message.encode(), (host, port))
            except OSError as e:
                note(f"UDP send error: {e}")
                return out
            local = s.getsockname()
            note(f"UDP sendto {len(message.encode())} B from port {local[1]}  (attempt {attempt}/{tries}, no handshake)")
            try:
                data, _ = s.recvfrom(4096)
                note(f"UDP reply {len(data)} B in {(time.perf_counter() - t0) * 1000:.2f} ms: {data.decode(errors='replace')!r}")
                return out
            except socket.timeout:
                if attempt < tries:
                    note(f"UDP no reply within {timeout:g} s. UDP does not retry; this APPLICATION sends it again.")
                else:
                    note(f"UDP no reply within {timeout:g} s: lost datagram or no listener. Nothing will resend it unless the application does.")
            except ConnectionRefusedError:
                note("UDP got ICMP port unreachable (nothing bound to that port)")
                return out
            except OSError as e:
                note(f"UDP error: {e}")
                return out
    return out
