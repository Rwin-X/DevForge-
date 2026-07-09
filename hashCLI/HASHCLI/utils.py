from pathlib import Path


def file_size(path: str) -> int:

    return Path(path).stat().st_size


def readable_size(size: int) -> str:

    units = ["B", "KB", "MB", "GB", "TB"]

    value = float(size)

    for unit in units:

        if value < 1024:

            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} PB"
