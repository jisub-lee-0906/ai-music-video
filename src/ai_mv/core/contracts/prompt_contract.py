from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PromptPlan:
    shot_id: str
    section: str
    prompt: str
    negative_prompt: str
    duration_sec: float
    seed: int

