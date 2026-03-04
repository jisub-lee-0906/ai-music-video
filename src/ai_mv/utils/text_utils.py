from __future__ import annotations


def compact(text: str) -> str:
    return " ".join((text or "").split())

