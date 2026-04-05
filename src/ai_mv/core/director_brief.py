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

_DEFAULT_SECTION_EVENT_SCRIPTS = {
    "Intro": [
        "She enters through the first public boundary and commits to the connected night world.",
        "She clears the threshold and leaves the outside behind in one readable step.",
    ],
    "Verse 1": [
        "She takes the route outside the station and lets the street-side path claim her line.",
        "She keeps the same route alive on the sidewalk edge instead of drifting into the road.",
        "She arrives at the next sidewalk-side beat with the road still held beside her.",
    ],
    "Verse 2": [
        "She re-enters the route from a slightly changed street-side angle without breaking continuity.",
        "She keeps the sidewalk-side carry alive through the same connected block.",
        "She sets the next sidewalk-side stride so the path already feels chosen before the cut.",
    ],
    "Pre-Chorus": [
        "She reaches a gate or threshold where the route could widen.",
        "She commits past the threshold so the next move is already inevitable.",
    ],
    "Chorus": [
        "She begins a visible crossing event instead of another neutral walk.",
        "She keeps the crossing alive inside the same open space.",
        "She carries the crossing into a readable next-state handoff.",
    ],
    "Bridge": [
        "She compresses her movement into a shorter, tighter step without fully stopping.",
        "She regains a forward line inside the same compressed world.",
    ],
    "Final Chorus": [
        "She enters the final release as a visible crossing event.",
        "She keeps the crossing alive instead of resetting to a centered walk.",
        "She carries the release to the next crossing state with the open road held beside her.",
        "She leaves the crossing behind in a wider forward departure.",
    ],
    "Outro": [
        "She is already gone, but the route still holds the shape of her movement.",
    ],
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
    section_event_scripts = _section_event_scripts(visual.get("section_event_scripts", {}))
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
        "time_anchor": _time_anchor(_text(visual, "story_premise"), world_rules),
        "story_premise": _text(visual, "story_premise"),
        "world_rules": world_rules,
        "heroine_arc": _text(visual, "heroine_arc"),
        "forbidden_story_moves": _text(visual, "forbidden_story_moves"),
        "section_story_roles": section_roles,
        "section_event_scripts": section_event_scripts,
        "section_grammar": section_roles,
        "wan_negative": _text(visual, "wan_negative") or _DEFAULT_WAN_NEGATIVE,
        "audio_language": _text(audio, "language") or "ko",
        "audio_brief": _text(audio, "brief"),
        "audio_hook_brief": _text(audio, "hook_brief"),
        "audio_hook_english_fragments": _str_list(audio.get("hook_english_fragments", [])),
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


def _section_event_scripts(raw: object) -> dict[str, list[str]]:
    out = {key: list(value) for key, value in _DEFAULT_SECTION_EVENT_SCRIPTS.items()}
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            label = str(key).strip()
            if not label:
                continue
            if isinstance(value, list):
                events = [str(item).strip() for item in value if str(item).strip()]
            else:
                text = str(value).strip()
                events = [text] if text else []
            if events:
                out[label] = events
    alias_pairs = {
        "Pre-Chorus": ["Pre-Chorus 2"],
        "Chorus": ["Chorus 2"],
    }
    for canonical, aliases in alias_pairs.items():
        events = list(out.get(canonical, []))
        if not events:
            continue
        for alias in aliases:
            out.setdefault(alias, list(events))
    return out


def _time_anchor(story_premise: str, world_rules: str) -> str:
    text = f"{story_premise} {world_rules}".lower()
    if "late-night" in text or "late night" in text or "night world" in text or "at night" in text or "night" in text:
        return "at night"
    return ""


def _section(config: dict, key: str) -> dict:
    node = config.get(key, {}) if isinstance(config, dict) else {}
    return node if isinstance(node, dict) else {}


def _text(node: dict, key: str) -> str:
    return str(node.get(key, "")).strip() if isinstance(node, dict) else ""


def _str_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]
