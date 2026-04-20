from __future__ import annotations

from ai_mv.styles.citypop.bible import get_citypop_bible
from ai_mv.styles.citypop.prompting import build_citypop_prompt_draft, build_citypop_prompt_seed
from ai_mv.styles.citypop.rules import apply_citypop_section_variants, citypop_section_shot_specs
from ai_mv.styles.synthwave.bible import get_synthwave_bible
from ai_mv.styles.synthwave.prompting import build_synthwave_prompt_draft, build_synthwave_prompt_seed
from ai_mv.styles.synthwave.rules import apply_synthwave_section_variants, synthwave_section_shot_specs


STYLE_PACKS = {
    "citypop": {
        "bible": get_citypop_bible,
        "prompt_seed": build_citypop_prompt_seed,
        "prompt_draft": build_citypop_prompt_draft,
        "section_specs": citypop_section_shot_specs,
        "section_variants": apply_citypop_section_variants,
    },
    "synthwave": {
        "bible": get_synthwave_bible,
        "prompt_seed": build_synthwave_prompt_seed,
        "prompt_draft": build_synthwave_prompt_draft,
        "section_specs": synthwave_section_shot_specs,
        "section_variants": apply_synthwave_section_variants,
    },
}

STYLE_SELECTION_MIN_CONFIDENCE = 0.58
STYLE_SELECTION_MIN_MARGIN = 0.08



def _style_pack(style_name: str) -> dict:
    normalized = str(style_name or "").strip()
    if normalized not in STYLE_PACKS:
        raise KeyError(f"unknown style pack: {normalized}")
    return STYLE_PACKS[normalized]



def resolve_style_name(concept_text: str, *, default_style_name: str | None = None) -> str:
    return resolve_style_selection(concept_text, default_style_name=default_style_name)["style_name"]



def resolve_style_selection(concept_text: str, *, default_style_name: str | None = None) -> dict:
    normalized_default = str(default_style_name or "").strip()
    if normalized_default:
        _style_pack(normalized_default)
    text = _normalized_text(concept_text)
    raw_scores = {style_name: _style_match_score(text, pack["bible"]()) for style_name, pack in STYLE_PACKS.items()}
    best_style = max(raw_scores, key=raw_scores.get)
    best_score = raw_scores[best_style]
    if best_score <= 0:
        if normalized_default:
            return {
                "style_name": normalized_default,
                "selection_source": "override",
                "selection_stability": "override",
                "confidence": 1.0,
                "runner_up_lanes": _runner_up_lanes(raw_scores, exclude=normalized_default),
            }
        raise KeyError("style_name could not be resolved from concept_text and no explicit default_style_name was provided")
    confidence = _selection_confidence(raw_scores, best_style)
    margin = _selection_margin(raw_scores, best_style)
    return {
        "style_name": best_style,
        "selection_source": "auto",
        "selection_stability": _selection_stability(confidence, margin),
        "confidence": confidence,
        "runner_up_lanes": _runner_up_lanes(raw_scores, exclude=best_style),
    }



def get_style_bible(style_name: str) -> dict:
    return _style_pack(style_name)["bible"]()



def build_style_prompt_seed(style_name: str, concept_text: str, style_bible: dict, shot: dict) -> str:
    return _style_pack(style_name)["prompt_seed"](concept_text, style_bible, shot)



def build_style_prompt_draft(style_name: str, shot: dict) -> str:
    return _style_pack(style_name)["prompt_draft"](shot)



def style_section_shot_specs(style_name: str, section_type: str, duration_sec: float) -> list[dict]:
    return _style_pack(style_name)["section_specs"](section_type, duration_sec)



def apply_style_section_variants(style_name: str, section_type: str, parts: list[dict]) -> list[dict]:
    return _style_pack(style_name)["section_variants"](section_type, parts)



def _normalized_text(concept_text: str) -> str:
    return " ".join(str(concept_text or "").strip().lower().replace("_", " ").replace("-", " ").split())



def _style_match_score(text: str, bible: dict) -> int:
    if not text:
        return 0
    score = 0
    for phrase in _style_signals(bible):
        normalized_phrase = _normalized_text(phrase)
        if normalized_phrase and normalized_phrase in text:
            score += max(1, len(normalized_phrase.split()))
    return score



def _style_signals(bible: dict) -> list[str]:
    signals: list[str] = []
    for key in ("style", "style_aliases", "palette", "motifs", "wardrobe_rules", "camera_rules", "negative_rules"):
        value = bible.get(key)
        if isinstance(value, str):
            signals.append(value)
        elif isinstance(value, list):
            signals.extend(str(item).strip() for item in value if str(item).strip())
    return signals



def _selection_confidence(scores: dict[str, int], best_style: str) -> float:
    best_score = float(scores.get(best_style, 0))
    total = float(sum(max(0, score) for score in scores.values()))
    if total <= 0.0:
        return 0.0
    return round(best_score / total, 3)



def _selection_margin(scores: dict[str, int], best_style: str) -> float:
    total = float(sum(max(0, score) for score in scores.values()))
    if total <= 0.0:
        return 0.0
    runner_up_scores = [float(score) for style_name, score in scores.items() if style_name != best_style]
    runner_up = max(runner_up_scores) if runner_up_scores else 0.0
    return round((float(scores.get(best_style, 0)) / total) - (runner_up / total), 3)



def _selection_stability(confidence: float, margin: float) -> str:
    if confidence >= STYLE_SELECTION_MIN_CONFIDENCE and margin >= STYLE_SELECTION_MIN_MARGIN:
        return "stable"
    return "contested"



def _runner_up_lanes(scores: dict[str, int], *, exclude: str) -> list[dict]:
    return [
        {"lane": style_name, "score": float(score)}
        for style_name, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        if style_name != exclude
    ]
