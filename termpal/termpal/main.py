"""TERMPAL entry point.

Handles the parts that must happen before curses takes over the
screen (first-run naming, save-file loading) and then hands off to
the curses application loop.
"""

from __future__ import annotations

import argparse
import curses
import sys

from termpal import __version__
from termpal.core.creature import Creature
from termpal.core.storage import delete_save, get_save_path, load_creature, save_creature
from termpal.ui.app import run_app


def _prompt_for_name() -> str:
    print("TERMPAL - no creature found. Let's begin.")
    while True:
        name = input("Name your creature: ").strip()
        if name:
            return name[:20]
        print("A creature needs a name.")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="termpal",
        description="A persistent ASCII creature that lives in your terminal.",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="delete the existing save file and start over",
    )
    parser.add_argument(
        "--save-path", action="store_true",
        help="print the save file location and exit",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="print the version and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"termpal {__version__}")
        return 0

    if args.save_path:
        print(get_save_path())
        return 0

    if args.reset:
        deleted = delete_save()
        print("Save file deleted." if deleted else "No save file existed.")

    creature = load_creature()
    if creature is None:
        name = _prompt_for_name()
        creature = Creature(name=name)
        save_creature(creature)

    try:
        curses.wrapper(run_app, creature)
    except KeyboardInterrupt:
        save_creature(creature)
    return 0


if __name__ == "__main__":
    sys.exit(main())
