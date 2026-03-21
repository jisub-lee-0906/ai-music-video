from __future__ import annotations

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


def _sentence(text: object) -> str:
    cleaned = _clean(text).rstrip(". ")
    return f"{_capitalize_first(cleaned)}." if cleaned else ""


def _clean(text: object) -> str:
    return " ".join(str(text).strip().split())


def _capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else ""


