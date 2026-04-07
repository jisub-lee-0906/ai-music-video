from __future__ import annotations

from collections.abc import Mapping


_LEGACY_REQUIRED_FIELDS = (
    ("audio", "brief"),
    ("audio", "hook_brief"),
    ("visual", "story_premise"),
    ("visual", "world_rules"),
    ("visual", "forbidden_story_moves"),
    ("character", "identity_core"),
)

_DEFAULT_SECTION_STORY_ROLES = {
    "Intro": "The performer enters the first grounded image of the sequence.",
    "Verse 1": "The performer settles into the world and establishes a readable direction.",
    "Verse 2": "The performer varies the route without breaking continuity.",
    "Pre-Chorus": "The performer hesitates at a wider opening before committing to the next move.",
    "Chorus": "The performer releases forward with a readable physical change.",
    "Bridge": "The performer compresses briefly without fully stopping, then regains direction.",
    "Final Chorus": "The performer reaches the widest and clearest release image.",
    "Outro": "The world keeps the after-image after the performer has already moved through.",
}

_DEFAULT_SECTION_EVENT_SCRIPTS = {
    "Intro": [
        "The performer enters the first grounded location and commits to the sequence.",
        "The performer clears the first transition in one readable step.",
    ],
    "Verse 1": [
        "The performer takes the first readable route through the location.",
        "The performer keeps the route alive instead of resetting to a neutral pose.",
        "The performer arrives at the next beat with the same direction intact.",
    ],
    "Verse 2": [
        "The performer re-enters the route from a slightly changed angle without breaking continuity.",
        "The performer keeps the carry alive through the same connected place.",
        "The performer sets the next move so the path already feels chosen before the cut.",
    ],
    "Pre-Chorus": [
        "The performer reaches a point where the route could widen.",
        "The performer commits so the next move is already inevitable.",
    ],
    "Chorus": [
        "The performer begins a visible release event instead of another neutral walk.",
        "The performer keeps the release alive inside the same open space.",
        "The performer carries the release into a readable next-state handoff.",
    ],
    "Bridge": [
        "The performer compresses the movement into a shorter, tighter beat without fully stopping.",
        "The performer regains a forward line inside the same compressed world.",
    ],
    "Final Chorus": [
        "The performer enters the final release as a visible physical event.",
        "The performer keeps the release alive instead of resetting to a centered walk.",
        "The performer carries the release to the next state with stronger momentum.",
        "The performer leaves the release behind in a wider forward departure.",
    ],
    "Outro": [
        "The performer is already gone, but the route still holds the shape of the movement.",
    ],
}

_DEFAULT_IDENTITY_HOOKS = [
    "consistent hair silhouette",
    "stable face framing",
    "clean everyday wardrobe silhouette",
    "small repeatable accessory detail",
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
    if not _text(_section(config, "visual"), "performer_arc"):
        missing.append("visual.performer_arc")
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
        "ref_subject_intro": _text(character, "ref_subject_intro") or "The same performer",
        "ref_continuity_guidance": _text(
            character,
            "ref_continuity_guidance",
        )
        or "Keep the same performer identity, realistic facial structure, consistent hair silhouette, and stable wardrobe continuity.",
        "style_contract": style,
        "world_core": world_rules,
        "time_anchor": _time_anchor(_text(visual, "story_premise"), world_rules),
        "story_premise": _text(visual, "story_premise"),
        "world_rules": world_rules,
        "performer_arc": _text(visual, "performer_arc"),
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
        "cinematic live-action music video with premium realism and stable human continuity",
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


def _top_list(config: dict, key: str) -> list[str]:
    if not isinstance(config, dict):
        return []
    raw = config.get(key, [])
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


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
    visual_concept = _top_text(config, "visual_concept")
    locations = _top_list(config, "locations")
    props = _top_list(config, "props")
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
    section_roles = _generic_section_story_roles(prompt, visual_concept, locations)
    section_events = _generic_section_event_scripts(prompt, visual_concept, locations, props)
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
        "story_premise": visual_concept or prompt,
        "world_rules": "",
        "performer_arc": "Keep one readable direction across the song.",
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
        "visual_concept": visual_concept,
        "profile_locations": locations,
        "profile_props": props,
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
    if "solo female" in low:
        return "The same solo female vocalist"
    if "solo male" in low:
        return "The same solo male vocalist"
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
    if "solo female" in voice:
        return "young adult female vocalist"
    if "solo male" in voice:
        return "young adult male vocalist"
    if "female" in voice:
        return "young adult female vocalist"
    if "male" in voice:
        return "young adult male vocalist"
    if "duo" in voice or "group" in voice or "mixed" in voice:
        return "vocal performer"
    return "young adult vocalist"


def _anchor_wardrobe_guidance(config: dict) -> str:
    parts = [
        _anchor_text(config, "anchor_top"),
        _anchor_text(config, "anchor_bottom"),
        _anchor_text(config, "anchor_shoes"),
    ]
    return ", ".join(part for part in parts if part)


def _generic_section_story_roles(prompt: str, visual_concept: str, locations: list[str]) -> dict[str, str]:
    mood = _generic_visual_mood(f"{prompt} {visual_concept}")
    location_hint = locations[0] if locations else "real-world location"
    return {
        "Intro": f"Establish the protagonist and world with a {mood} opening image in {location_hint}.",
        "Verse 1": "Introduce the first readable environment and emotional state through grounded physical behavior.",
        "Verse 2": "Carry the same emotional thread into a new but connected place without breaking continuity.",
        "Pre-Chorus": "Tighten tension and reduce space before the release.",
        "Chorus": "Open the frame into the clearest emotional release image.",
        "Bridge": "Interrupt the movement with a more stripped-back or intimate visual turn.",
        "Final Chorus": "Deliver the widest and most memorable release image with stronger forward momentum.",
        "Outro": "Leave one final after-image that resolves the sequence without overexplaining it.",
    }


def _generic_section_event_scripts(prompt: str, visual_concept: str, locations: list[str], props: list[str]) -> dict[str, list[str]]:
    motif = _generic_prompt_motif(f"{prompt} {visual_concept}")
    location_bits = [str(x).strip() for x in locations if str(x).strip()]
    prop_bits = [str(x).strip() for x in props if str(x).strip()]
    intro_open, intro_hold = _generic_intro_events(motif, location_bits, prop_bits)
    verse_first, verse_shift, verse_carry = _generic_verse_events(motif, location_bits, prop_bits)
    verse2_open, verse2_carry, verse2_land = _generic_verse2_events(motif, location_bits, prop_bits)
    chorus_open, chorus_carry, chorus_land = _generic_chorus_events(motif, location_bits, prop_bits)
    return {
        "Intro": [
            intro_open,
            intro_hold,
        ],
        "Verse 1": [
            verse_first,
            verse_shift,
            verse_carry,
        ],
        "Verse 2": [
            verse2_open,
            verse2_carry,
            verse2_land,
        ],
        "Pre-Chorus": [
            "She slows down or pauses briefly as the tension gathers.",
            "She commits toward the next emotional release without breaking continuity.",
        ],
        "Chorus": [
            chorus_open,
            chorus_carry,
            chorus_land,
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
            "The final image lingers after she has already moved through the scene.",
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


def _generic_intro_events(motif: str, locations: list[str], props: list[str]) -> tuple[str, str]:
    first_location = locations[0] if locations else "the first location"
    first_prop = props[0] if props else "one everyday object"
    if motif == "city-night":
        return (
            f"She stands alone in {first_location} before she starts moving.",
            f"She pauses long enough for the empty street, reflections, and {first_prop} to settle into the frame.",
        )
    if motif == "performance":
        return (
            "She settles into the room before the performance energy begins.",
            "She holds a quiet beat beside the instrument or stage setup.",
        )
    if motif == "interior":
        return (
            f"She sits alone in {first_location}, taking in the space before she moves.",
            f"She holds a quiet still moment with {first_prop} close to her.",
        )
    return (
        "She appears alone in the first grounded location before the motion begins.",
        "She holds a quiet still beat that fixes the mood and the place.",
    )


def _generic_verse_events(motif: str, locations: list[str], props: list[str]) -> tuple[str, str, str]:
    carry_prop = props[0] if props else "one physical detail"
    if motif == "city-night":
        return (
            "She passes one grounded street detail in a natural everyday way.",
            "She keeps walking with a small but readable change in posture or direction.",
            f"She continues forward while rain, reflections, passing light, and {carry_prop} carry over from the previous shot.",
        )
    if motif == "performance":
        return (
            "She adjusts or touches one piece of gear in a natural rehearsal-like way.",
            "She moves through the room with a small but readable shift in rhythm or posture.",
            f"She keeps {carry_prop} or one lighting detail alive from the previous shot.",
        )
    if motif == "interior":
        return (
            "She interacts with one everyday object in a natural unforced way.",
            "She shifts through the same room with a small but readable change in posture or direction.",
            f"She keeps {carry_prop} and one physical detail from the previous shot alive.",
        )
    return (
        "She interacts with one grounded environment detail in a natural everyday way.",
        "She moves through the same area with a small but readable shift in posture or direction.",
        "She continues forward while keeping one physical detail from the previous shot alive.",
    )


def _generic_verse2_events(motif: str, locations: list[str], props: list[str]) -> tuple[str, str, str]:
    next_location = locations[1] if len(locations) > 1 else (locations[0] if locations else "a connected place")
    carry_prop = props[0] if props else "one object"
    if motif == "city-night":
        return (
            f"She reaches {next_location} without breaking the same night route.",
            f"She keeps moving while the same rain, pavement texture, window light, and {carry_prop} carry over.",
            "She lands in a clearer visual state before the next cut.",
        )
    if motif == "performance":
        return (
            f"She reaches {next_location} without breaking continuity.",
            f"She keeps moving while {carry_prop}, one instrument, cable, or light cue carries over from the last shot.",
            "She lands in a clearer visual state before the next cut.",
        )
    if motif == "interior":
        return (
            f"She reaches {next_location} as a different but connected corner of the same interior world.",
            f"She keeps moving while {carry_prop} or one texture carries over from the last location.",
            "She lands in a clearer visual state before the next cut.",
        )
    return (
        "She reaches a different but connected environment that expands the same mood.",
        "She keeps moving while one physical object or texture carries over from the last location.",
        "She lands in a clearer visual state before the next cut.",
    )


def _generic_chorus_events(motif: str, locations: list[str], props: list[str]) -> tuple[str, str, str]:
    payoff_location = locations[-1] if locations else "the widest location"
    carry_prop = props[0] if props else "one continuity prop"
    if motif == "city-night":
        return (
            f"She steps into {payoff_location} as the widest and clearest night image of the song so far.",
            f"She keeps the energy alive with a more open stride, gesture, or body turn while still carrying {carry_prop}.",
            "She lands the moment in a readable visual payoff.",
        )
    if motif == "performance":
        return (
            f"She steps into {payoff_location} as the strongest and most open performance image of the song so far.",
            f"She keeps the energy alive with a clearer performance beat or body movement while still carrying {carry_prop}.",
            "She lands the moment in a readable visual payoff.",
        )
    return (
        "She enters the strongest and most open image of the song so far.",
        "She keeps the energy alive with a clearer gesture, stride, or performance beat.",
        "She lands the moment in a readable visual payoff.",
    )
