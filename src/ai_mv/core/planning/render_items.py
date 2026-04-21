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
    still_prompt_text = build_still_prompt_text(prompt_seed, prompt_draft, prompt_polish)
    clip_prompt_seed = build_clip_prompt_seed(render_mode, shot, prompt_seed)
    clip_positive_prompt = build_clip_positive_prompt(render_mode, shot, clip_prompt_seed)
    edit_intent = build_edit_intent(shot)
    render_count = calculate_render_count(float(shot.get("duration_sec", 0.0) or 0.0))
    render_planning = build_render_planning(style_name, shot)
    out = {
        "shot_id": shot["shot_id"],
        "section_id": str(shot.get("section_id", "")).strip(),
        "render_mode": render_mode,
        "render_count": render_count,
        "render_planning": render_planning,
        "render_priority_score": render_planning["render_priority_score"],
        "seed": _render_seed_for_shot(shot),
        "prompt_seed": prompt_seed,
        "prompt_draft": prompt_draft,
        "prompt_polish": prompt_polish,
        "still_prompt_text": still_prompt_text,
        "clip_prompt_seed": clip_prompt_seed,
        "clip_positive_prompt": clip_positive_prompt,
        "edit_intent": edit_intent,
        "still_a": "",
        "still_b": str(shot.get("bridge_to_shot_id", "")).strip(),
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



def build_still_prompt_text(prompt_seed: str, prompt_draft: str, prompt_polish: str) -> str:
    return str(prompt_polish or prompt_draft or prompt_seed).strip()



def build_clip_prompt_seed(render_mode: str, shot: dict, prompt_seed: str) -> str:
    role = str(shot.get("shot_role", "")).replace("_", " ").strip()
    visual_mode = str(shot.get("visual_mode", "")).replace("_", " ").strip()
    seed_prefix = str(prompt_seed or "").split(",")[0].strip()
    if render_mode == "flf2v":
        return _join_prompt_tokens(
            [
                seed_prefix,
                "bridge transition",
                role or "continuous handoff",
            ]
        )
    if render_mode == "ia2v":
        return _join_prompt_tokens(
            [
                seed_prefix,
                role or "performance shot",
                visual_mode or "music-responsive motion",
                "stable camera motion",
                "audio-reactive energy",
            ]
        )
    return _join_prompt_tokens(
        [
            seed_prefix,
            role or "cinematic motion beat",
            visual_mode or "single-shot movement",
            "stable motion",
            "preserve subject continuity",
        ]
    )



def build_clip_positive_prompt(render_mode: str, shot: dict, clip_prompt_seed: str) -> str:
    if render_mode == "flf2v":
        return _join_prompt_tokens(
            [
                clip_prompt_seed,
                "matched endpoints",
                "short transition beat",
                "no world change",
            ]
        )
    if render_mode == "ia2v":
        return _join_prompt_tokens(
            [
                clip_prompt_seed,
                "stable performer identity",
                "restrained camera",
                "no abrupt pose change",
            ]
        )
    return _join_prompt_tokens(
        [
            clip_prompt_seed,
            "single continuous motion",
            "no abrupt pose change",
        ]
    )



def build_edit_intent(shot: dict) -> dict:
    edit_role = str(shot.get("edit_role", "support")).strip()
    duration_sec = float(shot.get("duration_sec", 0.0) or 0.0)
    if edit_role == "hook":
        return {
            "edit_priority": "high",
            "section_emphasis": "chorus_push",
            "target_clip_sec": duration_sec,
            "transition_in": "accent_in",
            "transition_out": "accent_out",
        }
    if edit_role == "bridge":
        return {
            "edit_priority": "medium",
            "section_emphasis": "bridge_contrast",
            "target_clip_sec": duration_sec,
            "transition_in": "glide_in",
            "transition_out": "handoff_out",
        }
    if edit_role == "release":
        return {
            "edit_priority": "medium",
            "section_emphasis": "release_fade",
            "target_clip_sec": duration_sec,
            "transition_in": "hold_in",
            "transition_out": "fade_out",
        }
    return {
        "edit_priority": "medium",
        "section_emphasis": "sequence_support",
        "target_clip_sec": duration_sec,
        "transition_in": "cut_in",
        "transition_out": "cut_out",
    }



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
    render_mode = str(shot.get("render_mode", "")).strip()
    section_type = str(shot.get("section_type", "")).strip()
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if render_mode == "ia2v" or framing_intent == "performance_medium" or section_type == "chorus":
        return 1.00
    if render_mode == "flf2v" or "bridge" in visual_mode or section_type == "bridge":
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
