from __future__ import annotations


def clean_prompt(text: str) -> str:
    return " ".join((text or "").split()).strip()

