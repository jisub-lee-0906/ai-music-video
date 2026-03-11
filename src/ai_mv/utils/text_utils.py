from __future__ import annotations

import unicodedata

def parse_size(size: str) -> tuple[int, int]:
    w, h = str(size).split("x", 1)
    return int(w), int(h)


def parse_target(target: str) -> tuple[int, int, int]:
    size, fps = str(target).split("@", 1)
    w, h = parse_size(size)
    return w, h, int(fps)


def ensure_16_9(width: int, height: int) -> None:
    if width * 9 != height * 16:
        raise ValueError(f"non-16:9 size: {width}x{height}")


def ensure_positive_size(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid size: {width}x{height}")


def ascii_safe_text(text: str) -> str:
    src = str(text or "")
    table = str.maketrans(
        {
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "—": "-",
            "–": "-",
            "…": "...",
            "\u00a0": " ",
        }
    )
    normalized = unicodedata.normalize("NFKD", src.translate(table))
    return normalized.encode("ascii", "ignore").decode("ascii")
