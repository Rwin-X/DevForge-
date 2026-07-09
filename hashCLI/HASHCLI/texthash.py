from algorithms import create_hasher


def hash_text(text: str, algorithm: str) -> str:

    hasher = create_hasher(algorithm)

    hasher.update(text.encode("utf-8"))

    if algorithm.startswith("shake"):
        return hasher.hexdigest(64)

    return hasher.hexdigest()
