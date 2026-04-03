from __future__ import annotations

from collections.abc import Mapping


_REQUIRED_FIELDS = (
    ("audio", "brief"),
    ("audio", "hook_brief"),
    ("visual", "story_premise"),
    ("visual", "world_rules"),
    ("visual", "heroine_arc"),
    ("visual", "forbidden_story_moves"),
    ("character", "identity_core"),
)

_DEFAULT_SECTION_STORY_ROLES = {
    "Intro": "The heroine crosses the first boundary into the connected night world.",
    "Verse 1": "She moves deeper into the same world and lets the route define her direction.",
    "Verse 2": "She varies her path inside the same world without breaking continuity.",
    "Pre-Chorus": "She hesitates at a wider opening before committing to the next move.",
    "Chorus": "She releases forward inside the same world with readable physical movement.",
    "Bridge": "She compresses briefly without fully stopping, then regains direction.",
    "Final Chorus": "She crosses into the widest forward release the world can hold.",
    "Outro": "The world keeps her after-image after she has already passed through.",
}

_DEFAULT_IDENTITY_HOOKS = [
    "airy see-through bangs with high ponytail",
    "soft face-framing strands around the jawline",
    "polished ivory and navy off-duty idol silhouette with a short casual outer layer",
    "subtle silver jewelry accent",
]

_DEFAULT_WAN_NEGATIVE = (
    "morphing, melting, static, anatomy collapse, warped hands, extra limbs, identity drift, toy-like cgi"
)


def validate_director_brief_config(config: dict) -> None:
    missing = [f"{section}.{key}" for section, key in _REQUIRED_FIELDS if not _text(_section(config, section), key)]
    if missing:
        raise ValueError(f"director brief fields missing: {', '.join(missing)}")


def build_director_brief_intent(config: dict) -> dict:
    validate_director_brief_config(config)
    audio = _section(config, "audio")
    visual = _section(config, "visual")
    character = _section(config, "character")
    style = _compose_style_contract(audio, visual)
    world_rules = _text(visual, "world_rules")
    section_roles = _section_story_roles(visual.get("section_story_roles", {}))
    return {
        "brief_name": str(config.get("brief", "")).strip() or "director_brief_example",
        "identity_core": _text(character, "identity_core"),
        "identity_hooks": _str_list(character.get("identity_hooks", [])) or list(_DEFAULT_IDENTITY_HOOKS),
        "anchor_wardrobe_guidance": _text(character, "anchor_wardrobe_guidance"),
        "anchor_avoid": _text(character, "anchor_avoid"),
        "ref_subject_intro": _text(character, "ref_subject_intro") or "The same Korean female idol",
        "ref_continuity_guidance": _text(
            character,
            "ref_continuity_guidance",
        )
        or "Keep the same heroine identity, realistic facial structure, consistent hair silhouette, and stable wardrobe continuity.",
        "style_contract": style,
        "world_core": world_rules,
        "story_premise": _text(visual, "story_premise"),
        "world_rules": world_rules,
        "heroine_arc": _text(visual, "heroine_arc"),
        "forbidden_story_moves": _text(visual, "forbidden_story_moves"),
        "section_story_roles": section_roles,
        "section_grammar": section_roles,
        "wan_negative": _text(visual, "wan_negative") or _DEFAULT_WAN_NEGATIVE,
        "audio_language": _text(audio, "language") or "ko",
        "audio_brief": _text(audio, "brief"),
        "audio_hook_brief": _text(audio, "hook_brief"),
        "visual_brief": _text(visual, "story_premise"),
        "visual_negative": _text(visual, "forbidden_story_moves"),
        "story_world": world_rules,
        "action_vocabulary": "",
        "payoff_style": "",
        "outro_feel": "",
        "avoid": _text(visual, "forbidden_story_moves"),
        "camera_bias": "",
        "lighting_bias": "",
        "shadow_bias": "",
        "motion_bias": "",
        "transition_bias": "",
        "ref_frame_style": "natural cinematic music-video keyframe with grounded environmental realism",
        "wan_motion_style": "natural motion that stays connected between the two keyframes",
        "motif_families": [],
    }


def _compose_style_contract(audio: dict, visual: dict) -> str:
    tags = _str_list(audio.get("tags", []))
    audio_style = _text(audio, "brief")
    visual_premise = _text(visual, "story_premise")
    parts = [
        "cinematic live-action Korean pop music video with premium realism and stable human continuity",
        visual_premise,
        audio_style,
        ", ".join(tags[:3]) if tags else "",
    ]
    return " ".join(part.strip() for part in parts if part.strip())


def _section_story_roles(raw: object) -> dict[str, str]:
    out = dict(_DEFAULT_SECTION_STORY_ROLES)
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            label = str(key).strip()
            desc = str(value).strip()
            if label and desc:
                out[label] = desc
    alias_pairs = {
        "Pre-Chorus": ["Pre-Chorus 2"],
        "Chorus": ["Chorus 2"],
    }
    for canonical, aliases in alias_pairs.items():
        desc = str(out.get(canonical, "")).strip()
        if not desc:
            continue
        for alias in aliases:
            out.setdefault(alias, desc)
    return out


def _section(config: dict, key: str) -> dict:
    node = config.get(key, {}) if isinstance(config, dict) else {}
    return node if isinstance(node, dict) else {}


def _text(node: dict, key: str) -> str:
    return str(node.get(key, "")).strip() if isinstance(node, dict) else ""


def _str_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]
