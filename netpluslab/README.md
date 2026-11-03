# NET+ LAB

A Network+ study and troubleshooting toolkit with a minimal, monochrome GUI.
Pure Python, **standard library only** (Tkinter). No `pip install` needed.

```
python netplus_lab.py
```

Requires Python 3.10+ with Tkinter.
Linux: `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora).
Windows and macOS: the python.org installer already includes it.

## Modules

| # | Module | What it does |
|---|--------|--------------|
| 02 | **Transport** | TCP vs UDP comparison, clickable bit-accurate header diagrams (TCP, UDP, IPv4, ICMP), flags, options, the 11 TCP states |
| 03 | **Simulator** | Step-through packet ladder for 9 scenarios: full session, 3-way handshake, data transfer, teardown, packet loss and retransmit, zero-window flow control, closed port (RST), UDP exchange, UDP loss. Editable IPs, ports, ISNs, payload sizes. Relative or absolute sequence numbers. Each packet explains why it exists. |
| 04 | **Subnetting** | Calculator with live binary view and prefix slider; VLSM allocator; split by subnets or hosts; route summarization; "same subnet?" and gateway check; CIDR table |
| 05 | **Converters** | IPv6 (compress, expand, type, solicited-node), EUI-64, number bases, IPv4 forms, MAC formats, transfer time, TCP window / bandwidth-delay product |
| 06 | **Ports** | 53 well-known ports with secure alternatives and exam notes, searchable; IP protocol numbers |
| 07 | **OSI & Encapsulation** | The seven layers, plus a builder that wraps your payload layer by layer with real header sizes, 64-byte minimum frame padding, 802.1Q, MTU, TCP segmentation and IP fragmentation |
| 08 | **Reference** | Troubleshooting method, commands, cabling, Ethernet standards, T568A/B, connectors, Wi-Fi, Wi-Fi security, DNS records, special IPv4 ranges, routing and administrative distance, protocol flows, threats and mitigations |
| 09 | **Live tools** | Hand-built DNS client (shows the query bytes, parses compression pointers), TCP port checker (open / closed / filtered), allow-listed system commands with streamed output, and a **local socket lab**: a real TCP + UDP echo server with adjustable UDP packet loss |
| 10 | **Drills** | Endless generated questions (subnetting, ports, OSI, concepts) with per-topic accuracy saved to `~/.netplus_lab.json` |

## Architecture

```
netplus_lab.py        launcher (checks Python and Tkinter)
netplus/
  data.py             static reference data, no logic
  subnet.py           addressing, VLSM, IPv6, converters      (pure logic)
  sim.py              TCP/UDP scenario engine + encapsulation  (pure logic)
  netio.py            DNS client, port check, commands, echo lab (sockets, no GUI)
  quiz.py             question generators                      (pure logic)
  ui.py               theme + widget kit (the design system)
  pages_a/b/c.py      the ten pages
  app.py              shell: sidebar, header, theme switch, background jobs
tests/test_core.py    43 headless tests for every logic module
```

The GUI never contains networking or maths: pages call the logic modules and render the result.
That is why the logic is testable without a display.

## Design

Follows the *minimal-webdesign* system: two colour roles (`bg`/`fg`) with muted, hairline and card
tones derived from them; no hue anywhere; one oversized display headline per page; small uppercase
eyebrow labels; 1 px hairline borders; a single strong rule under the header; data as decoration
(the overview backdrop is a lightweight animated network graph, ~30 fps, drawn only while visible).
Dark by default, light via the button in the sidebar (choice is remembered).

## Tests

```
python -m unittest discover -s tests -v
```

Covers subnet maths against Python's `ipaddress`, VLSM with no-overlap checks, IPv6/EUI-64,
sequence/ACK arithmetic including 32-bit wraparound in every scenario, DNS packet building and
parsing (compression pointers, loop rejection), a real DNS exchange against a local fake server,
a real TCP port scan of loopback, command-injection rejection, the echo lab over loopback
(including simulated UDP loss), and consistency of every generated quiz question.

## Notes and limits

* The simulator is a scripted, deterministic teaching model, not a packet capture. Real stacks add
  options, delayed ACK timing and congestion behaviour that vary by OS.
* Live tools send real traffic. The port checker only performs full TCP connects, limited to 1024
  ports per run. Use them on hosts and networks you own or are authorized to test.
* System commands run without a shell and the host argument is validated; only a fixed set of
  commands is offered, and availability depends on your OS.
* Study content follows the CompTIA Network+ domains in general terms. Always confirm details
  against the current official exam objectives.
* Changing the theme rebuilds the pages, so in-progress simulator state resets; the socket lab
  server keeps running.
