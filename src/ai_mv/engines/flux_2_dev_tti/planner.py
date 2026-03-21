from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_shot_timeline
from ai_mv.core.contracts.prompt_schema import KINETIC_INTENSITIES, KINETIC_TRANSITIONS, SHOT_TYPES, shot_timeline_schema
from ai_mv.core.profile_policy import resolve_profile_policy
from ai_mv.core.workflow_prompt_contracts import clean_prompt_clause, compact_prompt_clause, compose_flux2_prompt, compose_flux2_tti_prompt
from ai_mv.core.visual_pipeline import attach_tti_metadata
from ai_mv.infra.codex_cli_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    story_bible = payload["visual_story_bible"]
    lyrics_timeline = payload["lyrics_timeline"]
    spec = _generate_tti_spec(config, payload, story_bible)
    plan = normalize_shot_timeline(spec, story_bible.get("lyric_beats", []))
    plan["master_anchor"] = _style_master_anchor(plan["master_anchor"], story_bible)
    plan["shots"] = _apply_profile_shot_policy(plan["shots"], story_bible)
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
        "master_anchor prompt_text must contain only stable identity and world facts for image prompting. "
        "Every shot must include lyric_beat_id,shot_type,camera_language,pose_delta,emotion,scene_detail,motion_hint,workflow_motion_clause,space_relation,edit_role,continuity_lock,scene_change_level,anchor_strategy,continuity_basis,clip_count,start_frame,end_frame,kinetic_transition,lighting_fx,kinetic_intensity. "
        "Every shot must include lyric_beat_id,shot_type,camera_language,pose_delta,emotion,scene_detail,motion_hint,workflow_motion_clause,space_relation,edit_role,continuity_lock,clip_count,start_frame,end_frame,kinetic_transition,lighting_fx,kinetic_intensity. "
        "Base required fields remain lyric_beat_id,shot_type,camera_language,pose_delta,emotion,scene_detail,motion_hint,workflow_motion_clause,space_relation,edit_role,continuity_lock,clip_count,start_frame,end_frame,kinetic_transition,lighting_fx,kinetic_intensity. "
        "scene_change_level must be one of hold,evolve,shift,reset. "
        "anchor_strategy must be one of reuse_anchor,refine_anchor,new_anchor. "
        "continuity_basis must be one of heroine,motif,world,none. "
        "TTI creates new scene anchors; ref refines an existing scene anchor for continuity. "
        "Use scene_change_level to decide whether the beat stays on the same image state, evolves it, shifts to a new state in the same world, or resets into a fresh visual event. "
        "Use anchor_strategy to say whether downstream should mostly reuse the same anchor logic, refine the anchor for continuity, or generate a new anchor. "
        "new_anchor is for fresh image invention and strong scene resets; refine_anchor is for continuity-sensitive continuation; reuse_anchor is only for near-hold beats that should not ask ref to invent a new scene. "
        "workflow_motion_clause must be a short natural-English action clause for downstream Flux Ref and WAN prompts. "
        "Write it so it can complete a sentence like 'The girl ...', for example swings the guitar down with extreme force, turns sharply to the left, steps through the gate line, or eyes dart quickly to the side. "
        "Do not write workflow_motion_clause as a gerund-led fragment such as stepping, holding, turning, moving, easing, pivoting, or advancing. "
        "Do not write workflow_motion_clause as a full sentence and do not start it with she/he/the girl. "
        "camera_language must already be a short natural-English camera phrase that can be copied directly into a prompt, such as an extreme low-angle dynamic shot, a wide off-center frame from the left, or a tight off-center close-up. "
        "camera_language must read like one clean shot phrase only. "
        "Do not repeat words such as shot shot, frame frame, angle angle, or close-up close-up. "
        "Do not output broken hybrids such as diagonal corridor-in a wide shot shot, very in a wide shot, or decisive off-center in a close-up. "
        "Do not output taxonomy labels or compressed metadata. "
        "scene_detail must already be a drawable natural-English visual phrase, not a category label. "
        "space_relation must already be a natural-English relation phrase, not a diagram label or shorthand token. "
        "Use the story bible and lyric beat as the source of truth. "
        "NO TEXT, NO TYPOGRAPHY, NO WATERMARKS, NO LOGOS, NO SIGNAGE, NO UI OVERLAY. "
        "Make the shot plan genuinely varied: if two nearby beats share a shot_type, they must still differ materially in camera_language, pose_delta, scene_detail, or framing scale. "
        "Honor story-bible prompt_focus, edit_device, symbolic_image, motif_object, space_event, and composition_shape when deciding shot_type. "
        "If prompt_focus is object, space, or graphic, do not default back to a heroine-facing close-up unless the policy explicitly demands it. "
        "Use shot_type as a storytelling choice, not a default. Verses should usually favor observation and traversal, pre-chorus should tighten intention, chorus should simplify into the hook image, bridge should interrupt or isolate, and outro should resolve. "
        "Do not repeat the same lane/crosswalk/reflection composition across adjacent beats unless the lyric explicitly repeats and the camera intent escalates. "
        "Do not solve most graphic beats with split-screen, diptych, mirrored-face, doubled-subject, centered two-body, centered sparse-negative-space staging, centered floating-object staging, static cover-pose close crops, tight face crops, badge-like emblem compositions, runway poses, or mannequin stances; prefer asymmetrical poster crops, anime keyframe turns, mid-step lane cuts, isolated small figures, floating object fields with off-center figures, offset silhouette holds, sticker-like clusters, and off-center compositions as the default graphic language. "
        "scene_detail should name the concrete visual state of the beat, not just restate the location family. "
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
            _validate_tti_language_contract(spec)
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


_BANNED_TTI_LABELS = {
    "asymmetrical poster crop",
    "editorial three-quarter turn",
    "mid-step lane cut",
    "low horizon silhouette",
    "diagonal lane cut",
    "floating object field",
    "isolated small figure",
    "sticker-cluster layout",
    "offset silhouette crop",
    "single-profile reflection trace",
}


def _validate_tti_language_contract(spec: dict) -> None:
    shots = [row for row in spec.get("shots", []) if isinstance(row, dict)]
    for idx, row in enumerate(shots, start=1):
        for field in ("camera_language", "scene_detail", "space_relation", "workflow_motion_clause"):
            text = str(row.get(field, "")).strip()
            if not text:
                raise RuntimeError(f"tti language contract mismatch: blank {field} at shot {idx}")
            low = text.lower()
            if low in _BANNED_TTI_LABELS:
                raise RuntimeError(f"tti language contract mismatch: {field} is still a taxonomy label at shot {idx}: {text}")
            if any(mark in text for mark in ("[", "]", "|", ";")):
                raise RuntimeError(f"tti language contract mismatch: {field} contains metadata punctuation at shot {idx}: {text}")
        motion = str(row.get("workflow_motion_clause", "")).strip().lower()
        first_token = motion.split(" ", 1)[0] if motion else ""
        if first_token.endswith("ing"):
            raise RuntimeError(
                f"tti language contract mismatch: workflow_motion_clause is still gerund-led at shot {idx}: {motion}"
            )
        if motion.startswith(("she ", "he ", "the girl ", "the heroine ")):
            raise RuntimeError(
                f"tti language contract mismatch: workflow_motion_clause starts with an explicit subject at shot {idx}: {motion}"
            )
        camera = str(row.get("camera_language", "")).strip().lower()
        if any(token in camera for token in ("shot shot", "frame frame", "angle angle", "close-up close-up", "close up close up")):
            raise RuntimeError(f"tti language contract mismatch: camera_language repeats camera terms at shot {idx}: {camera}")
        if camera.startswith(("very in ", "decisive off-center in ", "diagonal corridor-in ")):
            raise RuntimeError(f"tti language contract mismatch: camera_language is malformed at shot {idx}: {camera}")


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
        "camera_language, scene_detail, and space_relation must be plain natural-English prompt phrases, not taxonomy labels or shorthand tags. "
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


def _apply_profile_shot_policy(shots: list[dict], story_bible: dict) -> list[dict]:
    policy = story_bible.get("resolved_profile_policy", resolve_profile_policy({})) if isinstance(story_bible, dict) else resolve_profile_policy({})
    beat_map = {
        str(beat.get("beat_id", "")).strip(): beat
        for beat in story_bible.get("lyric_beats", [])
        if isinstance(beat, dict)
    }
    targets = _target_shot_counts(policy.get("shot_distribution", {}), len(shots))
    remaining = dict(targets)
    out: list[dict] = []
    total = len(shots)
    for idx, shot in enumerate(shots):
        item = dict(shot)
        beat = beat_map.get(str(item.get("lyric_beat_id", "")).strip(), {})
        forced = _forced_shot_type(item, beat, policy)
        ranked = _rank_shot_types(item, beat, policy, idx, total)
        selected = forced or next((shot_type for shot_type in ranked if remaining.get(shot_type, 0) > 0), ranked[0] if ranked else item.get("shot_type", "PERF_WIDE"))
        item["planner_shot_type"] = str(item.get("shot_type", "")).strip().upper()
        item["shot_type"] = str(selected).strip().upper()
        remaining[item["shot_type"]] = max(0, int(remaining.get(item["shot_type"], 0)) - 1)
        out.append(item)
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
        item["scene_detail"] = str(item.get("scene_detail", "")).strip() or str(beat.get("literal_image", "")).strip()
        item["motion_hint"] = str(item.get("motion_hint", "")).strip() or str(beat.get("visible_action", "")).strip()
        item["emotion"] = str(item.get("emotion", "")).strip() or str(beat.get("emotional_turn", "")).strip()
        item["continuity_anchor"] = str(beat.get("continuity_anchor", "")).strip()
        item["scene_change_level"] = _canonical_scene_change_level(item, beat)
        item["anchor_strategy"] = _canonical_anchor_strategy(item, beat)
        item["continuity_basis"] = _canonical_continuity_basis(item, beat, policy)
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


def _canonical_scene_change_level(shot: dict, beat: dict) -> str:
    raw = str(shot.get("scene_change_level", "")).strip().lower()
    base = raw if raw in {"hold", "evolve", "shift", "reset"} else "evolve"
    payoff = str(beat.get("payoff_role", "")).strip().lower()
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    if payoff in {"interrupt", "entry", "peak"}:
        return "reset"
    if base == "hold" and (focus in {"space", "graphic"} or shot_type in {"WORLD_EVENT", "ENV_TRANSITION", "TRANSITIONAL_ABSTRACT"}):
        return "shift"
    return base


def _canonical_anchor_strategy(shot: dict, beat: dict) -> str:
    raw = str(shot.get("anchor_strategy", "")).strip().lower()
    scene_change = _canonical_scene_change_level(shot, beat)
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    if scene_change == "reset":
        return "new_anchor"
    if raw in {"reuse_anchor", "refine_anchor", "new_anchor"}:
        if scene_change in {"hold", "evolve"} and raw == "new_anchor":
            return "refine_anchor" if scene_change == "evolve" else "reuse_anchor"
        return raw
    if scene_change == "shift":
        return "new_anchor" if focus in {"space", "graphic"} else "refine_anchor"
    if scene_change == "evolve":
        return "refine_anchor"
    return "reuse_anchor"


def _canonical_continuity_basis(shot: dict, beat: dict, policy: dict) -> str:
    raw = str(shot.get("continuity_basis", "")).strip().lower()
    base = raw if raw in {"heroine", "motif", "world", "none"} else "world"
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    continuity_mode = str(policy.get("continuity_mode", "")).strip().lower() if isinstance(policy, dict) else ""
    if focus == "object" or shot_type in {"DETAIL_INSERT", "SYMBOLIC_INSERT", "RHYTHM_DETAIL"}:
        return "motif"
    if continuity_mode == "same_heroine" and str(shot.get("face_exposure_level", "")).strip().lower() in {"direct", "soft"}:
        return "heroine"
    if focus in {"space", "graphic"} or shot_type in {"WORLD_EVENT", "ENV_TRANSITION", "TRANSITIONAL_ABSTRACT", "GRAPHIC_EVENT"}:
        return "world"
    return base


def _shot_prompt_text(shot: dict, story_bible: dict) -> str:
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    style = str(story_bible.get("visual_style_contract", "")).strip()
    heroine = str(story_bible.get("heroine_invariants", story_bible.get("hero_identity_lock", ""))).strip()
    world = str(story_bible.get("world_invariants", story_bible.get("world_rules", ""))).strip()
    location = clean_prompt_clause(str(shot.get("location_family", "")).strip())
    scene = clean_prompt_clause(str(shot.get("scene_detail", "")).strip())
    space_event = str(shot.get("space_event", "")).strip()
    emotion = str(shot.get("emotion", "")).strip()
    camera = str(shot.get("camera_language", "")).strip()
    device = str(shot.get("edit_device", "")).strip()
    motif = str(shot.get("motif_object", "")).strip()
    composition = clean_prompt_clause(str(shot.get("composition_shape", "")).strip())
    palette_mode = str(shot.get("palette_mode", "")).strip()
    render_mode = str(shot.get("character_render_mode", "")).strip()
    shot_type_text = shot_type.lower().replace("_", " ")
    face = str(shot.get("face_exposure_level", "")).strip()
    continuity = str(shot.get("continuity_lock", "")).strip()
    if focus == "object":
        subject_sentence = (
            f"A 2D anime heroine appears as a secondary full-body figure while {motif or scene or 'a symbolic object'} carries the action."
        )
        background_sentence = (
            f"The background is {location or 'a planar city block'} with {scene or space_event or 'simplified geometry'} and {palette_mode or 'a high-chroma pop palette'}."
        )
        camera_sentence = f"The camera uses {camera or composition or 'an off-center frame'}."
    elif focus == "space":
        subject_sentence = (
            f"A 2D anime heroine moves as a small full-body figure through {space_event or scene or 'a flat city geometry event'}."
        )
        background_sentence = (
            f"The background is {location or 'a planar city block'} with {palette_mode or 'a high-chroma pop palette'} and non-photographic layered geometry."
        )
        camera_sentence = f"The camera uses {camera or composition or 'a wide asymmetrical frame'}."
    elif focus == "graphic":
        subject_sentence = (
            f"A 2D anime heroine moves through {device or motif or 'a graphic impact event'} as one living figure, never a split-screen emblem."
        )
        background_sentence = (
            f"The background is {location or 'a planar graphic field'} with {scene or space_event or 'symbolic graphic elements'} and {palette_mode or 'a vibrant pop palette'}."
        )
        camera_sentence = f"The camera uses {camera or composition or 'an asymmetrical graphic frame'}."
    else:
        subject_sentence = (
            f"A 2D anime heroine in {render_mode or 'long-limbed fashion proportions'} {str(shot.get('pose_delta', '')).strip() or 'moves through a readable acting pose'} through "
            f"{str(shot.get('literal_image', '')).strip() or scene or 'a clear visual beat'}, with {emotion or 'a cool expression'} and {face or 'partial'} face exposure."
        )
        background_sentence = (
            f"The background is {location or 'graphic city blocks'} with {scene or 'simplified environment geometry'}, {palette_mode or 'a vibrant pop palette'}, and {world or continuity or 'the same continuous world'}."
        )
        camera_sentence = f"The camera uses {camera or composition or 'an asymmetrical poster crop'}."
    return compose_flux2_tti_prompt(style, subject_sentence, background_sentence, camera_sentence)


def _style_master_anchor(master: dict, story_bible: dict) -> dict:
    style = str(story_bible.get("visual_style_contract", "")).strip()
    heroine = str(story_bible.get("heroine_invariants", story_bible.get("hero_identity_lock", ""))).strip()
    world = str(story_bible.get("world_invariants", story_bible.get("world_rules", ""))).strip()
    out = dict(master)
    out["prompt_text"] = compose_flux2_prompt(style, [heroine, world], 42)
    return out


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


def _target_shot_counts(distribution: dict[str, float], total: int) -> dict[str, int]:
    total = max(0, int(total))
    if total <= 0:
        return {shot_type: 0 for shot_type in SHOT_TYPES}
    normalized = {shot_type: max(0.0, float(distribution.get(shot_type, 0.0))) for shot_type in SHOT_TYPES}
    norm_total = sum(normalized.values()) or 1.0
    scaled = {shot_type: normalized[shot_type] / norm_total * total for shot_type in SHOT_TYPES}
    counts = {shot_type: int(scaled[shot_type]) for shot_type in SHOT_TYPES}
    remainders = sorted(((scaled[shot_type] - counts[shot_type], shot_type) for shot_type in SHOT_TYPES), reverse=True)
    missing = total - sum(counts.values())
    for _, shot_type in remainders[:missing]:
        counts[shot_type] += 1
    return counts


def _rank_shot_types(shot: dict, beat: dict, policy: dict, idx: int, total: int) -> list[str]:
    current = str(shot.get("shot_type", "")).strip().upper()
    section_name = str(beat.get("section_name", shot.get("section_name", ""))).strip().lower()
    section_label = str(beat.get("section_label", shot.get("section_label", ""))).strip()
    payoff_role = str(beat.get("payoff_role", shot.get("edit_role", ""))).strip().lower()
    visual_mode = str(policy.get("visual_mode", "")).strip().lower()
    visual_mv_mode = str(policy.get("visual_mv_mode", "")).strip().lower()
    continuity_mode = str(policy.get("continuity_mode", "")).strip().lower()
    face_policy = str(policy.get("face_policy", "")).strip().lower()
    shot_bias = str(policy.get("shot_bias", "")).strip().lower()
    prompt_focus = str(beat.get("prompt_focus", shot.get("prompt_focus", "heroine"))).strip().lower() or "heroine"
    edit_device = str(beat.get("edit_device", "")).strip().lower()
    symbolic_image = str(beat.get("symbolic_image", "")).strip().lower()
    motif_object = str(beat.get("motif_object", "")).strip().lower()
    composition_shape = str(beat.get("composition_shape", "")).strip().lower()
    visual_payoff_mode = str(policy.get("visual_payoff_mode", "")).strip().lower()
    reflection_usage = str(policy.get("reflection_usage", "")).strip().lower()
    direct_face_sections = {str(x).strip() for x in policy.get("direct_face_sections", []) if str(x).strip()}
    detail_friendly = _detail_friendly_text(
        str(beat.get("literal_image", shot.get("scene_detail", ""))).strip(),
        str(beat.get("visible_action", shot.get("motion_hint", ""))).strip(),
    )
    allow_direct_face = section_label in direct_face_sections or face_policy == "frequent"

    scores = {shot_type: 0.0 for shot_type in SHOT_TYPES}
    if current in scores:
        scores[current] += 1.5

    if visual_mode == "character_heavy":
        scores["EMOTION_CLOSE"] += 2.5
        scores["CHAR_MASTER"] += 2.0
        scores["PERF_WIDE"] += 1.0
    elif visual_mode == "environment_first":
        scores["ENV_TRANSITION"] += 2.5
        scores["DETAIL_INSERT"] += 1.5
        scores["WORLD_EVENT"] += 1.5
        scores["PERF_WIDE"] += 0.5
        scores["EMOTION_CLOSE"] -= 3.0
        scores["CHAR_MASTER"] -= 1.0
    else:
        scores["PERF_WIDE"] += 1.0
        scores["ENV_TRANSITION"] += 0.5

    if visual_mv_mode == "bga_event":
        scores["GRAPHIC_EVENT"] += 2.0
        scores["TRANSITIONAL_ABSTRACT"] += 1.5
        scores["RHYTHM_DETAIL"] += 1.0
    elif visual_mv_mode == "symbolic_edit":
        scores["SYMBOLIC_INSERT"] += 2.0
        scores["WORLD_EVENT"] += 1.5
        scores["GRAPHIC_EVENT"] += 0.5

    if shot_bias == "performance":
        scores["PERF_WIDE"] += 2.0
        scores["CHAR_MASTER"] += 1.0
    elif shot_bias == "environment":
        scores["ENV_TRANSITION"] += 2.0
        scores["WORLD_EVENT"] += 1.5
        scores["DETAIL_INSERT"] += 1.0
        scores["EMOTION_CLOSE"] -= 1.0
    elif shot_bias == "object_symbol":
        scores["DETAIL_INSERT"] += 2.5
        scores["SYMBOLIC_INSERT"] += 2.0
        scores["RHYTHM_DETAIL"] += 0.5
        scores["ENV_TRANSITION"] += 0.5
        scores["EMOTION_CLOSE"] -= 1.0
        scores["CHAR_MASTER"] -= 1.0

    if prompt_focus == "object":
        scores["SYMBOLIC_INSERT"] += 3.0
        scores["DETAIL_INSERT"] += 2.0
        scores["RHYTHM_DETAIL"] += 1.0
        scores["EMOTION_CLOSE"] -= 3.0
        scores["CHAR_MASTER"] -= 2.0
    elif prompt_focus == "space":
        scores["WORLD_EVENT"] += 3.0
        scores["ENV_TRANSITION"] += 2.0
        scores["TRANSITIONAL_ABSTRACT"] += 1.0
        scores["EMOTION_CLOSE"] -= 2.0
    elif prompt_focus == "graphic":
        scores["GRAPHIC_EVENT"] += 3.0
        scores["TRANSITIONAL_ABSTRACT"] += 2.0
        scores["RHYTHM_DETAIL"] += 1.0
        scores["EMOTION_CLOSE"] -= 2.0

    payoff_roles = {"release", "arrival", "payoff", "peak"}

    if face_policy == "avoid":
        scores["EMOTION_CLOSE"] -= 6.0
        scores["CHAR_MASTER"] -= 2.0
        scores["PERF_WIDE"] += 1.0
        scores["ENV_TRANSITION"] += 1.0
        scores["DETAIL_INSERT"] += 1.0
    elif face_policy == "payoff_only":
        if allow_direct_face and payoff_role in payoff_roles:
            scores["EMOTION_CLOSE"] += 3.0
            scores["CHAR_MASTER"] += 1.0
        else:
            scores["EMOTION_CLOSE"] -= 5.0
    elif face_policy == "selective":
        if allow_direct_face or section_name == "chorus" or payoff_role in payoff_roles:
            scores["EMOTION_CLOSE"] += 1.5
        else:
            scores["EMOTION_CLOSE"] -= 1.5
    elif face_policy == "frequent":
        scores["EMOTION_CLOSE"] += 3.0
        scores["CHAR_MASTER"] += 1.0

    if section_name == "chorus" or payoff_role in payoff_roles:
        scores["PERF_WIDE"] += 2.0
        scores["CHAR_MASTER"] += 1.5
        if allow_direct_face:
            scores["EMOTION_CLOSE"] += 2.0
        if visual_payoff_mode == "motif_peak":
            scores["SYMBOLIC_INSERT"] += 1.5
            scores["RHYTHM_DETAIL"] += 0.5
        elif visual_payoff_mode == "system_peak":
            scores["WORLD_EVENT"] += 1.5
            scores["GRAPHIC_EVENT"] += 1.5
            scores["SYMBOLIC_INSERT"] += 0.5
            scores["TRANSITIONAL_ABSTRACT"] += 1.0
            scores["CHAR_MASTER"] -= 2.5
            scores["EMOTION_CLOSE"] -= 2.0
            if section_label in direct_face_sections or payoff_role == "peak":
                scores["WORLD_EVENT"] += 0.75
                scores["GRAPHIC_EVENT"] += 0.75
                scores["SYMBOLIC_INSERT"] += 0.25
    if visual_payoff_mode == "system_peak" and section_label in direct_face_sections:
        scores["WORLD_EVENT"] += 2.0
        scores["GRAPHIC_EVENT"] += 2.0
        scores["SYMBOLIC_INSERT"] += 0.75
        scores["TRANSITIONAL_ABSTRACT"] += 0.5
        scores["CHAR_MASTER"] -= 4.0
        scores["EMOTION_CLOSE"] -= 3.0
        if prompt_focus == "heroine":
            scores["GRAPHIC_EVENT"] += 1.0
            scores["WORLD_EVENT"] += 0.5
    if section_name in {"intro", "bridge", "outro"} or payoff_role in {"entry", "interrupt", "residue"}:
        scores["ENV_TRANSITION"] += 1.5
        scores["WORLD_EVENT"] += 1.0
    if continuity_mode == "same_heroine":
        scores["CHAR_MASTER"] += 1.5
        scores["PERF_WIDE"] += 1.0
    if detail_friendly:
        scores["DETAIL_INSERT"] += 2.5
    if any(token in edit_device for token in ("graphic", "smear", "flash", "silhouette", "rhythm cut")):
        scores["GRAPHIC_EVENT"] += 1.5
        scores["TRANSITIONAL_ABSTRACT"] += 0.5
    if any(token in edit_device for token in ("object reveal", "token", "insert")) or motif_object:
        scores["SYMBOLIC_INSERT"] += 1.0
        scores["RHYTHM_DETAIL"] += 0.5
    if any(token in edit_device for token in ("space", "drop-out", "open", "compress")) or "space" in symbolic_image:
        scores["WORLD_EVENT"] += 1.0
        scores["ENV_TRANSITION"] += 0.5
    if any(token in composition_shape for token in ("poster", "asymmetrical", "offset", "isolated", "floating object", "low horizon", "sticker")):
        scores["GRAPHIC_EVENT"] += 1.0
        scores["SYMBOLIC_INSERT"] += 0.5
    if any(token in composition_shape for token in ("centered icon", "centered two-body", "bilateral", "symmetrical", "centered", "face-forward", "dominant against", "close hero", "near face", "stable subject", "balanced around")):
        scores["GRAPHIC_EVENT"] -= 0.75
        scores["WORLD_EVENT"] -= 1.0
        scores["TRANSITIONAL_ABSTRACT"] -= 0.25
        scores["CHAR_MASTER"] -= 1.5
        scores["EMOTION_CLOSE"] -= 1.0
    if any(token in composition_shape for token in ("split", "diptych", "mirrored", "doubled")) or any(
        token in edit_device for token in ("mirror", "split", "reflection split")
    ):
        scores["GRAPHIC_EVENT"] += 0.25
        scores["WORLD_EVENT"] -= 1.25
        scores["TRANSITIONAL_ABSTRACT"] -= 0.5
        scores["SYMBOLIC_INSERT"] -= 0.5
    if reflection_usage == "selected_only" and not (section_name in {"bridge", "chorus"} or payoff_role in payoff_roles):
        if any(token in composition_shape for token in ("split", "diptych", "mirrored", "doubled")) or any(
            token in edit_device for token in ("mirror", "split", "reflection split")
        ):
            scores["GRAPHIC_EVENT"] -= 1.5
            scores["WORLD_EVENT"] -= 1.0
            scores["SYMBOLIC_INSERT"] -= 1.0
    if idx == 0 or idx == total - 1:
        scores["ENV_TRANSITION"] += 0.5
        scores["CHAR_MASTER"] += 0.5

    return sorted(SHOT_TYPES, key=lambda shot_type: (scores[shot_type], shot_type == current), reverse=True)


def _detail_friendly_text(literal_image: str, visible_action: str) -> bool:
    text = f"{literal_image} {visible_action}".lower()
    return any(
        token in text
        for token in (
            "hand",
            "hands",
            "ring",
            "heels",
            "shoe",
            "mirror",
            "reflection",
            "glass",
            "door",
            "sleeve",
            "microphone",
            "cassette",
            "vinyl",
            "necklace",
            "lip",
            "eye",
        )
    )


def _normalize_composition_for_prompt(composition: str, shot_type: str, focus: str) -> str:
    text = str(composition).strip()
    if not text:
        return text
    graphic_like = str(shot_type).strip().upper() == "GRAPHIC_EVENT" or focus in {"graphic", "space"}
    if not graphic_like:
        return text
    lowered = text.lower()
    if "split reflection diptych" in lowered:
        return "single-profile reflection crop"
    if "centered icon frame" in lowered:
        return "off-center icon crop"
    if "centered low" in lowered:
        return "off-center low moving figure"
    if "poster close crop" in lowered:
        return "off-center three-quarter step turn"
    if "close heroine crop" in lowered:
        return "off-center upper-body turn"
    if "tight face crop" in lowered:
        return "off-center three-quarter step turn"
    if "near face" in lowered:
        return "near upper-body turn in off-center space"
    if "face-forward payoff" in lowered:
        return "off-center heroine turn in open negative space"
    if "heroine dominant against" in lowered:
        return "off-center heroine turn against organized city planes"
    if "balanced around her" in lowered:
        return "off-center around organized city planes"
    if "stable subject" in lowered:
        return "moving figure"
    if "emblematic composition" in lowered or "emblematic" in lowered:
        return "off-center moving figure"
    if "editorial three-quarter turn" in lowered:
        return "off-center three-quarter step turn"
    if "walking line profile" in lowered:
        return "anime side-step turn"
    if "centered two-body" in lowered or "bilateral" in lowered or "symmetrical" in lowered:
        return "offset silhouette crop"
    if "mirrored-face" in lowered or "doubled" in lowered:
        return "single-subject poster crop"
    if "low horizon silhouette" in lowered:
        return "off-center low horizon moving figure"
    if "diagonal lane cut" in lowered:
        return "off-center diagonal lane cut"
    if "floating object field" in lowered:
        return "floating object field with off-center figure"
    if "isolated small figure" in lowered:
        return "small moving figure in open negative space"
    if "offset silhouette crop" in lowered:
        return "off-center moving silhouette"
    if "single-profile reflection trace" in lowered:
        return "side reflection trace with one figure"
    return text


def _normalize_scene_for_prompt(scene: str, shot_type: str, focus: str) -> str:
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
        ("two silhouettes separated by a narrow gap", "a single silhouette held against an offset pane"),
        ("two-body silhouette balance", "offset silhouette tension"),
        ("two silhouettes", "a single silhouette"),
        ("narrow gap", "offset pane tension"),
        ("balanced", "offset"),
        ("paired movement", "single-figure movement"),
        ("reflected name", "reflection trace"),
        ("name", "trace"),
        ("letters", "marks"),
        ("words", "marks"),
        ("signage", "panels"),
        ("reflection loosens from stillness into ribbon-like separation", "reflection thins into a single offset trace"),
        ("side-face reflection in dark window", "single side profile against dark window"),
        ("mirrored glass", "dark glass plane"),
        ("city pull coming from deep center", "city bands stacked behind"),
        ("street planes converge toward center", "street planes stack in flat bands"),
        ("block receding toward the center", "block stacked in flat layers"),
        ("block receding in layers", "block stacked in flat layers"),
        ("near face with the world condensed behind her", "near upper-body turn with the world compressed into flat bands"),
        ("small heroine centered low against broad moving city bands", "small heroine off-center against broad moving city bands"),
        ("heroine centered in a widened street compressed passage blocks", "heroine off-center in widened street passage blocks"),
        ("heroine centered in a widened street corridor", "heroine off-center in a widened street corridor"),
        ("curving exterior ribbon enclosing a stable subject", "curving exterior ribbon crossing a moving figure"),
        ("fully embedded in the city grid with the frame balanced around her", "fully embedded in the city grid with off-center city pressure around her"),
        ("tiny circle centered in open negative space", "tiny circle off-center in open negative space"),
        ("lights arranged around center, block feels complete", "lights arranged across the block, the block feels complete"),
        ("two figures aligned across the crossing, city receding", "one figure crossing with an offset echo, city stacked behind"),
        ("city receding", "city stacked behind"),
        ("receding city planes", "stacked city planes"),
        ("receding city plane blocks", "stacked city plane blocks"),
        ("graphic corridor receding behind a single red point near center", "graphic corridor stacked in flat bands behind an off-center red point"),
        ("close heroine crop against a layered blue field and receding city plane blocks", "off-center upper-body turn against a layered blue field and stacked city plane blocks"),
        ("close heroine crop against a layered blue field and receding city planes", "off-center upper-body turn against a layered blue field and stacked city planes"),
        ("close heroine crop against a shallow field of night geometry", "off-center upper-body turn against a shallow field of night geometry"),
        ("dense layered field where the motifs converge around a small anchor point", "dense layered field where the motifs converge around a small off-center figure"),
        ("broad city space with the heroine reduced to a small anchored point", "broad city space with the heroine reduced to a small off-center figure"),
        ("object-led foreground window with the route receding behind it", "object-led foreground window with the route stacked behind it"),
        ("small anchored point", "small off-center figure"),
        ("small anchor point", "small off-center figure"),
        ("near center", "off-center"),
        ("foreground dominant", "foreground left"),
        ("occupying most of the frame edge", "touching the frame edge"),
    )
    out = text
    lowered = out.lower()
    for old, new in replacements:
        if old in lowered:
            out = out.replace(old, new).replace(old.title(), new)
            lowered = out.lower()
    return out


def _normalize_location_for_prompt(location: str) -> str:
    text = str(location).strip()
    if not text:
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


def _forced_shot_type(shot: dict, beat: dict, policy: dict) -> str | None:
    if not isinstance(policy, dict):
        return None
    face_policy = str(policy.get("face_policy", "")).strip().lower()
    visual_payoff_mode = str(policy.get("visual_payoff_mode", "")).strip().lower()
    section_label = str(beat.get("section_label", shot.get("section_label", ""))).strip()
    payoff_role = str(beat.get("payoff_role", shot.get("edit_role", ""))).strip().lower()
    prompt_focus = str(beat.get("prompt_focus", shot.get("prompt_focus", "heroine"))).strip().lower() or "heroine"
    direct_face_sections = {str(x).strip() for x in policy.get("direct_face_sections", []) if str(x).strip()}
    payoff_roles = {"release", "arrival", "payoff", "peak"}
    if visual_payoff_mode == "system_peak" and section_label in direct_face_sections:
        if prompt_focus == "space":
            return "WORLD_EVENT"
        if prompt_focus == "object":
            return "SYMBOLIC_INSERT"
        return "GRAPHIC_EVENT"
    if visual_payoff_mode == "system_peak" and payoff_role in payoff_roles:
        if prompt_focus == "space":
            return "WORLD_EVENT"
        if prompt_focus == "object":
            return "SYMBOLIC_INSERT"
        return "GRAPHIC_EVENT"
    if face_policy == "payoff_only" and section_label in direct_face_sections and payoff_role in payoff_roles and prompt_focus == "heroine":
        return "EMOTION_CLOSE"
    if visual_payoff_mode == "motif_peak" and payoff_role in payoff_roles and prompt_focus == "object":
        return "SYMBOLIC_INSERT"
    return None


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
