"""Visual scenes: pure geometry (numpy), no GUI. Renderers draw what build() returns.

build(player, now, dt, vp) -> (segs, pts, strips)
  segs   [(A, B, Z, alpha)]  line segments; alpha None means depth-shaded
  pts    [(P, S, Z)]         squares of size S at screen points P (Z may be None)
  strips [(P, alpha, fill)]  polylines drawn in order; fill=True occludes what is behind
vp = (cx, cy, zoom, mouse_x, mouse_y)
"""
import math

import numpy as np

from core.audio import COLS
from core.geometry import project, rotate

BUCKET_ALPHA = (0.08, 0.22, 0.5)
THRESH = 105.0
TAU = 2 * math.pi


def split_segments(A, B, Z, alpha):
    """Yield (alpha, A, B) groups; depth-shades the segments when alpha is None."""
    if alpha is not None:
        yield alpha, A, B
        return
    bucket = np.where(Z < -THRESH, 2, np.where(Z < THRESH, 1, 0))
    for k, a in enumerate(BUCKET_ALPHA):
        sel = bucket == k
        if sel.any():
            yield a, A[sel], B[sel]


def point_alpha(Z, n):
    return np.where(Z < 0, 0.9, 0.4) if Z is not None else np.full(n, 0.85)


def link(scr, z, ia, ib, alpha=None):
    return scr[ia].reshape(-1, 2), scr[ib].reshape(-1, 2), ((z[ia] + z[ib]) / 2).ravel(), alpha


def col_index(f):
    """Map fractions 0..1 to spectrum column indices."""
    return np.round(np.asarray(f) * (COLS - 1)).astype(int)


class Scene:
    name, pitch, yaw0, drift = "scene", -0.3, 0.6, 1.0

    def __init__(self):
        self.yaw, self.cr = self.yaw0, 0.0
        self.rows, self.acc = None, 0.0

    def step(self, p, dt):
        k = dt * 30
        self.yaw += k * self.drift * (0.004 + p.energy * 0.015 + p.spin * 0.01)
        self.cr += k * (0.006 + p.energy * 0.03 + p.spin * 0.03)

    def view(self, pts, vp):
        cx, cy, zoom, mx, my = vp
        return project(rotate(pts, self.yaw + mx * 0.3, self.pitch + my * 0.2), cx, cy, zoom)

    def history(self, p, dt, n, ms):
        """Rolling buffer of spectrum snapshots; returns scroll progress 0..1."""
        if self.rows is None:
            self.rows = np.zeros((n, COLS))
        self.acc += dt * 1000
        if self.acc >= ms:
            self.acc -= ms
            self.rows = np.roll(self.rows, 1, 0)
            self.rows[0] = p.lv
        return self.acc / ms

    def shocks(self, p, now, vp, r0, grow, y=0.0, gain=0.35):
        ang, out = np.linspace(0, TAU, 49), []
        for w in p.waves:
            age = (now - w) / 1.5
            if age < 1:
                r = r0 + age * grow
                ring = np.stack([np.cos(ang) * r, np.full_like(ang, y), np.sin(ang) * r], -1)
                out.append((self.view(ring, vp)[0], (1 - age) * gain, False))
        return out


class Helix(Scene):
    name, pitch, N = "Helix", -0.12, 96

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        f = np.arange(self.N) / self.N
        L = p.lv[col_index(f)]
        r = 105 * (1 + p.bass * 0.25 + p.beat_pulse * 0.08) + L * 140
        y = (f - 0.5) * 660
        strands = [np.stack([np.cos(a) * r, y, np.sin(a) * r], -1)
                   for a in (f * 13 + s * math.pi + now * 0.5 + p.spin * 0.35 * (f - 0.5) * 6 for s in (0, 1))]
        scr, z = self.view(np.stack(strands), vp)
        rung = slice(0, self.N, 3)
        segs = [link(scr, z, (s, slice(0, -1)), (s, slice(1, None))) for s in (0, 1)]
        segs.append(link(scr, z, (0, rung), (1, rung), min(0.6, 0.12 + p.mid * 1.2 + p.beat_pulse * 0.25)))
        pts = [(scr[:, rung].reshape(-1, 2), np.tile(1.5 + L[rung] * 7, 2), z[:, rung].ravel())]
        return segs, pts, self.shocks(p, now, vp, 170, 0)


class Terrain(Scene):
    name, pitch, yaw0, drift, R = "Terrain", 0.5, 0.0, 0.0, 18

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        pr = self.history(p, dt, self.R, 70)
        k = np.arange(self.R)
        x = (np.arange(COLS) / (COLS - 1) - 0.5) * 780
        amp = 170 * (1 + np.where(k == 0, p.beat_pulse * 0.15, 0))
        pts = np.stack(np.broadcast_arrays(x[None, :], 60 - self.rows * amp[:, None], ((k + pr) * 42 - 250)[:, None]), -1)
        scr, _ = self.view(pts, vp)
        return [], [], [(scr[i], 0.9 - i * 0.045, True) for i in reversed(range(self.R))]


class Tunnel(Scene):
    name, pitch, yaw0, drift, NR, TRI = "Tunnel", 0.0, 0.0, 0.0, 24, 48

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        pr = self.history(p, dt, self.NR, 60)
        k = np.arange(self.NR)[:, None]
        m = np.arange(self.TRI + 1)[None, :]
        h = self.rows[:, col_index(m[0] / self.TRI)]
        base = 160 * (1 + p.bass * 0.12 * (1 - k / self.NR) + (k < 2) * p.beat_pulse * 0.08)
        rr = base + h * 110
        an = m / self.TRI * TAU + self.cr * 0.5 + k * 0.02
        z = np.broadcast_to((k + pr) * 60 - 150, rr.shape)
        scr, zz = self.view(np.stack([np.cos(an) * rr, np.sin(an) * rr, z], -1), vp)
        sp = slice(0, self.TRI, 6)
        segs = [link(scr, zz, (slice(0, self.NR - 1), sp), (slice(1, self.NR), sp), min(0.5, 0.1 + p.mid * 1.2))]
        strips = [(scr[i], min(0.9, 0.05 + 0.6 * (1 - i / self.NR) + (i == 0) * p.beat_pulse * 0.3), False) for i in range(self.NR)]
        return segs, [], strips


class Lattice(Scene):
    name, pitch, G = "Lattice", -0.4, 7

    def __init__(self):
        super().__init__()
        g = (np.arange(self.G) - 3) * 90.0
        self.base = np.stack(np.meshgrid(g, g, g, indexing="ij"), -1)
        self.d = np.linalg.norm(self.base, axis=-1)

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        d = self.d
        v = p.lv[col_index(0.5 * (1 - np.minimum(1, d / 470)))]
        g = 1 + v * 0.7 + p.bass * 0.14 + p.beat_pulse * 0.1 + p.hi * 0.1 * np.sin(d * 0.04 - now * 3)
        if p.waves:
            wa = (now - p.waves[-1]) / 1.5
            if wa < 1:
                dd = np.abs(d - wa * 480)
                g = g + np.where(dd < 70, 0.15 * (1 - dd / 70) * (1 - wa), 0)
        scr, z = self.view(self.base * g[..., None], vp)
        segs = []
        for ax in range(3):
            a, b = [slice(None)] * 3, [slice(None)] * 3
            a[ax], b[ax] = slice(0, -1), slice(1, None)
            segs.append(link(scr, z, tuple(a), tuple(b)))
        return segs, [(scr.reshape(-1, 2), 1 + v.ravel() * 6, None)], []


class Galaxy(Scene):
    name, pitch, yaw0, A, P = "Galaxy", 0.95, 0.0, 3, 150

    def __init__(self):
        super().__init__()
        rng = np.random.default_rng(3)
        self.j1, self.j2 = rng.uniform(-1, 1, (self.A, self.P)), rng.uniform(-1, 1, (self.A, self.P))

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        f = np.tile(np.arange(self.P) / self.P, (self.A, 1))
        arm = np.arange(self.A)[:, None]
        L = p.lv[col_index(0.5 * (1 - f))]
        rad = (34 + f * 340) * (1 + L * 0.32 + p.beat_pulse * 0.06 * (1 - f)) + self.j1 * (10 + f * 26)
        ang = arm * 2.0944 + f * 5 + self.cr * (1.3 - f) + self.j2 * 0.18
        y = self.j1 * (18 + p.hi * 80) * (1 - f * 0.5) + np.sin(ang * 2 + now) * L * 34
        scr, z = self.view(np.stack([np.cos(ang) * rad, y, np.sin(ang) * rad], -1), vp)
        segs = [link(scr, z, (slice(None), slice(0, -1)), (slice(None), slice(1, None)))]
        core = float(4 + p.bass * 16 + p.beat_pulse * 8)
        cs, _ = self.view(np.zeros((1, 3)), vp)
        return segs, [(scr.reshape(-1, 2), (1 + L * 5).ravel(), z.ravel()), (cs, np.array([core]), None)], self.shocks(p, now, vp, 46 + p.bass * 60, 0, gain=0.5)


class Ripple(Scene):
    name, pitch, G, H = "Ripple", 0.6, 21, 24

    def __init__(self):
        super().__init__()
        g = (np.arange(self.G) - 10) * 36.0
        self.X, self.Z = np.meshgrid(g, g, indexing="ij")
        self.d, self.ang = np.hypot(self.X, self.Z), np.abs(np.arctan2(self.Z, self.X))
        self.hist, self.hacc = np.zeros(self.H), 0.0

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        self.hacc += dt * 1000
        if self.hacc >= 60:
            self.hacc -= 60
            self.hist = np.roll(self.hist, 1)
            self.hist[0] = min(1.4, p.energy * 1.8 + p.beat_pulse * 0.5)
        d = self.d
        hv = np.interp(d, np.linspace(0, 480, self.H), self.hist)
        y = -(hv * 130 * np.cos(d * 0.05 - now * 2.5) * np.exp(-d / 420) + p.lv[col_index(self.ang / math.pi)] * 55 * np.maximum(0, 1 - d / 500))
        scr, z = self.view(np.stack([self.X, y, self.Z], -1), vp)
        s0, s1, n = slice(0, -1), slice(1, None), slice(None)
        segs = [link(scr, z, (s0, n), (s1, n)), link(scr, z, (n, s0), (n, s1))]
        hi = (-y) > 14
        return segs, [(scr[hi], 1 + np.minimum(4, -y[hi] / 18), None)], []


class Bars(Scene):
    name, pitch, BR, BN = "Bars", 0.55, 3, 64

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        self.history(p, dt, self.BR, 110)
        i = np.arange(self.BN)
        r = np.arange(self.BR)[:, None]
        a = i / self.BN * TAU + self.cr * np.where(r % 2, -1, 1) * 0.4
        rad = 180 + r * 100
        v = self.rows[:, col_index(i / self.BN)]
        h = 6 + v * 230 * (1 - r * 0.15) * (1 + p.beat_pulse * 0.08)
        base = np.stack([np.cos(a) * rad, np.full_like(a, 40.0), np.sin(a) * rad], -1)
        top = base.copy()
        top[..., 1] = 40 - h
        scr, z = self.view(np.stack([base, top]), vp)
        ang = np.linspace(0, TAU, 73)
        rings = np.stack([np.stack([np.cos(ang) * (180 + 100 * k), np.full_like(ang, 40.0), np.sin(ang) * (180 + 100 * k)], -1) for k in range(self.BR)])
        rs, _ = self.view(rings, vp)
        strips = [(rs[k], 0.12, False) for k in range(self.BR)] + self.shocks(p, now, vp, 160, 420, y=40.0)
        strips += [(np.concatenate([scr[1, k], scr[1, k, :1]]), 0.35 - 0.08 * k, False) for k in range(self.BR)]
        segs = [link(scr, z, (0,), (1,), 0.6)]
        return segs, [(scr[1][:, ::2].reshape(-1, 2), (2 + v[:, ::2] * 4).ravel(), None)], strips


class Strings(Scene):
    name, pitch, N = "Strings", 0.45, 24

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        s = np.arange(self.N)
        L = p.lv[col_index(s / (self.N - 1))]
        f = np.linspace(0, 1, 49)[None, :]
        amp = (L * 170 * (1 + p.beat_pulse * 0.25))[:, None]
        y = -(amp * np.sin(math.pi * f) + np.sin(3 * math.pi * f + now * 6 + s[:, None]) * L[:, None] * 40 * np.sin(math.pi * f))
        x = np.broadcast_to((f - 0.5) * 660, y.shape)
        z = np.broadcast_to(((s - 11.5) * 36)[:, None], y.shape)
        scr, zz = self.view(np.stack([x, y, z], -1), vp)
        strips = [(scr[k], min(0.85, 0.15 + L[k] * 0.8), False) for k in reversed(range(self.N))]
        segs = [(scr[:-1, 24], scr[1:, 24], (zz[:-1, 24] + zz[1:, 24]) / 2, min(0.5, 0.1 + p.mid * 1.2))]
        return segs, [(scr[:, [0, 48]].reshape(-1, 2), np.repeat(1.5 + L * 6, 2), None)], strips


class Torus(Scene):
    name, pitch, TU, TV = "Torus", -0.55, 36, 16

    def build(self, p, now, dt, vp):
        self.step(p, dt)
        u, v = np.arange(self.TU)[:, None], np.arange(self.TV)[None, :]
        phi = u / self.TU * TAU
        rt = 62 + p.lv[col_index(u / self.TU)] * 95 + p.bass * 30 + p.beat_pulse * 14
        tt = v / self.TV * TAU + phi + self.cr
        rv = rt + np.sin(tt * 3 + now * 2) * min(0.4, p.mid * 2) * 28
        rm = 190 * (1 + p.bass * 0.1 + p.beat_pulse * 0.04)
        q = rm + rv * np.cos(tt)
        scr, z = self.view(np.stack([q * np.cos(phi), rv * np.sin(tt), q * np.sin(phi)], -1), vp)
        n, ev = slice(None), slice(0, None, 2)
        A2, B2 = np.roll(scr, -1, 0), np.roll(scr, -1, 1)
        zu, zv = (z + np.roll(z, -1, 0)) / 2, (z + np.roll(z, -1, 1)) / 2
        segs = [(scr.reshape(-1, 2), A2.reshape(-1, 2), zu.ravel(), None), (scr[ev].reshape(-1, 2), B2[ev].reshape(-1, 2), zv[ev].ravel(), None)]
        return segs, [], self.shocks(p, now, vp, rm * 0.5, rm * 1.1)


SCENES = [Torus, Helix, Terrain, Tunnel, Lattice, Galaxy, Ripple, Bars, Strings]
