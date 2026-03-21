from __future__ import annotations

from ai_mv.core.workflow_prompt_contracts import clean_prompt_clause
from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms, compact_world_atoms


def build_flux2_ref_plan(config: dict, payload: dict) -> dict:
    routes = [dict(row) for row in payload.get("clip_routes", []) if isinstance(row, dict) and bool(row.get("use_ref", False))]
    if not routes:
        return {"items": []}
    items = [_build_item(route, payload["visual_story_bible"], idx) for idx, route in enumerate(routes, start=1)]
    return {"items": items}


def _planner_prompt(config: dict, payload: dict, anchors: list[dict], carry: str) -> str:
    summary = _anchor_summary(anchors)
    return (
        "deterministic flux2 reference composer; "
        "maintain the same character and world while changing pose, action, or framing; "
        "compose short continuity prompts only; "
        "follow this formula: The same heroine + changed action or pose + camera or framing + flat cel shading and thick clean outlines; "
        "do not restate full background, palette, or long style paragraphs; "
        "no text, no typography, no watermarks, no logos, no signage, no ui overlay; "
        f"anchors={summary}."
    )


def _flux2_ref_planner_batch_size(config: dict) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("flux2_ref_planner_batch_size", 4) if isinstance(render, dict) else 4
    try:
        return max(1, min(20, int(raw)))
    except Exception:
        return 4


def _build_item(anchor: dict, brief: dict, timeline_index: int) -> dict:
    section = _beat_atoms(brief, anchor)
    subject_clause = _subject_clause(brief, anchor)
    action_clause = _action_clause(anchor, section)
    camera_clause = _camera_clause(anchor)
    continuity_clause = _continuity_clause(anchor)
    prompt_text = _compose_flux2_ref_prompt(
        subject_clause,
        action_clause,
        camera_clause,
        continuity_clause,
    )
    ref = str(anchor.get("identity_anchor", anchor["anchor"]))
    return {
        "shot_id": anchor["shot_id"],
        "chain_key": _chain_key(anchor),
        "timeline_index": int(timeline_index),
        "anchor": anchor["anchor"],
        "ref": ref,
        "style_ref": "",
        "prompt_text": prompt_text,
        "style_clause": "",
        "subject_clause": subject_clause,
        "action_clause": action_clause,
        "camera_clause": camera_clause,
        "environment_clause": "",
        "continuity_clause": continuity_clause,
        "duration_sec": float(anchor["duration_sec"]),
        "clip_index": int(anchor.get("clip_index", 1)),
        "clip_count": int(anchor.get("clip_count", 1)),
        "clip_phase": _clip_phase(anchor),
        "shot_type": str(anchor["shot_type"]),
        "section_name": str(anchor.get("section_name", "section")),
        "section_label": str(anchor.get("section_label", anchor.get("section_name", "section"))),
        "is_chorus": bool(anchor.get("is_chorus", False)),
        "camera_language": str(anchor.get("camera_language", "")),
        "pose_delta": str(anchor.get("pose_delta", "")),
        "emotion": str(anchor.get("emotion", "")),
        "scene_detail": str(anchor.get("scene_detail", "")),
        "motion_hint": str(anchor.get("motion_hint", "")),
        "space_relation": str(anchor.get("space_relation", "")),
        "kinetic_transition": str(anchor.get("kinetic_transition", "")),
        "lighting_fx": str(anchor.get("lighting_fx", "")),
        "kinetic_intensity": str(anchor.get("kinetic_intensity", "")),
        "route_reason": str(anchor.get("route_reason", "")),
        "scene_change_level": str(anchor.get("scene_change_level", "evolve")),
        "anchor_strategy": str(anchor.get("anchor_strategy", "refine_anchor")),
        "continuity_basis": str(anchor.get("continuity_basis", "world")),
    }


def _chain_key(anchor: dict) -> str:
    return f"{str(anchor.get('shot_id', '')).strip()}:{int(anchor.get('clip_index', 1))}"


def _subject_clause(brief: dict, anchor: dict) -> str:
    return "The same anime girl"


def _ref_heroine_phrase(text: str) -> str:
    cleaned = str(text).strip()
    low = cleaned.lower()
    prefixes = (
        "same heroine throughout the video,",
        "same heroine throughout the video",
        "the same heroine throughout the video,",
        "the same heroine throughout the video",
    )
    for prefix in prefixes:
        if low.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip(" ,")
            break
    shortened = clean_prompt_clause(cleaned or "anime girl")
    if not shortened:
        return "anime girl"
    if shortened.lower().startswith("stylized east asian heroine"):
        return "anime girl"
    return shortened


def _action_clause(anchor: dict, section: dict) -> str:
    pose_phrase = _planned_motion_clause(anchor)
    return clean_prompt_clause(pose_phrase)


def _camera_clause(anchor: dict) -> str:
    composition = clean_prompt_clause(str(anchor.get("composition_shape", "")).strip())
    camera = clean_prompt_clause(str(anchor.get("camera_language", "")).strip())
    clause = camera or composition
    if not clause:
        return ""
    return clause


def _continuity_clause(anchor: dict) -> str:
    return "Flat cel shading, thick clean outlines"


def _compose_flux2_ref_prompt(
    subject_clause: str,
    action_clause: str,
    camera_clause: str,
    continuity_clause: str,
) -> str:
    action_text = clean_prompt_clause(action_clause)
    if action_text and not action_text.lower().startswith(("now ", "while ", "as ")):
        action_text = f"now {action_text}"
    lead = ", ".join(
        part
        for part in (
            subject_clause,
            action_text,
        )
        if str(part).strip()
    )
    parts = [lead, camera_clause, continuity_clause]
    return " ".join(_sentence(part) for part in parts if str(part).strip()).strip()




def _anchor_summary(anchors: list[dict]) -> str:
    return ", ".join(_anchor_summary_row(a) for a in anchors)


def _anchor_summary_row(anchor: dict) -> str:
    sid = str(anchor["shot_id"])
    shot_type = str(anchor.get("shot_type", "CHAR_MASTER"))
    focus = str(anchor.get("prompt_focus", "")).strip().lower() or "heroine"
    phase = _clip_phase(anchor)
    kinetic = str(anchor.get("kinetic_transition", "")).strip() or "none"
    pose = clean_prompt_clause(str(anchor.get("pose_delta", "")).strip()) or "pose shift"
    camera = clean_prompt_clause(str(anchor.get("camera_language", "")).strip()) or "framing shift"
    return f"{sid}({shot_type}|{focus}|{phase}|{kinetic}|{pose}|{camera})"


def _sentence(text: str) -> str:
    cleaned = str(text).strip().rstrip(". ")
    return f"{cleaned}."


def _clip_phase(anchor: dict) -> str:
    index = int(anchor.get("clip_index", 1))
    count = int(anchor.get("clip_count", 1))
    if count <= 1:
        return "single beat"
    if index <= 1:
        return "establish"
    if index >= count:
        return "resolve"
    return "advance"


def _beat_atoms(brief: dict, anchor: dict) -> dict:
    beat_id = str(anchor.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(anchor.get("section_name", "")), beat_id)


def _planned_motion_clause(anchor: dict) -> str:
    text = " ".join(str(anchor.get("pose_delta", "")).strip().rstrip(". ").split())
    if text:
        return text
    text = " ".join(str(anchor.get("workflow_motion_clause", "")).strip().rstrip(". ").split())
    if not text:
        raise RuntimeError(f"pose_delta missing for flux2_ref shot: {anchor.get('shot_id', '')}")
    if text.lower().startswith("she "):
        text = text[4:].strip()
    elif text.lower().startswith("the girl "):
        text = text[9:].strip()
    return text
