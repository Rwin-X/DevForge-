"""ASCII sprite selection.

Pure lookup logic - returns a list of strings (one per line) for a
given life stage and mood. No rendering, no curses. The ui layer is
responsible for putting these lines on screen with color.
"""

from __future__ import annotations

from termpal.core.creature import Mood

EGG = [
    r"   ____   ",
    r"  /    \  ",
    r" |      | ",
    r"  \____/  ",
]

HATCHLING = {
    Mood.THRIVING: [
        r"   /\_/\  ",
        r"  ( ^.^ ) ",
        r"   > ^ <  ",
    ],
    Mood.CONTENT: [
        r"   /\_/\  ",
        r"  ( -.- ) ",
        r"   >   <  ",
    ],
    Mood.BORED: [
        r"   /\_/\  ",
        r"  ( -.-)  ",
        r"   >   <  ",
    ],
    Mood.HUNGRY: [
        r"   /\_/\  ",
        r"  ( o.o ) ",
        r"   > ? <  ",
    ],
    Mood.TIRED: [
        r"   /\_/\  ",
        r"  ( u.u ) ",
        r"   >   <  ",
    ],
    Mood.SICK: [
        r"   /\_/\  ",
        r"  ( x.x ) ",
        r"   >   <  ",
    ],
    Mood.CRITICAL: [
        r"   /\_/\  ",
        r"  ( X.X ) ",
        r"   > ! <  ",
    ],
}

JUVENILE = {
    Mood.THRIVING: [
        r"    /\___/\    ",
        r"   (  ^.^  )~  ",
        r"  __)     (__  ",
        r" (___________) ",
    ],
    Mood.CONTENT: [
        r"    /\___/\    ",
        r"   (  -.-  )   ",
        r"  __)     (__  ",
        r" (___________) ",
    ],
    Mood.BORED: [
        r"    /\___/\    ",
        r"   ( -.-  )    ",
        r"  __)  z  (__  ",
        r" (___________) ",
    ],
    Mood.HUNGRY: [
        r"    /\___/\    ",
        r"   (  o.o  )   ",
        r"  __)  ?  (__  ",
        r" (___________) ",
    ],
    Mood.TIRED: [
        r"    /\___/\    ",
        r"   (  u.u  )   ",
        r"  __)     (__  ",
        r" (_____zzz___) ",
    ],
    Mood.SICK: [
        r"    /\___/\    ",
        r"   (  x.x  )   ",
        r"  __)  +  (__  ",
        r" (___________) ",
    ],
    Mood.CRITICAL: [
        r"    /\___/\    ",
        r"   (  X.X  )   ",
        r"  __)  !  (__  ",
        r" (___________) ",
    ],
}

ADULT = {
    Mood.THRIVING: [
        r"      /\_______/\      ",
        r"     /  ^         ^ \  ",
        r"    (     ^.^       ) ",
        r"   __)             (__",
        r"  (_________________)",
    ],
    Mood.CONTENT: [
        r"      /\_______/\      ",
        r"     /                \ ",
        r"    (      -.-        ) ",
        r"   __)             (__",
        r"  (_________________)",
    ],
    Mood.BORED: [
        r"      /\_______/\      ",
        r"     /                \ ",
        r"    (      -.-  z     ) ",
        r"   __)             (__",
        r"  (_________________)",
    ],
    Mood.HUNGRY: [
        r"      /\_______/\      ",
        r"     /                \ ",
        r"    (      o.o  ?     ) ",
        r"   __)             (__",
        r"  (_________________)",
    ],
    Mood.TIRED: [
        r"      /\_______/\      ",
        r"     /                \ ",
        r"    (      u.u         ) ",
        r"   __)           zzz(__",
        r"  (_________________)",
    ],
    Mood.SICK: [
        r"      /\_______/\      ",
        r"     /                \ ",
        r"    (      x.x  +     ) ",
        r"   __)             (__",
        r"  (_________________)",
    ],
    Mood.CRITICAL: [
        r"      /\_______/\      ",
        r"     /                \ ",
        r"    (      X.X  !     ) ",
        r"   __)             (__",
        r"  (_________________)",
    ],
}

ELDER = {
    Mood.THRIVING: [
        r"    __/\_______/\__    ",
        r"   /   ~   ^   ~   \   ",
        r"  (       ^.^        ) ",
        r"  ()               ()  ",
        r"   \_______________/   ",
    ],
    Mood.CONTENT: [
        r"    __/\_______/\__    ",
        r"   /                 \ ",
        r"  (        -.-        ) ",
        r"  ()               ()  ",
        r"   \_______________/   ",
    ],
    Mood.BORED: [
        r"    __/\_______/\__    ",
        r"   /                 \ ",
        r"  (        -.-  z     ) ",
        r"  ()               ()  ",
        r"   \_______________/   ",
    ],
    Mood.HUNGRY: [
        r"    __/\_______/\__    ",
        r"   /                 \ ",
        r"  (        o.o  ?     ) ",
        r"  ()               ()  ",
        r"   \_______________/   ",
    ],
    Mood.TIRED: [
        r"    __/\_______/\__    ",
        r"   /                 \ ",
        r"  (        u.u        ) ",
        r"  ()            zzz()  ",
        r"   \_______________/   ",
    ],
    Mood.SICK: [
        r"    __/\_______/\__    ",
        r"   /                 \ ",
        r"  (        x.x  +     ) ",
        r"  ()               ()  ",
        r"   \_______________/   ",
    ],
    Mood.CRITICAL: [
        r"    __/\_______/\__    ",
        r"   /                 \ ",
        r"  (        X.X  !     ) ",
        r"  ()               ()  ",
        r"   \_______________/   ",
    ],
}

TOMBSTONE = [
    r"    _______    ",
    r"   /       \   ",
    r"  |  R.I.P  |  ",
    r"  |         |  ",
    r"  |_________|  ",
]

_STAGE_TABLE = {
    "hatchling": HATCHLING,
    "juvenile": JUVENILE,
    "adult": ADULT,
    "elder": ELDER,
}


def get_sprite(life_stage: str, mood: Mood) -> list[str]:
    """Return the ASCII art lines for a given life stage and mood."""
    if mood == Mood.DEAD:
        return TOMBSTONE
    if life_stage == "egg":
        return EGG

    table = _STAGE_TABLE.get(life_stage, JUVENILE)
    # Fall back to CONTENT if a stage's table is ever missing a mood.
    return table.get(mood, table[Mood.CONTENT])
