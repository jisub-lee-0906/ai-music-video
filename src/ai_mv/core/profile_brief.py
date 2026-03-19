from __future__ import annotations

from ai_mv.core.contracts.intent_models import ProfileIntent
from ai_mv.core.profile_policy import resolve_profile_policy
from ai_mv.core.workflow_prompt_contracts import flux2_visual_style_contract, sanitize_flux2_negative_text, sanitize_flux2_positive_text


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
    ending_policy = _audio_ending_policy(config)
    intent = ProfileIntent(
        audio_intent={
            "language": _text(audio, "language") or "en",
            "brief": _text(audio, "brief"),
            "hook_brief": _text(audio, "hook_brief"),
            "tags": [str(x).strip() for x in audio.get("tags", []) if str(x).strip()] if isinstance(audio.get("tags", []), list) else [],
            "ending_policy": dict(ending_policy),
        },
        world_intent={
            "visual_intent": _visual_intent(config, visual, mv, policy),
            "story_world": _text(mv, "story_world"),
            "action_vocabulary": _text(mv, "action_vocabulary"),
            "payoff_style": _text(mv, "payoff_style"),
            "heroine_invariants": _heroine_invariants(visual, mv),
            "world_invariants": _world_invariants(visual, mv),
            "visual_style_contract": _visual_style_contract(config, visual, mv, policy),
            "location_families": _location_families(mv),
            "closeup_policy": _closeup_policy(visual, mv),
            "motion_policy": _motion_policy(visual, mv),
            "payoff_closeup_policy": _payoff_closeup_policy(mv),
            "resolved_profile_policy": dict(policy),
        },
        negative_intent={
            "visual_negative": _visual_negative(visual),
            "mv_avoid": _text(mv, "avoid"),
        },
        escalation_intent={
            "chorus_payoff": _text(mv, "payoff_style"),
            "bridge_interrupt": _text(mv, "action_vocabulary"),
            "outro_residue": _text(mv, "outro_feel"),
            "audio_ending_policy": dict(ending_policy),
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
            "stylized East Asian heroine with a sticker-like silhouette, simplified icon face, sharp heavy-lid eye shape, minimal facial detail, angular fashion shape, and toy-like deformed proportions",
            _extract_fragment(_text(visual, "brief"), ("East Asian heroine", "young adult East Asian heroine", "female solo vocal", "lead")),
            _extract_fragment(_text(mv, "story_world"), ("same heroine",)),
        ]
    )


def _world_invariants(visual: dict, mv: dict) -> str:
    return _join_parts(
        [
            "one continuous world",
            "stylized 2d graphic music-video space with flat poster depth and strong negative space",
            _extract_fragment(_text(mv, "story_world"), ("same night", "one continuous", "continuous", "same emotional weather", "same luxurious pulse", "same momentum", "same rebellious force", "same electric pressure", "same suspended emotional current", "same sense of supernatural authority")),
            _extract_fragment(_text(visual, "brief"), ("readable", "center framing", "center-dominant", "heroine legible", "heroine readable")),
        ]
    )


def _visual_intent(config: dict, visual: dict, mv: dict, policy: dict) -> str:
    source = " ".join([_text(visual, "brief"), _text(mv, "story_world"), _text(mv, "payoff_style")]).strip()
    cleaned = sanitize_flux2_positive_text(source)
    style = _visual_style_contract(config, visual, mv, policy)
    return _join_parts([style, cleaned])


def _visual_style_contract(config: dict, visual: dict, mv: dict, policy: dict) -> str:
    source = " ".join([_text(visual, "brief"), _text(mv, "story_world"), _text(mv, "payoff_style"), _text(mv, "action_vocabulary")])
    return flux2_visual_style_contract(source, policy)


def _visual_negative(visual: dict) -> str:
    return sanitize_flux2_negative_text(_text(visual, "negative"))


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


def _audio_ending_policy(config: dict) -> dict:
    audio = _section(config, "audio")
    mv = _section(config, "mv")
    raw = config.get("audio_ending_policy", {}) if isinstance(config, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    mode = _enum(raw.get("ending_mode"), {"hard_stop", "clean_resolve", "glow_fade", "bittersweet_tail", "anthem_lift"}, _derive_ending_mode(audio, mv))
    final_chorus_required = _bool(raw.get("final_chorus_required"), True)
    outro_required = _bool(raw.get("outro_required"), mode in {"glow_fade", "bittersweet_tail", "anthem_lift"})
    energy_drop = _enum(raw.get("ending_energy_drop"), {"low", "medium", "high"}, _default_energy_drop(mode))
    vocal_density = _enum(raw.get("ending_vocal_density"), {"full", "medium", "low", "tail_only"}, _default_vocal_density(mode))
    ending_tags = _ending_tags(raw.get("ending_tags", []), mode, audio, mv)
    return {
        "ending_mode": mode,
        "final_chorus_required": final_chorus_required,
        "outro_required": outro_required,
        "ending_energy_drop": energy_drop,
        "ending_vocal_density": vocal_density,
        "ending_tags": ending_tags,
    }


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


def _derive_ending_mode(audio: dict, mv: dict) -> str:
    text = " ".join([_text(audio, "brief"), _text(mv, "outro_feel"), _text(mv, "avoid")]).lower()
    if any(token in text for token in ("fade", "linger", "glow", "luminous", "after-image")):
        return "glow_fade"
    if any(token in text for token in ("bittersweet", "decay", "burned", "residue")):
        return "bittersweet_tail"
    if any(token in text for token in ("anthem", "breakthrough", "forward-looking")):
        return "anthem_lift"
    if any(token in text for token in ("slammed shut", "nailed down", "impossible to shrink", "not allowed to dissolve", "sealed", "hard after-image")):
        return "hard_stop"
    return "clean_resolve"


def _default_energy_drop(mode: str) -> str:
    return {
        "hard_stop": "low",
        "clean_resolve": "medium",
        "glow_fade": "high",
        "bittersweet_tail": "high",
        "anthem_lift": "medium",
    }.get(mode, "medium")


def _default_vocal_density(mode: str) -> str:
    return {
        "hard_stop": "full",
        "clean_resolve": "medium",
        "glow_fade": "low",
        "bittersweet_tail": "tail_only",
        "anthem_lift": "medium",
    }.get(mode, "medium")


def _ending_tags(raw: object, mode: str, audio: dict, mv: dict) -> list[str]:
    vals = [str(x).strip() for x in raw if str(x).strip()] if isinstance(raw, list) else []
    if vals:
        return vals[:6]
    source = " ".join([_text(audio, "brief"), _text(mv, "outro_feel")]).lower()
    if "city pop" in source:
        return ["soft outro", "warm final resolve", "gentle fade out"]
    if "k-pop" in source or "k pop" in source:
        return ["big final chorus", "clean final hit", "polished ending"]
    if "j-rock" in source or "j rock" in source or "anime rock" in source:
        return ["anthemic final chorus", "clean resolve", "driving outro"]
    if "grunge" in source or "alternative rock" in source:
        return ["raw ending", "dirty after-image", "hard stop"]
    if "ethereal" in source or "future-pop" in source or "future pop" in source:
        return ["luminous outro", "final resolve", "lingering fade"]
    if "cyber" in source or "future bass" in source or "electro-pop" in source:
        return ["final impact", "system-locked ending", "clean final hit"]
    if "mystical" in source or "ritual" in source:
        return ["ritual resolve", "sealed ending", "final strike"]
    return {
        "hard_stop": ["hard stop", "clean final hit", "decisive ending"],
        "clean_resolve": ["final resolve", "clean ending", "controlled finish"],
        "glow_fade": ["soft outro", "final resolve", "gentle fade out"],
        "bittersweet_tail": ["decaying tail", "final residue", "soft ending"],
        "anthem_lift": ["anthemic final chorus", "uplifted outro", "clean resolve"],
    }.get(mode, ["final resolve", "clean ending"])


def _enum(value: object, allowed: set[str], default: str) -> str:
    text = str(value).strip().lower()
    return text if text in allowed else default


def _bool(value: object, default: bool) -> bool:
    if value in ("", None):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    return default
