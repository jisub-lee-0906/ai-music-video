from __future__ import annotations


TRUE_SET = {"1", "true", "yes", "on", "y"}
FALSE_SET = {"0", "false", "no", "off", "n", ""}


def parse_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in TRUE_SET:
        return True
    if text in FALSE_SET:
        return False
    return default
