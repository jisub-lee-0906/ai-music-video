from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileIntent:
    audio_intent: dict
    world_intent: dict
    negative_intent: dict
    escalation_intent: dict


@dataclass(frozen=True)
class VisualBriefContract:
    hero_identity_lock: str
    world_rules: str
    recurring_location_families: tuple[str, ...]
    allowed_visual_variation: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    section_briefs: tuple[dict, ...]


@dataclass(frozen=True)
class ShotPlanContract:
    master_anchor: dict
    shots: tuple[dict, ...]
