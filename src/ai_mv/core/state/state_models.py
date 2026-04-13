from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RunState:
    run_id: str
    status: str = "running"
    completed_stages: list[str] = field(default_factory=list)

