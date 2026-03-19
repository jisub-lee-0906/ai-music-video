from __future__ import annotations

from ai_mv.core.contracts.intent_models import ProfileIntent
from ai_mv.core.profile_policy import resolve_profile_policy


_REQUIRED_FIELDS = (
    ("audio", "brief"),
    ("audio", "hook_brief"),
    ("visual", "brief"),
    ("visual", "negative"),
    ("mv", "story_world"),
    ("mv", "payoff_style"),
    ("mv", "outro_feel"),
    ("mv", "avoid"),
)


def validate_profile_brief_config(config: dict) -> None:
    missing = [f"{section}.{key}" for section, key in _REQUIRED_FIELDS if not _text(_section(config, section), key)]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"profile briefing fields missing: {joined}")


def build_profile_intent(config: dict) -> dict:
    validate_profile_brief_config(config)
    audio = _section(config, "audio")
    visual = _section(config, "visual")
    mv = _section(config, "mv")
    policy = resolve_profile_policy(config)
    intent = ProfileIntent(
        audio_intent={
            "language": _text(audio, "language") or "en",
            "brief": _text(audio, "brief"),
            "hook_brief": _text(audio, "hook_brief"),
            "tags": [str(x).strip() for x in audio.get("tags", []) if str(x).strip()] if isinstance(audio.get("tags", []), list) else [],
        },
        world_intent={
            "visual_intent": _text(visual, "brief"),
            "story_world": _text(mv, "story_world"),
            "action_vocabulary": _text(mv, "action_vocabulary"),
            "payoff_style": _text(mv, "payoff_style"),
            "heroine_invariants": _heroine_invariants(visual, mv),
            "world_invariants": _world_invariants(visual, mv),
            "location_families": _location_families(mv),
            "closeup_policy": _closeup_policy(visual, mv),
            "motion_policy": _motion_policy(visual, mv),
            "payoff_closeup_policy": _payoff_closeup_policy(mv),
            "resolved_profile_policy": dict(policy),
        },
        negative_intent={
            "visual_negative": _text(visual, "negative"),
            "mv_avoid": _text(mv, "avoid"),
        },
        escalation_intent={
            "chorus_payoff": _text(mv, "payoff_style"),
            "bridge_interrupt": _text(mv, "action_vocabulary"),
            "outro_residue": _text(mv, "outro_feel"),
        },
    )
    return {
        "audio_intent": dict(intent.audio_intent),
        "world_intent": dict(intent.world_intent),
        "negative_intent": dict(intent.negative_intent),
        "escalation_intent": dict(intent.escalation_intent),
        "resolved_profile_policy": dict(policy),
    }


def _section(config: dict, key: str) -> dict:
    node = config.get(key, {}) if isinstance(config, dict) else {}
    return node if isinstance(node, dict) else {}


def _text(node: dict, key: str) -> str:
    return str(node.get(key, "")).strip() if isinstance(node, dict) else ""


def _heroine_invariants(visual: dict, mv: dict) -> str:
    return _join_parts(
        [
            "same heroine throughout the video",
            _extract_fragment(_text(visual, "brief"), ("East Asian heroine", "young adult East Asian heroine", "female solo vocal", "lead")),
            _extract_fragment(_text(mv, "story_world"), ("same heroine",)),
        ]
    )


def _world_invariants(visual: dict, mv: dict) -> str:
    return _join_parts(
        [
            "one continuous world",
            _extract_fragment(_text(mv, "story_world"), ("same night", "one continuous", "continuous", "same emotional weather", "same luxurious pulse", "same momentum", "same rebellious force", "same electric pressure", "same suspended emotional current", "same sense of supernatural authority")),
            _extract_fragment(_text(visual, "brief"), ("readable", "center framing", "center-dominant", "heroine legible", "heroine readable")),
        ]
    )


def _location_families(mv: dict) -> list[str]:
    text = _text(mv, "story_world")
    marker = "families:"
    low = text.lower()
    if marker not in low:
        return []
    tail = text[low.index(marker) + len(marker) :]
    tail = tail.split(".", 1)[0]
    return [part.strip(" .") for part in tail.split(",") if part.strip(" .")][:8]


def _closeup_policy(visual: dict, mv: dict) -> str:
    visual_text = _text(visual, "brief").lower()
    payoff_text = _text(mv, "payoff_style").lower()
    if "one extreme close-up" in payoff_text:
        return "reserve direct close-up impact for payoff return shots"
    if "selective extreme close-up" in visual_text or "selective extreme close-ups" in visual_text:
        return "use selective close-ups only when the heroine remains readable and continuity-safe"
    if "extreme close-up" in visual_text:
        return "limit extreme close-ups to identity-sensitive or payoff shots"
    return "keep the heroine readable before close-up emphasis"


def _motion_policy(visual: dict, mv: dict) -> str:
    return _join_parts(
        [
            _extract_fragment(_text(mv, "action_vocabulary"), ("one clean motion", "one decisive motion idea", "one lucid movement", "one ceremonially clear action", "single-impact clauses", "compact physical beats")),
            _extract_fragment(_text(visual, "brief"), ("readable", "before extra motion", "before adding aggression", "before layering grit", "before adding effects")),
        ]
    ) or "favor one readable action per beat in a controlled world"


def _payoff_closeup_policy(mv: dict) -> str:
    text = _text(mv, "payoff_style").lower()
    if "one extreme close-up" in text:
        return "allow one decisive payoff close-up"
    if "extreme close-up" in text:
        return "allow limited payoff close-up emphasis"
    return "prefer posture and eye-line escalation over repeated close-up use"


def _extract_fragment(text: str, markers: tuple[str, ...]) -> str:
    raw = str(text).strip()
    low = raw.lower()
    for marker in markers:
        idx = low.find(marker.lower())
        if idx >= 0:
            return raw[idx:].split(".", 1)[0].strip(" ,.")
    return ""


def _join_parts(parts: list[str]) -> str:
    return ", ".join(part.strip(" ,.") for part in parts if str(part).strip(" ,."))
