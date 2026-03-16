from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_shot_timeline
from ai_mv.core.contracts.prompt_schema import KINETIC_INTENSITIES, KINETIC_TRANSITIONS, SHOT_TYPES, shot_timeline_schema
from ai_mv.core.visual_pipeline import attach_tti_metadata
from ai_mv.infra.codex_cli_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    story_bible = payload["visual_story_bible"]
    lyrics_timeline = payload["lyrics_timeline"]
    spec = generate_structured(config, _planner_prompt(config, payload), shot_timeline_schema())
    plan = normalize_shot_timeline(spec, story_bible.get("lyric_beats", []))
    shots = _assign_story_metadata(plan["shots"], lyrics_timeline, story_bible)
    return {"master_anchor": plan["master_anchor"], "shots": shots}


def build_tti_preview_prompt(config: dict, payload: dict) -> str:
    return _planner_prompt(config, payload)


def _planner_prompt(config: dict, payload: dict) -> str:
    story_bible = payload["visual_story_bible"]
    timeline = payload["lyrics_timeline"]
    return (
        "You are a lyric-first shot planner building a shot timeline for downstream renderers. "
        "Return strict JSON only with shape {\"master_anchor\":{...},\"shots\":[...]}. No prose outside JSON. "
        "Create exactly one shot item for every lyric beat in order. "
        "master_anchor prompt_text must contain only stable identity and world facts. "
        "Default aesthetic baseline is stunningly beautiful photorealistic live-action imagery with idol-like features, "
        "high-end fashion model aesthetic, cinematic lighting, sharp focus on eyes, 8k polish, and highly detailed face rendering. "
        "Every shot must include lyric_beat_id,shot_type,camera_language,pose_delta,emotion,scene_detail,motion_hint,space_relation,edit_role,continuity_lock,clip_count,start_frame,end_frame,kinetic_transition,lighting_fx,kinetic_intensity. "
        "Use the lyric beat as the source of truth. "
        "Safe coverage is forbidden. Do not default to generic portrait coverage, gentle glide, or static beauty framing. "
        "camera_language must explicitly name an aggressive camera move or frame behavior usable by downstream render stages. "
        "For release, payoff, and high-energy beats, prioritize whip pan, snap zoom, crash push-in, smash reframe, strobe jump, match-cut pose, extreme close-up pressure, or hard lateral streaks. "
        "lighting_fx must treat lighting as an active tension device: strobe hit, overexposed flash reset, hard neon contrast, pulsing practical flare, or blackout edge recovery. "
        "Even at maximum motion, the heroine must remain stunningly beautiful and editorial-grade: preserve flattering facial structure, clean skin, strong eye detail, premium hair styling, and luxury fashion image quality. "
        "start_frame and end_frame must differ clearly in framing, subject scale, camera axis, or lighting state. "
        "If a beat is high or max kinetic intensity, do not return a static start/end pair. "
        "NO TEXT, NO TYPOGRAPHY, NO WATERMARKS, NO LOGOS, NO SIGNAGE, NO UI OVERLAY. "
        "All frames must read as clean live-action imagery with zero rendered text elements. "
        "camera_language and space_relation must be compact structural phrases usable by downstream render stages. "
        "edit_role should fit the lyric beat function: entry, develop, release, hold, interrupt, or residue. "
        f"Allowed kinetic transitions={', '.join(KINETIC_TRANSITIONS)}. "
        f"Allowed kinetic intensities={', '.join(KINETIC_INTENSITIES)}. "
        "Examples: payoff beat -> camera_language='whip pan into extreme close-up', kinetic_transition='strobe_jump', lighting_fx='white flash to hard neon lock'. "
        "Examples: interrupt beat -> camera_language='crash push then hold', kinetic_transition='smash_reframe', lighting_fx='single strobe hit then shadow recovery'. "
        f"Allowed shot types={', '.join(SHOT_TYPES)}. "
        f"Story bible={_story_bible_digest(story_bible)}. "
        f"Lyric timeline={_timeline_digest(timeline)}."
    )


def _assign_story_metadata(shots: list[dict], timeline: dict, story_bible: dict) -> list[dict]:
    beat_map = {
        str(beat.get("beat_id", "")).strip(): beat
        for beat in story_bible.get("lyric_beats", [])
        if isinstance(beat, dict)
    }
    section_bounds = _section_bounds(timeline)
    out: list[dict] = []
    for shot in shots:
        beat = beat_map[str(shot["lyric_beat_id"])]
        bounds = section_bounds.get(str(beat.get("beat_id", "")), {"start_sec": 0.0, "end_sec": 4.0})
        item = dict(shot)
        item["duration_sec"] = round(max(0.001, float(bounds["end_sec"]) - float(bounds["start_sec"])), 3)
        item["scene_detail"] = str(item.get("scene_detail", "")).strip() or str(beat.get("literal_image", "")).strip()
        item["motion_hint"] = str(item.get("motion_hint", "")).strip() or str(beat.get("visible_action", "")).strip()
        item["emotion"] = str(item.get("emotion", "")).strip() or str(beat.get("emotional_turn", "")).strip()
        item["continuity_anchor"] = str(beat.get("continuity_anchor", "")).strip()
        item["edit_role"] = str(item.get("edit_role", "")).strip().lower()
        item["mv_function"] = _mv_function(item["edit_role"])
        item["transition_role"] = _transition_role(item["edit_role"])
        item["line_refs"] = list(beat.get("line_refs", []))
        item["literal_image"] = str(beat.get("literal_image", "")).strip()
        out.append(attach_tti_metadata(item, item["section_name"], item["section_label"]))
    return out


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
            f"{beat.get('literal_image', '')}|{beat.get('visible_action', '')}|"
            f"{beat.get('payoff_role', '')}|{beat.get('camera_commitment', '')}"
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
