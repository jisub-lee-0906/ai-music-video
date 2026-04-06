from __future__ import annotations

from collections.abc import Mapping


_LEGACY_REQUIRED_FIELDS = (
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
    if _has_minimal_profile(config):
        missing = [key for key in ("prompt", "genre", "voice", "language") if not _top_text(config, key)]
        if missing:
            raise ValueError(f"director brief fields missing: {', '.join(missing)}")
        return
    missing = [f"{section}.{key}" for section, key in _LEGACY_REQUIRED_FIELDS if not _text(_section(config, section), key)]
    if missing:
        raise ValueError(f"director brief fields missing: {', '.join(missing)}")


def build_director_brief_intent(config: dict) -> dict:
    validate_director_brief_config(config)
    if _has_minimal_profile(config):
        return _build_minimal_brief_intent(config)
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


def materialize_profile_config(config: dict) -> None:
    if not _has_minimal_profile(config):
        return
    prompt = _top_text(config, "prompt")
    genre = _top_text(config, "genre")
    voice = _top_text(config, "voice")
    language = _top_text(config, "language") or "ko"
    audio = config.setdefault("audio", {})
    if isinstance(audio, dict):
        audio["language"] = language
        audio["brief"] = prompt
        audio["hook_brief"] = prompt
        audio.setdefault("genre_head", genre)
        audio.setdefault("vocal_profile", voice)
        audio.setdefault("vocal_tone", voice)
    visual = config.setdefault("visual", {})
    if isinstance(visual, dict):
        visual.setdefault("story_premise", prompt)
        visual.setdefault("world_rules", "")
        visual.setdefault("heroine_arc", "Keep one readable direction across the song.")
        visual.setdefault("forbidden_story_moves", "")
    character = config.setdefault("character", {})
    if isinstance(character, dict):
        character.setdefault("identity_core", _identity_core_from_voice(voice))
        character.setdefault("ref_subject_intro", _ref_subject_intro_from_voice(voice))
        character.setdefault("identity_hooks", [])
        character.setdefault("anchor_wardrobe_guidance", _anchor_wardrobe_guidance(config))
        character.setdefault("anchor_avoid", "")


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


def _top_text(config: dict, key: str) -> str:
    return str(config.get(key, "")).strip() if isinstance(config, dict) else ""


def _text(node: dict, key: str) -> str:
    return str(node.get(key, "")).strip() if isinstance(node, dict) else ""


def _str_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _has_minimal_profile(config: dict) -> bool:
    if not isinstance(config, dict):
        return False
    keys = {"prompt", "genre", "voice", "language"}
    return any(str(config.get(key, "")).strip() for key in keys)


def _build_minimal_brief_intent(config: dict) -> dict:
    prompt = _top_text(config, "prompt")
    genre = _top_text(config, "genre")
    voice = _top_text(config, "voice")
    language = _top_text(config, "language") or "ko"
    style = " ".join(part for part in (genre, voice, prompt) if part).strip()
    subject_intro = _ref_subject_intro_from_voice(voice)
    identity_core = _identity_core_from_voice(voice)
    anchor_subject = _anchor_subject(config)
    anchor_hair = _anchor_text(config, "anchor_hair")
    anchor_top = _anchor_text(config, "anchor_top")
    anchor_bottom = _anchor_text(config, "anchor_bottom")
    anchor_shoes = _anchor_text(config, "anchor_shoes")
    anchor_pose = _anchor_text(config, "anchor_pose") or "full-body standing pose, slight side angle, both hands visible, shoes fully visible"
    anchor_background = _anchor_text(config, "anchor_background") or "plain neutral studio background, no props, no environmental elements"
    section_roles = _generic_section_story_roles(prompt)
    section_events = _generic_section_event_scripts(prompt)
    return {
        "brief_name": str(config.get("brief", "")).strip() or "director_brief_example",
        "identity_core": identity_core,
        "identity_hooks": [],
        "anchor_wardrobe_guidance": _anchor_wardrobe_guidance(config),
        "anchor_avoid": "",
        "ref_subject_intro": subject_intro,
        "ref_continuity_guidance": "Keep the same vocalist identity and stable single-subject continuity.",
        "style_contract": style,
        "world_core": "",
        "time_anchor": "at night" if "night" in prompt.lower() else "",
        "story_premise": prompt,
        "world_rules": "",
        "heroine_arc": "Keep one readable direction across the song.",
        "forbidden_story_moves": "",
        "section_story_roles": section_roles,
        "section_event_scripts": section_events,
        "section_grammar": section_roles,
        "wan_negative": _DEFAULT_WAN_NEGATIVE,
        "audio_language": language,
        "audio_brief": prompt,
        "audio_hook_brief": prompt,
        "audio_hook_english_fragments": [],
        "visual_brief": prompt,
        "visual_negative": "",
        "story_world": "",
        "action_vocabulary": "",
        "payoff_style": "",
        "outro_feel": "",
        "avoid": "",
        "camera_bias": "",
        "lighting_bias": "",
        "shadow_bias": "",
        "motion_bias": "",
        "transition_bias": "",
        "ref_frame_style": "natural cinematic music-video keyframe with grounded environmental realism",
        "wan_motion_style": "natural motion that stays connected between the two keyframes",
        "motif_families": [],
        "profile_prompt": prompt,
        "profile_genre": genre,
        "profile_voice": voice,
        "anchor_subject": anchor_subject,
        "anchor_hair": anchor_hair,
        "anchor_top": anchor_top,
        "anchor_bottom": anchor_bottom,
        "anchor_shoes": anchor_shoes,
        "anchor_pose": anchor_pose,
        "anchor_background": anchor_background,
    }


def _ref_subject_intro_from_voice(voice: str) -> str:
    low = voice.lower()
    if "female" in low:
        return "The same female vocalist"
    if "male" in low:
        return "The same male vocalist"
    if "duo" in low or "group" in low or "mixed" in low:
        return "The same vocal act"
    return "The same vocalist"


def _identity_core_from_voice(voice: str) -> str:
    cleaned = " ".join(str(voice).strip().split())
    if cleaned:
        return f"same vocalist, {cleaned}"
    return "same vocalist"


def _anchor_text(config: dict, key: str) -> str:
    return str(config.get(key, "")).strip() if isinstance(config, dict) else ""


def _anchor_subject(config: dict) -> str:
    explicit = _anchor_text(config, "anchor_subject")
    if explicit:
        return explicit
    voice = _top_text(config, "voice").lower()
    if "female" in voice:
        return "pretty young Korean female idol in her 20s"
    if "male" in voice:
        return "handsome young Korean male idol in his 20s"
    return "young Korean idol performer in their 20s"


def _anchor_wardrobe_guidance(config: dict) -> str:
    parts = [
        _anchor_text(config, "anchor_top"),
        _anchor_text(config, "anchor_bottom"),
        _anchor_text(config, "anchor_shoes"),
    ]
    return ", ".join(part for part in parts if part)


def _generic_section_story_roles(prompt: str) -> dict[str, str]:
    mood = _generic_visual_mood(prompt)
    return {
        "Intro": f"Establish the protagonist and world with a {mood} opening image.",
        "Verse 1": "Introduce the first readable environment and emotional state through grounded physical behavior.",
        "Verse 2": "Carry the same emotional thread into a new but connected place without breaking continuity.",
        "Pre-Chorus": "Tighten tension and reduce space before the release.",
        "Chorus": "Open the frame into the clearest emotional release image.",
        "Bridge": "Interrupt the movement with a more stripped-back or intimate visual turn.",
        "Final Chorus": "Deliver the widest and most memorable release image with stronger forward momentum.",
        "Outro": "Leave one final after-image that resolves the sequence without overexplaining it.",
    }


def _generic_section_event_scripts(prompt: str) -> dict[str, list[str]]:
    motif = _generic_prompt_motif(prompt)
    return {
        "Intro": [
            f"She appears alone inside the first {motif} space of the sequence.",
            "She settles into the emotional tone before the movement begins.",
        ],
        "Verse 1": [
            "She interacts with the first grounded environment detail in a natural everyday way.",
            "She moves through the same area with a small but readable change in posture or direction.",
            "She continues forward while keeping one visual detail from the previous shot alive.",
        ],
        "Verse 2": [
            "She reaches a different but connected environment that expands the same emotional thread.",
            "She keeps moving while one physical object or texture carries over from the last location.",
            "She lands in a clearer visual state before the next transition.",
        ],
        "Pre-Chorus": [
            "She slows down or pauses briefly as the tension gathers.",
            "She commits toward the next emotional release without breaking continuity.",
        ],
        "Chorus": [
            "She enters the strongest and most open image of the current sequence.",
            "She keeps the energy alive with a clearer gesture, stride, or performance beat.",
            "She lands the moment in a readable visual payoff.",
        ],
        "Bridge": [
            "She compresses into a quieter or more isolated moment.",
            "She regains direction just before the final release.",
        ],
        "Final Chorus": [
            "She enters the widest release image of the song.",
            "She carries the release through a stronger forward movement or performance beat.",
            "She leaves the moment with a clear sense of emotional resolution.",
        ],
        "Outro": [
            "The final image lingers after she has already emotionally moved through the scene.",
        ],
    }


def _generic_visual_mood(prompt: str) -> str:
    low = str(prompt).lower()
    if any(token in low for token in ("rain", "wet", "night", "lonely", "late-night", "late night")):
        return "moody late-night"
    if any(token in low for token in ("anger", "rebell", "fire", "raw", "shout")):
        return "charged and restless"
    if any(token in low for token in ("dream", "memory", "float", "fade")):
        return "dreamlike but grounded"
    return "grounded cinematic"


def _generic_prompt_motif(prompt: str) -> str:
    low = str(prompt).lower()
    if any(token in low for token in ("city", "street", "night", "rain", "wet")):
        return "city-night"
    if any(token in low for token in ("club", "stage", "perform", "synth", "band")):
        return "performance"
    if any(token in low for token in ("room", "diner", "cafe", "apartment")):
        return "interior"
    return "real-world"
