from __future__ import annotations

import math
import zlib
from decimal import Decimal, ROUND_HALF_UP

from ai_mv.core.planning.edit_intents import build_edit_intent as edit_intents_build_edit_intent
from ai_mv.core.planning.prompt_contracts import (
    build_clip_positive_prompt as prompt_contracts_build_clip_positive_prompt,
    build_clip_prompt_seed as prompt_contracts_build_clip_prompt_seed,
    build_still_prompt_text as prompt_contracts_build_still_prompt_text,
)
from ai_mv.styles.resolver import build_style_prompt_draft, build_style_prompt_seed, resolve_style_name



def build_render_item(config: dict, concept_text: str, style_name_or_bible, style_bible_or_shot, shot: dict | None = None) -> dict:
    if shot is None:
        planning = config.get("planning", {}) if isinstance(config, dict) else {}
        default_style_name = str(planning.get("default_style_name", "")).strip() or None
        style_name = resolve_style_name(concept_text, default_style_name=default_style_name)
        style_bible = style_name_or_bible
        shot = style_bible_or_shot
    else:
        style_name = str(style_name_or_bible)
        style_bible = style_bible_or_shot
    prompt_seed = build_prompt_seed(style_name, concept_text, style_bible, shot)
    prompt_draft = build_prompt_draft(style_name, shot)
    prompt_polish = polish_prompt(prompt_seed, prompt_draft)
    render_mode = str(shot["render_mode"]).strip()
    continuity_contract = build_continuity_contract(shot)
    shot_relation_contract = build_shot_relation_contract(shot)
    variation_seed = _variation_seed_for_shot(shot)
    variation_profile = build_variation_profile(variation_seed, shot)
    still_prompt_text = build_still_prompt_text(prompt_seed, prompt_draft, prompt_polish, variation_profile, shot_relation_contract)
    clip_prompt_seed = build_clip_prompt_seed(render_mode, shot, prompt_seed, variation_profile, shot_relation_contract)
    clip_positive_prompt = build_clip_positive_prompt(render_mode, shot, clip_prompt_seed, variation_profile, shot_relation_contract)
    edit_intent = build_edit_intent(shot, variation_profile)
    render_count = calculate_render_count(float(shot.get("duration_sec", 0.0) or 0.0))
    render_planning = build_render_planning(style_name, shot)
    out = {
        "shot_id": shot["shot_id"],
        "section_id": str(shot.get("section_id", "")).strip(),
        "material_id": str(shot.get("material_id", "")).strip(),
        "render_mode": render_mode,
        "render_count": render_count,
        "render_planning": render_planning,
        "render_priority_score": render_planning["render_priority_score"],
        "seed": _render_seed_for_shot(shot),
        "variation_seed": variation_seed,
        "variation_profile": variation_profile,
        "continuity_contract": continuity_contract,
        "shot_relation_contract": shot_relation_contract,
        "prompt_seed": prompt_seed,
        "prompt_draft": prompt_draft,
        "prompt_polish": prompt_polish,
        "still_prompt_text": still_prompt_text,
        "clip_prompt_seed": clip_prompt_seed,
        "clip_positive_prompt": clip_positive_prompt,
        "edit_intent": edit_intent,
        "still_a": "",
    }
    if render_mode == "ia2v":
        out["audio_segment"] = {
            "start_sec": shot["start_sec"],
            "duration_sec": shot["duration_sec"],
        }
    return out



def build_prompt_seed(style_name: str, concept_text: str, style_bible: dict, shot: dict) -> str:
    return build_style_prompt_seed(style_name, concept_text, style_bible, shot)



def build_prompt_draft(style_name: str, shot: dict) -> str:
    return build_style_prompt_draft(style_name, shot)



def build_still_prompt_text(
    prompt_seed: str,
    prompt_draft: str,
    prompt_polish: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
) -> str:
    return prompt_contracts_build_still_prompt_text(
        prompt_seed,
        prompt_draft,
        prompt_polish,
        variation_profile,
        shot_relation_contract,
    )



def build_clip_prompt_seed(
    render_mode: str,
    shot: dict,
    prompt_seed: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
) -> str:
    return prompt_contracts_build_clip_prompt_seed(
        render_mode,
        shot,
        prompt_seed,
        variation_profile,
        shot_relation_contract,
    )



def build_clip_positive_prompt(
    render_mode: str,
    shot: dict,
    clip_prompt_seed: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
) -> str:
    return prompt_contracts_build_clip_positive_prompt(
        render_mode,
        shot,
        clip_prompt_seed,
        variation_profile,
        shot_relation_contract,
    )



def build_continuity_contract(shot: dict) -> dict:
    return {
        "protagonist_anchor": str(shot.get("protagonist_anchor", "")).strip(),
        "world_anchor": str(shot.get("world_anchor", "")).strip(),
        "wardrobe_anchor": _wardrobe_anchor(shot),
        "no_competing_subjects": True,
        "time_band_anchor": "same night time band",
    }



def build_shot_relation_contract(shot: dict) -> dict:
    explicit = shot.get("shot_relation_contract") if isinstance(shot.get("shot_relation_contract"), dict) else {}
    if explicit:
        return {
            "relation_to_previous_shot": str(explicit.get("relation_to_previous_shot", "")).strip(),
            "camera_distance_progression": str(explicit.get("camera_distance_progression", "")).strip(),
            "same_block_vs_new_block": str(explicit.get("same_block_vs_new_block", "")).strip(),
            "emotional_delta": str(explicit.get("emotional_delta", "")).strip(),
        }
    section_type = str(shot.get("section_type", "")).strip().lower()
    framing_intent = str(shot.get("framing_intent", "")).strip()
    if section_type == "intro":
        return {
            "relation_to_previous_shot": "sequence opener",
            "camera_distance_progression": "set baseline distance",
            "same_block_vs_new_block": "same block baseline",
            "emotional_delta": "establish lonely night-world baseline",
        }
    progression = {
        "establishing_wide": "hold or widen from previous shot",
        "hero_medium": "move closer than previous shot",
        "connective_medium": "shift laterally while keeping distance readable",
        "performance_medium": "move into performance distance",
        "release_wide": "step wider for release",
    }.get(framing_intent, "adjust distance without breaking continuity")
    emotional = {
        "chorus": "open into hook release without changing world",
        "bridge": "turn inward without changing world",
        "outro": "resolve into afterglow on the same block",
    }.get(section_type, "increase intimacy without changing world")
    return {
        "relation_to_previous_shot": "continue same protagonist and world from previous shot",
        "camera_distance_progression": progression,
        "same_block_vs_new_block": "same block, new angle",
        "emotional_delta": emotional,
    }



def build_edit_intent(shot: dict, variation_profile: dict | None = None) -> dict:
    return edit_intents_build_edit_intent(shot, variation_profile)



def calculate_render_count(duration_sec: float) -> int:
    duration_sec = float(duration_sec or 0.0)
    if duration_sec <= 6.5:
        return 1
    if duration_sec <= 13.0:
        return 2
    if duration_sec <= 19.5:
        return 3
    return min(4, max(1, int(math.ceil(duration_sec / 6.0))))



def _render_seed_for_shot(shot: dict) -> int:
    text = "|".join(
        [
            str(shot.get("shot_id", "")).strip(),
            str(shot.get("start_sec", "")).strip(),
            str(shot.get("duration_sec", "")).strip(),
            str(shot.get("visual_mode", "")).strip(),
            str(shot.get("render_mode", "")).strip(),
        ]
    ).encode("utf-8")
    return 1000 + int(zlib.crc32(text) % 1_000_000)



def _variation_seed_for_shot(shot: dict) -> int:
    text = "|".join(
        [
            str(shot.get("shot_id", "")).strip(),
            str(shot.get("section_type", "")).strip(),
            str(shot.get("section_name", "")).strip(),
            str(shot.get("shot_role", "")).strip(),
            str(shot.get("visual_mode", "")).strip(),
            str(shot.get("start_sec", "")).strip(),
        ]
    ).encode("utf-8")
    return 2000 + int(zlib.crc32(text) % 1_000_000)



def build_variation_profile(variation_seed: int, shot: dict) -> dict:
    section_type = str(shot.get("section_type", "")).strip().lower()
    energy = str(shot.get("energy", "")).strip().lower()
    shot_role = str(shot.get("shot_role", "")).strip().lower()
    visual_mode = str(shot.get("visual_mode", "")).strip().lower()
    is_performance_peak = section_type == "chorus" or "chorus" in shot_role or "performance" in visual_mode
    framing_options = ["balanced", "subject_forward"] if is_performance_peak else ["balanced", "subject_forward", "environment_forward"]
    continuity_options = ["strict", "anchored"] if is_performance_peak else ["strict", "anchored", "expressive"]
    return {
        "variation_family": _pick_variant(variation_seed, ["editorial-a", "editorial-b", "editorial-c"]),
        "framing_variant": _pick_variant(variation_seed + 11, framing_options),
        "environment_variant": _pick_variant(variation_seed + 23, ["atmospheric", "textural", "spatial"]),
        "motion_variant": _pick_variant(variation_seed + 37, ["restrained", "gliding", "pulsed"]),
        "continuity_variant": _pick_variant(variation_seed + 53, continuity_options),
        "section_emphasis_variant": _section_emphasis_variant(section_type, energy, variation_seed + 71),
    }



def build_render_planning(style_name: str, shot: dict) -> dict:
    section_energy_score = _section_energy_score(str(shot.get("energy", "")).strip())
    section_emphasis_score = _section_emphasis_score(str(shot.get("section_type", "")).strip())
    mode_importance_score = _mode_importance_score(shot)
    lane_priority_score = _lane_priority_score(style_name)
    continuity_need_score = _continuity_need_score(str(shot.get("continuity_mode", "")).strip())
    render_priority_score = _round_half_up(
        (0.30 * section_energy_score)
        + (0.25 * section_emphasis_score)
        + (0.20 * mode_importance_score)
        + (0.15 * lane_priority_score)
        + (0.10 * continuity_need_score),
        2,
    )
    return {
        "section_energy_score": section_energy_score,
        "section_emphasis_score": section_emphasis_score,
        "mode_importance_score": mode_importance_score,
        "lane_priority_score": lane_priority_score,
        "continuity_need_score": continuity_need_score,
        "render_priority_score": render_priority_score,
    }



def polish_prompt(prompt_seed: str, prompt_draft: str) -> str:
    tokens: list[str] = []
    for block in (prompt_seed, prompt_draft):
        for token in [part.strip() for part in str(block).split(",") if part.strip()]:
            if token not in tokens:
                tokens.append(token)
    return ", ".join(tokens)



def _pick_variant(seed: int, options: list[str]) -> str:
    if not options:
        return ""
    return options[int(seed) % len(options)]



def _section_emphasis_variant(section_type: str, energy: str, seed: int) -> str:
    normalized_type = str(section_type or "").strip()
    normalized_energy = str(energy or "").strip()
    if normalized_type == "chorus":
        return _pick_variant(seed, ["hook_forward", "lifted_release", "performance_peak"])
    if normalized_type == "bridge":
        return _pick_variant(seed, ["contrastive_turn", "late-night drift", "reset_suspension"])
    if normalized_type in {"intro", "outro"}:
        return _pick_variant(seed, ["world_anchor", "afterglow_hold", "slow_release"])
    if normalized_energy == "high":
        return _pick_variant(seed, ["forward_drive", "cinematic_push", "contained_intensity"])
    return _pick_variant(seed, ["sequence_support", "observational_flow", "ambient_progression"])



def _wardrobe_anchor(shot: dict) -> str:
    continuity = shot.get("continuity_contract") if isinstance(shot.get("continuity_contract"), dict) else {}
    explicit = str(continuity.get("wardrobe_anchor", "")).strip()
    if explicit:
        return explicit
    protagonist_anchor = str(shot.get("protagonist_anchor", "")).strip().lower()
    if "dark outerwear silhouette" in protagonist_anchor:
        return "stable dark outerwear silhouette"
    return "stable signature silhouette"



def _section_energy_score(energy: str) -> float:
    return {
        "low": 0.25,
        "medium": 0.50,
        "high": 0.75,
        "peak": 1.00,
        "release": 0.55,
    }.get(str(energy or "").strip(), 0.50)



def _section_emphasis_score(section_type: str) -> float:
    return {
        "intro": 0.55,
        "verse": 0.60,
        "pre_chorus": 0.70,
        "chorus": 1.00,
        "bridge": 0.78,
        "outro": 0.72,
        "instrumental_break": 0.58,
        "post_chorus": 0.68,
    }.get(str(section_type or "").strip(), 0.60)



def _mode_importance_score(shot: dict) -> float:
    framing_intent = str(shot.get("framing_intent", "")).strip()
    section_type = str(shot.get("section_type", "")).strip()
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if framing_intent == "performance_medium" or section_type == "chorus":
        return 1.00
    if "bridge" in visual_mode or section_type == "bridge":
        return 0.85
    if framing_intent == "release_wide" or visual_mode.endswith("anchor"):
        return 0.72
    if "travel" in visual_mode or "drive" in visual_mode:
        return 0.66
    if "closeup" in framing_intent or "closeup" in visual_mode:
        return 0.64
    return 0.68



def _lane_priority_score(style_name: str) -> float:
    return 0.85 if str(style_name or "").strip() in {"synthwave", "alt_pop", "j_rock"} else 0.70



def _continuity_need_score(continuity_mode: str) -> float:
    return {
        "strict": 1.00,
        "high": 0.80,
        "medium_high": 0.65,
        "medium": 0.50,
    }.get(str(continuity_mode or "").strip(), 0.80)



def _round_half_up(value: float, digits: int) -> float:
    quantize_exp = "1." + ("0" * max(0, digits))
    adjusted = Decimal(str(value + 1e-12))
    return float(adjusted.quantize(Decimal(quantize_exp), rounding=ROUND_HALF_UP))
