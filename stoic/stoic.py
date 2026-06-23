#!/usr/bin/env python3
"""
STOIC — a command-line companion that hands you one Stoic thought
every time you run it.

No network calls. No API keys. No tracking. Just a quiet voice
from Rome, Greece, or right now — chosen at random, dressed for
your terminal.

Run it:
    python stoic.py
"""

import random
import sys
import textwrap
import time
from datetime import datetime

# ──────────────────────────────────────────────────────────────────
#  THE QUOTES
#
#  Two kinds live in this list:
#
#  · REAL  — genuine lines from Marcus Aurelius, Epictetus, and
#            Seneca, drawn from public-domain translations
#            (chiefly George Long's 1862 Meditations, and the
#            classic Long/Oldfather renderings of Epictetus and
#            Seneca that have circulated freely for over a century).
#
#  · ORIGINAL — new lines written in the Stoic voice: short,
#            unsentimental, aimed at the gap between what happens
#            and how you meet it. Not contemporary self-help
#            paraphrases of the classics — distinct thoughts, in
#            the same register.
#
#  Every entry is a (text, author) tuple. Author is one of:
#  "Marcus Aurelius", "Epictetus", "Seneca", or "—" for originals.
# ──────────────────────────────────────────────────────────────────

QUOTES = [
    # ── REAL: Marcus Aurelius ──────────────────────────────────
    ("You have power over your mind, not outside events. Realize this, and you will find strength.", "Marcus Aurelius"),
    ("Waste no more time arguing about what a good man should be. Be one.", "Marcus Aurelius"),
    ("The impediment to action advances action. What stands in the way becomes the way.", "Marcus Aurelius"),
    ("If it is not right, do not do it. If it is not true, do not say it.", "Marcus Aurelius"),
    ("Choose not to be harmed, and you won't feel harmed. Don't feel harmed, and you haven't been.", "Marcus Aurelius"),
    ("The soul becomes dyed with the colour of its thoughts.", "Marcus Aurelius"),
    ("Be tolerant with others and strict with yourself.", "Marcus Aurelius"),
    ("External things are not the problem. It's your assessment of them — which you can erase right now.", "Marcus Aurelius"),
    ("It never ceases to amaze me: we all love ourselves more than other people, but we care more about their opinion than our own.", "Marcus Aurelius"),
    ("You always own the option of having no opinion. There is never any need to get worked up.", "Marcus Aurelius"),
    ("The best revenge is to be unlike him who performed the injury.", "Marcus Aurelius"),
    ("He who lives in harmony with himself lives in harmony with the universe.", "Marcus Aurelius"),
    ("Confine yourself to the present.", "Marcus Aurelius"),
    ("Nowhere can man find a quieter or more untroubled retreat than in his own soul.", "Marcus Aurelius"),

    # ── REAL: Epictetus ─────────────────────────────────────────
    ("Men are disturbed not by things, but by the principles and notions which they form concerning things.", "Epictetus"),
    ("Make the best use of what is in your power, and take the rest as it happens.", "Epictetus"),
    ("It is not events that disturb people, it is their judgements concerning them.", "Epictetus"),
    ("First say to yourself what you would be; and then do what you have to do.", "Epictetus"),
    ("No man is free who is not master of himself.", "Epictetus"),
    ("Don't hope that events will turn out the way you want. Welcome events in whichever way they happen — this is the path to peace.", "Epictetus"),
    ("It is the act of an ill-instructed man to blame others for his own bad condition.", "Epictetus"),
    ("We have two ears and one mouth, so that we can listen twice as much as we speak.", "Epictetus"),
    ("Know, first, who you are, and then adorn yourself accordingly.", "Epictetus"),
    ("A ship should not ride on a single anchor, nor life on a single hope.", "Epictetus"),
    ("If you want to improve, be content to be thought foolish and stupid with regard to external things.", "Epictetus"),

    # ── REAL: Seneca ────────────────────────────────────────────
    ("We suffer more often in imagination than in reality.", "Seneca"),
    ("If a man knows not which port he sails, no wind is favorable.", "Seneca"),
    ("Life is long, if you know how to use it.", "Seneca"),
    ("While we wait for life, life passes.", "Seneca"),
    ("No person has the power to have everything they want, but it is in their power not to want what they don't have, and to cheerfully put to good use what they do have.", "Seneca"),
    ("Nothing, to my way of thinking, is a better proof of a well-ordered mind than a man's ability to stop just where he is and pass some time in his own company.", "Seneca"),
    ("People are frugal in guarding their personal property, but as soon as it comes to squandering time, they are most wasteful of the one thing in which it is right to be stingy.", "Seneca"),
    ("As long as you live, keep learning how to live.", "Seneca"),
    ("Difficulties strengthen the mind, as labor does the body.", "Seneca"),
    ("True happiness is to enjoy the present, without anxious dependence on the future.", "Seneca"),
    ("He who is brave is free.", "Seneca"),
    ("Hang on to your youthful enthusiasms — you'll be able to use them better when you're older.", "Seneca"),
    ("It is a rough road that leads to the heights of greatness.", "Seneca"),

    # ── ORIGINAL: written in the Stoic register ─────────────────
    ("The obstacle was never separate from the path. It was the only path that ever actually existed.", "—"),
    ("You do not need the world to apologize for being indifferent to you. Indifference was never an insult.", "—"),
    ("Most of what wounds you arrives twice: once as the event, and once more as the story you keep telling about it.", "—"),
    ("A closed fist cannot receive anything new. Neither can a closed mind, and that one is harder to notice.", "—"),
    ("The version of you that handled yesterday's crisis no longer exists. Stop consulting it for today's.", "—"),
    ("Discipline is just respect you've decided to show your future self before he's arrived to ask for it.", "—"),
    ("What you call bad luck is usually just reality declining to consult your preferences.", "—"),
    ("You rehearse disasters in your head as if rehearsal were the same as preparation. It isn't. One calms nothing; the other changes something.", "—"),
    ("Anger is a loan you take out against your own peace, and the interest is always due immediately.", "—"),
    ("The cure for envy is arithmetic: you are comparing your entire life to someone else's highlight reel, and the math was rigged before you started.", "—"),
    ("Nobody owes you a life free of friction. Friction is the tuition; wisdom is what you get if you actually attend class.", "—"),
    ("You do not control the dice. You have never controlled the dice. You only control how you hold them.", "—"),
    ("Complaining is rehearsing a problem in front of an audience that cannot solve it.", "—"),
    ("The opinions of strangers are rent you stopped owing the day you noticed you were paying it.", "—"),
    ("A grudge is a weight you agreed to carry so the other person wouldn't have to feel the consequences of dropping it.", "—"),
    ("Most fear is just imagination working overtime without being asked to clock in.", "—"),
    ("You are not in control of the storm. You are, however, the one deciding whether to also be the storm.", "—"),
    ("Patience is not the absence of urgency. It is urgency that has learned where it is and is not welcome.", "—"),
    ("The body keeps moving forward in time whether or not the mind agrees to come along. Bring it along anyway.", "—"),
    ("What frightens you about death is usually a fear about an unlived life wearing a more dramatic costume.", "—"),
    ("Every comfort you cling to was once something you survived without. You can survive without it again.", "—"),
    ("You do not need to win every argument you're having with people who are not in the room.", "—"),
    ("Virtue is rarely loud. It is mostly just doing the necessary, unglamorous thing again, on a day no one is watching.", "—"),
    ("The mind that needs constant praise to function has built its house on someone else's land.", "—"),
    ("Suffering announces itself. Acceptance has to be chosen quietly, usually more than once a day.", "—"),
    ("If the criticism is true, it's information. If it's false, it's just noise. Either way, it was never an injury.", "—"),
    ("You will not remember most of what upset you today a year from now. Spend accordingly.", "—"),
    ("Self-pity feels like comfort and functions like a cage you built with your own hands and call cozy.", "—"),
    ("The job was never to feel nothing. The job was to notice the feeling and still choose the action that reason recommends.", "—"),
    ("A man who needs the world's approval has handed the world the keys to his own mood.", "—"),
    ("Time does not owe you a warning before it takes something. Treat today like the unannounced gift it is.", "—"),
    ("You cannot reason with weather. You were never meant to. You were meant to dress for it.", "—"),
    ("The habit of blaming circumstance is just the mind's way of avoiding the harder audit — of itself.", "—"),
    ("Whatever you fear losing was, from the very start, only ever on loan.", "—"),
    ("Strength is not the absence of trembling hands. It's doing the necessary thing with hands that tremble anyway.", "—"),
    ("Nobody is coming to rescue you from the work of becoming who you're capable of being. That part was always yours alone.", "—"),
    ("The mind, like a guest house, will host whatever shows up uninvited. Your job is deciding who gets to stay for dinner.", "—"),
    ("Most regret is just the mind insisting it should have known the unknowable in advance.", "—"),
    ("You can lose your wealth, your title, your reputation, and your health, in roughly that order or any other, and none of it touches the part of you that chooses.", "—"),
    ("The unexamined grievance grows roots. The examined one usually turns out to be smaller than the soil it occupied.", "—"),
]


def banner_glitch():
    """A short cyberpunk-styled boot sequence before the quote drops."""
    lines = [
        "▓▓▓ INITIALIZING STOA ▓▓▓",
        "> loading wisdom.dat ...",
        "> consulting the ancients ...",
    ]
    for line in lines:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        time.sleep(0.12)


def render_card(text, author):
    """Render the quote in a terminal-friendly bordered card."""
    width = 64
    inner = width - 2          # space between the two ┃ borders
    text_width = inner - 4     # leaving 2-space padding each side

    wrapped = textwrap.wrap(text, text_width)

    top = "┏" + "━" * inner + "┓"
    bottom = "┗" + "━" * inner + "┛"
    empty = "┃" + " " * inner + "┃"

    body_lines = []
    for line in wrapped:
        padded = line.center(text_width)
        body_lines.append(f"┃  {padded}  ┃")

    attribution = f"— {author}" if author != "—" else "— a Stoic, unnamed, just now"
    attr_padded = attribution.rjust(text_width)
    attr_line = f"┃  {attr_padded}  ┃"

    print()
    print(top)
    print(empty)
    for line in body_lines:
        print(line)
    print(empty)
    print(attr_line)
    print(empty)
    print(bottom)
    print()


def footer(author):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    tag = "[ORIGINAL]" if author == "—" else "[CLASSICAL]"
    print(f"  {tag}  {now}")
    print()


def main():
    banner_glitch()
    text, author = random.choice(QUOTES)
    render_card(text, author)
    footer(author)


if __name__ == "__main__":
    main()
