#!/usr/bin/env python3

"""
HashCLI
Fast Multi-Algorithm Hash Generator
"""

import argparse
import sys
from pathlib import Path

from algorithms import available_algorithms
from banner import show_banner
from filehash import hash_file
from texthash import hash_text
from timer import Timer
from ui import success, error
from utils import readable_size


def build_parser():

    parser = argparse.ArgumentParser(
        prog="HashCLI",
        description="Fast Multi-Algorithm Hash Generator"
    )

    parser.add_argument(
        "-a",
        "--algorithm",
        required=True,
        choices=available_algorithms(),
        help="Hash algorithm"
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-t",
        "--text",
        help="Text to hash"
    )

    group.add_argument(
        "-f",
        "--file",
        help="File to hash"
    )

    return parser


def hash_text_mode(args):

    with Timer() as timer:

        digest = hash_text(
            args.text,
            args.algorithm
        )

    success(
        algorithm=args.algorithm.upper(),
        digest=digest,
        elapsed=timer.elapsed,
        source="TEXT"
    )


def hash_file_mode(args):

    file = Path(args.file)

    if not file.exists():
        error("File not found.")
        sys.exit(1)

    if not file.is_file():
        error("Invalid file.")
        sys.exit(1)

    size = readable_size(file.stat().st_size)

    with Timer() as timer:

        digest = hash_file(
            str(file),
            args.algorithm
        )

    success(
        algorithm=args.algorithm.upper(),
        digest=digest,
        elapsed=timer.elapsed,
        source=file.name,
        size=size
    )


def main():

    show_banner()

    parser = build_parser()

    args = parser.parse_args()

    try:

        if args.text is not None:

            hash_text_mode(args)

        else:

            hash_file_mode(args)

    except KeyboardInterrupt:

        error("Interrupted by user.")

    except PermissionError:

        error("Permission denied.")

    except ValueError as exc:

        error(str(exc))

    except Exception as exc:

        error(f"Unexpected error: {exc}")


if __name__ == "__main__":

    main()
