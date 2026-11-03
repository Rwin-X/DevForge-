"""Question generators for the Drills page. Pure logic, no GUI."""

from __future__ import annotations

import ipaddress
import random
from dataclasses import dataclass, field

from . import subnet as sn
from .data import OSI, PORTS, QUIZ


@dataclass
class Question:
    prompt: str
    kind: str                      # 'mc' | 'text'
    answer: str
    explanation: str
    tag: str
    choices: list[str] = field(default_factory=list)
    placeholder: str = ""


def normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "").lstrip("/")


def check(q: Question, given: str) -> bool:
    if q.kind == "mc":
        return given == q.answer
    return normalize(given) == normalize(q.answer)


# --------------------------------------------------------------------------
# Subnetting
# --------------------------------------------------------------------------
def _rand_ip(rng: random.Random) -> str:
    base = rng.choice(("10", "172", "192"))
    if base == "10":
        return f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    if base == "172":
        return f"172.{rng.randint(16, 31)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    return f"192.168.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def subnet_question(rng: random.Random) -> Question:
    kind = rng.choice(["hosts", "mask", "prefix", "network", "broadcast", "first", "last",
                       "borrow", "fit", "next", "same"])
    tag = "Subnetting"
    if kind == "hosts":
        p = rng.randint(20, 30)
        total, usable = sn.host_counts(p)
        return Question(f"How many usable host addresses does a /{p} network provide?", "text", str(usable),
                        f"{32 - p} host bits: 2^{32 - p} = {total} addresses, minus network and broadcast = {usable}.",
                        tag, placeholder="number")
    if kind == "mask":
        p = rng.randint(9, 30)
        m = sn.prefix_to_mask(p)
        return Question(f"Write the dotted-decimal subnet mask for /{p}.", "text", m,
                        f"/{p} = {p} one-bits: {sn.dotted_binary((sn.M32 << (32 - p)) & sn.M32)} = {m}.",
                        tag, placeholder="255.255.x.x")
    if kind == "prefix":
        p = rng.randint(9, 30)
        m = sn.prefix_to_mask(p)
        return Question(f"What prefix length is the mask {m}?", "text", str(p),
                        f"Count the one-bits: {sn.dotted_binary((sn.M32 << (32 - p)) & sn.M32)} has {p}.",
                        tag, placeholder="e.g. 26 or /26")
    if kind in ("network", "broadcast", "first", "last", "next"):
        p = rng.randint(17, 29)
        ip = _rand_ip(rng)
        d = sn.describe_ipv4(ipaddress.IPv4Address(ip), p)
        block = 1 << (32 - p) if p >= 24 else None
        hint = (f"The block size in the interesting octet is {256 - int(d['mask'].split('.')[(p - 1) // 8])}. "
                if p % 8 else "")
        what = {"network": ("network address", d["network_address"]),
                "broadcast": ("broadcast address", d["broadcast"]),
                "first": ("first usable host address", d["first"]),
                "last": ("last usable host address", d["last"]),
                "next": ("network address of the NEXT subnet", d["next_network"])}[kind]
        return Question(f"What is the {what[0]} for {ip}/{p}?", "text", str(what[1]),
                        f"{hint}{ip}/{p} lives in {d['network']} (mask {d['mask']}). Network {d['network_address']}, "
                        f"first {d['first']}, last {d['last']}, broadcast {d['broadcast']}.",
                        tag, placeholder="x.x.x.x")
    if kind == "borrow":
        n = rng.randint(1, 6)
        return Question(f"You borrow {n} host bit{'s' if n > 1 else ''} to create subnets. How many subnets result?", "text",
                        str(2 ** n), f"Each borrowed bit doubles the number of subnets: 2^{n} = {2 ** n}.", tag, placeholder="number")
    if kind == "fit":
        h = rng.choice([2, 5, 6, 10, 12, 25, 30, 50, 60, 100, 120, 200, 500])
        p = sn.prefix_for_hosts(h)
        total, usable = sn.host_counts(p)
        return Question(f"What is the longest prefix (smallest subnet) that still fits {h} usable hosts?", "text", str(p),
                        f"{h} hosts + network + broadcast = {h + 2} addresses, so you need 2^{32 - p} = {total} ({usable} usable) -> /{p}.",
                        tag, placeholder="e.g. /26")
    # same subnet
    p = rng.randint(24, 28)
    base = ipaddress.IPv4Address(_rand_ip(rng))
    a = sn.describe_ipv4(base, p)
    size = 1 << (32 - p)
    same = rng.random() < 0.5
    off = rng.randint(1, size - 2)
    b_int = int(a["network_address"]) + (off if same else size + off)
    b = ipaddress.IPv4Address(min(b_int, sn.M32))
    b_net = sn.describe_ipv4(b, p)["network"]
    truth = "Yes" if b_net == a["network"] else "No"
    return Question(f"With mask /{p}, are {base} and {b} in the same subnet?", "mc", truth,
                    f"{base} is in {a['network']}; {b} is in {b_net}. Same network = direct delivery, different = needs a router.",
                    tag, choices=["Yes", "No"])


# --------------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------------
def port_question(rng: random.Random) -> Question:
    entry = rng.choice(PORTS)
    port, transport, service, desc, _sec, _note = entry
    form = rng.choice(["port", "service", "transport"])
    tag = "Ports"
    if form == "port":
        return Question(f"Which default port number does {service} use? ({transport})", "text", str(port),
                        f"{service}: {transport} {port}. {desc}.", tag, placeholder="port number")
    if form == "service":
        others = [e[2] for e in PORTS if e[2] != service]
        choices = rng.sample(others, 3) + [service]
        rng.shuffle(choices)
        return Question(f"Which service uses {transport} port {port}?", "mc", service,
                        f"{service} ({transport} {port}): {desc}.", tag, choices=choices)
    pool = [e for e in PORTS if e[0] != 443]
    port, transport, service, desc, _sec, _note = rng.choice(pool)
    ans = {"TCP": "TCP", "UDP": "UDP", "TCP/UDP": "Both TCP and UDP"}[transport]
    return Question(f"Which transport protocol does {service} (port {port}) use?", "mc", ans,
                    f"{service} uses {transport}. {desc}.", tag, choices=["TCP", "UDP", "Both TCP and UDP"])


# --------------------------------------------------------------------------
# OSI
# --------------------------------------------------------------------------
_OSI_ITEMS = [
    ("HTTP", 7), ("DNS", 7), ("SMTP", 7), ("SNMP", 7), ("Data encryption, compression and encoding", 6),
    ("Session setup, maintenance and teardown between applications", 5),
    ("TCP", 4), ("UDP", 4), ("Port numbers", 4), ("Flow control and retransmission (TCP)", 4),
    ("IP addressing", 3), ("ICMP", 3), ("OSPF routing", 3), ("A router", 3),
    ("MAC addressing", 2), ("A switch", 2), ("Frame check sequence (FCS)", 2), ("VLAN tagging (802.1Q)", 2),
    ("A hub", 1), ("Cat 6 cabling", 1), ("Fiber optic cable", 1), ("A repeater", 1),
]
_LAYER = {o["n"]: o for o in OSI}


def _layer_label(n: int) -> str:
    return f"Layer {n} - {_LAYER[n]['name']}"


def osi_question(rng: random.Random) -> Question:
    form = rng.choice(["item", "pdu", "pdu_rev"])
    tag = "OSI"
    if form == "item":
        item, n = rng.choice(_OSI_ITEMS)
        choices = [_layer_label(n)] + [_layer_label(x) for x in rng.sample([k for k in _LAYER if k != n], 3)]
        rng.shuffle(choices)
        return Question(f"At which OSI layer does this operate: {item}?", "mc", _layer_label(n),
                        f"{item} belongs to Layer {n} ({_LAYER[n]['name']}). {_LAYER[n]['function']}", tag, choices=choices)
    if form == "pdu":
        n = rng.choice(list(_LAYER))
        pdu = _LAYER[n]["pdu"]
        options = list({o["pdu"] for o in OSI})
        choices = [pdu] + rng.sample([o for o in options if o != pdu], min(3, len(options) - 1))
        rng.shuffle(choices)
        return Question(f"What is the PDU at Layer {n} ({_LAYER[n]['name']})?", "mc", pdu,
                        f"Layer {n} ({_LAYER[n]['name']}) data unit: {pdu}.", tag, choices=choices)
    n = rng.choice([1, 2, 3, 4])
    pdu = _LAYER[n]["pdu"].split(" (")[0].split(" /")[0]
    choices = [_layer_label(n)] + [_layer_label(x) for x in rng.sample([k for k in _LAYER if k != n], 3)]
    rng.shuffle(choices)
    return Question(f"Which layer's PDU is called a {pdu}?", "mc", _layer_label(n),
                    f"{pdu} is the Layer {n} ({_LAYER[n]['name']}) data unit.", tag, choices=choices)


# --------------------------------------------------------------------------
# Concepts
# --------------------------------------------------------------------------
def concept_question(rng: random.Random) -> Question:
    prompt, correct, wrong, expl, domain = rng.choice(QUIZ)
    choices = [correct] + list(wrong)
    rng.shuffle(choices)
    return Question(prompt, "mc", correct, expl, domain, choices=choices)


MODES = {
    "mixed": None,
    "subnet": subnet_question,
    "ports": port_question,
    "osi": osi_question,
    "concepts": concept_question,
}


def make_question(mode: str, rng: random.Random | None = None) -> Question:
    rng = rng or random.Random()
    if mode == "mixed":
        fn = rng.choice([subnet_question, port_question, osi_question, concept_question, concept_question])
    else:
        fn = MODES[mode]
    return fn(rng)
