from __future__ import annotations


def with_defaults(plan: dict, defaults: dict) -> dict:
    if not isinstance(plan, dict):
        raise RuntimeError("plan must be dict")
    out = dict(defaults)
    out.update(plan)
    return out
