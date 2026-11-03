"""Headless tests for the pure-logic modules. Run:  python -m unittest discover -s tests -v"""

import ipaddress
import os
import random
import socket
import struct
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netplus import data, netio, quiz, sim, subnet as sn  # noqa: E402


class TestSubnet(unittest.TestCase):
    def test_parse_forms(self):
        for text in ("192.168.1.77/26", "192.168.1.77 /26", "192.168.1.77 255.255.255.192"):
            ip, p, given = sn.parse_ip_and_prefix(text)
            self.assertEqual((str(ip), p, given), ("192.168.1.77", 26, True))
        ip, p, given = sn.parse_ip_and_prefix("10.1.2.3")
        self.assertEqual((p, given), (8, False))
        ip, p, _ = sn.parse_ip_and_prefix("172.20.1.1")
        self.assertEqual(p, 16)

    def test_bad_input(self):
        for bad in ("", "300.1.1.1/24", "10.0.0.1/33", "10.0.0.1 255.0.255.0", "hello"):
            with self.assertRaises(sn.NetError, msg=bad):
                sn.parse_ip_and_prefix(bad)

    def test_describe_c26(self):
        ip, p, _ = sn.parse_ip_and_prefix("192.168.1.77/26")
        d = sn.describe_ipv4(ip, p)
        self.assertEqual(str(d["network_address"]), "192.168.1.64")
        self.assertEqual(str(d["broadcast"]), "192.168.1.127")
        self.assertEqual(str(d["first"]), "192.168.1.65")
        self.assertEqual(str(d["last"]), "192.168.1.126")
        self.assertEqual(d["usable"], 62)
        self.assertEqual(d["mask"], "255.255.255.192")
        self.assertEqual(d["wildcard"], "0.0.0.63")
        self.assertEqual(str(d["next_network"]), "192.168.1.128")
        self.assertEqual(d["type"], "Private (RFC 1918)")
        self.assertEqual(d["class"], "C")

    def test_edge_prefixes(self):
        d = sn.describe_ipv4(ipaddress.IPv4Address("10.0.0.5"), 32)
        self.assertEqual((d["usable"], str(d["first"]), str(d["last"])), (1, "10.0.0.5", "10.0.0.5"))
        d = sn.describe_ipv4(ipaddress.IPv4Address("10.0.0.5"), 31)
        self.assertEqual((d["usable"], str(d["first"]), str(d["last"])), (2, "10.0.0.4", "10.0.0.5"))
        d = sn.describe_ipv4(ipaddress.IPv4Address("10.0.0.5"), 30)
        self.assertEqual((d["usable"], str(d["first"]), str(d["last"])), (2, "10.0.0.5", "10.0.0.6"))
        d = sn.describe_ipv4(ipaddress.IPv4Address("1.2.3.4"), 0)
        self.assertEqual(str(d["network_address"]), "0.0.0.0")
        self.assertEqual(d["mask"], "0.0.0.0")
        self.assertEqual(d["total"], 2 ** 32)
        d = sn.describe_ipv4(ipaddress.IPv4Address("255.255.255.255"), 32)
        self.assertIsNone(d["next_network"])

    def test_masks(self):
        for p in range(0, 33):
            self.assertEqual(sn.mask_to_prefix(sn.prefix_to_mask(p)), p)
        self.assertEqual(sn.prefix_to_mask(27), "255.255.255.224")
        self.assertEqual(sn.prefix_to_mask(19), "255.255.224.0")

    def test_classify(self):
        cases = {"10.1.1.1": ("A", "Private (RFC 1918)"), "172.16.5.5": ("B", "Private (RFC 1918)"),
                 "172.32.0.1": ("B", "Public (globally routable)"), "169.254.3.3": ("B", "Link-local (APIPA)"),
                 "127.0.0.1": ("Loopback block", "Loopback"), "224.0.0.5": ("D (multicast)", "Multicast"),
                 "8.8.8.8": ("A", "Public (globally routable)"), "100.64.0.1": ("A", "Carrier-grade NAT (RFC 6598)"),
                 "255.255.255.255": ("E (reserved)", "Limited broadcast")}
        for ip, (cls, kind) in cases.items():
            self.assertEqual(sn.classify(ipaddress.IPv4Address(ip)), (cls, kind), ip)

    def test_vlsm_classic(self):
        r = sn.vlsm("192.168.1.0/24", [("HR", 25), ("Sales", 50), ("IT", 10), ("WAN", 2)])
        got = [(a["name"], str(a["network"])) for a in r["allocations"]]
        self.assertEqual(got, [("Sales", "192.168.1.0/26"), ("HR", "192.168.1.64/27"),
                               ("IT", "192.168.1.96/28"), ("WAN", "192.168.1.112/30")])
        self.assertEqual([str(f) for f in r["free"]], ["192.168.1.116/30", "192.168.1.120/29", "192.168.1.128/25"])
        self.assertEqual(r["used"], 64 + 32 + 16 + 4)
        # no overlaps
        nets = [a["network"] for a in r["allocations"]]
        for i, a in enumerate(nets):
            for b in nets[i + 1:]:
                self.assertFalse(a.overlaps(b))

    def test_vlsm_overflow(self):
        r = sn.vlsm("192.168.1.0/24", [("A", 100), ("B", 100)])      # two /25 fill a /24 exactly
        self.assertEqual((r["used"], r["free"]), (256, []))
        with self.assertRaises(sn.NetError):
            sn.vlsm("192.168.1.0/24", [("A", 100), ("B", 100), ("C", 10)])
        with self.assertRaises(sn.NetError):
            sn.vlsm("192.168.1.0/28", [("A", 100)])

    def test_prefix_for_hosts(self):
        cases = {1: 30, 2: 30, 3: 29, 6: 29, 7: 28, 14: 28, 30: 27, 62: 26, 126: 25, 254: 24, 255: 23}
        for h, p in cases.items():
            self.assertEqual(sn.prefix_for_hosts(h), p, h)

    def test_summarize(self):
        r = sn.summarize(["192.168.0.0/24", "192.168.1.0/24", "192.168.2.0/24", "192.168.3.0/24"])
        self.assertEqual(str(r["supernet"]), "192.168.0.0/22")
        self.assertTrue(r["exact"])
        r = sn.summarize(["192.168.0.0/24", "192.168.2.0/24"])
        self.assertEqual(str(r["supernet"]), "192.168.0.0/22")
        self.assertFalse(r["exact"])
        self.assertEqual(r["wasted"], 512)
        r = sn.summarize(["10.0.0.0/24"])
        self.assertEqual(str(r["supernet"]), "10.0.0.0/24")
        r = sn.summarize(["10.1.0.0/16", "172.16.0.0/16"])
        self.assertEqual(str(r["supernet"]), "0.0.0.0/0")

    def test_split(self):
        r = sn.split_network("192.168.10.0/24", "subnets", 5)
        self.assertEqual((r["new_prefix"], r["count"], r["usable"]), (27, 8, 30))
        self.assertEqual(str(r["rows"][1]["network"]), "192.168.10.32/27")
        r = sn.split_network("10.0.0.0/16", "hosts", 500)
        self.assertEqual(r["new_prefix"], 23)
        with self.assertRaises(sn.NetError):
            sn.split_network("192.168.10.0/30", "subnets", 8)
        with self.assertRaises(sn.NetError):
            sn.split_network("192.168.10.0/24", "hosts", 1000)

    def test_compare(self):
        r = sn.compare_hosts("192.168.1.10", "192.168.1.200", "255.255.255.0", "192.168.1.1")
        self.assertTrue(r["same"])
        self.assertEqual(r["problems"], [])
        r = sn.compare_hosts("192.168.1.10", "192.168.1.200", "/25", "192.168.1.1")
        self.assertFalse(r["same"])
        r = sn.compare_hosts("192.168.1.10", "192.168.1.11", "24", "192.168.2.1")
        self.assertTrue(any("Gateway" in p for p in r["problems"]))
        r = sn.compare_hosts("192.168.1.0", "192.168.1.255", "24")
        self.assertEqual(len(r["problems"]), 2)

    def test_cidr_table(self):
        rows = {r[0]: r for r in sn.cidr_table()}
        self.assertEqual(rows["/24"][4], 254)
        self.assertEqual(rows["/26"][5], "octet 4, block 64")
        self.assertEqual(rows["/16"][5], "whole octets")

    def test_ipv6(self):
        d = sn.describe_ipv6("2001:0db8:0000:0000:0000:ff00:0042:8329/64")
        self.assertEqual(d["compressed"], "2001:db8::ff00:42:8329")
        self.assertTrue(d["type"].startswith("Documentation"))
        self.assertEqual(d["solicited_node"], "ff02::1:ff42:8329")
        self.assertEqual(d["slash64s"], 1)
        d = sn.describe_ipv6("fe80::1")
        self.assertTrue(d["type"].startswith("Link-local"))
        d = sn.describe_ipv6("ff02::1")
        self.assertEqual(d["scope"], "link-local")
        d = sn.describe_ipv6("2606:4700::1111/48")
        self.assertEqual(d["slash64s"], 65536)
        self.assertTrue(d["type"].startswith("Global unicast"))
        d = sn.describe_ipv6("::1")
        self.assertTrue(d["type"].startswith("Loopback"))
        with self.assertRaises(sn.NetError):
            sn.describe_ipv6("12345::1")

    def test_eui64(self):
        r = sn.eui64("00:1A:2B:3C:4D:5E", "fe80::/64")
        self.assertEqual(str(r["address"]), "fe80::21a:2bff:fe3c:4d5e")
        self.assertEqual(r["flipped_first"], "00 -> 02")
        r = sn.eui64("02-1A-2B-3C-4D-5E", "2001:db8:1:1::/64")
        self.assertEqual(str(r["address"]), "2001:db8:1:1:1a:2bff:fe3c:4d5e")
        with self.assertRaises(sn.NetError):
            sn.eui64("zz:zz", "fe80::/64")
        with self.assertRaises(sn.NetError):
            sn.eui64("00:1A:2B:3C:4D:5E", "2001:db8::/48")

    def test_converters(self):
        self.assertEqual(sn.parse_int("0xFF"), 255)
        self.assertEqual(sn.parse_int("0b1111_1111"), 255)
        self.assertEqual(sn.parse_int("0o377"), 255)
        f = sn.base_forms(255)
        self.assertEqual((f["bin"], f["hex"], f["oct"]), ("11111111", "0xFF", "0o377"))
        self.assertEqual(sn.base_forms(256)["bin"], "00000001 00000000")
        f = sn.ipv4_forms("192.168.0.1")
        self.assertEqual((f["hex"], f["integer"]), ("0xC0A80001", "3232235521"))
        self.assertEqual(sn.ipv4_forms("3232235521")["dotted"], "192.168.0.1")
        self.assertEqual(sn.ipv4_forms("0xC0A80001")["dotted"], "192.168.0.1")
        self.assertEqual(sn.ipv4_forms("11000000.10101000.00000000.00000001")["dotted"], "192.168.0.1")
        with self.assertRaises(sn.NetError):
            sn.ipv4_forms("4294967296")
        m = sn.mac_forms("00-1A-2B-3C-4D-5E")
        self.assertEqual(m["colon"], "00:1A:2B:3C:4D:5E")
        self.assertEqual(m["cisco"], "001a.2b3c.4d5e")
        self.assertEqual(m["oui"], "00:1A:2B")
        self.assertEqual(m["cast"], "Unicast")
        self.assertTrue(sn.mac_forms("ff:ff:ff:ff:ff:ff")["broadcast"])
        self.assertTrue(sn.mac_forms("01:00:5e:00:00:05")["cast"].startswith("Multicast"))

    def test_transfer(self):
        r = sn.transfer_time(1, "GB", 1, "Gbps", 100)
        self.assertAlmostEqual(r["ideal"], 8.0)
        r = sn.transfer_time(100, "MB", 100, "Mbps", 80)
        self.assertAlmostEqual(r["ideal"], 8.0)
        self.assertAlmostEqual(r["real"], 10.0)
        with self.assertRaises(sn.NetError):
            sn.transfer_time(0, "MB", 100, "Mbps")

    def test_tcp_window(self):
        r = sn.tcp_window_math(1000, 50, 65535)
        self.assertAlmostEqual(r["bdp_bytes"], 6_250_000)
        self.assertAlmostEqual(r["window_cap_mbps"], 65535 * 8 / 0.05 / 1e6)
        self.assertTrue(r["limited"] and r["needs_scaling"])


class TestSim(unittest.TestCase):
    def setUp(self):
        self.cfg = sim.SimConfig(c_isn=1000, s_isn=5000, c_len=300, s_len=1200)

    def test_handshake_numbers(self):
        s = sim.build_handshake(self.cfg)
        self.assertEqual([x.flags for x in s], ["SYN", "SYN,ACK", "ACK"])
        self.assertEqual((s[0].seq, s[0].ack), (1000, None))
        self.assertEqual((s[1].seq, s[1].ack), (5000, 1001))
        self.assertEqual((s[2].seq, s[2].ack), (1001, 5001))
        self.assertEqual((s[1].seq_r, s[1].ack_r), (0, 1))
        self.assertEqual((s[2].seq_r, s[2].ack_r), (1, 1))
        self.assertEqual([(x.cstate, x.sstate) for x in s],
                         [("SYN_SENT", "LISTEN"), ("SYN_SENT", "SYN_RCVD"), ("ESTABLISHED", "ESTABLISHED")])
        self.assertEqual(s[0].dport, 443)
        self.assertEqual(s[1].sport, 443)

    def test_data_acks_cover_bytes(self):
        s = sim.build_data(self.cfg)
        pk = [x for x in s if x.kind == "pkt"]
        self.assertEqual((pk[0].seq, pk[0].length), (1001, 300))
        self.assertEqual(pk[1].ack, 1301)           # server ACKs request
        self.assertEqual((pk[2].seq, pk[2].length), (5001, 1200))
        self.assertEqual(pk[3].ack, 6201)

    def test_segmentation(self):
        cfg = sim.SimConfig(s_len=4000)
        s = [x for x in sim.build_data(cfg) if x.kind == "pkt" and x.direction == "s2c" and x.length]
        self.assertEqual([x.length for x in s], [1460, 1460, 1080])
        self.assertEqual(s[1].seq, s[0].seq + 1460)

    def test_teardown_states(self):
        s = sim.build_teardown(self.cfg)
        self.assertEqual(s[-1].cstate, "CLOSED")
        states = [(x.cstate, x.sstate) for x in s if x.kind == "pkt"]
        self.assertEqual(states, [("FIN_WAIT_1", "ESTABLISHED"), ("FIN_WAIT_2", "CLOSE_WAIT"),
                                  ("FIN_WAIT_2", "LAST_ACK"), ("TIME_WAIT", "CLOSED")])
        pk = [x for x in s if x.kind == "pkt"]
        self.assertEqual(pk[1].ack, pk[0].seq + 1)       # FIN consumes one sequence number
        self.assertEqual(pk[3].ack, pk[2].seq + 1)

    def test_loss_retransmit_same_seq(self):
        s = sim.build_loss(self.cfg)
        lost = [x for x in s if x.kind == "lost"][0]
        re = [x for x in s if x.retrans][0]
        self.assertEqual(lost.seq, re.seq)
        self.assertEqual(s[-1].ack, re.seq + re.length)

    def test_refused(self):
        s = sim.build_refused(self.cfg)
        self.assertEqual(s[1].flags, "RST,ACK")
        self.assertEqual((s[1].seq, s[1].seq_r, s[1].ack_r), (0, 0, 1))
        self.assertEqual(s[1].cstate, "CLOSED")

    def test_window(self):
        s = [x for x in sim.build_window(self.cfg) if x.kind == "pkt"]
        self.assertEqual(s[2].win, 0)
        self.assertEqual(s[3].win, 2000)

    def test_full_and_wrap(self):
        s = sim.build_full(self.cfg)
        self.assertEqual(s[0].cstate, "SYN_SENT")
        self.assertEqual(s[-1].cstate, "CLOSED")
        cfg = sim.SimConfig(c_isn=0xFFFFFFFF, s_isn=0xFFFFFFF0)
        for x in sim.build_full(cfg):
            for v in (x.seq, x.ack, x.seq_r, x.ack_r):
                if v is not None:
                    self.assertTrue(0 <= v <= 0xFFFFFFFF)
        h = sim.build_handshake(cfg)
        self.assertEqual(h[1].ack, 0)                     # wrapped
        self.assertEqual(h[1].ack_r, 1)

    def test_udp(self):
        s = sim.build_udp(self.cfg)
        pk = [x for x in s if x.kind == "pkt"]
        self.assertTrue(all(x.proto == "UDP" and x.seq is None for x in pk))
        self.assertEqual(pk[0].dport, 53)
        self.assertEqual(pk[0].udp_len, 8 + 300)
        s = sim.build_udp_loss(self.cfg)
        self.assertEqual([x.kind for x in s], ["lost", "note", "pkt", "pkt"])

    def test_all_scenarios_build(self):
        for key, _n, proto, _f, _d in sim.SCENARIOS:
            steps = sim.build_scenario(key, self.cfg)
            self.assertTrue(steps)
            for st in steps:
                self.assertTrue(st.label())
                if st.kind != "note":
                    self.assertIn(st.proto, ("TCP", "UDP"))

    def test_encapsulation_sizes(self):
        r = sim.encapsulate("hello", "TCP", "1.1.1.1", "2.2.2.2", 49000, 80, "aa:bb:cc:00:00:01", "aa:bb:cc:00:00:02")
        sizes = {l["layer"]: l["size"] for l in r["layers"]}
        self.assertEqual(sizes[7], 5)
        self.assertEqual(sizes[4], 25)
        self.assertEqual(sizes[3], 45)
        self.assertEqual(sizes[2], 64)              # 14 + 45 + pad 1 + 4 = 64
        self.assertEqual(r["frames"], 1)
        self.assertTrue(any("padded" in n for n in r["notes"]))
        r = sim.encapsulate("x" * 3000, "TCP", "1.1.1.1", "2.2.2.2", 1, 2, "a", "b")
        self.assertEqual(r["frames"], 3)
        r = sim.encapsulate("x" * 3000, "UDP", "1.1.1.1", "2.2.2.2", 1, 2, "a", "b")
        self.assertEqual(r["frames"], 3)           # (3008 bytes) / 1480
        self.assertTrue(any("fragment" in n for n in r["notes"]))
        r = sim.encapsulate("hi", "UDP", "1.1.1.1", "2.2.2.2", 1, 2, "a", "b", vlan=10)
        self.assertEqual(r["layers"][3]["header"], 18)
        self.assertEqual(r["frame_sizes"][0], 64)


def build_fake_dns_response(qid, name, answers):
    """Craft a compressed DNS response: answers = list of (type, rdata bytes)."""
    qname = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    msg = struct.pack("!HHHHHH", qid, 0x8180, 1, len(answers), 0, 0) + qname + struct.pack("!HH", 1, 1)
    for rtype, rdata in answers:
        msg += b"\xc0\x0c" + struct.pack("!HHIH", rtype, 1, 300, len(rdata)) + rdata
    return msg


class TestNetio(unittest.TestCase):
    def test_query_packet(self):
        q = netio.build_dns_query("www.example.com", "A", qid=0x1234)
        self.assertEqual(q[:2], b"\x12\x34")
        self.assertEqual(q[12:], b"\x03www\x07example\x03com\x00\x00\x01\x00\x01")
        with self.assertRaises(sn.NetError):
            netio.build_dns_query("a" * 70 + ".com")
        with self.assertRaises(sn.NetError):
            netio.build_dns_query("example.com", "BOGUS")

    def test_parse_response(self):
        resp = build_fake_dns_response(7, "example.com", [
            (1, bytes([93, 184, 216, 34])),
            (28, ipaddress.IPv6Address("2606:2800:220:1::1").packed),
            (15, struct.pack("!H", 10) + b"\x04mail\xc0\x0c"),
            (16, b"\x0bv=spf1 -all"),
            (5, b"\x03www\xc0\x0c"),
        ])
        r = netio.parse_dns_response(resp)
        self.assertEqual((r["id"], r["rcode"], r["qr"], r["rd"], r["ra"]), (7, "NOERROR", True, True, True))
        vals = {a[1]: a[3] for a in r["answers"]}
        self.assertEqual(vals["A"], "93.184.216.34")
        self.assertEqual(vals["AAAA"], "2606:2800:220:1::1")
        self.assertEqual(vals["MX"], "10 mail.example.com")
        self.assertEqual(vals["TXT"], '"v=spf1 -all"')
        self.assertEqual(vals["CNAME"], "www.example.com")
        self.assertEqual(r["answers"][0][2], 300)

    def test_pointer_loop_rejected(self):
        bad = struct.pack("!HHHHHH", 1, 0x8180, 1, 0, 0, 0) + b"\xc0\x0c" + struct.pack("!HH", 1, 1)
        with self.assertRaises(sn.NetError):
            netio.parse_dns_response(bad)
        with self.assertRaises(sn.NetError):
            netio.parse_dns_response(b"\x00\x01")

    def test_dns_over_loopback_udp(self):
        """Run a tiny fake DNS server on loopback and query it for real."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.settimeout(3)

        def serve():
            data, addr = srv.recvfrom(512)
            qid = struct.unpack("!H", data[:2])[0]
            srv.sendto(build_fake_dns_response(qid, "example.test", [(1, bytes([10, 0, 0, 9]))]), addr)

        threading.Thread(target=serve, daemon=True).start()
        # dns_query always uses port 53, so patch getaddrinfo's port by using the helper directly:
        orig = socket.getaddrinfo

        def fake(host, p, *a, **k):
            return orig(host, port, *a, **k)

        socket.getaddrinfo = fake
        try:
            r = netio.dns_query("example.test", "A", server="127.0.0.1", timeout=2)
        finally:
            socket.getaddrinfo = orig
            srv.close()
        self.assertEqual(r["answers"][0][3], "10.0.0.9")
        self.assertEqual(r["transport"], "UDP")

    def test_reverse(self):
        self.assertEqual(netio.reverse_name("192.0.2.5"), "5.2.0.192.in-addr.arpa")
        with self.assertRaises(sn.NetError):
            netio.reverse_name("nope")

    def test_parse_ports(self):
        self.assertEqual(netio.parse_ports("22, 80,443 8000-8002"), [22, 80, 443, 8000, 8001, 8002])
        self.assertEqual(netio.parse_ports("10-8"), [8, 9, 10])
        for bad in ("", "0", "70000", "abc", "1-5000"):
            with self.assertRaises(sn.NetError, msg=bad):
                netio.parse_ports(bad)

    def test_port_scan_loopback(self):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(4)
        open_port = srv.getsockname()[1]
        tmp = socket.socket()
        tmp.bind(("127.0.0.1", 0))
        closed_port = tmp.getsockname()[1]
        tmp.close()
        try:
            r = netio.scan_ports("127.0.0.1", sorted({open_port, closed_port}), timeout=1.0, workers=4)
        finally:
            srv.close()
        self.assertEqual(r["results"][open_port][0], "open")
        self.assertEqual(r["results"][closed_port][0], "closed")
        with self.assertRaises(sn.NetError):
            netio.scan_ports("no-such-host.invalid", [80])

    def test_command_validation(self):
        for bad in ("", "-c 1 x", "a b", "x;rm -rf /", "$(id)", "a|b", "--help"):
            with self.assertRaises(sn.NetError, msg=bad):
                netio.build_command("ping", bad)
        with self.assertRaises(sn.NetError):
            netio.build_command("rm")

    def test_run_command(self):
        lines = []
        rc = netio.run_command([sys.executable, "-c", "print('a'); print('b')"], lines.append)
        self.assertEqual((rc, lines), (0, ["a", "b"]))
        stop = threading.Event()
        lines = []
        t0 = time.time()
        threading.Timer(0.5, stop.set).start()
        netio.run_command([sys.executable, "-c", "import time; time.sleep(30)"], lines.append, stop)
        self.assertLess(time.time() - t0, 10)

    def test_echo_lab(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        lab = netio.EchoLab(port=port, udp_loss=0.0)
        lab.start()
        try:
            out = netio.tcp_client("127.0.0.1", port, "hello", 2)
            self.assertTrue(any("ECHO: hello" in t for _w, t in out), out)
            out = netio.udp_client("127.0.0.1", port, "ping", 1, 1)
            self.assertTrue(any("ECHO: ping" in t for _w, t in out), out)
            lab.udp_loss = 1.0
            out = netio.udp_client("127.0.0.1", port, "ping", 0.3, 2)
            self.assertEqual(sum("no reply" in t for _w, t in out), 2)
        finally:
            lab.stop()
        out = netio.tcp_client("127.0.0.1", port, "x", 1)
        self.assertTrue(any("refused" in t for _w, t in out), out)
        with self.assertRaises(sn.NetError):
            a = netio.EchoLab(port=port)
            b = netio.EchoLab(port=port)
            a.start()
            try:
                b.start()
            finally:
                a.stop()


class TestQuiz(unittest.TestCase):
    def test_generators_are_self_consistent(self):
        rng = random.Random(1234)
        for mode in ("subnet", "ports", "osi", "concepts", "mixed"):
            for _ in range(400):
                q = quiz.make_question(mode, rng)
                self.assertTrue(quiz.check(q, q.answer), q.prompt)
                self.assertFalse(quiz.check(q, "definitely-wrong-xyz"))
                if q.kind == "mc":
                    self.assertIn(q.answer, q.choices)
                    self.assertEqual(len(set(q.choices)), len(q.choices), q.prompt)
                    self.assertGreaterEqual(len(q.choices), 2)

    def test_subnet_answers_match_ipaddress(self):
        rng = random.Random(5)
        seen = set()
        for _ in range(600):
            q = quiz.subnet_question(rng)
            seen.add(q.prompt.split(" for ")[0][:28])
            if q.prompt.startswith("What is the network address for"):
                ip, p = q.prompt.split(" for ")[1].rstrip("?").split("/")
                self.assertEqual(q.answer, str(ipaddress.IPv4Network(f"{ip}/{p}", strict=False).network_address))
            if "NEXT subnet" in q.prompt:
                ip, p = q.prompt.split(" for ")[1].rstrip("?").split("/")
                net = ipaddress.IPv4Network(f"{ip}/{p}", strict=False)
                self.assertEqual(q.answer, str(net.network_address + net.num_addresses))
            if q.prompt.startswith("What is the broadcast"):
                ip, p = q.prompt.split(" for ")[1].rstrip("?").split("/")
                self.assertEqual(q.answer, str(ipaddress.IPv4Network(f"{ip}/{p}", strict=False).broadcast_address))
        self.assertGreater(len(seen), 5)

    def test_normalize(self):
        q = quiz.Question("x", "text", "26", "", "t")
        self.assertTrue(quiz.check(q, " /26 "))
        self.assertTrue(quiz.check(q, "26"))
        self.assertFalse(quiz.check(q, "27"))

    def test_data_integrity(self):
        ports = [(p[0], p[1]) for p in data.PORTS]
        self.assertEqual(len(ports), len(set(ports)))
        for p in data.PORTS:
            self.assertTrue(1 <= p[0] <= 65535)
            self.assertIn(p[1], ("TCP", "UDP", "TCP/UDP"))
        for name, h in data.HEADERS.items():
            for i, row in enumerate(h["rows"]):
                self.assertEqual(sum(f[1] for f in row), 32, f"{name} row {i}")
        for q in data.QUIZ:
            self.assertEqual(len(q[2]), 3)
            self.assertNotIn(q[1], q[2])
            self.assertEqual(len({q[1], *q[2]}), 4, q[0])
        for key, label, cols, rows, note in data.REFERENCE:
            for r in rows:
                self.assertEqual(len(r), len(cols), f"{key}: {r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
