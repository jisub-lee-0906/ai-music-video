from __future__ import annotations

from ai_mv.core.director_brief import build_director_brief_intent


def verbalize_ref_prompts(config: dict, rows: list[dict]) -> dict[str, str]:
    if not rows:
        return {}
    brief = build_director_brief_intent(config) if isinstance(config, dict) and config else {}
    face_lock = _face_lock(brief)
    motifs = _motifs(brief)
    subject_form = _subject_form(brief)
    out: dict[str, str] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        parts = [
            _label("SubjectForm", subject_form),
            _label("Action", row.get("action", "")),
            _label("Place", row.get("place", "")),
            _label("Detail", row.get("literal_image", "")),
            _label("Carry", row.get("carry", "")),
            _label("Framing", row.get("framing", "")),
            _label("Focus", row.get("segment_focus", "")),
            _label("Lines", ", ".join(_lyric_lines(row))),
            _label("Motifs", motifs),
            face_lock,
        ]
        out[shot_id] = " ".join(part for part in parts if part).strip()
    return out


def verbalize_wan_prompts(config: dict, rows: list[dict]) -> dict[str, str]:
    if not rows:
        return {}
    brief = build_director_brief_intent(config) if isinstance(config, dict) and config else {}
    subject_form = _subject_form(brief)
    out: dict[str, str] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        parts = [
            _label("SubjectForm", subject_form),
            _label("Motion", row.get("bridge_action", "")),
            _label("Place", row.get("place", "")),
            _label("Carry", row.get("carry", "")),
            _label("Transition", f"{_clean(row.get('start_ref_shot_id', ''))} -> {_clean(row.get('end_ref_shot_id', ''))}"),
            _label("Duration", f"{float(row.get('duration_sec', 0.0) or 0.0):.3f}s"),
        ]
        out[shot_id] = " ".join(part for part in parts if part).strip()
    return out


def _subject_form(brief: dict) -> str:
    voice = str(brief.get("profile_voice", "")).strip().lower()
    if "duo" in voice or "group" in voice or "mixed" in voice:
        return "plural"
    if "female" in voice or "woman" in voice or "girl" in voice:
        return "single female"
    if "male" in voice or "man" in voice or "boy" in voice:
        return "single male"
    return "single person"


def _face_lock(brief: dict) -> str:
    voice = str(brief.get("profile_voice", "")).strip().lower()
    if "duo" in voice or "group" in voice or "mixed" in voice:
        return "Keep the faces consistent."
    return "Keep the face."


def _motifs(brief: dict) -> str:
    rows = [str(x).strip() for x in brief.get("profile_motifs", []) if str(x).strip()]
    return ", ".join(rows[:4])


def _lyric_lines(row: dict) -> list[str]:
    return [str(x).strip() for x in row.get("lyric_lines", []) if str(x).strip()]


def _label(label: str, value: object) -> str:
    text = _clean(value)
    if not text:
        return ""
    return f"{label}: {text}."

def _clean(text: object) -> str:
    return " ".join(str(text).strip().rstrip(". ").split())
