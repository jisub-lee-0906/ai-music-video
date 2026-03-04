from __future__ import annotations

import json


def parse_json_obj(text: str) -> dict:
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("JSON object expected")
    return obj

