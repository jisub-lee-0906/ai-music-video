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



def _style_pack(style_name: str) -> dict:
    normalized = str(style_name or "").strip()
    if normalized not in STYLE_PACKS:
        raise KeyError(f"unknown style pack: {normalized}")
    return STYLE_PACKS[normalized]



def resolve_style_name(concept_text: str, *, default_style_name: str | None = None) -> str:
    text = _normalized_text(concept_text)
    scores = {style_name: _style_match_score(text, pack["bible"]()) for style_name, pack in STYLE_PACKS.items()}
    best_style = max(scores, key=scores.get)
    if scores[best_style] > 0:
        return best_style
    if default_style_name is not None and str(default_style_name).strip():
        return str(default_style_name).strip() if _style_pack(default_style_name) else ""
    raise KeyError("style_name could not be resolved from concept_text and no explicit default_style_name was provided")


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
