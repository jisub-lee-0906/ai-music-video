from __future__ import annotations

from typing import Iterable

WAN_BASE_NEGATIVE = (
    "overexposed, static frame, unclear details, subtitle, watermark, logo, "
    "low quality, jpeg artifacts, ugly, defective, extra fingers, poorly drawn hands, "
    "poorly drawn face, deformed anatomy, disfigured limbs, fused fingers, cluttered background"
)

def clean_prompt_clause(text: object) -> str:
    return _clean(text).strip(" ,.")


def compose_flux2_tti_prompt(
    style_contract: object,
    subject_action_sentence: object,
    background_sentence: object = "",
    camera_framing_sentence: object = "",
) -> str:
    base = _sentence(style_contract)
    parts = [
        _sentence(subject_action_sentence),
        _sentence(background_sentence),
        _sentence(camera_framing_sentence),
    ]
    detail = " ".join(part for part in parts if part)
    if base and detail:
        return f"{base} {detail}".strip()
    return base or detail


def workflow_negative_prompt(extra_terms: Iterable[str] | None = None) -> str:
    extras = [clean_prompt_clause(term) for term in list(extra_terms or []) if clean_prompt_clause(term)]
    return ", ".join(part for part in (WAN_BASE_NEGATIVE, ", ".join(extras).strip(", ")) if part).strip(", ")


def _sentence(text: object) -> str:
    cleaned = _clean(text).rstrip(". ")
    return f"{_capitalize_first(cleaned)}." if cleaned else ""


def _clean(text: object) -> str:
    return " ".join(str(text).strip().split())


def _capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else ""


