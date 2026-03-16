from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileIntent:
    audio_intent: dict
    world_intent: dict
    negative_intent: dict
    escalation_intent: dict
