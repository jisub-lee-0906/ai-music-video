from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def with_retry(fn: Callable[[], T], attempts: int = 3, delay: float = 1.0) -> T:
    last: Exception | None = None
    for idx in range(attempts):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover
            last = exc
            if idx + 1 < attempts:
                time.sleep(delay * (2**idx))
    raise last if last else RuntimeError("retry failed")

