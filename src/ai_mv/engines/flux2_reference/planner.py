from __future__ import annotations

from ai_mv.engines.visual_bridge.brief_views import compact_section_atoms, compact_world_atoms


def build_flux2_ref_plan(config: dict, payload: dict) -> dict:
    routes = [dict(row) for row in payload.get("clip_routes", []) if isinstance(row, dict) and bool(row.get("use_ref", False))]
    if not routes:
        return {"items": []}
    items = [_build_item(route, payload["visual_brief"]) for route in routes]
    return {"items": items}


def _planner_prompt(config: dict, payload: dict, anchors: list[dict], carry: str) -> str:
    world = compact_world_atoms(payload["visual_brief"])
    summary = _anchor_summary(anchors)
    carry_clause = f"carry={carry}; " if carry else ""
    escalation = " Final Chorus should feel like the visual peak." if any("final chorus" in str(anchor.get("section_label", "")).lower() for anchor in anchors) else ""
    return (
        "deterministic flux2 reference composer; "
        f"{carry_clause}hero={world['hero_identity']}; world={world['world_rules']}; anchors={summary}.{escalation}"
    )


def _flux2_ref_planner_batch_size(config: dict) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("flux2_ref_planner_batch_size", 4) if isinstance(render, dict) else 4
    try:
        return max(1, min(20, int(raw)))
    except Exception:
        return 4


def _build_item(anchor: dict, brief: dict) -> dict:
    section = compact_section_atoms(brief, str(anchor.get("section_name", "")))
    subject_clause = _subject_clause(brief, anchor)
    action_clause = _action_clause(anchor, section)
    environment_clause = _environment_clause(anchor, section)
    continuity_clause = _continuity_clause(anchor)
    prompt_text = _compose_flux2_ref_prompt(subject_clause, action_clause, continuity_clause, environment_clause)
    ref = str(anchor.get("identity_anchor", anchor["anchor"]))
    return {
        "shot_id": anchor["shot_id"],
        "anchor": anchor["anchor"],
        "ref": ref,
        "style_ref": "",
        "prompt_text": prompt_text,
        "subject_clause": subject_clause,
        "action_clause": action_clause,
        "environment_clause": environment_clause,
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
        "route_reason": str(anchor.get("route_reason", "")),
    }


def _subject_clause(brief: dict, anchor: dict) -> str:
    world = compact_world_atoms(brief)
    shot_type = str(anchor.get("shot_type", "")).strip().lower().replace("_", " ")
    return _trim_words(f"{world['hero_identity']}, {shot_type} framing", 20)


def _action_clause(anchor: dict, section: dict) -> str:
    phase = _clip_phase(anchor)
    motion_axis = str(section.get("motion_axis", "")).strip() or "pose shift"
    pose = str(anchor.get("pose_delta", "")).strip() or str(section.get("story_beat", "")).strip()
    pose_phrase = _action_fragment(pose)
    if phase == "establish":
        return _trim_words(f"set the {motion_axis} with {pose_phrase}", 16)
    if phase == "resolve":
        return _trim_words(f"land the {motion_axis} with {pose_phrase}", 16)
    if phase == "advance":
        return _trim_words(f"carry the {motion_axis} forward with {pose_phrase}", 16)
    return _trim_words(pose_phrase, 16)


def _environment_clause(anchor: dict, section: dict) -> str:
    palette = str(section.get("palette_hint", "")).strip()
    lighting = str(section.get("lighting_hint", "")).strip()
    location = str(section.get("location_anchor", "")).strip() or str(anchor.get("scene_detail", "")).strip()
    parts = [location, palette, lighting]
    return _trim_words(", ".join(part for part in parts if part), 20)


def _continuity_clause(anchor: dict) -> str:
    relation = str(anchor.get("space_relation", "")).strip() or "keeping the same space relation"
    phase = _clip_phase(anchor)
    return _trim_words(f"{relation}, phase {phase}", 22)


def _compose_flux2_ref_prompt(subject_clause: str, action_clause: str, continuity_clause: str, environment_clause: str) -> str:
    parts = [subject_clause, action_clause, continuity_clause, environment_clause]
    return _sentence(", ".join(part for part in parts if part))


def _anchor_summary(anchors: list[dict]) -> str:
    return ", ".join(_anchor_summary_row(a) for a in anchors)


def _anchor_summary_row(anchor: dict) -> str:
    sid = str(anchor["shot_id"])
    section = str(anchor.get("section_name", "section"))
    label = str(anchor.get("section_label", section))
    shot_type = str(anchor.get("shot_type", "CHAR_MASTER"))
    relation = str(anchor.get("space_relation", "")).strip() or "space stays stable"
    phase = _clip_phase(anchor)
    return f"{sid}({section}|{label}|{shot_type}|{relation}|{phase})"


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


def _trim_words(text: str, max_words: int) -> str:
    words = [word for word in str(text).replace(",", " ,").split() if word]
    out = " ".join(words[: max_words]).replace(" ,", ",")
    return out.strip(" ,")


def _action_fragment(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    if not cleaned:
        return ""
    low = cleaned.lower()
    if low.startswith("she "):
        cleaned = cleaned[4:]
    return cleaned[:1].lower() + cleaned[1:] if cleaned else ""
