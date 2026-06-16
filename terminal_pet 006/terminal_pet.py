#!/usr/bin/env python3
"""
Terminal Pet
============
A real-time ASCII terminal pet that follows your cursor (keyboard-driven
target) with smooth, physics-based (lerp + inertia) movement, idle AI
wandering, an emotion system, and a small command line for interaction.

Controls
--------
Arrow keys / WASD : move the target the pet follows
f                 : feed the pet (happy animation)
1 / 2 / 3         : switch pet (cat / ghost / drone)
:                 : open command line  (type a command, Enter to run, Esc cancels)
                    commands: follow | idle | sleep | feed | switch <pet>
q                 : quit

Technical notes
----------------
- Pure standard library (curses). No third-party dependencies.
- Non-blocking input via curses.nodelay + getch loop.
- Double-buffered rendering: we build the whole frame as a string list and
  blit it in one go each tick to avoid flicker.
- Physics: target position is updated by input; pet position eases toward
  the target using velocity + acceleration (critically-damped spring-ish
  lerp) for smooth inertia-based following.
- Cross-platform: curses is available on Linux/macOS by default. On
  Windows, install `windows-curses` (pip install windows-curses).
"""

import curses
import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple


# --------------------------------------------------------------------------
# Pet definitions
# --------------------------------------------------------------------------

@dataclass
class PetType:
    name: str
    frames: dict          # emotion -> list of ascii frames (for simple anim)
    follow_strength: float  # how strongly it eases toward target (0-1)
    max_speed: float        # max units/sec
    drag: float              # velocity damping factor per second
    color_pair: int


PETS = {
    "cat": PetType(
        name="cat",
        frames={
            "idle":    ["(=^..^=)", "(=^..^=)"],
            "happy":   ["(=^o^=)", "(=^O^=)"],
            "sleepy":  ["(=-..-=)", "(=_..-=)"],
            "excited": ["(=^_^=)*", "(=^o^=)!"],
        },
        follow_strength=6.0,
        max_speed=28.0,
        drag=4.0,
        color_pair=1,
    ),
    "ghost": PetType(
        name="ghost",
        frames={
            "idle":    ["( o.o )~", "( o.o )~"],
            "happy":   [" (^.^)~ ", " (^o^)~ "],
            "sleepy":  ["( -.- )", "( _.- )"],
            "excited": ["( O.O )!", "( *.* )!"],
        },
        follow_strength=3.5,
        max_speed=18.0,
        drag=2.0,
        color_pair=2,
    ),
    "drone": PetType(
        name="drone",
        frames={
            "idle":    ["[-#-]", "[=#=]"],
            "happy":   ["{-#-}", "{=#=}"],
            "sleepy":  ["[...]", "[. .]"],
            "excited": ["<*#*>", "<-#->"],
        },
        follow_strength=9.0,
        max_speed=40.0,
        drag=6.0,
        color_pair=3,
    ),
}

EMOTIONS = ["idle", "happy", "sleepy", "excited"]


# --------------------------------------------------------------------------
# Pet state / physics
# --------------------------------------------------------------------------

@dataclass
class Pet:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    pet_type: PetType = field(default_factory=lambda: PETS["cat"])
    emotion: str = "idle"
    emotion_timer: float = 0.0
    anim_frame: int = 0
    anim_timer: float = 0.0
    mode: str = "follow"   # follow | idle | sleep
    last_interaction: float = field(default_factory=time.time)
    wander_target: Tuple[float, float] = (0.0, 0.0)
    wander_timer: float = 0.0

    def current_frame(self) -> str:
        frames = self.pet_type.frames.get(self.emotion, self.pet_type.frames["idle"])
        return frames[self.anim_frame % len(frames)]

    def update_animation(self, dt: float):
        self.anim_timer += dt
        speed = 0.6 if self.emotion != "excited" else 0.25
        if self.anim_timer >= speed:
            self.anim_timer = 0.0
            self.anim_frame += 1

    def set_emotion(self, emotion: str, duration: float = 2.5):
        self.emotion = emotion
        self.emotion_timer = duration

    def update_emotion(self, dt: float, idle_seconds: float):
        if self.emotion_timer > 0:
            self.emotion_timer -= dt
            if self.emotion_timer <= 0:
                self.emotion = "idle"
        else:
            if self.mode == "sleep":
                self.emotion = "sleepy"
            elif idle_seconds > 8:
                self.emotion = "sleepy"
            elif self.mode == "idle":
                self.emotion = "idle"


# --------------------------------------------------------------------------
# Physics integration (lerp + inertia, frame-rate independent)
# --------------------------------------------------------------------------

def update_physics(pet: Pet, target_x: float, target_y: float, dt: float):
    pt = pet.pet_type

    if pet.mode == "sleep":
        # Strong damping, no chase: pet just settles down.
        accel_strength = 0.5
        speed_cap = pt.max_speed * 0.15
    elif pet.mode == "idle":
        # Wander toward a roaming target instead of the cursor.
        accel_strength = pt.follow_strength * 0.4
        speed_cap = pt.max_speed * 0.5
        target_x, target_y = pet.wander_target
    else:  # follow
        accel_strength = pt.follow_strength
        speed_cap = pt.max_speed

    dx = target_x - pet.x
    dy = target_y - pet.y
    dist = math.hypot(dx, dy)

    if dist > 0.001:
        ax = (dx / dist) * accel_strength * min(dist, 10)
        ay = (dy / dist) * accel_strength * min(dist, 10)
    else:
        ax = ay = 0.0

    pet.vx += ax * dt
    pet.vy += ay * dt

    # Drag / damping for smooth deceleration (critically-damped feel).
    damping = max(0.0, 1.0 - pt.drag * dt)
    pet.vx *= damping
    pet.vy *= damping

    # Clamp speed.
    speed = math.hypot(pet.vx, pet.vy)
    if speed > speed_cap:
        scale = speed_cap / speed
        pet.vx *= scale
        pet.vy *= scale

    pet.x += pet.vx * dt
    pet.y += pet.vy * dt


def update_wander_target(pet: Pet, dt: float, bounds: Tuple[int, int]):
    pet.wander_timer -= dt
    if pet.wander_timer <= 0:
        w, h = bounds
        pet.wander_target = (
            random.uniform(2, max(3, w - 10)),
            random.uniform(2, max(3, h - 3)),
        )
        pet.wander_timer = random.uniform(1.5, 4.0)


# --------------------------------------------------------------------------
# Rendering (flicker-free: build buffer, then single blit)
# --------------------------------------------------------------------------

def draw_frame(stdscr, pet: Pet, target_x: float, target_y: float,
               trail: List[Tuple[float, float]], status_msg: str,
               command_buffer: str, command_mode: bool):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Border
    try:
        stdscr.border()
    except curses.error:
        pass

    # Optional motion trail (faint dots behind the pet)
    color_trail = curses.color_pair(4) if curses.has_colors() else 0
    for i, (tx, ty) in enumerate(trail):
        ix, iy = int(tx), int(ty)
        if 1 <= iy < h - 1 and 1 <= ix < w - 1:
            try:
                stdscr.addch(iy, ix, '.', color_trail)
            except curses.error:
                pass

    # Cursor / target marker
    tx_i, ty_i = int(target_x), int(target_y)
    if 1 <= ty_i < h - 1 and 1 <= tx_i < w - 1:
        try:
            stdscr.addstr(ty_i, tx_i, "x", curses.color_pair(5) if curses.has_colors() else 0)
        except curses.error:
            pass

    # Pet sprite
    frame = pet.current_frame()
    px, py = int(pet.x), int(pet.y)
    color = curses.color_pair(pet.pet_type.color_pair) if curses.has_colors() else 0
    if 1 <= py < h - 1:
        clipped_x = max(1, min(px, w - len(frame) - 2))
        try:
            stdscr.addstr(py, clipped_x, frame, color | curses.A_BOLD)
        except curses.error:
            pass

    # Status bar (top)
    status = (f" Terminal Pet | pet:{pet.pet_type.name:<6} mode:{pet.mode:<7} "
              f"emotion:{pet.emotion:<8} | 1=cat 2=ghost 3=drone f=feed :=cmd q=quit ")
    try:
        stdscr.addstr(0, 1, status[:max(0, w - 2)], curses.A_REVERSE)
    except curses.error:
        pass

    # Bottom message / command line
    bottom_y = h - 1
    if command_mode:
        line = f":{command_buffer}"
    else:
        line = status_msg
    try:
        stdscr.addstr(bottom_y, 1, line[:max(0, w - 2)], curses.A_BOLD)
    except curses.error:
        pass

    stdscr.refresh()


# --------------------------------------------------------------------------
# Command handling
# --------------------------------------------------------------------------

def handle_command(cmd: str, pet: Pet) -> str:
    cmd = cmd.strip().lower()
    if not cmd:
        return ""
    parts = cmd.split()
    action = parts[0]

    if action == "follow":
        pet.mode = "follow"
        return "Pet is now following the cursor."
    elif action == "idle":
        pet.mode = "idle"
        return "Pet is wandering freely."
    elif action == "sleep":
        pet.mode = "sleep"
        pet.set_emotion("sleepy", duration=9999)
        return "Pet is going to sleep."
    elif action == "feed":
        pet.set_emotion("happy", duration=3.0)
        pet.last_interaction = time.time()
        return "Yum! Pet is happy."
    elif action == "switch" and len(parts) > 1:
        name = parts[1]
        if name in PETS:
            pet.pet_type = PETS[name]
            pet.anim_frame = 0
            return f"Switched to {name}."
        else:
            return f"Unknown pet '{name}'. Options: {', '.join(PETS)}"
    else:
        return f"Unknown command: {cmd}"


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------

def main(stdscr):
    curses.curs_set(0)            # hide terminal cursor
    stdscr.nodelay(True)          # non-blocking input
    stdscr.timeout(0)
    curses.start_color()
    curses.use_default_colors()

    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_YELLOW, -1)   # cat
        curses.init_pair(2, curses.COLOR_CYAN, -1)      # ghost
        curses.init_pair(3, curses.COLOR_GREEN, -1)     # drone
        curses.init_pair(4, curses.COLOR_BLUE, -1)      # trail
        curses.init_pair(5, curses.COLOR_RED, -1)       # target marker

    h, w = stdscr.getmaxyx()
    target_x, target_y = w / 2, h / 2

    pet = Pet(x=target_x, y=target_y, pet_type=PETS["cat"])
    pet.wander_target = (target_x, target_y)

    trail: List[Tuple[float, float]] = []
    status_msg = "Welcome! Press : for commands, arrows to move cursor."
    command_mode = False
    command_buffer = ""

    last_time = time.time()
    move_step = 1.6  # cursor movement per keypress (units)

    target_fps = 30
    frame_duration = 1.0 / target_fps

    try:
        while True:
            frame_start = time.time()
            now = frame_start
            dt = now - last_time
            last_time = now
            dt = min(dt, 0.1)  # clamp dt to avoid huge jumps (e.g. after resize/pause)

            h, w = stdscr.getmaxyx()

            # ---- Input handling (non-blocking) ----
            interacted = False
            try:
                while True:
                    ch = stdscr.getch()
                    if ch == -1:
                        break

                    if command_mode:
                        if ch in (10, 13):  # Enter
                            status_msg = handle_command(command_buffer, pet) or status_msg
                            command_buffer = ""
                            command_mode = False
                        elif ch == 27:  # Esc
                            command_buffer = ""
                            command_mode = False
                        elif ch in (curses.KEY_BACKSPACE, 127, 8):
                            command_buffer = command_buffer[:-1]
                        elif 32 <= ch <= 126:
                            command_buffer += chr(ch)
                        continue

                    if ch == ord(':'):
                        command_mode = True
                        command_buffer = ""
                    elif ch == ord('q'):
                        return
                    elif ch in (curses.KEY_UP, ord('w')):
                        target_y = max(1, target_y - move_step)
                        interacted = True
                    elif ch in (curses.KEY_DOWN, ord('s')):
                        target_y = min(h - 2, target_y + move_step)
                        interacted = True
                    elif ch in (curses.KEY_LEFT, ord('a')):
                        target_x = max(1, target_x - move_step)
                        interacted = True
                    elif ch in (curses.KEY_RIGHT, ord('d')):
                        target_x = min(w - 2, target_x + move_step)
                        interacted = True
                    elif ch == ord('f'):
                        status_msg = handle_command("feed", pet)
                        interacted = True
                    elif ch == ord('1'):
                        status_msg = handle_command("switch cat", pet)
                    elif ch == ord('2'):
                        status_msg = handle_command("switch ghost", pet)
                    elif ch == ord('3'):
                        status_msg = handle_command("switch drone", pet)
            except curses.error:
                pass

            if interacted:
                pet.last_interaction = time.time()
                if pet.mode != "sleep":
                    pet.mode = "follow"

            idle_seconds = time.time() - pet.last_interaction

            # ---- AI behavior: auto-switch to idle wandering on inactivity ----
            if pet.mode == "follow" and idle_seconds > 5:
                pet.mode = "idle"
                status_msg = "Pet got bored and is wandering..."
            if pet.mode == "idle":
                update_wander_target(pet, dt, (w, h))
                # Occasionally glance back at cursor briefly (soft behavior)
                if random.random() < 0.002:
                    pet.set_emotion("excited", duration=1.0)

            # ---- Physics update ----
            update_physics(pet, target_x, target_y, dt)
            pet.update_emotion(dt, idle_seconds)
            pet.update_animation(dt)

            # ---- Trail effect ----
            trail.append((pet.x + 1, pet.y))
            if len(trail) > 6:
                trail.pop(0)

            # ---- Render ----
            draw_frame(stdscr, pet, target_x, target_y, trail, status_msg,
                       command_buffer, command_mode)

            # ---- Frame pacing (cap FPS, low CPU usage) ----
            elapsed = time.time() - frame_start
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        pass


def run():
    curses.wrapper(main)


if __name__ == "__main__":
    run()
