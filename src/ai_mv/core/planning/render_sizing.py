from __future__ import annotations

import math



def calculate_render_count(duration_sec: float) -> int:
    duration_sec = float(duration_sec or 0.0)
    if duration_sec <= 6.5:
        return 1
    if duration_sec <= 13.0:
        return 2
    if duration_sec <= 19.5:
        return 3
    return min(4, max(1, int(math.ceil(duration_sec / 6.0))))
