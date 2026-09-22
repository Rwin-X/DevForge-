# SysPulse

Real-time system telemetry monitor with a phosphor-green CRT terminal
aesthetic. Built with PyQt6 + pyqtgraph.

## Panels

- **CPU LOAD** — total load, live strip-chart, current frequency, per-core bars
- **MEMORY** — RAM usage + history graph, used/available, swap
- **NETWORK** — live up/down throughput, dual-line strip-chart, session totals
- **DISK** — per-partition usage bars (auto-detected)
- **THERMAL** — sensor temperatures where the OS exposes them
- **TOP PROCESSES** — uptime, process count, top 6 by CPU usage

All metrics update once per second on a background thread, so the UI never
blocks even under heavy load.

## Install & run

```bash
pip install -r requirements.txt
python syspulse.py
```

Requires Python 3.10+. Tested on Linux; should run on Windows/macOS as-is
(temperature sensors are OS-dependent — some platforms won't expose any,
in which case the THERMAL panel just shows "NO SENSOR DATA").

## Notes

- Colors shift green → amber → red per-metric as load crosses 70% / 90%.
- Font: JetBrains Mono if installed, otherwise falls back to the best
  available monospace font on the system.
- Sampling interval is 1000ms; change `interval_ms` in `SystemSampler.__init__`
  if you want it faster/slower.

  created by Rwin-X
