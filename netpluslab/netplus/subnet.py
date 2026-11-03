"""IPv4/IPv6 addressing logic, converters and calculators. No GUI, stdlib only."""

from __future__ import annotations

import ipaddress
import math
import re
from itertools import islice

M32 = 0xFFFFFFFF


class NetError(ValueError):
    """User-facing validation error."""


# --------------------------------------------------------------------------
# IPv4 basics
# --------------------------------------------------------------------------
def prefix_to_mask(prefix: int) -> str:
    if not 0 <= prefix <= 32:
        raise NetError("Prefix length must be between 0 and 32.")
    return str(ipaddress.IPv4Address((M32 << (32 - prefix)) & M32 if prefix else 0))


def mask_to_prefix(mask: str) -> int:
    try:
        value = int(ipaddress.IPv4Address(mask.strip()))
    except ValueError:
        raise NetError(f"'{mask}' is not a valid dotted-decimal mask.") from None
    inverted = value ^ M32
    if inverted & (inverted + 1):
        raise NetError(f"'{mask}' is not a contiguous subnet mask (ones must come first, then zeros).")
    return bin(value).count("1")


def wildcard(prefix: int) -> str:
    return str(ipaddress.IPv4Address(((M32 << (32 - prefix)) & M32 if prefix else 0) ^ M32))


def classful_prefix(ip: ipaddress.IPv4Address) -> int:
    first = int(ip) >> 24
    if first < 128:
        return 8
    if first < 192:
        return 16
    return 24


def parse_ipv4(text: str) -> ipaddress.IPv4Address:
    try:
        return ipaddress.IPv4Address(text.strip())
    except ValueError:
        raise NetError(f"'{text.strip()}' is not a valid IPv4 address.") from None


def parse_ip_and_prefix(text: str) -> tuple[ipaddress.IPv4Address, int, bool]:
    """Accept '10.1.2.3/24', '10.1.2.3 /24', '10.1.2.3 255.255.255.0' or '10.1.2.3'.

    Returns (address, prefix, mask_was_given)."""
    t = text.strip()
    if not t:
        raise NetError("Enter an IPv4 address with a mask, e.g. 192.168.1.10/24")
    parts = re.split(r"\s*/\s*|\s+|,", t)
    parts = [p for p in parts if p]
    ip = parse_ipv4(parts[0])
    if len(parts) == 1:
        return ip, classful_prefix(ip), False
    if len(parts) > 2:
        raise NetError("Too many values. Use 'address/prefix' or 'address mask'.")
    m = parts[1]
    if re.fullmatch(r"\d{1,2}", m):
        p = int(m)
        if p > 32:
            raise NetError("Prefix length must be between 0 and 32.")
        return ip, p, True
    return ip, mask_to_prefix(m), True


def classify(ip: ipaddress.IPv4Address) -> tuple[str, str]:
    """Return (class label, address type)."""
    v = int(ip)
    a = v >> 24
    if a == 0:
        cls = "Reserved (0.0.0.0/8)"
    elif a < 127:
        cls = "A"
    elif a == 127:
        cls = "Loopback block"
    elif a < 192:
        cls = "B"
    elif a < 224:
        cls = "C"
    elif a < 240:
        cls = "D (multicast)"
    else:
        cls = "E (reserved)"

    def inside(cidr: str) -> bool:
        return ip in ipaddress.IPv4Network(cidr)

    if v == M32:
        kind = "Limited broadcast"
    elif inside("0.0.0.0/8"):
        kind = "This network / unspecified"
    elif inside("10.0.0.0/8"):
        kind = "Private (RFC 1918)"
    elif inside("100.64.0.0/10"):
        kind = "Carrier-grade NAT (RFC 6598)"
    elif inside("127.0.0.0/8"):
        kind = "Loopback"
    elif inside("169.254.0.0/16"):
        kind = "Link-local (APIPA)"
    elif inside("172.16.0.0/12"):
        kind = "Private (RFC 1918)"
    elif inside("192.0.0.0/24"):
        kind = "IETF protocol assignments"
    elif inside("192.0.2.0/24") or inside("198.51.100.0/24") or inside("203.0.113.0/24"):
        kind = "Documentation (TEST-NET)"
    elif inside("192.168.0.0/16"):
        kind = "Private (RFC 1918)"
    elif inside("198.18.0.0/15"):
        kind = "Benchmarking"
    elif inside("224.0.0.0/4"):
        kind = "Multicast"
    elif inside("240.0.0.0/4"):
        kind = "Reserved"
    else:
        kind = "Public (globally routable)"
    return cls, kind


def dotted_binary(value: int) -> str:
    b = f"{value & M32:032b}"
    return ".".join(b[i:i + 8] for i in range(0, 32, 8))


def host_counts(prefix: int) -> tuple[int, int]:
    """(total addresses, usable hosts)."""
    total = 1 << (32 - prefix)
    if prefix == 32:
        return total, 1
    if prefix == 31:
        return total, 2
    return total, total - 2


def describe_ipv4(ip: ipaddress.IPv4Address, prefix: int) -> dict:
    net = ipaddress.IPv4Network((int(ip) & ((M32 << (32 - prefix)) & M32 if prefix else 0), prefix))
    net_int = int(net.network_address)
    bcast_int = int(net.broadcast_address)
    total, usable = host_counts(prefix)
    if prefix == 32:
        first = last = ip
    elif prefix == 31:
        first, last = net.network_address, net.broadcast_address
    else:
        first, last = ipaddress.IPv4Address(net_int + 1), ipaddress.IPv4Address(bcast_int - 1)
    cls, kind = classify(ip)
    nxt = net_int + total
    prv = net_int - total
    host_role = "host address"
    if prefix < 31:
        if int(ip) == net_int:
            host_role = "network address (not assignable)"
        elif int(ip) == bcast_int:
            host_role = "broadcast address (not assignable)"
    return {
        "ip": ip, "prefix": prefix, "network": net, "mask": prefix_to_mask(prefix),
        "wildcard": wildcard(prefix), "network_address": net.network_address,
        "broadcast": net.broadcast_address, "first": first, "last": last,
        "total": total, "usable": usable, "class": cls, "type": kind, "host_role": host_role,
        "next_network": ipaddress.IPv4Address(nxt) if nxt <= M32 else None,
        "prev_network": ipaddress.IPv4Address(prv) if prv >= 0 else None,
        "host_bits": 32 - prefix,
        "ip_bin": dotted_binary(int(ip)),
        "mask_bin": dotted_binary((M32 << (32 - prefix)) & M32 if prefix else 0),
        "net_bin": dotted_binary(net_int),
        "bcast_bin": dotted_binary(bcast_int),
    }


# --------------------------------------------------------------------------
# VLSM / split / summarize / membership
# --------------------------------------------------------------------------
def prefix_for_hosts(hosts: int) -> int:
    """Smallest block (largest prefix) that holds `hosts` usable addresses (classic: +2)."""
    if hosts < 1:
        raise NetError("Host count must be at least 1.")
    need = hosts + 2
    bits = max(2, math.ceil(math.log2(need)))
    if bits > 32:
        raise NetError("Too many hosts.")
    return 32 - bits


def parse_network(text: str) -> ipaddress.IPv4Network:
    try:
        return ipaddress.IPv4Network(text.strip(), strict=False)
    except ValueError:
        raise NetError(f"'{text.strip()}' is not a valid IPv4 network (use CIDR, e.g. 192.168.1.0/24).") from None


def vlsm(base_text: str, requirements: list[tuple[str, int]]) -> dict:
    base = parse_network(base_text)
    if not requirements:
        raise NetError("Add at least one requirement, e.g. 'Sales 50'.")
    reqs = sorted(requirements, key=lambda r: -r[1])
    start = int(base.network_address)
    end = int(base.broadcast_address) + 1
    pointer = start
    allocations = []
    for name, hosts in reqs:
        prefix = prefix_for_hosts(hosts)
        if prefix < base.prefixlen:
            raise NetError(f"'{name}' needs a /{prefix}, which is larger than the base network {base}.")
        size = 1 << (32 - prefix)
        if pointer % size:
            pointer += size - (pointer % size)
        if pointer + size > end:
            raise NetError(f"Out of address space: '{name}' ({hosts} hosts, /{prefix}) does not fit in {base}.")
        net = ipaddress.IPv4Network((pointer, prefix))
        d = describe_ipv4(net.network_address, prefix)
        allocations.append({
            "name": name, "required": hosts, "prefix": prefix, "network": net, "mask": d["mask"],
            "first": d["first"], "last": d["last"], "broadcast": d["broadcast"],
            "usable": d["usable"], "spare": d["usable"] - hosts, "size": size,
        })
        pointer += size
    free = []
    if pointer < end:
        free = list(ipaddress.summarize_address_range(
            ipaddress.IPv4Address(pointer), ipaddress.IPv4Address(end - 1)))
    used = sum(a["size"] for a in allocations)
    return {"base": base, "allocations": allocations, "free": free,
            "used": used, "total": end - start, "utilization": used / (end - start)}


def summarize(lines: list[str]) -> dict:
    nets = [parse_network(l) for l in lines if l.strip()]
    if not nets:
        raise NetError("Enter one or more networks, one per line.")
    collapsed = list(ipaddress.collapse_addresses(nets))
    lo = min(int(n.network_address) for n in nets)
    hi = max(int(n.broadcast_address) for n in nets)
    bits = (lo ^ hi).bit_length()
    prefix = 32 - bits
    supernet = ipaddress.IPv4Network(((lo >> bits) << bits if bits else lo, prefix))
    covered = sum(n.num_addresses for n in collapsed)
    return {"inputs": nets, "collapsed": collapsed, "supernet": supernet,
            "exact": len(collapsed) == 1 and collapsed[0] == supernet,
            "wasted": supernet.num_addresses - covered, "covered": covered}


def split_network(base_text: str, mode: str, value: int, limit: int = 256) -> dict:
    base = parse_network(base_text)
    if value < 1:
        raise NetError("Value must be at least 1.")
    if mode == "subnets":
        bits = math.ceil(math.log2(value)) if value > 1 else 0
        new_prefix = base.prefixlen + bits
    elif mode == "hosts":
        new_prefix = prefix_for_hosts(value)
    else:
        raise NetError("Unknown split mode.")
    if new_prefix > 32:
        raise NetError("Not enough host bits left for that split.")
    if new_prefix < base.prefixlen:
        raise NetError(f"Each subnet would need a /{new_prefix}, larger than the base network {base}.")
    count = 1 << (new_prefix - base.prefixlen)
    rows = []
    for sub in islice(base.subnets(new_prefix=new_prefix), limit):
        d = describe_ipv4(sub.network_address, new_prefix)
        rows.append({"network": sub, "first": d["first"], "last": d["last"], "broadcast": d["broadcast"]})
    total, usable = host_counts(new_prefix)
    return {"base": base, "new_prefix": new_prefix, "mask": prefix_to_mask(new_prefix),
            "count": count, "usable": usable, "rows": rows, "truncated": count > limit,
            "borrowed": new_prefix - base.prefixlen}


def compare_hosts(a_text: str, b_text: str, mask_text: str, gw_text: str = "") -> dict:
    a = parse_ipv4(a_text)
    b = parse_ipv4(b_text)
    prefix = mask_to_prefix(mask_text) if "." in mask_text else _prefix_only(mask_text)
    da = describe_ipv4(a, prefix)
    db = describe_ipv4(b, prefix)
    out = {"a": da, "b": db, "same": da["network"] == db["network"]}
    problems = []
    for label, d in (("Host A", da), ("Host B", db)):
        if d["host_role"] != "host address" and prefix < 31:
            problems.append(f"{label} is the {d['host_role']}.")
    out["gateway"] = None
    if gw_text.strip():
        gw = parse_ipv4(gw_text)
        dg = describe_ipv4(gw, prefix)
        out["gateway"] = dg
        if dg["network"] != da["network"]:
            problems.append(f"Gateway {gw} is NOT in Host A's subnet {da['network']}: Host A cannot reach it.")
        if dg["network"] != db["network"]:
            problems.append(f"Gateway {gw} is NOT in Host B's subnet {db['network']}: Host B cannot reach it.")
        if dg["host_role"] != "host address" and prefix < 31:
            problems.append(f"Gateway is the {dg['host_role']}.")
    out["problems"] = problems
    return out


def _prefix_only(text: str) -> int:
    t = text.strip().lstrip("/")
    if not t.isdigit() or not 0 <= int(t) <= 32:
        raise NetError("Mask must be dotted decimal (255.255.255.0) or a prefix length (24 or /24).")
    return int(t)


def cidr_table() -> list[tuple]:
    rows = []
    for p in range(8, 33):
        total, usable = host_counts(p)
        octet = (p - 1) // 8 + 1 if p % 8 else None
        block = f"octet {octet}, block {1 << (8 - p % 8)}" if p % 8 else "whole octets"
        rows.append((f"/{p}", prefix_to_mask(p), wildcard(p), total, usable, block))
    return rows


# --------------------------------------------------------------------------
# IPv6
# --------------------------------------------------------------------------
_MULTICAST_SCOPES = {0x1: "interface-local", 0x2: "link-local", 0x4: "admin-local", 0x5: "site-local",
                     0x8: "organization-local", 0xE: "global"}


def classify_ipv6(ip: ipaddress.IPv6Address) -> tuple[str, str]:
    def inside(cidr):
        return ip in ipaddress.IPv6Network(cidr)

    if ip == ipaddress.IPv6Address("::"):
        return "Unspecified (::/128)", "none"
    if ip == ipaddress.IPv6Address("::1"):
        return "Loopback (::1/128)", "host"
    if inside("ff00::/8"):
        scope = _MULTICAST_SCOPES.get(ip.packed[1] & 0xF, "other")
        return "Multicast (FF00::/8)", scope
    if inside("fe80::/10"):
        return "Link-local unicast (FE80::/10)", "link"
    if inside("fc00::/7"):
        return "Unique local unicast (FC00::/7)", "site / organization"
    if inside("::ffff:0:0/96"):
        return "IPv4-mapped (::ffff:0:0/96)", "n/a"
    if inside("2001:db8::/32"):
        return "Documentation (2001:db8::/32)", "n/a"
    if inside("2002::/16"):
        return "6to4 (2002::/16)", "global"
    if inside("2001::/32"):
        return "Teredo (2001::/32)", "global"
    if inside("2000::/3"):
        return "Global unicast (2000::/3)", "global"
    return "Reserved / unassigned", "n/a"


def describe_ipv6(text: str) -> dict:
    t = text.strip()
    if not t:
        raise NetError("Enter an IPv6 address, e.g. 2001:db8:abcd:12::1/64")
    try:
        iface = ipaddress.IPv6Interface(t if "/" in t else t + "/64")
    except ValueError:
        raise NetError(f"'{t}' is not a valid IPv6 address.") from None
    ip = iface.ip
    net = iface.network
    kind, scope = classify_ipv6(ip)
    low = int(ip) & ((1 << 64) - 1)
    sn = int(ipaddress.IPv6Address("ff02::1:ff00:0")) | (int(ip) & 0xFFFFFF)
    return {
        "ip": ip, "prefix": net.prefixlen, "exploded": ip.exploded, "compressed": ip.compressed,
        "type": kind, "scope": scope, "network": net,
        "first": net.network_address, "last": net.broadcast_address if hasattr(net, "broadcast_address") else None,
        "slash64s": (1 << (64 - net.prefixlen)) if net.prefixlen <= 64 else None,
        "interface_id": ":".join(f"{(low >> s) & 0xFFFF:04x}" for s in (48, 32, 16, 0)),
        "eui64_hint": ((low >> 24) & 0xFFFF) == 0xFFFE,
        "solicited_node": str(ipaddress.IPv6Address(sn)),
        "reverse": ip.reverse_pointer,
        "prefix_bits": f"{int(net.network_address) >> (128 - net.prefixlen):b}".zfill(net.prefixlen)[-min(net.prefixlen, 64):] if net.prefixlen else "",
    }


def parse_mac(text: str) -> bytes:
    h = re.sub(r"[^0-9A-Fa-f]", "", text)
    if len(h) != 12:
        raise NetError("A MAC address has 12 hex digits, e.g. 00:1A:2B:3C:4D:5E")
    return bytes.fromhex(h)


def eui64(mac_text: str, prefix_text: str = "fe80::/64") -> dict:
    mac = parse_mac(mac_text)
    try:
        net = ipaddress.IPv6Network(prefix_text.strip() or "fe80::/64", strict=False)
    except ValueError:
        raise NetError("Prefix must look like 2001:db8:1:1::/64") from None
    if net.prefixlen != 64:
        raise NetError("SLAAC with EUI-64 needs a /64 prefix.")
    flipped = bytes([mac[0] ^ 0x02]) + mac[1:3] + b"\xff\xfe" + mac[3:]
    iid = int.from_bytes(flipped, "big")
    addr = ipaddress.IPv6Address(int(net.network_address) | iid)
    return {
        "mac": ":".join(f"{b:02X}" for b in mac),
        "flipped_first": f"{mac[0]:02X} -> {mac[0] ^ 0x02:02X}",
        "interface_id": ":".join(f"{int.from_bytes(flipped[i:i + 2], 'big'):04x}" for i in range(0, 8, 2)),
        "address": addr, "prefix": net,
    }


# --------------------------------------------------------------------------
# Converters
# --------------------------------------------------------------------------
def parse_int(text: str) -> int:
    t = text.strip().lower().replace("_", "").replace(" ", "")
    if not t:
        raise NetError("Enter a number.")
    try:
        if t.startswith("0x"):
            return int(t, 16)
        if t.startswith("0b"):
            return int(t, 2)
        if t.startswith("0o"):
            return int(t, 8)
        return int(t, 10)
    except ValueError:
        raise NetError(f"'{text.strip()}' is not a number. Use 255, 0xFF, 0b1111_1111 or 0o377.") from None


def base_forms(n: int) -> dict:
    if n < 0:
        raise NetError("Negative numbers are not supported here.")
    b = bin(n)[2:]
    pad = (-len(b)) % 8
    bg = (("0" * pad) + b)
    return {"dec": str(n), "bin": " ".join(bg[i:i + 8] for i in range(0, len(bg), 8)),
            "hex": f"0x{n:X}", "oct": f"0o{n:o}", "bits": n.bit_length()}


def ipv4_forms(text: str) -> dict:
    t = text.strip()
    if not t:
        raise NetError("Enter an IPv4 address (dotted decimal, dotted binary, hex or a 32-bit integer).")
    if re.fullmatch(r"[01]{8}(\.[01]{8}){3}", t):
        value = int(t.replace(".", ""), 2)
    elif "." in t:
        value = int(parse_ipv4(t))
    else:
        value = parse_int(t)
        if not 0 <= value <= M32:
            raise NetError("Value does not fit in 32 bits.")
    ip = ipaddress.IPv4Address(value)
    return {"dotted": str(ip), "binary": dotted_binary(value), "hex": f"0x{value:08X}",
            "integer": str(value), "octets": " . ".join(f"{o:3d}" for o in ip.packed)}


def mac_forms(text: str) -> dict:
    mac = parse_mac(text)
    h = mac.hex().upper()
    return {
        "colon": ":".join(h[i:i + 2] for i in range(0, 12, 2)),
        "hyphen": "-".join(h[i:i + 2] for i in range(0, 12, 2)),
        "cisco": ".".join(h[i:i + 4].lower() for i in range(0, 12, 4)),
        "plain": h,
        "oui": ":".join(h[i:i + 2] for i in range(0, 6, 2)),
        "nic": ":".join(h[i:i + 2] for i in range(6, 12, 2)),
        "cast": "Multicast / broadcast group" if mac[0] & 1 else "Unicast",
        "admin": "Locally administered" if mac[0] & 2 else "Universally administered (burned-in OUI)",
        "broadcast": mac == b"\xff" * 6,
    }


_SIZE = {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12,
         "KiB": 1024, "MiB": 1024 ** 2, "GiB": 1024 ** 3, "TiB": 1024 ** 4}
_SPEED = {"bps": 1, "Kbps": 1e3, "Mbps": 1e6, "Gbps": 1e9}
SIZE_UNITS = list(_SIZE)
SPEED_UNITS = list(_SPEED)


def human_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{int(m)} min {s:.0f} s"
    h, m = divmod(m, 60)
    if h < 48:
        return f"{int(h)} h {int(m)} min"
    d, h = divmod(h, 24)
    return f"{int(d)} d {int(h)} h"


def transfer_time(size: float, size_unit: str, speed: float, speed_unit: str, efficiency: float = 90.0) -> dict:
    if size <= 0 or speed <= 0:
        raise NetError("Size and speed must be greater than zero.")
    if not 1 <= efficiency <= 100:
        raise NetError("Efficiency must be between 1 and 100 percent.")
    bits = size * _SIZE[size_unit] * 8
    bps = speed * _SPEED[speed_unit]
    ideal = bits / bps
    real = ideal / (efficiency / 100)
    return {"bits": bits, "bps": bps, "ideal": ideal, "real": real,
            "ideal_h": human_time(ideal), "real_h": human_time(real),
            "mbytes_s": bps * efficiency / 100 / 8 / 1e6}


def tcp_window_math(bandwidth_mbps: float, rtt_ms: float, window_bytes: float) -> dict:
    if bandwidth_mbps <= 0 or rtt_ms <= 0 or window_bytes <= 0:
        raise NetError("All values must be greater than zero.")
    bdp = bandwidth_mbps * 1e6 * (rtt_ms / 1000) / 8
    cap = window_bytes * 8 / (rtt_ms / 1000) / 1e6
    return {"bdp_bytes": bdp, "bdp_kb": bdp / 1024, "window_cap_mbps": cap,
            "limited": cap < bandwidth_mbps, "achievable_mbps": min(cap, bandwidth_mbps),
            "needs_scaling": bdp > 65535}
