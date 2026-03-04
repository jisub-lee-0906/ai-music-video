from __future__ import annotations

from ai_mv.core.orchestration.stage_registry import ordered_stages


def schedule() -> list[tuple[str, callable]]:
    return ordered_stages()

