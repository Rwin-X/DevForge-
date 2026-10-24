"""Pulse for the terminal: mirrored spectrum bars driven by the shared engine."""
import shutil
import sys
import time

import numpy as np

from core.audio import COLS, Player

BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


def clock(s):
    return "%d:%02d" % (int(s) // 60, int(s) % 60)


def main():
    player = Player()
    player.load(sys.argv[1]) if len(sys.argv) > 1 else player.load_demo()
    last = time.monotonic()
    sys.stdout.write("\x1b[?25l\x1b[2J")
    try:
        while True:
            now = time.monotonic()
            player.analyse(now - last)
            last = now
            cols, rows = shutil.get_terminal_size()
            rows = max(6, rows - 4)
            vals = np.interp(np.linspace(0, COLS - 1, cols), np.arange(COLS), player.lv)
            lines = []
            for r in range(rows, 0, -1):
                idx = np.clip(((vals * rows - (r - 1)) * 8).astype(int), 0, 8)
                lines.append("".join(BLOCKS[i] for i in idx))
            head = "%s   %s / %s   BPM %d   BASS %d" % (
                player.title.upper()[:30], clock(player.position), clock(player.duration), player.bpm, player.bass * 100)
            sys.stdout.write("\x1b[H" + head.ljust(cols) + "\n\n" + "\n".join(lines) + "\n")
            sys.stdout.flush()
            time.sleep(1 / 30)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[?25h\n")
        player.close()


if __name__ == "__main__":
    main()
