"""
HashCLI Algorithms Module
Author: RWIN-x
"""

import hashlib

ALGORITHMS = {
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


def available_algorithms() -> list[str]:
    return sorted(ALGORITHMS.keys())


def create_hasher(name: str):
    name = name.lower()

    if name not in ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {name}")

    return ALGORITHMS[name]()
