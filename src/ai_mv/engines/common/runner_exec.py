from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def call_with_retries(attempts: int, fn: Callable[[int], T], label: str, item_id: str) -> T:
    last: Exception | None = None
    for retry in range(max(1, attempts)):
        try:
            return fn(retry)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"{label} failed for {item_id}: {last}")

