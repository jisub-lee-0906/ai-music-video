from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_scene_outline
from ai_mv.core.director_brief import build_director_brief_intent


def build_scene_outline(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    timeline = payload["lyrics_timeline"]
    bpm = _resolve_bpm(config, payload)
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    shot_packages: list[dict] = []
    for section_index, section in enumerate(sections, start=1):
        section_name = str(section.get("section_name", "")).strip()
        section_label = str(section.get("section_label", section_name)).strip() or section_name or f"Section {section_index}"
        line_map = {
            int(row.get("line_index", 0)): str(row.get("text", "")).strip()
            for row in section.get("lines", [])
            if isinstance(row, dict) and int(row.get("line_index", 0)) > 0 and str(row.get("text", "")).strip()
        }
        beats = [row for row in section.get("lyric_beats", []) if isinstance(row, dict)]
        for beat_index, beat in enumerate(beats, start=1):
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            shot_role = _shot_role(section_label, beat_index, len(beats), str(beat.get("payoff_role", "")).strip())
            for segment in _beat_segments(config, beat, shot_role, bpm):
                shot_packages.append(
                    {
                        "shot_id": _segment_shot_id(beat_id, segment["segment_index"], segment["segment_count"]),
                        "section_name": section_name,
                        "section_label": section_label,
                        "beat_refs": [beat_id],
                        "line_refs": [int(x) for x in beat.get("line_refs", []) if int(x) > 0],
                        "lyric_lines": [line_map.get(int(x), "") for x in beat.get("line_refs", []) if int(x) in line_map],
                        "literal_image": str(beat.get("literal_image", "")).strip(),
                        "visible_action": str(beat.get("visible_action", "")).strip(),
                        "emotional_turn": str(beat.get("emotional_turn", "")).strip(),
                        "continuity_anchor": str(beat.get("continuity_anchor", "")).strip(),
                        "payoff_role": str(beat.get("payoff_role", "")).strip(),
                        "shot_role": _segment_shot_role(shot_role, segment["segment_index"], segment["segment_count"]),
                        "duration_sec": segment["duration_sec"],
                        "segment_index": segment["segment_index"],
                        "segment_count": segment["segment_count"],
                        "segment_focus": _segment_focus(segment["segment_index"], segment["segment_count"], shot_role),
                        "start_sec": segment["start_sec"],
                        "end_sec": segment["end_sec"],
                    }
                )
    return normalize_scene_outline(
        {
            "brief_name": brief["brief_name"],
            "story_premise": brief["story_premise"],
            "shot_packages": shot_packages,
        }
    )


def build_scene_plan(config: dict, payload: dict) -> dict:
    return build_scene_outline(config, payload)


def build_scene_outline_preview_prompt(config: dict, payload: dict) -> str:
    brief = build_director_brief_intent(config)
    return (
        "Create a minimal scene outline from the lyric timeline. "
        f"Story premise={brief['story_premise']}. "
        "Use lyrics as the source of what is happening now. "
        "Use the profile only as world context for connected places and carry-over props. "
        "For each lyric beat, keep only the visible image, visible action, emotional turn, carry-forward detail, and timing. "
        "Do not create final prompt prose."
    )


def build_scene_plan_preview_prompt(config: dict, payload: dict) -> str:
    return build_scene_outline_preview_prompt(config, payload)


def _shot_role(section_label: str, beat_index: int, beat_count: int, payoff_role: str) -> str:
    low = section_label.lower()
    payoff = payoff_role.lower()
    if "bridge" in low:
        if beat_index == 1:
            return "tighten"
        if beat_index == beat_count:
            return "handoff"
        return "tighten"
    if payoff == "release":
        return "release"
    if payoff in {"tighten", "pressure"}:
        return "tighten"
    if beat_count <= 1:
        return "setup"
    if beat_index == 1:
        return "setup"
    if beat_index == beat_count:
        return "release" if "final chorus" in low else "handoff"
    if beat_index == beat_count - 1:
        return "handoff"
    return "carry"


def _duration(beat: dict) -> float:
    start = float(beat.get("start_sec", 0.0) or 0.0)
    end = float(beat.get("end_sec", 0.0) or 0.0)
    return max(0.5, end - start) if end > start else 2.0


def _beat_segments(config: dict, beat: dict, shot_role: str, bpm: int) -> list[dict]:
    duration = _duration(beat)
    render = config.get("render", {}) if isinstance(config, dict) else {}
    wan_safe = float(render.get("wan_safe_max_gap_sec", 4.0) or 4.0)
    wan_max = float(render.get("wan_max_clip_sec", 5.0) or 5.0)
    beat_sec = _musical_beat_sec(bpm)
    duration_beats = max(1.0, duration / beat_sec)
    target_beats = 4.0 if shot_role in {"release", "handoff"} else 6.0
    time_target = max(wan_safe, min(wan_max, target_beats * beat_sec))
    content_target = max(1, int(-(-duration_beats // target_beats)))
    time_target_count = max(1, int(-(-duration // time_target)))
    count = max(content_target, time_target_count)
    start = float(beat.get("start_sec", 0.0) or 0.0)
    segment_span = duration / float(count)
    out: list[dict] = []
    for idx in range(count):
        seg_start = round(start + segment_span * idx, 3)
        seg_end = round(start + segment_span * (idx + 1), 3)
        out.append(
            {
                "segment_index": idx + 1,
                "segment_count": count,
                "duration_sec": round(max(0.5, seg_end - seg_start), 3),
                "start_sec": seg_start,
                "end_sec": seg_end,
            }
        )
    return out


def _musical_beat_sec(bpm: int) -> float:
    bpm = bpm if bpm > 0 else 100
    return 60.0 / float(bpm)


def _resolve_bpm(config: dict, payload: dict) -> int:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    try:
        bpm = int(audio_map.get("bpm_estimate", 0) or 0)
    except Exception:
        bpm = 0
    if bpm > 0:
        return bpm
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    try:
        bpm = int(audio.get("bpm", 0) or 0)
    except Exception:
        bpm = 0
    return bpm if bpm > 0 else 100


def _segment_shot_role(base: str, segment_index: int, segment_count: int) -> str:
    if segment_count <= 1:
        return base
    if segment_index == 1:
        return "setup" if base == "setup" else "carry"
    if segment_index == segment_count:
        return base
    return "carry"


def _segment_focus(segment_index: int, segment_count: int, shot_role: str) -> str:
    if segment_count <= 1:
        return "balanced moment"
    if segment_index == 1:
        return "entry gesture"
    if segment_index == segment_count:
        if shot_role in {"release", "handoff"}:
            return "next-state release"
        return "carry-forward state"
    if shot_role == "tighten":
        return "physical tension detail"
    return "body detail or object detail"


def _segment_shot_id(beat_id: str, segment_index: int, segment_count: int) -> str:
    if segment_count <= 1:
        return beat_id
    return f"{beat_id}_s{segment_index}"
