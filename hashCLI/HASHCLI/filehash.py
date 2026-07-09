from pathlib import Path

from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from algorithms import create_hasher


CHUNK_SIZE = 8192


def hash_file(filename: str, algorithm: str) -> str:

    path = Path(filename)

    hasher = create_hasher(algorithm)

    total = path.stat().st_size

    with Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:

        task = progress.add_task("Hashing", total=total)

        with path.open("rb") as file:

            while True:

                chunk = file.read(CHUNK_SIZE)

                if not chunk:
                    break

                hasher.update(chunk)

                progress.update(task, advance=len(chunk))

    if algorithm.startswith("shake"):
        return hasher.hexdigest(64)

    return hasher.hexdigest()
