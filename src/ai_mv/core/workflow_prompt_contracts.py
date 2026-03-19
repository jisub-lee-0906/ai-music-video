from __future__ import annotations

from typing import Iterable


WORKFLOW_NO_TEXT_SUFFIX = (
    ", no text, no typography, no watermark, no logo, no signage, no ui overlay"
    ", ugly, deformed, distorted, low quality, blurry face"
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
    "flat 2d graphic character design",
    "hard cel shading",
    "bold clean outlines",
    "poster-like music-video layout",
    "high-chroma pop color blocking",
    "simplified icon face",
    "sticker-like silhouette design",
    "non-photorealistic image design",
)


def compact_prompt_clause(text: object, max_words: int) -> str:
    cleaned = _clean(text).strip(" ,")
    if not cleaned:
        return ""
    words = [word for word in cleaned.replace(",", " ,").split() if word]
    if max_words > 0:
        words = words[:max_words]
    return " ".join(words).replace(" ,", ",").strip(" ,")


def compact_prompt_sentence(parts: Iterable[object], max_words: int) -> str:
    text = ", ".join(part for part in (_clean(part) for part in parts) if part)
    return _sentence(compact_prompt_clause(text, max_words))


def compact_natural_sentence(text: object, max_words: int) -> str:
    cleaned = compact_prompt_clause(text, max_words)
    return _sentence(cleaned)


def compose_image_prompt(parts: Iterable[object], max_words: int = 48) -> str:
    text = ", ".join(part for part in (_clean(part) for part in parts) if part)
    cleaned = compact_prompt_clause(text, max_words).rstrip(". ")
    return f"{cleaned}." if cleaned else ""


def compose_flux2_prompt(style_contract: object, parts: Iterable[object], max_words: int = 56) -> str:
    base = [style_contract] if str(style_contract).strip() else list(FLUX2_BASE_STYLE)
    text = ", ".join(part for part in (_clean(part) for part in [*base, *parts]) if part)
    cleaned = compact_prompt_clause(text, max_words).rstrip(". ")
    return f"{cleaned}." if cleaned else ""


def compose_flux2_slot_prompt(style_contract: object, slots: Iterable[object]) -> str:
    parts: list[str] = []
    base = compact_prompt_clause(style_contract, 18)
    if base:
        parts.append(base)
    for slot in slots:
        cleaned = compact_prompt_clause(slot, 12)
        if cleaned:
            parts.append(cleaned)
    cleaned = ", ".join(part for part in parts if part).rstrip(". ")
    return f"{cleaned}." if cleaned else ""


def flux2_visual_style_contract(source: object = "", profile_policy: dict | None = None) -> str:
    policy = profile_policy or {}
    source_text = _clean(source).lower()
    parts = list(FLUX2_BASE_STYLE)
    parts.extend(
        [
            "minimal facial detail",
            "sharp heavy-lid eye shape",
            "small mouth",
            "minimal nose",
            "2-3 dominant color blocks",
            "angular fashion silhouette",
            "street-pop graphic attitude",
            "toy-like deformed proportions",
            "limited poster contrast palette",
        ]
    )
    if str(policy.get("visual_mv_mode", "")).strip() in {"symbolic_edit", "bga_event"}:
        parts.append("symbolic visual beats")
    if str(policy.get("graphic_event_density", "")).strip() == "high":
        parts.append("graphic shape contrast")
    if str(policy.get("environment_event_density", "")).strip() == "high":
        parts.append("designed negative space")
    if str(policy.get("subject_exposure", "")).strip() in {"selective", "low"}:
        parts.append("object-led and space-led framing")
    if str(policy.get("reflection_usage", "")).strip() == "selected_only":
        parts.append("reflection motif only on selected impact beats")
    palette_bias = str(policy.get("palette_bias", "")).strip()
    if palette_bias == "retro_pop_neon":
        parts.append("retro-pop neon palette discipline")
    elif palette_bias == "cyber_pop_high_contrast":
        parts.append("cyber-pop high-contrast palette")
    elif palette_bias == "graphic_pop":
        parts.append("graphic pop palette discipline")
    if any(token in source_text for token in ("city pop", "city-pop", "neon night", "late-night city")):
        parts.append("city-pop neon night palette")
    if any(token in source_text for token in ("street", "streetwear", "fashion")):
        parts.append("street-fashion silhouette")
    if any(token in source_text for token in ("cyber", "future bass", "electro-pop", "neon")):
        parts.append("cyber-pop accents")
    return compact_prompt_clause(", ".join(parts), 36)


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
    ]
    merged = ", ".join(part for part in (cleaned, ", ".join(extras)) if part)
    return compact_prompt_clause(merged, 40)


def compose_video_prompt(subject_motion: object, camera_relation: object, environment_detail: object) -> str:
    first = _sentence(compact_prompt_clause(subject_motion, 26))
    relation = compact_prompt_clause(camera_relation, 14)
    environment = compact_prompt_clause(environment_detail, 16)
    if relation and environment:
        second = _sentence(f"{_capitalize_first(relation)}, while {_lowercase_first(environment)}")
    elif environment:
        second = _sentence(environment)
    else:
        second = _sentence(relation)
    return " ".join(part for part in (first, second) if part).strip()


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


def _capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else ""


def _lowercase_first(text: str) -> str:
    text = _clean(text)
    return text[:1].lower() + text[1:] if text else ""
