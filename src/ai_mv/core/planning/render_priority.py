from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP



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
