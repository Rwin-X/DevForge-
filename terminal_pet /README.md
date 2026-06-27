<div align="center">

# 🐾 terminal-pet

**A living ASCII creature in your terminal — physics-driven, mood-aware, always watching.**

![Python](https://img.shields.io/badge/python-3.8+-39FF14?style=flat-square&logo=python&logoColor=black)
![stdlib](https://img.shields.io/badge/dependencies-stdlib%20only-00FFFF?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-black?style=flat-square)

</div>

---

## what it is

A real-time terminal pet that **chases a cursor you control**, using spring-damper
physics for smooth inertia — no teleporting, no snapping. It gets bored if you
ignore it, wanders on its own, and reacts through a small emotion system.

Pure Python stdlib (`curses`). Zero dependencies. 30 FPS, double-buffered, flicker-free.

## features

- 🐱 **3 pets** — cat / ghost / drone, each with its own physics signature
- 🧲 **Inertial following** — velocity + drag, not direct lerp
- 🤖 **Idle AI** — wanders on its own after 5s of inactivity
- 😴 **Emotion states** — idle / happy / sleepy / excited
- ⌨️ **In-app command line** — `:` opens a tiny shell

## controls

| Key             | Action               |
|-----------------|----------------------|
| `↑↓←→` / `wasd` | move target          |
| `f`             | feed (happy)         |
| `1` `2` `3`     | cat / ghost / drone  |
| `:`             | command mode         |
| `q`             | quit                 |

**commands:** `follow` · `idle` · `sleep` · `feed` · `switch <pet>`

## run

```bash
python3 terminal_pet.py
```

> Windows: `pip install windows-curses`

## how it moves

```
accel = direction * follow_strength * min(distance, 10)
vel  += accel * dt
vel  *= (1 - drag * dt)      # damping
pos  += vel * dt
```

Each pet tunes `follow_strength`, `max_speed`, and `drag` differently —
the drone snaps fast and tight, the ghost drifts and lags behind.

---

<div align="center">
<sub>part of <a href="#">devforge</a> — vibe-coded, terminal-native</sub>
</div>
