"""Pulse styles for pygame: nine 3D scenes on one engine. TAB / SHIFT+TAB or 1-9 switch style."""
import os
import sys
import time

import numpy as np
import pygame

from core.audio import Player
from core.scenes import SCENES, point_alpha, split_segments
from run_pygame import clock, mix, pick_file

THEMES = {"dark": ((10, 10, 10), (242, 242, 240)), "light": ((246, 246, 244), (12, 12, 12))}


def draw_primitives(screen, bg, fg, segs, pts, strips):
    h = screen.get_height()
    for A, B, Z, alpha in segs:
        for a, A_, B_ in split_segments(A, B, Z, alpha):
            col = mix(bg, fg, a)
            for s, e in zip(A_.tolist(), B_.tolist()):
                pygame.draw.aaline(screen, col, s, e)
    for P, alpha, fill in strips:
        pl = P.tolist()
        if fill:
            pygame.draw.polygon(screen, bg, pl + [(pl[-1][0], h), (pl[0][0], h)])
        pygame.draw.aalines(screen, mix(bg, fg, alpha), False, pl)
    for P, S, Z in pts:
        al = point_alpha(Z, len(P))
        for (x, y), s, a in zip(P.tolist(), np.broadcast_to(S, len(P)).tolist(), al.tolist()):
            pygame.draw.rect(screen, mix(bg, fg, a), (x - s / 2, y - s / 2, s, s))


def main():
    pygame.init()
    pygame.display.set_caption("Pulse styles")
    pygame.display.set_mode((1000, 720), pygame.RESIZABLE)
    font, big = pygame.font.Font(None, 20), pygame.font.Font(None, 64)
    player = Player()
    player.load(sys.argv[1]) if len(sys.argv) > 1 else player.load_demo()
    scenes, index, theme = [cls() for cls in SCENES], 0, "dark"
    last, frames, tick = time.monotonic(), 0, pygame.time.Clock()
    max_frames = int(os.environ.get("PULSE_MAX_FRAMES", "0"))
    running = True
    while running:
        now = time.monotonic()
        dt = min(now - last, 0.05)
        last = now
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.DROPFILE:
                player.load(e.file)
            elif e.type == pygame.KEYDOWN:
                step = -1 if e.mod & pygame.KMOD_SHIFT else 1
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_TAB:
                    index = (index + step) % len(scenes)
                elif pygame.K_1 <= e.key <= pygame.K_9 and e.key - pygame.K_1 < len(scenes):
                    index = e.key - pygame.K_1
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
        bg, fg = THEMES[theme]
        screen = pygame.display.get_surface()
        w, h = screen.get_size()
        mx, my = pygame.mouse.get_pos()
        vp = (w / 2, h * 0.46, min(w, h) / 1000, mx / w * 2 - 1, my / h * 2 - 1)
        screen.fill(bg)
        draw_primitives(screen, bg, fg, *scenes[index].build(player, now, dt, vp))
        screen.blit(big.render(player.title.upper()[:28], True, fg), (24, 20))
        frac = player.pos / max(1, len(player.data))
        pygame.draw.line(screen, mix(bg, fg, 0.2), (24, h - 34), (w - 24, h - 34))
        pygame.draw.line(screen, fg, (24, h - 34), (24 + (w - 48) * frac, h - 34))
        info = "%s    %s / %s    BPM %d    BASS %d" % (scenes[index].name.upper(), clock(player.position), clock(player.duration), player.bpm, player.bass * 100)
        screen.blit(font.render(info, True, fg), (24, h - 26))
        hint = font.render("TAB style   SPACE play   LEFT/RIGHT seek   UP/DOWN volume   O open   T theme", True, mix(bg, fg, 0.45))
        screen.blit(hint, (w - hint.get_width() - 24, h - 26))
        pygame.display.flip()
        tick.tick(60)
        frames += 1
        running = running and not (max_frames and frames >= max_frames)
    player.close()
    pygame.quit()


if __name__ == "__main__":
    main()
