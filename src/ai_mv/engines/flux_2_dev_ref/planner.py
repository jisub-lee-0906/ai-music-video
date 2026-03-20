from __future__ import annotations

from ai_mv.core.workflow_prompt_contracts import compact_prompt_clause, compose_flux2_prompt, compose_flux2_slot_prompt
from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms, compact_world_atoms


def build_flux2_ref_plan(config: dict, payload: dict) -> dict:
    routes = [dict(row) for row in payload.get("clip_routes", []) if isinstance(row, dict) and bool(row.get("use_ref", False))]
    if not routes:
        return {"items": []}
    items = [_build_item(route, payload["visual_story_bible"], idx) for idx, route in enumerate(routes, start=1)]
    return {"items": items}


def _planner_prompt(config: dict, payload: dict, anchors: list[dict], carry: str) -> str:
    world = compact_world_atoms(payload["visual_story_bible"])
    summary = _anchor_summary(anchors)
    carry_clause = f"carry={carry}; " if carry else ""
    return (
        "deterministic flux2 reference composer; "
        "maintain identity and continuity while preserving the anchor frame intent; "
        "compose compact prompts for the workflow positive text field; "
        "no text, no typography, no watermarks, no logos, no signage, no ui overlay; "
        f"{carry_clause}style={world.get('visual_style_contract', '')}; hero={world['hero_identity']}; world={world['world_rules']}; anchors={summary}."
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
    style_clause = compact_prompt_clause(str(brief.get("visual_style_contract", "")).strip(), 24)
    subject_clause = _subject_clause(brief, anchor)
    action_clause = _action_clause(anchor, section)
    environment_clause = _environment_clause(anchor, section)
    continuity_clause = _continuity_clause(anchor)
    kinetic_clause = _kinetic_clause(anchor)
    lighting_clause = _lighting_clause(anchor, section)
    safety_clause = _safety_clause()
    prompt_text = _compose_flux2_ref_prompt(
        subject_clause,
        action_clause,
        continuity_clause,
        environment_clause,
        kinetic_clause,
        lighting_clause,
        safety_clause,
        style_clause,
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
        "style_clause": style_clause,
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
    world = compact_world_atoms(brief)
    shot_type = str(anchor.get("shot_type", "")).strip().lower().replace("_", " ")
    face = str(anchor.get("face_exposure_level", "")).strip()
    focus = str(anchor.get("prompt_focus", "")).strip().lower()
    render_mode = str(anchor.get("character_render_mode", "")).strip()
    if focus == "object":
        return compact_prompt_clause(f"object-led frame, heroine implied only, single subject in frame, bubblegum pink and aqua cyan with deep navy, thick solid hair shape, off-center full figure, {shot_type} framing, {render_mode}", 24)
    if focus == "space":
        return compact_prompt_clause(f"space-led frame, heroine small as graphic figure, long-limbed fashion figure, single subject in frame, bubblegum pink and aqua cyan with deep navy, off-center moving figure, compressed anime background blocks, whole body readable, {shot_type} framing, {render_mode}", 24)
    if focus == "graphic":
        return compact_prompt_clause(f"graphic-led frame, heroine secondary but fully present, single subject in frame, bubblegum pink and aqua cyan with deep navy, graphic keyframe impact, off-center moving figure, flat background planes, anime acting pose, {shot_type} framing, {render_mode}", 24)
    return compact_prompt_clause(f"{world['heroine_invariants'] or world['hero_identity']}, long-limbed fashion figure, sharp almond eyes, thick solid hair shape, simplified environment geometry, bubblegum pink and aqua cyan with deep navy, anime three-quarter turn or full-figure framing, anime cel acting pose, {shot_type} framing, {face} face exposure, {render_mode}", 28)


def _action_clause(anchor: dict, section: dict) -> str:
    phase = _clip_phase(anchor)
    motion_axis = _workflow_axis(section, anchor)
    pose_phrase = _planned_motion_clause(anchor)
    if phase == "establish":
        return compact_prompt_clause(_join_action(f"set the {motion_axis}", pose_phrase), 16)
    if phase == "resolve":
        return compact_prompt_clause(_join_action(f"land the {motion_axis}", pose_phrase), 16)
    if phase == "advance":
        return compact_prompt_clause(_join_action(f"carry the {motion_axis} forward", pose_phrase), 16)
    return compact_prompt_clause(pose_phrase, 16)


def _environment_clause(anchor: dict, section: dict) -> str:
    palette = str(anchor.get("palette_mode", "")).strip() or str(section.get("palette_hint", "")).strip()
    lighting = str(anchor.get("lighting_fx", "")).strip() or str(section.get("lighting_hint", "")).strip()
    location = _normalize_location_for_prompt(
        str(section.get("location_family", "")).strip()
        or str(section.get("location_anchor", "")).strip()
        or str(anchor.get("scene_detail", "")).strip()
    )
    space_event = str(anchor.get("space_event", "")).strip()
    composition = str(anchor.get("composition_shape", "")).strip()
    parts = [location, _normalize_scene_for_prompt(str(anchor.get("scene_detail", "")).strip()), space_event, composition, palette, lighting]
    return compact_prompt_clause(", ".join(part for part in parts if part), 18)


def _normalize_location_for_prompt(location: str) -> str:
    text = str(location).strip()
    if not text:
        return text
    if "reflective threshold" in text.lower():
        return text
    replacements = (
        ("station front", "graphic station block"),
        ("station frontage", "graphic station block"),
        ("ticket gate", "gate silhouettes"),
        ("ticket gates", "gate silhouettes"),
        ("open night lane", "flat lane blocks"),
        ("reflective threshold", "threshold plane"),
        ("lit passage", "lit passage blocks"),
        ("sheltered edge", "sheltered edge plane"),
        ("mirrored glass", "dark glass plane"),
        ("street", "street blocks"),
        ("corridor", "passage blocks"),
    )
    out = text
    lowered = out.lower()
    for old, new in replacements:
        if old in lowered:
            out = out.replace(old, new).replace(old.title(), new)
            lowered = out.lower()
    return out


def _normalize_scene_for_prompt(scene: str) -> str:
    text = str(scene).strip()
    if not text:
        return text
    replacements = (
        ("late train station frontage", "graphic station frontage"),
        ("station frontage", "graphic station frontage"),
        ("ticket gate", "gate silhouettes"),
        ("ticket gates", "gate silhouettes"),
        ("wet, wide street frontage", "wet pavement plane"),
        ("wet street frontage", "wet pavement plane"),
        ("station front", "station block"),
        ("platform", "platform block"),
        ("window frame", "window block"),
        ("corridor", "compressed passage blocks"),
        ("street plane", "flat street plane"),
        ("street opening", "open block plane"),
        ("open street edge", "open block edge"),
        ("open night lane", "flat lane blocks"),
        ("lane", "lane block"),
        ("two figures offset", "a single figure with an offset echo"),
        ("paired figures", "a single figure"),
        ("two figures", "a single figure"),
        ("mirrored glass", "dark glass plane"),
    )
    out = text
    lowered = out.lower()
    for old, new in replacements:
        if old in lowered:
            out = out.replace(old, new).replace(old.title(), new)
            lowered = out.lower()
    return out


def _continuity_clause(anchor: dict) -> str:
    relation = str(anchor.get("space_relation", "")).strip() or "keeping the same space relation"
    phase = _clip_phase(anchor)
    continuity = str(anchor.get("continuity_lock", "")).strip() or "same heroine in one world"
    basis = str(anchor.get("continuity_basis", "")).strip() or "world"
    strategy = str(anchor.get("anchor_strategy", "")).strip().replace("_", " ") or "refine anchor"
    return compact_prompt_clause(f"{continuity}, continuity basis {basis}, {relation}, phase {phase}, {strategy}", 28)


def _compose_flux2_ref_prompt(
    subject_clause: str,
    action_clause: str,
    continuity_clause: str,
    environment_clause: str,
    kinetic_clause: str,
    lighting_clause: str,
    safety_clause: str,
    style_clause: str,
) -> str:
    return compose_flux2_slot_prompt(
        style_clause,
        [
            subject_clause,
            environment_clause,
            action_clause,
            continuity_clause,
            kinetic_clause,
            lighting_clause,
            safety_clause,
        ],
    )


def _anchor_summary(anchors: list[dict]) -> str:
    return ", ".join(_anchor_summary_row(a) for a in anchors)


def _anchor_summary_row(anchor: dict) -> str:
    sid = str(anchor["shot_id"])
    section = str(anchor.get("section_name", "section"))
    label = str(anchor.get("section_label", section))
    shot_type = str(anchor.get("shot_type", "CHAR_MASTER"))
    relation = str(anchor.get("space_relation", "")).strip() or "space stays stable"
    phase = _clip_phase(anchor)
    kinetic = str(anchor.get("kinetic_transition", "")).strip() or "none"
    intensity = str(anchor.get("kinetic_intensity", "")).strip() or "normal"
    return f"{sid}({section}|{label}|{shot_type}|{relation}|{phase}|{kinetic}|{intensity})"


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


def _kinetic_clause(anchor: dict) -> str:
    transition = str(anchor.get("kinetic_transition", "")).strip().replace("_", " ")
    intensity = str(anchor.get("kinetic_intensity", "")).strip().lower()
    if not transition and not intensity:
        return ""
    parts = []
    if transition:
        parts.append(f"kinetic move {transition}")
    if intensity:
        parts.append(f"intensity {intensity}")
    return compact_prompt_clause(", ".join(parts), 12)


def _lighting_clause(anchor: dict, section: dict) -> str:
    lighting = str(anchor.get("lighting_fx", "")).strip() or str(section.get("lighting_hint", "")).strip()
    if not lighting:
        return "cinematic lighting"
    return compact_prompt_clause(f"cinematic lighting, lighting accent {lighting}", 14)


def _safety_clause() -> str:
    return "no text, no typography, no watermarks, no logos, no signage, no ui overlay"


def _kinetic_axis(anchor: dict) -> str:
    transition = str(anchor.get("kinetic_transition", "")).strip().lower()
    mapping = {
        "snap_zoom_in": "forward snap",
        "snap_zoom_out": "recoil pullback",
        "whip_pan_left": "left whip line",
        "whip_pan_right": "right whip line",
        "crash_push_in": "impact push",
        "smash_reframe": "reframe break",
        "strobe_jump": "strobe burst",
        "match_cut_pose": "pose impact",
    }
    return mapping.get(transition, "pose shift")


def _beat_atoms(brief: dict, anchor: dict) -> dict:
    beat_id = str(anchor.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(anchor.get("section_name", "")), beat_id)


def _workflow_axis(section: dict, anchor: dict) -> str:
    raw = compact_prompt_clause(section.get("motion_axis", ""), 4)
    if raw and "," not in raw and "." not in raw:
        return raw
    return _kinetic_axis(anchor)


def _planned_motion_clause(anchor: dict) -> str:
    text = " ".join(str(anchor.get("workflow_motion_clause", "")).strip().rstrip(". ").split())
    if not text:
        raise RuntimeError(f"workflow_motion_clause missing for flux2_ref shot: {anchor.get('shot_id', '')}")
    if text.lower().startswith("she "):
        text = text[4:].strip()
    return text
def _join_action(prefix: str, action: str) -> str:
    text = str(action).strip()
    if not text:
        return str(prefix).strip()
    first = text.split(" ", 1)[0].lower()
    if first in {"staying", "holding", "remaining", "keeping"}:
        linker = "while"
    elif first.endswith("ing"):
        linker = "by"
    elif first in {"under", "over", "through", "into", "across", "inside", "between", "before", "after", "while", "as"}:
        linker = "as"
    elif first in {"a", "an", "the"}:
        linker = "through"
    else:
        linker = "with"
    return f"{str(prefix).strip()} {linker} {text}".strip()
