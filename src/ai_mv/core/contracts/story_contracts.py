from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LyricBeatContract:
    beat_id: str
    section_name: str
    section_label: str
    line_refs: list[int] = field(default_factory=list)
    literal_image: str = ""
    visible_action: str = ""
    emotional_turn: str = ""
    continuity_anchor: str = ""
    payoff_role: str = ""
    repeat_variant_of: str = ""
    start_sec: float = 0.0
    end_sec: float = 0.0


@dataclass
class LyricsTimelineContract:
    sections: list[dict] = field(default_factory=list)


@dataclass
class VisualStoryBible:
    hero_identity_lock: str = ""
    world_rules: str = ""
    recurring_location_families: list[str] = field(default_factory=list)
    forbidden_drift: list[str] = field(default_factory=list)
    lyric_beats: list[dict] = field(default_factory=list)
    section_progression: list[dict] = field(default_factory=list)
    repeat_escalation_rules: list[str] = field(default_factory=list)


@dataclass
class ShotTimelineContract:
    master_anchor: dict = field(default_factory=dict)
    shots: list[dict] = field(default_factory=list)
