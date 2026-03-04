from __future__ import annotations

import time


def now_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S")

