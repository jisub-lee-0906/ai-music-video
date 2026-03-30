from __future__ import annotations

from collections.abc import Mapping


_REQUIRED_FIELDS = (
    ("audio", "brief"),
    ("audio", "hook_brief"),
    ("visual", "brief"),
    ("visual", "negative"),
    ("mv", "story_world"),
    ("mv", "payoff_style"),
    ("mv", "outro_feel"),
    ("mv", "avoid"),
    ("character", "identity_core"),
    ("director", "target_style"),
    ("director", "world_core"),
    ("director", "camera_bias"),
    ("director", "lighting_bias"),
    ("director", "motion_bias"),
)

_DEFAULT_SECTION_GRAMMAR = {
    "Intro": "threshold setup and motif introduction",
    "Verse 1": "object-led narrow world",
    "Verse 2": "object-led world variation",
    "Pre-Chorus": "threshold and anticipation",
    "Chorus": "open world with wider motion",
    "Bridge": "compressed or reframed interruption",
    "Final Chorus": "motif system peak",
    "Outro": "residual world after-image",
}


def validate_director_brief_config(config: dict) -> None:
    missing = [f"{section}.{key}" for section, key in _REQUIRED_FIELDS if not _text(_section(config, section), key)]
    if missing:
        raise ValueError(f"director brief fields missing: {', '.join(missing)}")


def build_director_brief_intent(config: dict) -> dict:
    validate_director_brief_config(config)
    audio = _section(config, "audio")
    visual = _section(config, "visual")
    mv = _section(config, "mv")
    character = _section(config, "character")
    director = _section(config, "director")
    return {
        "brief_name": str(config.get("brief", "")).strip() or "director_brief_example",
        "identity_core": _text(character, "identity_core"),
        "identity_hooks": _str_list(character.get("identity_hooks", [])),
        "anchor_wardrobe_guidance": _text(character, "anchor_wardrobe_guidance"),
        "anchor_avoid": _text(character, "anchor_avoid"),
        "ref_subject_intro": _text(character, "ref_subject_intro"),
        "ref_continuity_guidance": _text(character, "ref_continuity_guidance"),
        "style_contract": _text(director, "target_style"),
        "world_core": _text(director, "world_core") or _text(mv, "story_world"),
        "camera_bias": _text(director, "camera_bias"),
        "lighting_bias": _text(director, "lighting_bias"),
        "shadow_bias": _text(director, "shadow_bias"),
        "motion_bias": _text(director, "motion_bias"),
        "transition_bias": _text(director, "transition_bias"),
        "ref_frame_style": _text(director, "ref_frame_style"),
        "wan_motion_style": _text(director, "wan_motion_style"),
        "wan_negative": _text(director, "wan_negative"),
        "motif_families": _str_list(director.get("motif_families", [])) or _derive_motif_families(mv, director),
        "section_grammar": _section_grammar(director.get("section_grammar", {})),
        "audio_language": _text(audio, "language") or "ko",
        "audio_brief": _text(audio, "brief"),
        "audio_hook_brief": _text(audio, "hook_brief"),
        "visual_brief": _text(visual, "brief"),
        "visual_negative": _text(visual, "negative"),
        "story_world": _text(mv, "story_world"),
        "action_vocabulary": _text(mv, "action_vocabulary"),
        "payoff_style": _text(mv, "payoff_style"),
        "outro_feel": _text(mv, "outro_feel"),
        "avoid": _text(mv, "avoid"),
    }


def _derive_motif_families(mv: dict, director: dict) -> list[str]:
    raw = _str_list(director.get("motif_examples", []))
    if raw:
        return raw
    text = _text(mv, "story_world")
    parts = [chunk.strip(" .") for chunk in text.replace(" and ", ", ").split(",") if chunk.strip(" .")]
    return parts[:6]


def _section_grammar(raw: object) -> dict[str, str]:
    grammar = dict(_DEFAULT_SECTION_GRAMMAR)
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            label = str(key).strip()
            desc = str(value).strip()
            if label and desc:
                grammar[label] = desc
    return grammar


def _section(config: dict, key: str) -> dict:
    node = config.get(key, {}) if isinstance(config, dict) else {}
    return node if isinstance(node, dict) else {}


def _text(node: dict, key: str) -> str:
    return str(node.get(key, "")).strip() if isinstance(node, dict) else ""


def _str_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]
