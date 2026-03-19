from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_shot_timeline
from ai_mv.core.contracts.prompt_schema import KINETIC_INTENSITIES, KINETIC_TRANSITIONS, SHOT_TYPES, shot_timeline_schema
from ai_mv.core.profile_policy import resolve_profile_policy
from ai_mv.core.workflow_prompt_contracts import compose_image_prompt
from ai_mv.core.visual_pipeline import attach_tti_metadata
from ai_mv.infra.codex_cli_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    story_bible = payload["visual_story_bible"]
    lyrics_timeline = payload["lyrics_timeline"]
    spec = generate_structured(config, _planner_prompt(config, payload), shot_timeline_schema())
    plan = normalize_shot_timeline(spec, story_bible.get("lyric_beats", []))
    plan["shots"] = _apply_profile_shot_policy(plan["shots"], story_bible)
    shots = _assign_story_metadata(plan["shots"], lyrics_timeline, story_bible)
    return {"master_anchor": plan["master_anchor"], "shots": shots}


def build_tti_preview_prompt(config: dict, payload: dict) -> str:
    return _planner_prompt(config, payload)


def _planner_prompt(config: dict, payload: dict) -> str:
    story_bible = payload["visual_story_bible"]
    timeline = payload["lyrics_timeline"]
    policy = story_bible.get("resolved_profile_policy", resolve_profile_policy(config)) if isinstance(story_bible, dict) else resolve_profile_policy(config)
    return (
        "Write a shot timeline for downstream Flux and video workflows. "
        "Return strict JSON only with shape {\"master_anchor\":{...},\"shots\":[...]}. No prose outside JSON. "
        "Create exactly one shot item for every lyric beat in order. "
        "master_anchor prompt_text must contain only stable identity and world facts for image prompting. "
        "Every shot must include lyric_beat_id,shot_type,camera_language,pose_delta,emotion,scene_detail,motion_hint,workflow_motion_clause,space_relation,edit_role,continuity_lock,clip_count,start_frame,end_frame,kinetic_transition,lighting_fx,kinetic_intensity. "
        "workflow_motion_clause must be a compact natural motion clause for downstream Flux Ref and WAN prompts. "
        "Make workflow_motion_clause phase-neutral and directly reusable across split clips; use a compact gerund-led clause such as stepping, holding, turning, moving, easing, pivoting, or advancing. "
        "Do not write workflow_motion_clause as a full sentence or finite-verb sentence starting with she/he. "
        "Use the story bible and lyric beat as the source of truth. "
        "NO TEXT, NO TYPOGRAPHY, NO WATERMARKS, NO LOGOS, NO SIGNAGE, NO UI OVERLAY. "
        "Make the shot plan genuinely varied: if two nearby beats share a shot_type, they must still differ materially in camera_language, pose_delta, scene_detail, or framing scale. "
        "Use shot_type as a storytelling choice, not a default. Verses should usually favor observation and traversal, pre-chorus should tighten intention, chorus should simplify into the hook image, bridge should interrupt or isolate, and outro should resolve. "
        "Do not repeat the same lane/crosswalk/reflection composition across adjacent beats unless the lyric explicitly repeats and the camera intent escalates. "
        "scene_detail should name the concrete visual state of the beat, not just restate the location family. "
        f"Allowed shot types={', '.join(SHOT_TYPES)}. "
        f"Allowed kinetic transitions={', '.join(KINETIC_TRANSITIONS)}. "
        f"Allowed kinetic intensities={', '.join(KINETIC_INTENSITIES)}. "
        "Honor the profile policy when choosing shot types and face exposure. "
        f"Profile policy={_policy_digest(policy)}. "
        f"Story bible={_story_bible_digest(story_bible)}. "
        f"Lyric timeline={_timeline_digest(timeline)}."
    )


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
        item["planner_edit_role"] = str(item.get("edit_role", "")).strip()
        item["edit_role"] = _canonical_edit_role(item.get("edit_role", ""), beat.get("payoff_role", ""))
        item["mv_function"] = _mv_function(item["edit_role"])
        item["transition_role"] = _transition_role(item["edit_role"])
        item["line_refs"] = list(beat.get("line_refs", []))
        item["literal_image"] = str(beat.get("literal_image", "")).strip()
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
    return compose_image_prompt(
        [
            str(story_bible.get("heroine_invariants", story_bible.get("hero_identity_lock", ""))).strip(),
            str(story_bible.get("world_invariants", story_bible.get("world_rules", ""))).strip(),
            str(shot.get("location_family", "")).strip(),
            str(shot.get("literal_image", "")).strip(),
            str(shot.get("scene_detail", "")).strip(),
            str(shot.get("emotion", "")).strip(),
            str(shot.get("camera_language", "")).strip(),
            str(shot.get("pose_delta", "")).strip(),
            str(shot.get("continuity_lock", "")).strip(),
            f"face exposure {str(shot.get('face_exposure_level', '')).strip()}",
        ],
        56,
    )


def _face_exposure_level(shot: dict, defaults: dict[str, str], policy: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    mv_function = str(shot.get("mv_function", "")).strip().lower()
    label = str(shot.get("section_label", shot.get("section_name", ""))).strip()
    direct_face_sections = {str(x).strip() for x in policy.get("direct_face_sections", [])} if isinstance(policy, dict) else set()
    if shot_type in defaults:
        base = str(defaults.get(shot_type, "")).strip().lower()
        if shot_type == "EMOTION_CLOSE" and mv_function == "payoff" and label in direct_face_sections:
            return "direct"
        if base:
            return base
    if shot_type == "DETAIL_INSERT":
        return "hidden"
    if shot_type == "ENV_TRANSITION":
        return "partial"
    if shot_type == "EMOTION_CLOSE":
        return "direct" if mv_function == "payoff" else "soft"
    if shot_type == "CHAR_MASTER":
        return "soft"
    return "partial"


def _heroine_visibility(shot: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    if shot_type == "DETAIL_INSERT":
        return "implied"
    if shot_type == "ENV_TRANSITION":
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
    visual_mode = str(policy.get("visual_mode", "")).strip().lower() if isinstance(policy, dict) else ""
    if visual_mode == "environment_first" and shot_type != "CHAR_MASTER":
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
            f"{beat.get('literal_image', '')}|{beat.get('visible_action', '')}|{beat.get('payoff_role', '')}"
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
        f"continuity_mode={policy.get('continuity_mode', '')}; "
        f"face_policy={policy.get('face_policy', '')}; "
        f"shot_bias={policy.get('shot_bias', '')}; "
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
    continuity_mode = str(policy.get("continuity_mode", "")).strip().lower()
    face_policy = str(policy.get("face_policy", "")).strip().lower()
    shot_bias = str(policy.get("shot_bias", "")).strip().lower()
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
        scores["PERF_WIDE"] += 0.5
        scores["EMOTION_CLOSE"] -= 3.0
        scores["CHAR_MASTER"] -= 1.0
    else:
        scores["PERF_WIDE"] += 1.0
        scores["ENV_TRANSITION"] += 0.5

    if shot_bias == "performance":
        scores["PERF_WIDE"] += 2.0
        scores["CHAR_MASTER"] += 1.0
    elif shot_bias == "environment":
        scores["ENV_TRANSITION"] += 2.0
        scores["DETAIL_INSERT"] += 1.0
        scores["EMOTION_CLOSE"] -= 1.0
    elif shot_bias == "object_symbol":
        scores["DETAIL_INSERT"] += 2.5
        scores["ENV_TRANSITION"] += 0.5
        scores["EMOTION_CLOSE"] -= 1.0
        scores["CHAR_MASTER"] -= 1.0

    if face_policy == "avoid":
        scores["EMOTION_CLOSE"] -= 6.0
        scores["CHAR_MASTER"] -= 2.0
        scores["PERF_WIDE"] += 1.0
        scores["ENV_TRANSITION"] += 1.0
        scores["DETAIL_INSERT"] += 1.0
    elif face_policy == "payoff_only":
        if allow_direct_face and payoff_role in {"release", "arrival", "payoff"}:
            scores["EMOTION_CLOSE"] += 3.0
            scores["CHAR_MASTER"] += 1.0
        else:
            scores["EMOTION_CLOSE"] -= 5.0
    elif face_policy == "selective":
        if allow_direct_face or section_name == "chorus" or payoff_role in {"release", "arrival", "payoff"}:
            scores["EMOTION_CLOSE"] += 1.5
        else:
            scores["EMOTION_CLOSE"] -= 1.5
    elif face_policy == "frequent":
        scores["EMOTION_CLOSE"] += 3.0
        scores["CHAR_MASTER"] += 1.0

    if section_name == "chorus" or payoff_role in {"release", "arrival", "payoff"}:
        scores["PERF_WIDE"] += 2.0
        scores["CHAR_MASTER"] += 1.5
        if allow_direct_face:
            scores["EMOTION_CLOSE"] += 2.0
    if section_name in {"intro", "bridge", "outro"} or payoff_role in {"entry", "interrupt", "residue"}:
        scores["ENV_TRANSITION"] += 1.5
    if continuity_mode == "same_heroine":
        scores["CHAR_MASTER"] += 1.5
        scores["PERF_WIDE"] += 1.0
    if detail_friendly:
        scores["DETAIL_INSERT"] += 2.5
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


def _forced_shot_type(shot: dict, beat: dict, policy: dict) -> str | None:
    if not isinstance(policy, dict):
        return None
    face_policy = str(policy.get("face_policy", "")).strip().lower()
    section_label = str(beat.get("section_label", shot.get("section_label", ""))).strip()
    payoff_role = str(beat.get("payoff_role", shot.get("edit_role", ""))).strip().lower()
    direct_face_sections = {str(x).strip() for x in policy.get("direct_face_sections", []) if str(x).strip()}
    if face_policy == "payoff_only" and section_label in direct_face_sections and payoff_role in {"release", "arrival", "payoff"}:
        return "EMOTION_CLOSE"
    return None


def _canonical_edit_role(raw_edit_role: object, payoff_role: object) -> str:
    payoff = str(payoff_role).strip().lower()
    if payoff in {"entry", "interrupt", "residue", "develop", "hold", "release"}:
        return payoff
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
