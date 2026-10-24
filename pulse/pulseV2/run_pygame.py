"""Pulse for pygame: wireframe sphere with a rhythm-bound core."""
import math
import os
import sys
import time

import numpy as np
import pygame

from core.audio import Player
from core.geometry import project, rotate

LAT, LON, R = 16, 36, 300
THEMES = {"dark": ((10, 10, 10), (242, 242, 240)), "light": ((246, 246, 244), (12, 12, 12))}
CUBE = np.array([(1 if q & 1 else -1, 1 if q & 2 else -1, 1 if q & 4 else -1) for q in range(8)], float)
CUBE_EDGES = [(q, q | b) for q in range(8) for b in (1, 2, 4) if not q & b]
OCTA = np.array([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)], float)
OCTA_EDGES = [(a, b) for a in range(6) for b in range(a + 1, 6) if a // 2 != b // 2]


def mix(bg, fg, a):
    return tuple(int(bg[i] + (fg[i] - bg[i]) * a) for i in range(3))


def pick_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.flac *.ogg *.mp3")])
        root.destroy()
        return path
    except Exception:
        return ""


def clock(s):
    return "%d:%02d" % (int(s) // 60, int(s) % 60)


def main():
    pygame.init()
    pygame.display.set_caption("Pulse")
    screen = pygame.display.set_mode((1000, 720), pygame.RESIZABLE)
    font, big = pygame.font.Font(None, 20), pygame.font.Font(None, 64)
    player = Player()
    player.load(sys.argv[1]) if len(sys.argv) > 1 else player.load_demo()

    th = np.linspace(0, math.pi, LAT + 1)[:, None]
    ph = np.linspace(0, 2 * math.pi, LON + 1)[None, :]
    unit = np.stack([np.sin(th) * np.cos(ph), np.cos(th) + 0 * ph, np.sin(th) * np.sin(ph)], -1)
    st = np.sin(th)

    theme, yaw, cr, last = "dark", 0.6, 0.0, time.monotonic()
    max_frames, frames, clock_ = int(os.environ.get("PULSE_MAX_FRAMES", "0")), 0, pygame.time.Clock()
    running = True
    while running:
        now = time.monotonic()
        dt = min(now - last, 0.05)
        last = now
        k = dt * 30
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.DROPFILE:
                player.load(e.file)
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    player.toggle()
                elif e.key == pygame.K_LEFT:
                    player.seek(-5)
                elif e.key == pygame.K_RIGHT:
                    player.seek(5)
                elif e.key == pygame.K_UP:
                    player.volume = min(1.0, player.volume + 0.05)
                elif e.key == pygame.K_DOWN:
                    player.volume = max(0.0, player.volume - 0.05)
                elif e.key == pygame.K_t:
                    theme = "light" if theme == "dark" else "dark"
                elif e.key == pygame.K_o:
                    path = pick_file()
                    if path:
                        player.load(path)

        player.analyse(dt)
        p = player
        bg, fg = THEMES[theme]
        screen = pygame.display.get_surface()
        w, h = screen.get_size()
        cx, cy, zoom = w / 2, h * 0.46, min(w, h) / 1000
        mx, my = pygame.mouse.get_pos()
        yaw += k * (0.004 + p.energy * 0.022 + p.spin * 0.008)
        cr += k * (0.008 + p.energy * 0.04 + p.spin * 0.035)
        cam = (yaw + (mx / w * 2 - 1) * 0.35, -0.35 + (my / h * 2 - 1) * 0.2)
        screen.fill(bg)

        # morphing sphere
        r = R * (1 + p.bass * 0.12 + p.beat_pulse * 0.04 + p.lv[None, :] * 0.5 * st ** 0.8
                 + p.mid * 0.04 * np.sin(th * 5 + now * 2 + ph * 2) + p.hi * 0.03 * np.sin(ph * 9 - now * 3))
        scr, z = project(rotate(unit * r[..., None], *cam), cx, cy, zoom)
        A = np.concatenate([scr[1:LAT, :-1].reshape(-1, 2), scr[:-1, 0:LON:3].reshape(-1, 2)])
        B = np.concatenate([scr[1:LAT, 1:].reshape(-1, 2), scr[1:, 0:LON:3].reshape(-1, 2)])
        Z = np.concatenate([((z[1:LAT, :-1] + z[1:LAT, 1:]) / 2).ravel(), ((z[:-1, 0:LON:3] + z[1:, 0:LON:3]) / 2).ravel()])
        bucket = np.where(Z < -R * 0.35, 2, np.where(Z < R * 0.35, 1, 0))
        for bk, alpha in enumerate((0.08, 0.22, 0.5)):
            col = mix(bg, fg, alpha)
            for a, b in zip(A[bucket == bk].tolist(), B[bucket == bk].tolist()):
                pygame.draw.aaline(screen, col, a, b)

        # beat shockwaves
        ang = np.linspace(0, 2 * math.pi, 49)
        for wv in p.waves:
            age = (now - wv) / 1.5
            if age < 1:
                rad = R * (1.05 + age)
                ring = np.stack([np.cos(ang) * rad, 0 * ang, np.sin(ang) * rad], -1)
                pygame.draw.aalines(screen, mix(bg, fg, (1 - age) * 0.35), False,
                                    project(rotate(ring, *cam), cx, cy, zoom)[0].tolist())

        # core: cube + octahedron + counter-rotating inner cube
        base = R * 0.34 * (1 + p.bass * 0.55 + p.beat_pulse * 0.14)
        shapes = (
            (CUBE * (base * (1 + p.lv[::5][:8, None] * 0.5)), cr, CUBE_EDGES),
            (OCTA * base * 1.3, cr, OCTA_EDGES),
            (CUBE * base * 0.5 * (1 + p.bass * 0.8 + p.beat_pulse * 0.2), -cr, CUBE_EDGES),
        )
        col = mix(bg, fg, min(0.85, 0.32 + p.beat_pulse * 0.4 + p.energy * 0.4))
        for pts, a, edges in shapes:
            sc = project(rotate(rotate(pts, a + 1, a * 0.7), *cam), cx, cy, zoom)[0].tolist()
            for i, j in edges:
                pygame.draw.aaline(screen, col, sc[i], sc[j])
            for q in sc:
                pygame.draw.rect(screen, fg, (q[0] - 1.5, q[1] - 1.5, 3, 3))

        # HUD
        screen.blit(big.render(p.title.upper()[:28], True, fg), (24, 20))
        frac = p.pos / max(1, len(p.data))
        pygame.draw.line(screen, mix(bg, fg, 0.2), (24, h - 34), (w - 24, h - 34))
        pygame.draw.line(screen, fg, (24, h - 34), (24 + (w - 48) * frac, h - 34))
        info = "%s / %s    BPM %d    BASS %d    VOL %d" % (clock(p.position), clock(p.duration), p.bpm, p.bass * 100, p.volume * 100)
        screen.blit(font.render(info, True, fg), (24, h - 26))
        help_txt = font.render("SPACE play   LEFT/RIGHT seek   UP/DOWN volume   O open   T theme", True, mix(bg, fg, 0.45))
        screen.blit(help_txt, (w - help_txt.get_width() - 24, h - 26))

        pygame.display.flip()
        clock_.tick(60)
        frames += 1
        if max_frames and frames >= max_frames:
            running = False
    player.close()
    pygame.quit()


if __name__ == "__main__":
    main()
