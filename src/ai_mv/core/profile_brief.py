from __future__ import annotations

from ai_mv.core.contracts.intent_models import ProfileIntent


_REQUIRED_FIELDS = (
    ("audio", "brief"),
    ("audio", "hook_brief"),
    ("visual", "brief"),
    ("visual", "negative"),
    ("mv", "story_world"),
    ("mv", "payoff_style"),
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
    intent = ProfileIntent(
        audio_intent={
            "language": _text(audio, "language") or "en",
            "brief": _text(audio, "brief"),
            "hook_brief": _text(audio, "hook_brief"),
            "tags": [str(x).strip() for x in audio.get("tags", []) if str(x).strip()] if isinstance(audio.get("tags", []), list) else [],
        },
        world_intent={
            "visual_brief": _text(visual, "brief"),
            "story_world": _text(mv, "story_world"),
            "action_vocabulary": _text(mv, "action_vocabulary"),
            "payoff_style": _text(mv, "payoff_style"),
        },
        negative_intent={
            "visual_negative": _text(visual, "negative"),
            "mv_avoid": _text(mv, "avoid"),
        },
        escalation_intent={
            "chorus_payoff": _text(mv, "payoff_style"),
            "bridge_interrupt": _text(mv, "action_vocabulary"),
            "outro_residue": _text(mv, "avoid"),
        },
    )
    return {
        "audio_intent": dict(intent.audio_intent),
        "world_intent": dict(intent.world_intent),
        "negative_intent": dict(intent.negative_intent),
        "escalation_intent": dict(intent.escalation_intent),
    }


def build_profile_brief(config: dict) -> dict[str, str]:
    intent = build_profile_intent(config)
    audio = intent["audio_intent"]
    world = intent["world_intent"]
    negative = intent["negative_intent"]
    profile_summary = _join_sentences(
        audio["brief"],
        world["visual_brief"],
        world["story_world"],
    )
    return {
        "profile_intent": intent,
        "profile_summary": profile_summary,
        "audio_direction": _join_sentences(
            audio["brief"],
        ),
        "hook_direction": _join_sentences(
            audio["hook_brief"],
        ),
        "visual_direction": _join_sentences(
            world["visual_brief"],
            world["story_world"],
            world["action_vocabulary"],
            world["payoff_style"],
        ),
        "negative_direction": _join_sentences(negative["visual_negative"], negative["mv_avoid"]),
    }


def resolve_style_guidance(config: dict) -> str:
    intent = build_profile_intent(config)
    audio = intent["audio_intent"]
    world = intent["world_intent"]
    return " ".join(
        [
            audio["brief"],
            world["visual_brief"],
            world["story_world"],
            world["action_vocabulary"],
            world["payoff_style"],
        ]
    ).strip()


def _section(config: dict, key: str) -> dict:
    node = config.get(key, {}) if isinstance(config, dict) else {}
    return node if isinstance(node, dict) else {}


def _text(node: dict, key: str) -> str:
    return str(node.get(key, "")).strip() if isinstance(node, dict) else ""


def _join_sentences(*parts: str) -> str:
    vals = [str(part).strip().rstrip(". ") for part in parts if str(part).strip()]
    return ". ".join(vals)
