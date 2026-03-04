from __future__ import annotations


def with_defaults(plan: dict, defaults: dict) -> dict:
    out = dict(defaults)
    out.update(plan or {})
    return out

