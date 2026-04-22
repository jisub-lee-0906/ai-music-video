from __future__ import annotations

import math
import zlib
from decimal import Decimal, ROUND_HALF_UP

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
    variation_seed = _variation_seed_for_shot(shot)
    variation_profile = build_variation_profile(variation_seed, shot)
    still_prompt_text = build_still_prompt_text(prompt_seed, prompt_draft, prompt_polish, variation_profile)
    clip_prompt_seed = build_clip_prompt_seed(render_mode, shot, prompt_seed, variation_profile)
    clip_positive_prompt = build_clip_positive_prompt(render_mode, shot, clip_prompt_seed, variation_profile)
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



def build_still_prompt_text(prompt_seed: str, prompt_draft: str, prompt_polish: str, variation_profile: dict | None = None) -> str:
    base = str(prompt_polish or prompt_draft or prompt_seed).strip()
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    return _join_prompt_tokens(
        [
            base,
            _framing_variant_token(str(variation.get("framing_variant", "")).strip()),
            _environment_variant_token(str(variation.get("environment_variant", "")).strip()),
            _section_emphasis_variant_token(str(variation.get("section_emphasis_variant", "")).strip()),
        ]
    )



def build_clip_prompt_seed(render_mode: str, shot: dict, prompt_seed: str, variation_profile: dict | None = None) -> str:
    role = str(shot.get("shot_role", "")).replace("_", " ").strip()
    visual_mode = str(shot.get("visual_mode", "")).replace("_", " ").strip()
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    seed_prefix = str(prompt_seed or "").split(",")[0].strip()
    return _join_prompt_tokens(
        [
            seed_prefix,
            role or "performance shot",
            visual_mode or "music-responsive motion",
            _motion_variant_token(str(variation.get("motion_variant", "")).strip()),
            _continuity_variant_token(str(variation.get("continuity_variant", "")).strip()),
            _section_emphasis_clip_token(str(variation.get("section_emphasis_variant", "")).strip()),
        ]
    )



def build_clip_positive_prompt(render_mode: str, shot: dict, clip_prompt_seed: str, variation_profile: dict | None = None) -> str:
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    return _join_prompt_tokens(
        [
            clip_prompt_seed,
            _continuity_identity_token(str(variation.get("continuity_variant", "")).strip()),
            _framing_camera_token(str(variation.get("framing_variant", "")).strip()),
            _environment_motion_token(str(variation.get("environment_variant", "")).strip()),
        ]
    )



def build_edit_intent(shot: dict, variation_profile: dict | None = None) -> dict:
    edit_role = str(shot.get("edit_role", "support")).strip()
    duration_sec = float(shot.get("duration_sec", 0.0) or 0.0)
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    motion_variant = str(variation.get("motion_variant", "")).strip()
    framing_variant = str(variation.get("framing_variant", "")).strip()
    if edit_role == "hook":
        if motion_variant == "pulsed":
            return {
                "edit_priority": "high",
                "section_emphasis": "chorus_push",
                "pattern_family": "hook_punch_in",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.4),
                "transition_in": "accent_in",
                "transition_out": "accent_out",
            }
        if motion_variant == "gliding":
            return {
                "edit_priority": "high",
                "section_emphasis": "chorus_push",
                "pattern_family": "hook_sustain",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.6),
                "transition_in": "glide_in",
                "transition_out": "accent_out",
            }
        return {
            "edit_priority": "high",
            "section_emphasis": "chorus_push",
            "pattern_family": "hook_surge",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.5),
            "transition_in": "cut_in",
            "transition_out": "accent_out",
        }
    if edit_role == "bridge":
        if motion_variant == "gliding":
            return {
                "edit_priority": "medium",
                "section_emphasis": "bridge_contrast",
                "pattern_family": "bridge_glide",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.6),
                "transition_in": "glide_in",
                "transition_out": "handoff_out",
            }
        return {
            "edit_priority": "medium",
            "section_emphasis": "bridge_contrast",
            "pattern_family": "bridge_pivot",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.45),
            "transition_in": "cut_in",
            "transition_out": "handoff_out",
        }
    if edit_role == "release":
        if motion_variant == "gliding" or framing_variant == "environment_forward":
            return {
                "edit_priority": "medium",
                "section_emphasis": "release_fade",
                "pattern_family": "release_drift",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.7),
                "transition_in": "hold_in",
                "transition_out": "fade_out",
            }
        return {
            "edit_priority": "medium",
            "section_emphasis": "release_fade",
            "pattern_family": "release_tail",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.5),
            "transition_in": "cut_in",
            "transition_out": "fade_out",
        }
    if motion_variant == "pulsed":
        return {
            "edit_priority": "medium",
            "section_emphasis": "sequence_support",
            "pattern_family": "support_drive",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.45),
            "transition_in": "cut_in",
            "transition_out": "cut_out",
        }
    return {
        "edit_priority": "medium",
        "section_emphasis": "sequence_support",
        "pattern_family": "support_hold",
        "target_clip_sec": _scaled_target_clip(duration_sec, 0.7),
        "transition_in": "hold_in",
        "transition_out": "cut_out",
    }



def _scaled_target_clip(duration_sec: float, ratio: float) -> float:
    duration = max(0.0, float(duration_sec or 0.0))
    if duration <= 0.0:
        return 0.0
    scaled = max(0.6, duration * float(ratio))
    return float(_round_half_up(min(duration, scaled), 3))



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



def _join_prompt_tokens(parts: list[str]) -> str:
    tokens: list[str] = []
    for part in parts:
        value = str(part or "").strip()
        if value and value not in tokens:
            tokens.append(value)
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



def _framing_variant_token(variant: str) -> str:
    return {
        "balanced": "balanced cinematic framing",
        "subject_forward": "subject-forward framing emphasis",
        "environment_forward": "environment-led framing emphasis",
    }.get(variant, "balanced cinematic framing")



def _environment_variant_token(variant: str) -> str:
    return {
        "atmospheric": "atmospheric world detail emphasis",
        "textural": "textural light and surface detail emphasis",
        "spatial": "clear spatial depth emphasis",
    }.get(variant, "atmospheric world detail emphasis")



def _section_emphasis_variant_token(variant: str) -> str:
    return {
        "hook_forward": "hook-first still emphasis",
        "lifted_release": "lifted release still emphasis",
        "performance_peak": "performance-peak still emphasis",
        "contrastive_turn": "contrastive section-turn emphasis",
        "late-night drift": "late-night drift emphasis",
        "reset_suspension": "reset-and-suspension emphasis",
        "world_anchor": "world-anchor still emphasis",
        "afterglow_hold": "afterglow hold emphasis",
        "slow_release": "slow release emphasis",
        "forward_drive": "forward-drive still emphasis",
        "cinematic_push": "cinematic push still emphasis",
        "contained_intensity": "contained intensity emphasis",
        "sequence_support": "sequence-support still emphasis",
        "observational_flow": "observational flow emphasis",
        "ambient_progression": "ambient progression emphasis",
    }.get(variant, "sequence-support still emphasis")



def _motion_variant_token(variant: str) -> str:
    return {
        "restrained": "restrained camera motion",
        "gliding": "gliding camera motion",
        "pulsed": "beat-responsive camera motion",
    }.get(variant, "restrained camera motion")



def _continuity_variant_token(variant: str) -> str:
    return {
        "strict": "strict continuity anchors",
        "anchored": "stable continuity anchors",
        "expressive": "expressive continuity within the same world",
    }.get(variant, "stable continuity anchors")



def _section_emphasis_clip_token(variant: str) -> str:
    return {
        "hook_forward": "audio-reactive hook energy",
        "lifted_release": "lifted release energy",
        "performance_peak": "audio-reactive performance peak",
        "contrastive_turn": "contrastive section turn",
        "late-night drift": "late-night motion drift",
        "reset_suspension": "reset-and-suspension beat",
        "world_anchor": "world-anchor motion restraint",
        "afterglow_hold": "afterglow hold beat",
        "slow_release": "slow release beat",
        "forward_drive": "forward-driving energy",
        "cinematic_push": "cinematic motion push",
        "contained_intensity": "contained motion intensity",
        "sequence_support": "sequence-support motion",
        "observational_flow": "observational motion flow",
        "ambient_progression": "ambient progression motion",
    }.get(variant, "audio-reactive energy")



def _continuity_identity_token(variant: str) -> str:
    return {
        "strict": "strict performer identity lock",
        "anchored": "stable performer identity",
        "expressive": "stable performer identity with expressive motion",
    }.get(variant, "stable performer identity")



def _framing_camera_token(variant: str) -> str:
    return {
        "balanced": "restrained camera",
        "subject_forward": "subject-led camera framing",
        "environment_forward": "environment-led camera framing",
    }.get(variant, "restrained camera")



def _environment_motion_token(variant: str) -> str:
    return {
        "atmospheric": "atmospheric motion continuity",
        "textural": "textural light continuity",
        "spatial": "clear spatial continuity",
    }.get(variant, "no abrupt pose change")



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
