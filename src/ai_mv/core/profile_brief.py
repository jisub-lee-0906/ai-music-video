from __future__ import annotations


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


def build_profile_brief(config: dict) -> dict[str, str]:
    validate_profile_brief_config(config)
    audio = _section(config, "audio")
    visual = _section(config, "visual")
    mv = _section(config, "mv")
    action = _text(mv, "action_vocabulary")
    profile_summary = _join_sentences(
        _text(audio, "brief"),
        _text(visual, "brief"),
        _text(mv, "story_world"),
    )
    return {
        "profile_summary": profile_summary,
        "audio_direction": _join_sentences(
            _text(audio, "brief"),
        ),
        "hook_direction": _join_sentences(
            _text(audio, "hook_brief"),
            _text(mv, "payoff_style"),
        ),
        "visual_direction": _join_sentences(
            _text(visual, "brief"),
            _text(mv, "story_world"),
            action,
        ),
        "negative_direction": _join_sentences(_text(visual, "negative"), _text(mv, "avoid")),
    }


def resolve_style_guidance(config: dict) -> str:
    validate_profile_brief_config(config)
    audio = _section(config, "audio")
    visual = _section(config, "visual")
    mv = _section(config, "mv")
    return " ".join(
        [
            _text(audio, "brief"),
            _text(visual, "brief"),
            _text(mv, "story_world"),
            _text(mv, "action_vocabulary"),
            _text(mv, "payoff_style"),
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
