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
