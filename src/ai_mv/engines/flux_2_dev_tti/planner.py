from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_shot_timeline
from ai_mv.core.contracts.prompt_schema import KINETIC_INTENSITIES, KINETIC_TRANSITIONS, SHOT_TYPES, shot_timeline_schema
from ai_mv.core.profile_policy import resolve_profile_policy
from ai_mv.core.workflow_prompt_contracts import compose_flux2_tti_prompt
from ai_mv.core.visual_pipeline import attach_tti_metadata
from ai_mv.infra.codex_cli_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    story_bible = payload["visual_story_bible"]
    lyrics_timeline = payload["lyrics_timeline"]
    spec = _generate_tti_spec(config, payload, story_bible)
    plan = normalize_shot_timeline(spec, story_bible.get("lyric_beats", []))
    shots = _assign_story_metadata(plan["shots"], lyrics_timeline, story_bible)
    return {"master_anchor": plan["master_anchor"], "shots": shots}


def build_tti_preview_prompt(config: dict, payload: dict) -> str:
    return _planner_prompt(config, payload)


def _planner_prompt(config: dict, payload: dict) -> str:
    story_bible = payload["visual_story_bible"]
    timeline = payload["lyrics_timeline"]
    policy = story_bible.get("resolved_profile_policy", resolve_profile_policy(config)) if isinstance(story_bible, dict) else resolve_profile_policy(config)
    beat_manifest = _tti_beat_manifest(story_bible)
    beat_count = len(beat_manifest)
    return (
        "Write a shot timeline for downstream Flux and video workflows. "
        "Return strict JSON only with shape {\"master_anchor\":{...},\"shots\":[...]}. No prose outside JSON. "
        "Create exactly one shot item for every lyric beat in order. "
        f"Exact shot count contract: return exactly {beat_count} shots. "
        "The shots array length must equal the lyric beat count exactly; do not add extra shots, do not omit shots. "
        "Use each lyric_beat_id exactly once and preserve the exact manifest order. "
        "master_anchor prompt_text should contain only stable identity and world facts. "
        "Every shot must include lyric_beat_id,shot_type,camera_language,pose_delta,emotion,scene_detail,motion_hint,workflow_motion_clause,space_relation,edit_role,continuity_lock,scene_change_level,anchor_strategy,continuity_basis,clip_count,start_frame,end_frame,kinetic_transition,lighting_fx,kinetic_intensity. "
        "scene_change_level must be one of hold,evolve,shift,reset. "
        "anchor_strategy must be one of reuse_anchor,refine_anchor,new_anchor. "
        "continuity_basis must be one of heroine,motif,world,none. "
        "TTI creates new scene anchors and ref refines an existing anchor for continuity. "
        "pose_delta should be the changed pose or action phrase that ref can reuse directly, for example 'fiercely smashing the guitar onto the ground, bending her knees'. "
        "workflow_motion_clause should be a full WAN action clause beginning with a finite verb phrase that fits after 'The girl', for example 'swings the guitar down with extreme force'. "
        "camera_language should be a clean camera or framing phrase such as 'Extreme low-angle dynamic shot'. "
        "scene_detail and space_relation should be plain drawable natural English. "
        "Use the story bible and lyric beat as the source of truth. "
        "Make nearby beats meaningfully different in framing, action, or visual state. "
        "Honor story-bible prompt_focus, edit_device, symbolic_image, motif_object, space_event, and composition_shape when deciding shot_type. "
        "If prompt_focus is object, space, or graphic, do not collapse back into a default heroine close-up. "
        "Use shot_type as a storytelling choice, not a default. "
        f"Allowed shot types={', '.join(SHOT_TYPES)}. "
        f"Allowed kinetic transitions={', '.join(KINETIC_TRANSITIONS)}. "
        f"Allowed kinetic intensities={', '.join(KINETIC_INTENSITIES)}. "
        "Honor the profile policy when choosing shot types and face exposure. "
        f"Profile policy={_policy_digest(policy)}. "
        f"Shot count manifest={'; '.join(beat_manifest)}. "
        f"Story bible={_story_bible_digest(story_bible)}. "
        f"Lyric timeline={_timeline_digest(timeline)}."
    )


def _generate_tti_spec(config: dict, payload: dict, story_bible: dict, attempts: int = 3) -> dict:
    prompt = _planner_prompt(config, payload)
    expected_ids = _expected_lyric_beat_ids(story_bible)
    current_prompt = prompt
    last_exc: Exception | None = None
    for attempt in range(1, max(1, int(attempts)) + 1):
        try:
            spec = generate_structured(config, current_prompt, shot_timeline_schema(), attempts=1)
        except TypeError:
            spec = generate_structured(config, current_prompt, shot_timeline_schema())
        try:
            _validate_tti_spec_contract(spec, expected_ids)
            return spec
        except RuntimeError as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            current_prompt = _tti_repair_prompt(prompt, spec, expected_ids, str(exc))
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("tti planner failed without a validation error")


def _validate_tti_spec_contract(spec: dict, expected_ids: list[str]) -> None:
    shots = [row for row in spec.get("shots", []) if isinstance(row, dict)]
    actual_ids = [str(row.get("lyric_beat_id", "")).strip() for row in shots]
    if len(shots) != len(expected_ids):
        raise RuntimeError(f"shot count mismatch: expected={len(expected_ids)} actual={len(shots)}")
    if any(not beat_id for beat_id in actual_ids):
        raise RuntimeError("shot contract mismatch: blank lyric_beat_id present")
    if actual_ids != expected_ids:
        missing = [beat_id for beat_id in expected_ids if beat_id not in actual_ids]
        extra = [beat_id for beat_id in actual_ids if beat_id not in set(expected_ids)]
        detail = []
        if missing:
            detail.append(f"missing={','.join(missing[:6])}")
        if extra:
            detail.append(f"extra={','.join(extra[:6])}")
        if not detail:
            detail.append("order mismatch")
        raise RuntimeError("shot contract mismatch: " + "; ".join(detail))


def _tti_repair_prompt(base_prompt: str, spec: dict, expected_ids: list[str], error: str) -> str:
    shots = [row for row in spec.get("shots", []) if isinstance(row, dict)]
    actual_ids = [str(row.get("lyric_beat_id", "")).strip() for row in shots if str(row.get("lyric_beat_id", "")).strip()]
    return (
        f"{base_prompt}\n\n"
        "Previous output failed the exact shot contract. "
        f"Failure={error}. "
        f"Expected lyric_beat_id order={', '.join(expected_ids)}. "
        f"Previous lyric_beat_id order={', '.join(actual_ids)}. "
        "Repair the JSON only. "
        "Keep master_anchor, but rewrite shots so that shots.length matches the expected count exactly and each expected lyric_beat_id appears once in the same order."
    )


def _expected_lyric_beat_ids(story_bible: dict) -> list[str]:
    return [
        str(beat.get("beat_id", "")).strip()
        for beat in story_bible.get("lyric_beats", [])
        if isinstance(beat, dict) and str(beat.get("beat_id", "")).strip()
    ]


def _tti_beat_manifest(story_bible: dict) -> list[str]:
    out: list[str] = []
    for beat in story_bible.get("lyric_beats", []):
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("beat_id", "")).strip()
        if not beat_id:
            continue
        section = str(beat.get("section_label", beat.get("section_name", ""))).strip()
        payoff = str(beat.get("payoff_role", "")).strip()
        out.append(f"{beat_id}|{section}|{payoff}")
    return out


def _assign_story_metadata(shots: list[dict], timeline: dict, story_bible: dict) -> list[dict]:
    policy = story_bible.get("resolved_profile_policy", resolve_profile_policy({})) if isinstance(story_bible, dict) else resolve_profile_policy({})
    face_defaults = policy.get("face_exposure_defaults", {}) if isinstance(policy, dict) else {}
    beat_map = {
        str(beat.get("beat_id", "")).strip(): beat
        for beat in story_bible.get("lyric_beats", [])
        if isinstance(beat, dict)
    }
    section_bounds = _section_bounds(timeline)
    out: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        beat = beat_map[str(shot["lyric_beat_id"])]
        bounds = section_bounds.get(str(beat.get("beat_id", "")), {"start_sec": 0.0, "end_sec": 4.0})
        item = dict(shot)
        item["duration_sec"] = round(max(0.001, float(bounds["end_sec"]) - float(bounds["start_sec"])), 3)
        item["scene_detail"] = str(item.get("scene_detail", "")).strip()
        item["motion_hint"] = str(item.get("motion_hint", "")).strip()
        item["emotion"] = str(item.get("emotion", "")).strip()
        item["continuity_anchor"] = str(beat.get("continuity_anchor", "")).strip()
        item["scene_change_level"] = str(item.get("scene_change_level", "")).strip().lower()
        item["anchor_strategy"] = str(item.get("anchor_strategy", "")).strip().lower()
        item["continuity_basis"] = str(item.get("continuity_basis", "")).strip().lower()
        item["planner_edit_role"] = str(item.get("edit_role", "")).strip()
        item["edit_role"] = _canonical_edit_role(item.get("edit_role", ""), beat.get("payoff_role", ""))
        item["mv_function"] = _mv_function(item["edit_role"])
        item["transition_role"] = _transition_role(item["edit_role"])
        item["line_refs"] = list(beat.get("line_refs", []))
        item["literal_image"] = str(beat.get("literal_image", "")).strip()
        item["symbolic_image"] = str(beat.get("symbolic_image", "")).strip()
        item["motif_object"] = str(beat.get("motif_object", "")).strip()
        item["edit_device"] = str(beat.get("edit_device", "")).strip()
        item["prompt_focus"] = str(beat.get("prompt_focus", "heroine")).strip() or "heroine"
        item["space_event"] = str(beat.get("space_event", "")).strip()
        item["composition_shape"] = str(beat.get("composition_shape", "")).strip()
        item["palette_mode"] = str(beat.get("palette_mode", "")).strip()
        item["character_render_mode"] = str(beat.get("character_render_mode", "")).strip()
        item = attach_tti_metadata(item, item["section_name"], item["section_label"])
        item["location_family"] = str(beat.get("location_family", "")).strip()
        item["face_exposure_level"] = _face_exposure_level(item, face_defaults, policy)
        item["heroine_visibility"] = _heroine_visibility(item)
        item["continuity_priority"] = _continuity_priority(item, policy)
        item["wardrobe_read"] = _wardrobe_read(item, policy)
        item["prompt_text"] = _shot_prompt_text(item, story_bible)
        item["seed"] = 10_000 + idx * 97 + int(item.get("hero_frame_score", 1)) * 13
        out.append(item)
    return out


def _shot_prompt_text(shot: dict, story_bible: dict) -> str:
    style = str(story_bible.get("visual_style_contract", "")).strip()
    render_mode = str(shot.get("character_render_mode", "")).strip()
    action = (
        str(shot.get("pose_delta", "")).strip()
        or str(shot.get("workflow_motion_clause", "")).strip()
        or "moves through the beat"
    )
    literal = str(shot.get("literal_image", "")).strip()
    emotion = str(shot.get("emotion", "")).strip()
    scene = str(shot.get("scene_detail", "")).strip()
    location = str(shot.get("location_family", "")).strip()
    space_event = str(shot.get("space_event", "")).strip()
    palette_mode = str(shot.get("palette_mode", "")).strip()
    camera = str(shot.get("camera_language", "")).strip() or str(shot.get("composition_shape", "")).strip()

    subject_sentence = (
        f"A 2D anime heroine in {render_mode or 'long-limbed fashion proportions'} {action}"
        + (f", with {emotion}" if emotion else "")
        + (f", around {literal}" if literal else "")
        + "."
    )
    background_bits = [part for part in (location, scene, space_event, palette_mode) if str(part).strip()]
    background_sentence = f"The background is {', '.join(background_bits)}." if background_bits else ""
    camera_sentence = camera
    return compose_flux2_tti_prompt(style, subject_sentence, background_sentence, camera_sentence)


def _face_exposure_level(shot: dict, defaults: dict[str, str], policy: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    mv_function = str(shot.get("mv_function", "")).strip().lower()
    label = str(shot.get("section_label", shot.get("section_name", ""))).strip()
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    direct_face_sections = {str(x).strip() for x in policy.get("direct_face_sections", [])} if isinstance(policy, dict) else set()
    if shot_type in defaults:
        base = str(defaults.get(shot_type, "")).strip().lower()
        if shot_type == "EMOTION_CLOSE" and mv_function == "payoff" and label in direct_face_sections:
            return "direct"
        if base:
            return base
    if shot_type in {"DETAIL_INSERT", "SYMBOLIC_INSERT", "RHYTHM_DETAIL"} or focus == "object":
        return "hidden"
    if shot_type in {"ENV_TRANSITION", "WORLD_EVENT", "TRANSITIONAL_ABSTRACT"} or focus == "space":
        return "partial"
    if shot_type == "GRAPHIC_EVENT" or focus == "graphic":
        return "partial"
    if shot_type == "EMOTION_CLOSE":
        return "direct" if mv_function == "payoff" else "soft"
    if shot_type == "CHAR_MASTER":
        return "soft"
    return "partial"


def _heroine_visibility(shot: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    if shot_type in {"DETAIL_INSERT", "SYMBOLIC_INSERT", "RHYTHM_DETAIL"} or focus == "object":
        return "implied"
    if shot_type in {"ENV_TRANSITION", "WORLD_EVENT", "TRANSITIONAL_ABSTRACT", "GRAPHIC_EVENT"} or focus in {"space", "graphic"}:
        return "partial"
    return "clear"


def _continuity_priority(shot: dict, policy: dict) -> str:
    continuity_mode = str(policy.get("continuity_mode", "")).strip().lower() if isinstance(policy, dict) else ""
    if continuity_mode == "same_heroine" and str(shot.get("face_exposure_level", "")).strip().lower() in {"direct", "soft"}:
        return "high"
    if str(shot.get("consistency_need", "")).strip().lower() == "high":
        return "high"
    if str(shot.get("shot_priority", "")).strip().lower() == "hero":
        return "high"
    if str(shot.get("mv_function", "")).strip().lower() in {"payoff", "interrupt", "establish"}:
        return "medium"
    return "low"


def _wardrobe_read(shot: dict, policy: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    visual_mode = str(policy.get("visual_mode", "")).strip().lower() if isinstance(policy, dict) else ""
    if visual_mode == "environment_first" and shot_type != "CHAR_MASTER":
        return "low"
    if focus in {"object", "space", "graphic"}:
        return "low"
    if shot_type in {"CHAR_MASTER", "PERF_WIDE"}:
        return "high"
    if shot_type == "EMOTION_CLOSE":
        return "medium"
    return "low"


def _section_bounds(timeline: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for section in timeline.get("sections", []):
        for beat in section.get("lyric_beats", []):
            out[str(beat.get("beat_id", ""))] = {
                "start_sec": float(beat.get("start_sec", section.get("start_sec", 0.0))),
                "end_sec": float(beat.get("end_sec", section.get("end_sec", 0.0))),
            }
    return out


def _story_bible_digest(story_bible: dict) -> str:
    beats = story_bible.get("lyric_beats", [])
    return (
        f"hero={story_bible.get('hero_identity_lock', '')}; world={story_bible.get('world_rules', '')}; "
        + "beats="
        + ", ".join(
            f"{beat.get('beat_id', '')}|{beat.get('section_label', beat.get('section_name', ''))}|"
            f"{beat.get('literal_image', '')}|{beat.get('symbolic_image', '')}|{beat.get('prompt_focus', '')}|{beat.get('edit_device', '')}|{beat.get('composition_shape', '')}|{beat.get('palette_mode', '')}|{beat.get('payoff_role', '')}"
            for beat in beats
            if isinstance(beat, dict)
        )
    )


def _timeline_digest(timeline: dict) -> str:
    rows: list[str] = []
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        rows.append(
            f"{section.get('section_label', section.get('section_name', 'section'))}="
            + ",".join(str(beat.get("beat_id", "")) for beat in section.get("lyric_beats", []) if isinstance(beat, dict))
        )
    return "; ".join(rows)


def _mv_function(edit_role: str) -> str:
    role = str(edit_role).strip().lower()
    mapping = {
        "entry": "establish",
        "develop": "coverage",
        "release": "payoff",
        "hold": "lift",
        "interrupt": "interrupt",
        "residue": "residue",
    }
    return mapping.get(role, "coverage")


def _transition_role(edit_role: str) -> str:
    role = str(edit_role).strip().lower()
    if role in {"entry", "interrupt", "residue"}:
        return role
    if role == "release":
        return "arrival"
    if role == "hold":
        return "build"
    return "carry"


def _policy_digest(policy: dict) -> str:
    if not isinstance(policy, dict):
        return ""
    distribution = policy.get("shot_distribution", {})
    mix = ",".join(f"{key}:{distribution[key]:.2f}" for key in SHOT_TYPES if key in distribution)
    direct_sections = ",".join(str(x).strip() for x in policy.get("direct_face_sections", []) if str(x).strip())
    return (
        f"visual_mode={policy.get('visual_mode', '')}; "
        f"visual_mv_mode={policy.get('visual_mv_mode', '')}; "
        f"continuity_mode={policy.get('continuity_mode', '')}; "
        f"face_policy={policy.get('face_policy', '')}; "
        f"shot_bias={policy.get('shot_bias', '')}; "
        f"subject_exposure={policy.get('subject_exposure', '')}; "
        f"motif_density={policy.get('motif_density', '')}; "
        f"graphic_event_density={policy.get('graphic_event_density', '')}; "
        f"environment_event_density={policy.get('environment_event_density', '')}; "
        f"visual_payoff_mode={policy.get('visual_payoff_mode', '')}; "
        f"ref_policy={policy.get('ref_policy', '')}; "
        f"shot_mix={mix}; "
        f"direct_face_sections={direct_sections}"
    )


def _canonical_edit_role(raw_edit_role: object, payoff_role: object) -> str:
    payoff = str(payoff_role).strip().lower()
    if payoff in {"entry", "interrupt", "residue", "develop", "hold", "release"}:
        return payoff
    if payoff in {"peak", "payoff", "arrival"}:
        return "release"
    text = str(raw_edit_role).strip().lower()
    if not text:
        return "develop"
    if any(token in text for token in ("climax", "release", "payoff", "arrives", "arrival")):
        return "release"
    if any(token in text for token in ("entry", "opening", "introduce", "sets the atmosphere", "introduce the emotional premise")):
        return "entry"
    if any(token in text for token in ("interrupt", "break", "rupture")):
        return "interrupt"
    if any(token in text for token in ("residue", "outro", "after-image", "linger", "resolve out")):
        return "residue"
    if any(token in text for token in ("hold", "lift", "build", "sustain")):
        return "hold"
    return "develop"
