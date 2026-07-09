#!/usr/bin/env python3

import argparse
import hashlib
import sys
from pathlib import Path

SUPPORTED_ALGORITHMS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha224": hashlib.sha224,
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
    "sha3_224": hashlib.sha3_224,
    "sha3_256": hashlib.sha3_256,
    "sha3_384": hashlib.sha3_384,
    "sha3_512": hashlib.sha3_512,
    "blake2b": hashlib.blake2b,
    "blake2s": hashlib.blake2s,
    "shake128": hashlib.shake_128,
    "shake256": hashlib.shake_256,
}


def hash_text(algorithm: str, text: str) -> str:
    hasher = SUPPORTED_ALGORITHMS[algorithm]()
    hasher.update(text.encode("utf-8"))

    if algorithm.startswith("shake"):
        return hasher.hexdigest(64)

    return hasher.hexdigest()


def hash_file(algorithm: str, filename: str) -> str:
    hasher = SUPPORTED_ALGORITHMS[algorithm]()

    with open(filename, "rb") as file:
        while True:
            chunk = file.read(8192)
            if not chunk:
                break
            hasher.update(chunk)

    if algorithm.startswith("shake"):
        return hasher.hexdigest(64)

    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        prog="HashCLI",
        description="Fast Hash Generator"
    )

    parser.add_argument(
        "-a",
        "--algorithm",
        required=True,
        choices=SUPPORTED_ALGORITHMS.keys(),
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

    args = parser.parse_args()

    try:
        if args.text:
            digest = hash_text(args.algorithm, args.text)

        else:
            if not Path(args.file).exists():
                print("Error: File not found.")
                sys.exit(1)

            digest = hash_file(args.algorithm, args.file)

        print()
        print("=" * 60)
        print(f"Algorithm : {args.algorithm}")
        print(f"Hash      : {digest}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
