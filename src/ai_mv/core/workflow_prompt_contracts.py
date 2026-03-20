from __future__ import annotations

from typing import Iterable


WORKFLOW_NO_TEXT_SUFFIX = (
    ", no text, no typography, no watermark, no logo, no signage, no ui overlay"
    ", no readable letters, no words, no subtitles, ugly, deformed, distorted, low quality, blurry face"
)

WAN_BASE_NEGATIVE = (
    "overexposed, static frame, unclear details, subtitle, watermark, logo, "
    "low quality, jpeg artifacts, ugly, defective, extra fingers, poorly drawn hands, "
    "poorly drawn face, deformed anatomy, disfigured limbs, fused fingers, cluttered background"
)

HOUSE_STYLE_PHRASES = (
    "stunningly beautiful",
    "idol-like",
    "high-end fashion model aesthetic",
    "sharp focus on eyes",
    "8k polish",
    "highly detailed face",
    "aggressive live-action",
    "luxury editorial",
)

FLUX2_BASE_STYLE = (
    "A high-quality 2D digital illustration in a bold Japanese pop visual style, featuring a hip anime heroine with sharp almond eyes, a small mouth, a minimal nose, and thick solid hair shapes.",
    "She has long-limbed streetwear-ready fashion proportions, clean anime linework, thick clean outlines, and flat cel shading with solid cel shadows and matte flat skin color.",
    "The image uses a vibrant pop-art palette with bubblegum pink, aqua cyan, and deep navy, high contrast, bold graphic poster style, asymmetrical framing, and rhythm-game-inspired visual impact.",
    "The background is non-photographic and planar, with simplified environment geometry, geometric shapes, blank sign panels, cut-paper shadow shapes, and minimalist patterns.",
)


def compact_prompt_clause(text: object, max_words: int) -> str:
    cleaned = _clean(text).strip(" ,")
    if not cleaned:
        return ""
    words = [word for word in cleaned.replace(",", " ,").split() if word]
    if max_words > 0:
        words = words[:max_words]
    return " ".join(words).replace(" ,", ",").strip(" ,")


def compose_flux2_prompt(style_contract: object, parts: Iterable[object], max_words: int = 56) -> str:
    base = _base_flux2_style(style_contract)
    variation = compact_prompt_clause(", ".join(part for part in (_clean(part) for part in parts) if part), max_words).rstrip(". ")
    if base and variation:
        return f"{base} {variation}."
    if base:
        return base
    return f"{variation}." if variation else ""


def compose_flux2_tti_prompt(style_contract: object, shot_sentence: object, character_sentence: object = "", background_sentence: object = "") -> str:
    base = _base_flux2_style(style_contract)
    parts = [_sentence(shot_sentence), _sentence(character_sentence), _sentence(background_sentence)]
    detail = " ".join(part for part in parts if part)
    if base and detail:
        return f"{base} {detail}".strip()
    return base or detail


def compose_flux2_refinement_prompt(change_sentence: object, continuity_sentence: object = "") -> str:
    change = _sentence(change_sentence)
    continuity = _sentence(
        continuity_sentence
        or "Maintain the exact character design, flat cel shading, and bold clean outlines"
    )
    return " ".join(part for part in (change, continuity) if part).strip()


def flux2_visual_style_contract(source: object = "", profile_policy: dict | None = None) -> str:
    policy = profile_policy or {}
    source_text = _clean(source).lower()
    detail_parts = [
        "hard cel shading",
        "bold clean outlines",
        "flat color blocking",
        "simple window blocks",
        "anime acting pose",
        "full-figure framing",
    ]
    if str(policy.get("visual_mv_mode", "")).strip() in {"symbolic_edit", "bga_event"}:
        detail_parts.append("symbolic visual beats")
    if str(policy.get("graphic_event_density", "")).strip() == "high":
        detail_parts.append("graphic shape contrast")
    if str(policy.get("environment_event_density", "")).strip() == "high":
        detail_parts.append("designed negative space")
    if str(policy.get("subject_exposure", "")).strip() in {"selective", "low"}:
        detail_parts.append("object-led and space-led framing")
    if str(policy.get("reflection_usage", "")).strip() == "selected_only":
        detail_parts.append("reflection motif only on selected impact beats")
    palette_bias = str(policy.get("palette_bias", "")).strip()
    if palette_bias == "retro_pop_neon":
        detail_parts.append("mint green hot pink lavender purple")
    elif palette_bias == "cyber_pop_high_contrast":
        detail_parts.append("aqua cyan magenta indigo")
    elif palette_bias == "graphic_pop":
        detail_parts.append("coral pink lavender purple blue-black")
    if any(token in source_text for token in ("city pop", "city-pop", "neon night", "late-night city")):
        detail_parts.append("bubblegum pink aqua cyan deep navy")
    if any(token in source_text for token in ("street", "streetwear", "fashion")):
        detail_parts.append("street-fashion silhouette")
    if any(token in source_text for token in ("cyber", "future bass", "electro-pop", "neon")):
        detail_parts.append("cyber-pop accents")
    detail_clause = compact_prompt_clause(", ".join(detail_parts), 22)
    style_sentences = list(FLUX2_BASE_STYLE)
    if detail_clause:
        style_sentences.append(
            f"The frame uses geometric shapes, minimalist patterns, rhythm-game-inspired MV framing, and {detail_clause}."
        )
    return " ".join(sentence.strip() for sentence in style_sentences if sentence.strip())


def sanitize_flux2_positive_text(text: object) -> str:
    cleaned = _clean(text)
    if not cleaned:
        return ""
    banned = (
        "photorealistic",
        "live-action",
        "camera-ready presence",
        "camera-ready face",
        "camera-ready",
        "anime or 2D stylization",
        "2D stylization",
    )
    low = cleaned.lower()
    for token in banned:
        idx = low.find(token.lower())
        while idx >= 0:
            end = idx + len(token)
            cleaned = (cleaned[:idx] + " " + cleaned[end:]).strip(" ,.")
            low = cleaned.lower()
            idx = low.find(token.lower())
    return " ".join(cleaned.replace(" ,", ",").split())


def sanitize_flux2_negative_text(text: object) -> str:
    cleaned = _clean(text)
    if not cleaned:
        return ""
    banned = (
        "anime or 2D stylization",
        "2D stylization",
        "anime stylization",
    )
    low = cleaned.lower()
    for token in banned:
        idx = low.find(token.lower())
        while idx >= 0:
            end = idx + len(token)
            cleaned = (cleaned[:idx] + " " + cleaned[end:]).strip(" ,.")
            low = cleaned.lower()
            idx = low.find(token.lower())
    extras = [
        "photorealistic skin texture",
        "live-action portrait",
        "cinematic realism",
        "soft atmospheric bloom",
        "photographic background depth",
        "realistic architecture detail",
        "readable letters",
        "printed words",
        "chibi",
        "mascot-like",
        "floating head",
        "detached portrait emblem",
        "split-screen",
        "bilateral symmetry",
        "centered two-shot",
        "static cover pose",
        "stiff half-body crop",
        "anime glamour portrait",
        "doll-like character",
        "runway pose",
        "mannequin stance",
        "airbrushed skin shading",
        "glossy hair shine",
        "pin-up glamour",
        "red-black editorial palette",
        "white-silver bloom",
    ]
    merged = ", ".join(part for part in (cleaned, ", ".join(extras)) if part)
    return compact_prompt_clause(merged, 40)


def workflow_no_text_suffix() -> str:
    return WORKFLOW_NO_TEXT_SUFFIX


def workflow_negative_prompt(extra_terms: Iterable[str] | None = None) -> str:
    extras = [compact_prompt_clause(term, 6) for term in list(extra_terms or []) if compact_prompt_clause(term, 6)]
    return ", ".join(part for part in (WAN_BASE_NEGATIVE, ", ".join(extras).strip(", ")) if part).strip(", ")


def leaked_house_phrases(text: object, profile_text: object) -> list[str]:
    haystack = str(text).lower()
    allowed = str(profile_text).lower()
    return [phrase for phrase in HOUSE_STYLE_PHRASES if phrase in haystack and phrase not in allowed]


def _sentence(text: object) -> str:
    cleaned = _clean(text).rstrip(". ")
    return f"{_capitalize_first(cleaned)}." if cleaned else ""


def _clean(text: object) -> str:
    return " ".join(str(text).strip().split())


def _base_flux2_style(style_contract: object) -> str:
    text = _clean(style_contract)
    if text:
        return _sentence(text)
    return " ".join(FLUX2_BASE_STYLE)


def _capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else ""


def _lowercase_first(text: str) -> str:
    text = _clean(text)
    return text[:1].lower() + text[1:] if text else ""
