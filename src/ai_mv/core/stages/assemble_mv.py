from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import final_video_path
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.utils.path_utils import resolve_generated_file
from ai_mv.utils.time_utils import ffprobe_duration


def run_assemble_mv(stage_input: StageInput) -> StageOutput:
    clip_segments = _assembly_clip_segments(stage_input.config, stage_input.payload)
    audio = Path(
        resolve_generated_file(
            stage_input.config,
            str(stage_input.payload.get("music_file", "")).strip(),
            {".wav", ".mp3", ".flac", ".m4a"},
            "audio",
        )
    )
    final_video = final_video_path(stage_input.config, stage_input.run_id)
    ok = run_ffmpeg_mux(clip_segments, audio, final_video, stage_input.config)
    if not ok:
        raise RuntimeError("ffmpeg assemble failed")
    review_inputs = {
        "music_file": str(stage_input.payload.get("music_file", "")).strip(),
        "clip_results": list(stage_input.payload.get("clip_results", [])),
        "final_video": str(final_video),
        "edit_intent_by_shot": _edit_intent_by_shot(stage_input.payload),
        "render_count_by_shot": _render_count_by_shot(stage_input.payload),
        "render_priority_by_shot": _render_priority_by_shot(stage_input.payload),
        "render_planning_by_shot": _render_planning_by_shot(stage_input.payload),
    }
    assembly_plan = _assembly_plan(stage_input.payload)
    quality_findings_path = _review_quality_findings_path(stage_input.config)
    if quality_findings_path:
        review_inputs["quality_findings_path"] = quality_findings_path
    return StageOutput(
        "assemble_mv",
        "done",
        {
            "final_video": str(final_video),
            "assembly_plan": assembly_plan,
            "review_inputs": review_inputs,
        },
        [str(final_video)],
    )


def _resolve_clip_results(config: dict, clip_rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in clip_rows:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        video = str(row.get("video", "")).strip()
        if not video:
            continue
        out.append(
            {
                "shot_id": shot_id,
                "section_id": str(row.get("section_id", "")).strip(),
                "material_id": str(row.get("material_id", "")).strip(),
                "path": Path(resolve_generated_file(config, video, {".mp4", ".mov", ".mkv", ".webm"}, "video")),
            }
        )
    if not out:
        raise RuntimeError("assemble requires at least one rendered clip")
    return out



def _review_quality_findings_path(config: object) -> str:
    review_cfg = config.get("review") if isinstance(config, dict) else None
    if not isinstance(review_cfg, dict):
        return ""
    return str(review_cfg.get("quality_findings_path", "")).strip()



def _assembly_clip_segments(config: dict, payload: dict, duration_by_shot: dict[str, float] | None = None) -> list[dict]:
    clip_rows = _resolve_clip_results(config, _ordered_clip_rows(payload))
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    shot_plan = payload.get("shot_plan") if isinstance(payload, dict) else None
    audio_map = payload.get("audio_map") if isinstance(payload, dict) else None
    render_rows = [row for row in render_plan if isinstance(row, dict)] if isinstance(render_plan, list) else []
    shot_plan_by_shot = {
        str(row.get("shot_id", "")).strip(): row
        for row in shot_plan
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    } if isinstance(shot_plan, list) else {}
    edit_intent_by_shot = {
        str(row.get("shot_id", "")).strip(): dict(row.get("edit_intent", {}))
        for row in render_rows
        if str(row.get("shot_id", "")).strip() and isinstance(row.get("edit_intent"), dict)
    }
    durations = duration_by_shot if isinstance(duration_by_shot, dict) else {}
    out: list[dict] = []
    for row in clip_rows:
        shot_id = str(row.get("shot_id", "")).strip()
        edit_intent = edit_intent_by_shot.get(shot_id, {})
        clip_duration = float(durations.get(shot_id) or ffprobe_duration(row["path"]))
        target_clip_sec = _safe_float(edit_intent.get("target_clip_sec"), 0.0)
        trim_start_sec, trim_end_sec = _trim_window_for_clip(clip_duration, target_clip_sec, edit_intent)
        trim_start_sec, trim_end_sec = _snap_trim_window_to_audio_timing(
            trim_start_sec,
            trim_end_sec,
            clip_duration,
            shot_plan_by_shot.get(shot_id, {}),
            audio_map if isinstance(audio_map, dict) else {},
            edit_intent,
        )
        out.append({**row, "trim_start_sec": trim_start_sec, "trim_end_sec": trim_end_sec})
    return out



def _trim_window_for_clip(clip_duration: float, target_clip_sec: float, edit_intent: dict) -> tuple[float | None, float | None]:
    duration = max(0.0, float(clip_duration or 0.0))
    target = max(0.0, float(target_clip_sec or 0.0))
    if duration <= 0.0 or target <= 0.0 or duration <= target + 0.05:
        return None, None
    section_emphasis = str(edit_intent.get("section_emphasis", "")).strip()
    transition_in = str(edit_intent.get("transition_in", "")).strip()
    transition_out = str(edit_intent.get("transition_out", "")).strip()
    available = max(0.0, duration - target)
    if section_emphasis == "chorus_push":
        start = available / 2.0
    elif section_emphasis in {"release_fade", "bridge_contrast"} or transition_out in {"fade_out", "handoff_out", "accent_out"}:
        start = available
    elif transition_in in {"accent_in", "cut_in", "glide_in", "hold_in"}:
        start = 0.0
    else:
        start = available / 2.0
    end = min(duration, start + target)
    return round(start, 3), round(end, 3)



def _snap_trim_window_to_audio_timing(
    trim_start_sec: float | None,
    trim_end_sec: float | None,
    clip_duration: float,
    shot: dict,
    audio_map: dict,
    edit_intent: dict,
) -> tuple[float | None, float | None]:
    if trim_start_sec is None or trim_end_sec is None or not isinstance(shot, dict) or not shot:
        return trim_start_sec, trim_end_sec
    shot_start_sec = _safe_float(shot.get("start_sec"), 0.0)
    shot_duration_sec = _safe_float(shot.get("duration_sec"), 0.0)
    clip_duration_sec = max(0.0, float(clip_duration or 0.0))
    effective_duration_sec = min(clip_duration_sec, shot_duration_sec) if shot_duration_sec > 0.0 else clip_duration_sec
    shot_end_sec = shot_start_sec + effective_duration_sec
    if shot_end_sec <= shot_start_sec:
        return trim_start_sec, trim_end_sec
    desired_start_sec = shot_start_sec + float(trim_start_sec)
    desired_end_sec = min(shot_end_sec, shot_start_sec + float(trim_end_sec))
    target_duration_sec = max(0.0, desired_end_sec - desired_start_sec)
    timing_points = _timing_points_for_shot(audio_map, edit_intent, shot_start_sec, shot_end_sec)
    if len(timing_points) < 2:
        return trim_start_sec, trim_end_sec
    best_pair: tuple[float, float] | None = None
    best_score: float | None = None
    for left_idx, start_sec in enumerate(timing_points[:-1]):
        for end_sec in timing_points[left_idx + 1 :]:
            duration_sec = end_sec - start_sec
            if duration_sec <= 0.05:
                continue
            score = (
                abs(start_sec - desired_start_sec)
                + abs(end_sec - desired_end_sec)
                + (0.25 * abs(duration_sec - target_duration_sec))
            )
            if best_score is None or score < best_score:
                best_pair = (start_sec, end_sec)
                best_score = score
    if not best_pair:
        return trim_start_sec, trim_end_sec
    snapped_start_sec = round(max(0.0, best_pair[0] - shot_start_sec), 3)
    snapped_end_sec = round(min(clip_duration_sec, best_pair[1] - shot_start_sec), 3)
    if snapped_end_sec <= snapped_start_sec + 0.05:
        return trim_start_sec, trim_end_sec
    return snapped_start_sec, snapped_end_sec



def _timing_points_for_shot(audio_map: dict, edit_intent: dict, shot_start_sec: float, shot_end_sec: float) -> list[float]:
    timing = audio_map.get("timing") if isinstance(audio_map, dict) else None
    if not isinstance(timing, dict):
        return []
    use_bar_grid = _prefer_bar_snap(edit_intent)
    primary_key = "bar_times_sec" if use_bar_grid else "grid_beat_times_sec"
    fallback_key = "grid_beat_times_sec" if use_bar_grid else "bar_times_sec"
    primary_real_points = _real_timing_points(timing.get(primary_key), shot_start_sec, shot_end_sec)
    if len(primary_real_points) >= 2:
        return _bounded_timing_points(primary_real_points, shot_start_sec, shot_end_sec)
    fallback_real_points = _real_timing_points(timing.get(fallback_key), shot_start_sec, shot_end_sec)
    if len(fallback_real_points) >= 2:
        return _bounded_timing_points(fallback_real_points, shot_start_sec, shot_end_sec)
    return []



def _real_timing_points(values: object, shot_start_sec: float, shot_end_sec: float) -> list[float]:
    real_points: set[float] = set()
    if isinstance(values, list):
        for raw in values:
            value = _safe_float(raw, -1.0)
            if shot_start_sec <= value <= shot_end_sec:
                real_points.add(round(value, 6))
    return sorted(real_points)



def _bounded_timing_points(real_points: list[float], shot_start_sec: float, shot_end_sec: float) -> list[float]:
    if not real_points:
        return []
    return sorted({round(shot_start_sec, 6), round(shot_end_sec, 6), *real_points})



def _prefer_bar_snap(edit_intent: dict) -> bool:
    section_emphasis = str(edit_intent.get("section_emphasis", "")).strip()
    transition_out = str(edit_intent.get("transition_out", "")).strip()
    return section_emphasis in {"chorus_push", "bridge_contrast", "release_fade"} or transition_out in {
        "fade_out",
        "handoff_out",
        "accent_out",
    }



def _safe_float(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if math.isfinite(parsed) else default



def _ordered_clip_rows(payload: dict) -> list[dict]:
    clip_results = payload.get("clip_results") if isinstance(payload, dict) else None
    shot_plan = payload.get("shot_plan") if isinstance(payload, dict) else None
    clip_rows = [dict(row) for row in clip_results if isinstance(row, dict)] if isinstance(clip_results, list) else []
    if not clip_rows:
        return []
    shot_order = {
        str(row.get("shot_id", "")).strip(): idx
        for idx, row in enumerate(shot_plan)
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    } if isinstance(shot_plan, list) else {}
    if not shot_order:
        return clip_rows
    return sorted(
        clip_rows,
        key=lambda row: (
            shot_order.get(str(row.get("shot_id", "")).strip(), len(shot_order)),
            str(row.get("shot_id", "")).strip(),
        ),
    )



def _edit_intent_by_shot(payload: dict) -> dict[str, dict]:
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    if not isinstance(render_plan, list):
        return {}
    out: dict[str, dict] = {}
    for row in render_plan:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        edit_intent = row.get("edit_intent")
        if shot_id and isinstance(edit_intent, dict):
            out[shot_id] = dict(edit_intent)
    return out



def _render_count_by_shot(payload: dict) -> dict[str, int]:
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    if not isinstance(render_plan, list):
        return {}
    out: dict[str, int] = {}
    for row in render_plan:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        try:
            render_count = int(row.get("render_count"))
        except Exception:
            continue
        out[shot_id] = render_count
    return out



def _render_priority_by_shot(payload: dict) -> dict[str, float]:
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    if not isinstance(render_plan, list):
        return {}
    out: dict[str, float] = {}
    for row in render_plan:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        try:
            render_priority = float(row.get("render_priority_score"))
        except Exception:
            continue
        out[shot_id] = render_priority
    return out



def _render_planning_by_shot(payload: dict) -> dict[str, dict]:
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    if not isinstance(render_plan, list):
        return {}
    out: dict[str, dict] = {}
    for row in render_plan:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        render_planning = row.get("render_planning")
        if shot_id and isinstance(render_planning, dict):
            out[shot_id] = dict(render_planning)
    return out



def _assembly_plan(payload: dict) -> dict:
    clip_results = payload.get("clip_results") if isinstance(payload, dict) else None
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    clip_rows = _ordered_clip_rows(payload)
    render_rows = [row for row in render_plan if isinstance(row, dict)] if isinstance(render_plan, list) else []
    edit_intent_by_shot = {
        str(row.get("shot_id", "")).strip(): dict(row.get("edit_intent", {}))
        for row in render_rows
        if str(row.get("shot_id", "")).strip() and isinstance(row.get("edit_intent"), dict)
    }
    section_id_by_shot = {
        str(row.get("shot_id", "")).strip(): str(row.get("section_id", "")).strip()
        for row in render_rows
        if str(row.get("shot_id", "")).strip()
    }
    material_id_by_shot = {
        str(row.get("shot_id", "")).strip(): str(row.get("material_id", "")).strip()
        for row in render_rows
        if str(row.get("shot_id", "")).strip() and str(row.get("material_id", "")).strip()
    }
    section_edits = []
    section_edit_map = {}
    transition_map = {}
    timing_map = {}
    used_ids: list[str] = []
    for idx, row in enumerate(clip_rows):
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        section_id = str(row.get("section_id", "")).strip() or section_id_by_shot.get(shot_id) or shot_id
        material_id = str(row.get("material_id", "")).strip() or material_id_by_shot.get(shot_id, "")
        edit_intent = edit_intent_by_shot.get(shot_id, {})
        coverage_sec = float(edit_intent.get("target_clip_sec", 0.0) or 0.0)
        editorial_weight = str(edit_intent.get("edit_priority", "medium")).strip() or "medium"
        transition_in = str(edit_intent.get("transition_in", "hard_cut")).strip() or "hard_cut"
        transition_out = str(edit_intent.get("transition_out", "hard_cut")).strip() or "hard_cut"
        existing = section_edit_map.get(section_id)
        if existing:
            existing["selected_clip_ids"].append(shot_id)
            if material_id and material_id not in existing["selected_material_ids"]:
                existing["selected_material_ids"].append(material_id)
            existing["coverage_sec"] = float(existing.get("coverage_sec", 0.0) or 0.0) + coverage_sec
            existing["editorial_weight"] = _higher_priority_weight(str(existing.get("editorial_weight", "medium")), editorial_weight)
            existing["transition_out"] = transition_out
        else:
            existing = {
                "section_id": section_id,
                "selected_clip_ids": [shot_id],
                "selected_material_ids": [material_id] if material_id else [],
                "coverage_sec": coverage_sec,
                "editorial_weight": editorial_weight,
                "transition_in": transition_in,
                "transition_out": transition_out,
            }
            section_edits.append(existing)
            section_edit_map[section_id] = existing
            timing_map[section_id] = {
                "sequence_index": idx,
                "coverage_sec": coverage_sec,
                "selected_clip_ids": [shot_id],
            }
        transition_map[section_id] = {
            "transition_in": str(existing.get("transition_in", "hard_cut")),
            "transition_out": str(existing.get("transition_out", "hard_cut")),
        }
        timing_map[section_id] = {
            "sequence_index": int(timing_map.get(section_id, {}).get("sequence_index", idx)),
            "coverage_sec": float(existing.get("coverage_sec", 0.0) or 0.0),
            "selected_clip_ids": list(existing.get("selected_clip_ids", [])),
        }
        used_ids.append(shot_id)
    rejected_clip_map = {
        str(row.get("shot_id", "")).strip(): str(row.get("video", "")).strip()
        for row in clip_rows
        if str(row.get("shot_id", "")).strip() and str(row.get("shot_id", "")).strip() not in used_ids
    }
    return {
        "section_edits": section_edits,
        "section_edit_map": section_edit_map,
        "transition_map": transition_map,
        "timing_map": timing_map,
        "rejected_clip_map": rejected_clip_map,
    }


def _higher_priority_weight(left: str, right: str) -> str:
    rank = {"low": 0, "medium": 1, "high": 2}
    normalized_left = str(left or "medium").strip() or "medium"
    normalized_right = str(right or "medium").strip() or "medium"
    return normalized_left if rank.get(normalized_left, 1) >= rank.get(normalized_right, 1) else normalized_right
