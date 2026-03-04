from __future__ import annotations

import hashlib
import json


def evaluate_quality(payload: dict) -> float:
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    head = hashlib.sha256(data).hexdigest()[:8]
    return int(head, 16) / float(0xFFFFFFFF)

