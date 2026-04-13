from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageInput:
    run_id: str
    config: dict[str, Any]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageOutput:
    stage: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    error: str = ""

