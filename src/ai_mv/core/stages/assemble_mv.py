from __future__ import annotations

import copy
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
        "production_policy_by_shot": _production_policy_by_shot(stage_input.payload),
        "cadence_profile_by_shot": _clip_segment_value_by_shot(clip_segments, "cadence_profile"),
        "snap_unit_by_shot": _clip_segment_value_by_shot(clip_segments, "snap_unit"),
        "trimmed_coverage_by_shot": _clip_segment_float_by_shot(clip_segments, "trimmed_coverage_sec"),
    }
    assembly_plan = _assembly_plan(stage_input.payload, clip_segments=clip_segments)
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
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    render_rows = [row for row in render_plan if isinstance(row, dict)] if isinstance(render_plan, list) else []
    production_policy_by_shot = _production_policy_by_render_rows(render_rows)
    clip_rows = _resolve_clip_results(config, _policy_interleaved_clip_rows(_ordered_clip_rows(payload), production_policy_by_shot))
    shot_plan = payload.get("shot_plan") if isinstance(payload, dict) else None
    audio_map = payload.get("audio_map") if isinstance(payload, dict) else None
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
        production_policy = production_policy_by_shot.get(shot_id, {})
        clip_duration = float(durations.get(shot_id) or ffprobe_duration(row["path"]))
        target_clip_sec = _policy_capped_target_clip_sec(edit_intent, production_policy)
        trim_start_sec, trim_end_sec = _trim_window_for_clip(clip_duration, target_clip_sec, edit_intent)
        trim_start_sec, trim_end_sec, snap_unit = _snap_trim_window_to_audio_timing(
            trim_start_sec,
            trim_end_sec,
            clip_duration,
            shot_plan_by_shot.get(shot_id, {}),
            audio_map if isinstance(audio_map, dict) else {},
            edit_intent,
        )
        trimmed_coverage_sec = _trimmed_coverage_sec(trim_start_sec, trim_end_sec, clip_duration, target_clip_sec)
        out.append(
            {
                **row,
                "trim_start_sec": trim_start_sec,
                "trim_end_sec": trim_end_sec,
                "trimmed_coverage_sec": trimmed_coverage_sec,
                "snap_unit": snap_unit,
                "cadence_profile": _cadence_profile(edit_intent),
                **_production_policy_segment_fields(production_policy),
            }
        )
    return out



def _policy_capped_target_clip_sec(edit_intent: dict, production_policy: dict) -> float:
    target = _safe_float(edit_intent.get("target_clip_sec"), 0.0)
    duration_policy = production_policy.get("recommended_duration_sec") if isinstance(production_policy, dict) else None
    max_duration = _safe_float(duration_policy.get("max") if isinstance(duration_policy, dict) else None, 0.0)
    if target > 0.0 and max_duration > 0.0:
        return min(target, max_duration)
    return target


def _production_policy_segment_fields(production_policy: dict) -> dict[str, object]:
    if not isinstance(production_policy, dict) or not production_policy:
        return {}
    fields: dict[str, object] = {"production_policy": dict(production_policy)}
    for key in ("candidate_role", "ia2v_risk_class", "anchor_reference_arm"):
        value = str(production_policy.get(key, "")).strip()
        if value:
            fields[key] = value
    duration_policy = production_policy.get("recommended_duration_sec")
    if isinstance(duration_policy, dict):
        fields["recommended_duration_sec"] = dict(duration_policy)
    return fields


def _trim_window_for_clip(clip_duration: float, target_clip_sec: float, edit_intent: dict) -> tuple[float | None, float | None]:
    duration = max(0.0, float(clip_duration or 0.0))
    target = max(0.0, float(target_clip_sec or 0.0))
    if duration <= 0.0 or target <= 0.0 or duration <= target + 0.05:
        return None, None
    section_emphasis = str(edit_intent.get("section_emphasis", "")).strip()
    transition_in = str(edit_intent.get("transition_in", "")).strip()
    transition_out = str(edit_intent.get("transition_out", "")).strip()
    pattern_family = str(edit_intent.get("pattern_family", "")).strip()
    available = max(0.0, duration - target)
    if pattern_family == "hook_punch_in":
        start = available / 2.0
    elif pattern_family == "hook_sustain":
        start = available * 0.25
    elif pattern_family == "hook_surge":
        start = available * 0.4
    elif pattern_family == "support_drive":
        start = available * 0.15
    elif pattern_family == "support_hold":
        start = 0.0
    elif pattern_family == "bridge_glide":
        start = available * 0.35
    elif pattern_family == "bridge_pivot":
        start = available * 0.55
    elif pattern_family == "release_drift":
        start = available * 0.6
    elif pattern_family == "release_tail":
        start = available
    elif section_emphasis == "chorus_push":
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
) -> tuple[float | None, float | None, str]:
    if trim_start_sec is None or trim_end_sec is None or not isinstance(shot, dict) or not shot:
        return trim_start_sec, trim_end_sec, "free"
    shot_start_sec = _safe_float(shot.get("start_sec"), 0.0)
    shot_duration_sec = _safe_float(shot.get("duration_sec"), 0.0)
    clip_duration_sec = max(0.0, float(clip_duration or 0.0))
    effective_duration_sec = min(clip_duration_sec, shot_duration_sec) if shot_duration_sec > 0.0 else clip_duration_sec
    shot_end_sec = shot_start_sec + effective_duration_sec
    if shot_end_sec <= shot_start_sec:
        return trim_start_sec, trim_end_sec, "free"
    desired_start_sec = shot_start_sec + float(trim_start_sec)
    desired_end_sec = min(shot_end_sec, shot_start_sec + float(trim_end_sec))
    target_duration_sec = max(0.0, desired_end_sec - desired_start_sec)
    timing_points, snap_unit = _timing_points_for_shot(audio_map, edit_intent, shot_start_sec, shot_end_sec)
    if len(timing_points) < 2:
        return trim_start_sec, trim_end_sec, "free"
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
        return trim_start_sec, trim_end_sec, "free"
    snapped_start_sec = round(max(0.0, best_pair[0] - shot_start_sec), 3)
    snapped_end_sec = round(min(clip_duration_sec, best_pair[1] - shot_start_sec), 3)
    if snapped_end_sec <= snapped_start_sec + 0.05:
        return trim_start_sec, trim_end_sec, "free"
    return snapped_start_sec, snapped_end_sec, snap_unit



def _timing_points_for_shot(audio_map: dict, edit_intent: dict, shot_start_sec: float, shot_end_sec: float) -> tuple[list[float], str]:
    timing = audio_map.get("timing") if isinstance(audio_map, dict) else None
    if not isinstance(timing, dict):
        return [], "free"
    use_bar_grid = _prefer_bar_snap(edit_intent)
    primary_key = "bar_times_sec" if use_bar_grid else "grid_beat_times_sec"
    fallback_key = "grid_beat_times_sec" if use_bar_grid else "bar_times_sec"
    primary_unit = "bar" if primary_key == "bar_times_sec" else "beat"
    fallback_unit = "bar" if fallback_key == "bar_times_sec" else "beat"
    primary_real_points = _real_timing_points(timing.get(primary_key), shot_start_sec, shot_end_sec)
    if len(primary_real_points) >= 2:
        return _bounded_timing_points(primary_real_points, shot_start_sec, shot_end_sec), primary_unit
    fallback_real_points = _real_timing_points(timing.get(fallback_key), shot_start_sec, shot_end_sec)
    if len(fallback_real_points) >= 2:
        return _bounded_timing_points(fallback_real_points, shot_start_sec, shot_end_sec), fallback_unit
    return [], "free"



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



def _trimmed_coverage_sec(
    trim_start_sec: float | None,
    trim_end_sec: float | None,
    clip_duration: float,
    default_coverage_sec: float = 0.0,
) -> float:
    if trim_start_sec is None or trim_end_sec is None:
        resolved_clip = max(0.0, float(clip_duration or 0.0))
        resolved_default = max(0.0, float(default_coverage_sec or 0.0))
        if resolved_clip > 0.0 and resolved_default > 0.0:
            return round(min(resolved_clip, resolved_default), 3)
        return round(max(resolved_clip, resolved_default), 3)
    return round(max(0.0, float(trim_end_sec) - float(trim_start_sec)), 3)



def _cadence_profile(edit_intent: dict) -> str:
    section_emphasis = str(edit_intent.get("section_emphasis", "")).strip()
    transition_in = str(edit_intent.get("transition_in", "")).strip()
    transition_out = str(edit_intent.get("transition_out", "")).strip()
    pattern_family = str(edit_intent.get("pattern_family", "")).strip()
    if pattern_family in {"hook_punch_in", "hook_sustain", "hook_surge"} or section_emphasis == "chorus_push":
        return "hook_dense"
    if pattern_family in {"bridge_glide", "bridge_pivot"} or section_emphasis == "bridge_contrast":
        return "bridge_pivot"
    if pattern_family in {"release_drift", "release_tail"} or section_emphasis == "release_fade":
        return "release_tail"
    if pattern_family == "support_drive" or transition_in in {"glide_in"} or transition_out in {"fade_out", "handoff_out"}:
        return "support_release"
    return "support_hold"



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



def _policy_interleaved_clip_rows(clip_rows: list[dict], production_policy_by_shot: dict[str, dict]) -> list[dict]:
    if not clip_rows or not isinstance(production_policy_by_shot, dict):
        return clip_rows
    out: list[dict] = []
    group: list[dict] = []
    current_section = ""
    for row in clip_rows:
        section_id = str(row.get("section_id", "")).strip()
        if group and section_id != current_section:
            out.extend(_interleave_section_clip_rows(group, production_policy_by_shot))
            group = []
        group.append(row)
        current_section = section_id
    if group:
        out.extend(_interleave_section_clip_rows(group, production_policy_by_shot))
    return out



def _interleave_section_clip_rows(section_rows: list[dict], production_policy_by_shot: dict[str, dict]) -> list[dict]:
    if len(section_rows) < 3:
        return section_rows
    remaining = list(section_rows)
    ordered: list[dict] = []
    while remaining:
        previous_role = _candidate_role_for_clip_row(ordered[-1], production_policy_by_shot) if ordered else ""
        next_index = 0
        if previous_role:
            replacement_index = _first_non_repeating_policy_index(remaining, previous_role, production_policy_by_shot)
            if replacement_index is not None:
                next_index = replacement_index
        ordered.append(remaining.pop(next_index))
    return ordered



def _first_non_repeating_policy_index(
    rows: list[dict],
    previous_role: str,
    production_policy_by_shot: dict[str, dict],
) -> int | None:
    candidates: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        role = _candidate_role_for_clip_row(row, production_policy_by_shot)
        if role and role != previous_role:
            candidates.append((_risk_rank_for_clip_row(row, production_policy_by_shot), index))
    if not candidates:
        return None
    return sorted(candidates)[0][1]



def _candidate_role_for_clip_row(row: dict, production_policy_by_shot: dict[str, dict]) -> str:
    shot_id = str(row.get("shot_id", "")).strip()
    policy = production_policy_by_shot.get(shot_id) if isinstance(production_policy_by_shot, dict) else None
    if not isinstance(policy, dict):
        return ""
    return str(policy.get("candidate_role", "")).strip()



def _risk_rank_for_clip_row(row: dict, production_policy_by_shot: dict[str, dict]) -> int:
    shot_id = str(row.get("shot_id", "")).strip()
    policy = production_policy_by_shot.get(shot_id) if isinstance(production_policy_by_shot, dict) else None
    risk = str(policy.get("ia2v_risk_class", "green")).strip() if isinstance(policy, dict) else "green"
    return {"green": 0, "yellow": 1, "red": 2}.get(risk, 0)



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



def _production_policy_by_shot(payload: dict) -> dict[str, dict]:
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    render_rows = [row for row in render_plan if isinstance(row, dict)] if isinstance(render_plan, list) else []
    return _production_policy_by_render_rows(render_rows)


def _production_policy_by_render_rows(render_rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in render_rows:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        policy = row.get("production_policy") if isinstance(row.get("production_policy"), dict) else {}
        if not policy:
            policy = {
                key: row.get(key)
                for key in ("candidate_role", "ia2v_risk_class", "anchor_reference_arm", "recommended_duration_sec")
                if row.get(key) not in (None, "", {})
            }
        if policy:
            out[shot_id] = dict(policy)
    return out


def _clip_segment_value_by_shot(clip_segments: list[dict], key: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in clip_segments if isinstance(clip_segments, list) else []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        value = str(row.get(key, "")).strip()
        if shot_id and value:
            out[shot_id] = value
    return out



def _clip_segment_float_by_shot(clip_segments: list[dict], key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in clip_segments if isinstance(clip_segments, list) else []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        value = _safe_float(row.get(key), -1.0)
        if value >= 0.0:
            out[shot_id] = value
    return out



def _assembly_plan(payload: dict, clip_segments: list[dict] | None = None) -> dict:
    clip_results = payload.get("clip_results") if isinstance(payload, dict) else None
    render_plan = payload.get("render_plan") if isinstance(payload, dict) else None
    render_rows = [row for row in render_plan if isinstance(row, dict)] if isinstance(render_plan, list) else []
    production_policy_by_shot = _production_policy_by_render_rows(render_rows)
    clip_rows = [dict(row) for row in clip_segments if isinstance(row, dict)] if isinstance(clip_segments, list) else _policy_interleaved_clip_rows(_ordered_clip_rows(payload), production_policy_by_shot)
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
        trim_start_sec = _safe_float(row.get("trim_start_sec"), 0.0) if row.get("trim_start_sec") is not None else None
        trim_end_sec = _safe_float(row.get("trim_end_sec"), 0.0) if row.get("trim_end_sec") is not None else None
        trimmed_coverage_sec = _safe_float(row.get("trimmed_coverage_sec"), coverage_sec)
        snap_unit = str(row.get("snap_unit", "")).strip() or "free"
        cadence_profile = str(row.get("cadence_profile", "")).strip() or _cadence_profile(edit_intent)
        candidate_role = str(row.get("candidate_role", "")).strip()
        ia2v_risk_class = str(row.get("ia2v_risk_class", "")).strip()
        anchor_reference_arm = str(row.get("anchor_reference_arm", "")).strip()
        existing = section_edit_map.get(section_id)
        if existing:
            existing["selected_clip_ids"].append(shot_id)
            if material_id and material_id not in existing["selected_material_ids"]:
                existing["selected_material_ids"].append(material_id)
            existing["coverage_sec"] = float(existing.get("coverage_sec", 0.0) or 0.0) + coverage_sec
            existing["trimmed_coverage_sec"] = float(existing.get("trimmed_coverage_sec", 0.0) or 0.0) + trimmed_coverage_sec
            existing["editorial_weight"] = _higher_priority_weight(str(existing.get("editorial_weight", "medium")), editorial_weight)
            existing["transition_out"] = transition_out
            existing["trim_start_sec"] = None
            existing["trim_end_sec"] = None
            existing["snap_unit"] = _combine_snap_units(str(existing.get("snap_unit", "free")), snap_unit)
            existing["cadence_profile"] = _combine_cadence_profiles(str(existing.get("cadence_profile", "support_hold")), cadence_profile)
            _append_unique(existing.setdefault("candidate_roles", []), candidate_role)
            _append_unique(existing.setdefault("anchor_reference_arms", []), anchor_reference_arm)
            existing["ia2v_risk_class"] = _combine_risk_classes(str(existing.get("ia2v_risk_class", "green")), ia2v_risk_class)
        else:
            existing = {
                "section_id": section_id,
                "selected_clip_ids": [shot_id],
                "selected_material_ids": [material_id] if material_id else [],
                "coverage_sec": coverage_sec,
                "trimmed_coverage_sec": trimmed_coverage_sec,
                "editorial_weight": editorial_weight,
                "transition_in": transition_in,
                "transition_out": transition_out,
                "trim_start_sec": trim_start_sec,
                "trim_end_sec": trim_end_sec,
                "snap_unit": snap_unit,
                "cadence_profile": cadence_profile,
                "candidate_roles": [candidate_role] if candidate_role else [],
                "anchor_reference_arms": [anchor_reference_arm] if anchor_reference_arm else [],
                "ia2v_risk_class": ia2v_risk_class or "green",
            }
            section_edits.append(existing)
            section_edit_map[section_id] = existing
            timing_map[section_id] = {
                "sequence_index": idx,
                "coverage_sec": coverage_sec,
                "trimmed_coverage_sec": trimmed_coverage_sec,
                "selected_clip_ids": [shot_id],
                "trim_start_sec": trim_start_sec,
                "trim_end_sec": trim_end_sec,
                "snap_unit": snap_unit,
                "cadence_profile": cadence_profile,
                "candidate_roles": [candidate_role] if candidate_role else [],
                "anchor_reference_arms": [anchor_reference_arm] if anchor_reference_arm else [],
                "ia2v_risk_class": ia2v_risk_class or "green",
            }
        transition_map[section_id] = {
            "transition_in": str(existing.get("transition_in", "hard_cut")),
            "transition_out": str(existing.get("transition_out", "hard_cut")),
        }
        timing_map[section_id] = {
            "sequence_index": int(timing_map.get(section_id, {}).get("sequence_index", idx)),
            "coverage_sec": float(existing.get("coverage_sec", 0.0) or 0.0),
            "trimmed_coverage_sec": float(existing.get("trimmed_coverage_sec", 0.0) or 0.0),
            "selected_clip_ids": list(existing.get("selected_clip_ids", [])),
            "trim_start_sec": existing.get("trim_start_sec"),
            "trim_end_sec": existing.get("trim_end_sec"),
            "snap_unit": str(existing.get("snap_unit", "free")),
            "cadence_profile": str(existing.get("cadence_profile", "support_hold")),
            "candidate_roles": list(existing.get("candidate_roles", [])) if isinstance(existing.get("candidate_roles"), list) else [],
            "anchor_reference_arms": list(existing.get("anchor_reference_arms", [])) if isinstance(existing.get("anchor_reference_arms"), list) else [],
            "ia2v_risk_class": str(existing.get("ia2v_risk_class", "green")),
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
        "transition_pairs": _transition_pairs_for_clip_sequence(clip_rows),
        "coverage_summary": _assembly_coverage_summary(payload, section_edits),
        "rejected_clip_map": rejected_clip_map,
    }


def _transition_pairs_for_clip_sequence(clip_rows: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    rows = [row for row in clip_rows if isinstance(row, dict) and str(row.get("shot_id", "")).strip()]
    for left, right in zip(rows, rows[1:]):
        left_id = str(left.get("shot_id", "")).strip()
        right_id = str(right.get("shot_id", "")).strip()
        snap_unit = _combine_snap_units(str(left.get("snap_unit", "free")), str(right.get("snap_unit", "free")))
        reason_codes = _bridge_reason_codes(left, right)
        transition_type = _transition_type_for_pair(left, right, snap_unit)
        needs_bridge = bool(reason_codes)
        pairs.append(
            {
                "from_shot_id": left_id,
                "to_shot_id": right_id,
                "from_section_id": str(left.get("section_id", "")).strip(),
                "to_section_id": str(right.get("section_id", "")).strip(),
                "transition_type": transition_type,
                "snap_unit": snap_unit,
                "continuity_strategy": "bridge_recommended" if needs_bridge else "direct_cut_ok",
                "needs_bridge": needs_bridge,
                "bridge_reason_codes": reason_codes,
            }
        )
    return pairs


def _transition_type_for_pair(left: dict, right: dict, snap_unit: str) -> str:
    left_out = str(left.get("transition_out", "")).strip()
    right_in = str(right.get("transition_in", "")).strip()
    left_cadence = str(left.get("cadence_profile", "")).strip()
    right_cadence = str(right.get("cadence_profile", "")).strip()
    if left_out in {"fade_out", "handoff_out"} or right_in in {"glide_in", "hold_in"}:
        return "short_dissolve"
    if snap_unit in {"beat", "bar"} or left_out in {"accent_out", "cut_out"} or right_in in {"accent_in", "cut_in"}:
        return "beat_cut"
    if "hook" in left_cadence or "hook" in right_cadence:
        return "beat_cut"
    return "hard_cut"


def _bridge_reason_codes(left: dict, right: dict) -> list[str]:
    reasons: list[str] = []
    left_role = str(left.get("candidate_role", "")).strip()
    right_role = str(right.get("candidate_role", "")).strip()
    if left_role and right_role and left_role == right_role:
        reasons.append("repeated_candidate_role")
    if _risk_rank(str(left.get("ia2v_risk_class", "green"))) >= 1 or _risk_rank(str(right.get("ia2v_risk_class", "green"))) >= 1:
        reasons.append("elevated_ia2v_risk")
    return reasons


def _risk_rank(value: str) -> int:
    return {"green": 0, "yellow": 1, "red": 2}.get(str(value or "green").strip() or "green", 0)


def _assembly_coverage_summary(payload: dict, section_edits: list[dict]) -> dict:
    audio_duration = _audio_duration_for_assembly(payload)
    raw_coverage = round(sum(_safe_float(row.get("trimmed_coverage_sec"), 0.0) for row in section_edits if isinstance(row, dict)), 3)
    required_min = round(audio_duration * 0.95, 3) if audio_duration > 0.0 else 0.0
    ratio = round(raw_coverage / audio_duration, 3) if audio_duration > 0.0 else 0.0
    deficit = round(max(0.0, required_min - raw_coverage), 3)
    status = "sufficient_raw_coverage" if audio_duration <= 0.0 or raw_coverage >= required_min else "insufficient_raw_coverage"
    return {
        "audio_duration_sec": round(audio_duration, 3),
        "raw_assembly_coverage_sec": raw_coverage,
        "raw_coverage_ratio": ratio,
        "required_min_raw_coverage_sec": required_min,
        "coverage_deficit_sec": deficit,
        "status": status,
        "recommended_action": "" if status == "sufficient_raw_coverage" else "revise_assembly_coverage_before_sync_pad",
    }


def _audio_duration_for_assembly(payload: dict) -> float:
    audio_map = payload.get("audio_map") if isinstance(payload, dict) else None
    if isinstance(audio_map, dict):
        duration = _safe_float(audio_map.get("duration_sec"), 0.0)
        if duration > 0.0:
            return duration
    shot_plan = payload.get("shot_plan") if isinstance(payload, dict) else None
    if isinstance(shot_plan, list) and shot_plan:
        end_times = []
        total = 0.0
        for row in shot_plan:
            if not isinstance(row, dict):
                continue
            start = _safe_float(row.get("start_sec"), 0.0)
            duration = _safe_float(row.get("duration_sec"), 0.0)
            if duration > 0.0:
                total += duration
                end_times.append(start + duration)
        if end_times:
            return max(max(end_times), total)
    return 0.0


def _append_unique(values: list, value: object) -> None:
    normalized = str(value or "").strip()
    if normalized and normalized not in values:
        values.append(normalized)


def _combine_risk_classes(left: str, right: str) -> str:
    rank = {"green": 0, "yellow": 1, "red": 2}
    normalized_left = str(left or "green").strip() or "green"
    normalized_right = str(right or "green").strip() or "green"
    return normalized_left if rank.get(normalized_left, 0) >= rank.get(normalized_right, 0) else normalized_right


def _higher_priority_weight(left: str, right: str) -> str:
    rank = {"low": 0, "medium": 1, "high": 2}
    normalized_left = str(left or "medium").strip() or "medium"
    normalized_right = str(right or "medium").strip() or "medium"
    return normalized_left if rank.get(normalized_left, 1) >= rank.get(normalized_right, 1) else normalized_right



def _combine_snap_units(left: str, right: str) -> str:
    rank = {"free": 0, "beat": 1, "bar": 2}
    normalized_left = str(left or "free").strip() or "free"
    normalized_right = str(right or "free").strip() or "free"
    return normalized_left if rank.get(normalized_left, 0) >= rank.get(normalized_right, 0) else normalized_right



def _combine_cadence_profiles(left: str, right: str) -> str:
    rank = {
        "support_hold": 0,
        "support_release": 1,
        "bridge_pivot": 2,
        "release_tail": 3,
        "hook_dense": 4,
    }
    normalized_left = str(left or "support_hold").strip() or "support_hold"
    normalized_right = str(right or "support_hold").strip() or "support_hold"
    return normalized_left if rank.get(normalized_left, 0) >= rank.get(normalized_right, 0) else normalized_right



def apply_assembly_revision(
    assembly_plan: dict,
    *,
    action: str,
    target_shots: list[str] | None = None,
    target_material_ids: list[str] | None = None,
    target_section_ids: list[str] | None = None,
    coverage_extension_sec: float = 0.0,
) -> tuple[dict, dict[str, dict[str, object]]]:
    plan = copy.deepcopy(assembly_plan) if isinstance(assembly_plan, dict) else {}
    section_edit_map = plan.get("section_edit_map") if isinstance(plan.get("section_edit_map"), dict) else {}
    transition_map = plan.get("transition_map") if isinstance(plan.get("transition_map"), dict) else {}
    timing_map = plan.get("timing_map") if isinstance(plan.get("timing_map"), dict) else {}
    section_edits = plan.get("section_edits") if isinstance(plan.get("section_edits"), list) else []
    targeted_shots = {str(value).strip() for value in target_shots or [] if str(value).strip()}
    targeted_materials = {str(value).strip() for value in target_material_ids or [] if str(value).strip()}
    targeted_sections = {str(value).strip() for value in target_section_ids or [] if str(value).strip()}
    revisions_by_shot: dict[str, dict[str, object]] = {}
    targeted_section_ids = [
        str(section_id).strip()
        for section_id, section_row in section_edit_map.items()
        if isinstance(section_row, dict)
        and _section_is_targeted(
            str(section_id).strip(),
            [str(value).strip() for value in section_row.get("selected_clip_ids", []) if str(value).strip()] if isinstance(section_row.get("selected_clip_ids"), list) else [],
            [str(value).strip() for value in section_row.get("selected_material_ids", []) if str(value).strip()] if isinstance(section_row.get("selected_material_ids"), list) else [],
            targeted_sections,
            targeted_shots,
            targeted_materials,
        )
    ]
    coverage_extension_per_section = coverage_extension_sec
    if action == "revise_assembly_coverage_before_sync_pad" and coverage_extension_sec > 0.0 and len(targeted_section_ids) > 1:
        coverage_extension_per_section = coverage_extension_sec / len(targeted_section_ids)

    for section_id, section_row in section_edit_map.items():
        if not isinstance(section_row, dict):
            continue
        normalized_section_id = str(section_id).strip()
        selected_shots = [str(value).strip() for value in section_row.get("selected_clip_ids", []) if str(value).strip()] if isinstance(section_row.get("selected_clip_ids"), list) else []
        selected_materials = [str(value).strip() for value in section_row.get("selected_material_ids", []) if str(value).strip()] if isinstance(section_row.get("selected_material_ids"), list) else []
        if not _section_is_targeted(normalized_section_id, selected_shots, selected_materials, targeted_sections, targeted_shots, targeted_materials):
            continue
        timing_row = timing_map.get(normalized_section_id) if isinstance(timing_map.get(normalized_section_id), dict) else {}
        transition_row = transition_map.get(normalized_section_id) if isinstance(transition_map.get(normalized_section_id), dict) else {}
        if action == "revise_assembly_weights_before_clip_rerender":
            _apply_weight_revision(section_row, timing_row)
        elif action == "revise_transition_selection":
            _apply_transition_revision(section_row, timing_row, transition_row)
        elif action == "revise_assembly_coverage_before_sync_pad":
            _apply_coverage_revision(section_row, timing_row, transition_row, coverage_extension_sec=coverage_extension_per_section)
        transition_map[normalized_section_id] = {
            "transition_in": str(section_row.get("transition_in", transition_row.get("transition_in", "cut_in"))).strip() or "cut_in",
            "transition_out": str(section_row.get("transition_out", transition_row.get("transition_out", "cut_out"))).strip() or "cut_out",
        }
        timing_map[normalized_section_id] = dict(timing_row)
        for shot_id in selected_shots:
            revisions_by_shot[shot_id] = {
                "cadence_profile": str(section_row.get("cadence_profile", timing_row.get("cadence_profile", ""))).strip() or str(timing_row.get("cadence_profile", "")).strip(),
                "snap_unit": str(section_row.get("snap_unit", timing_row.get("snap_unit", ""))).strip() or str(timing_row.get("snap_unit", "")).strip(),
                "trimmed_coverage_sec": float(timing_row.get("trimmed_coverage_sec", section_row.get("trimmed_coverage_sec", 0.0)) or 0.0),
                "transition_in": str(section_row.get("transition_in", transition_row.get("transition_in", "cut_in"))).strip() or "cut_in",
                "transition_out": str(section_row.get("transition_out", transition_row.get("transition_out", "cut_out"))).strip() or "cut_out",
            }

    if isinstance(section_edits, list):
        for row in section_edits:
            if not isinstance(row, dict):
                continue
            section_id = str(row.get("section_id", "")).strip()
            updated = section_edit_map.get(section_id)
            if isinstance(updated, dict):
                row.clear()
                row.update(updated)

    plan["section_edit_map"] = section_edit_map
    plan["transition_map"] = transition_map
    plan["timing_map"] = timing_map
    plan["section_edits"] = section_edits
    return plan, revisions_by_shot



def _section_is_targeted(
    section_id: str,
    selected_shots: list[str],
    selected_materials: list[str],
    target_sections: set[str],
    target_shots_set: set[str],
    target_materials_set: set[str],
) -> bool:
    if not target_sections and not target_shots_set and not target_materials_set:
        return True
    if section_id and section_id in target_sections:
        return True
    if any(shot_id in target_shots_set for shot_id in selected_shots):
        return True
    return any(material_id in target_materials_set for material_id in selected_materials)



def _apply_weight_revision(section_row: dict, timing_row: dict) -> None:
    section_row["editorial_weight"] = "high"
    section_row["cadence_profile"] = "hook_dense"
    section_row["snap_unit"] = "bar"
    base_trimmed = _safe_float(timing_row.get("trimmed_coverage_sec", section_row.get("trimmed_coverage_sec", 0.0)), 0.0)
    revised_trimmed = round(base_trimmed * 0.8, 3) if base_trimmed > 0.0 else base_trimmed
    section_row["trimmed_coverage_sec"] = revised_trimmed
    timing_row["trimmed_coverage_sec"] = revised_trimmed
    timing_row["cadence_profile"] = "hook_dense"
    timing_row["snap_unit"] = "bar"



def _apply_transition_revision(section_row: dict, timing_row: dict, transition_row: dict) -> None:
    section_row["transition_in"] = "glide_in"
    section_row["transition_out"] = "handoff_out"
    section_row["cadence_profile"] = "support_release"
    section_row["snap_unit"] = "beat"
    base_trimmed = _safe_float(timing_row.get("trimmed_coverage_sec", section_row.get("trimmed_coverage_sec", 0.0)), 0.0)
    revised_trimmed = round(base_trimmed * 0.9, 3) if base_trimmed > 0.0 else base_trimmed
    section_row["trimmed_coverage_sec"] = revised_trimmed
    timing_row["trimmed_coverage_sec"] = revised_trimmed
    timing_row["cadence_profile"] = "support_release"
    timing_row["snap_unit"] = "beat"
    transition_row["transition_in"] = "glide_in"
    transition_row["transition_out"] = "handoff_out"



def _apply_coverage_revision(section_row: dict, timing_row: dict, transition_row: dict, *, coverage_extension_sec: float = 0.0) -> None:
    section_row["transition_in"] = "coverage_handoff_in"
    section_row["transition_out"] = "coverage_handoff_out"
    section_row["cadence_profile"] = "coverage_extend"
    section_row["snap_unit"] = "beat"
    base_trimmed = _safe_float(timing_row.get("trimmed_coverage_sec", section_row.get("trimmed_coverage_sec", 0.0)), 0.0)
    extension = max(0.0, float(coverage_extension_sec or 0.0))
    revised_trimmed = round(max(base_trimmed * 1.25, base_trimmed + extension), 3) if base_trimmed > 0.0 else round(extension, 3)
    section_row["trimmed_coverage_sec"] = revised_trimmed
    timing_row["trimmed_coverage_sec"] = revised_trimmed
    timing_row["cadence_profile"] = "coverage_extend"
    timing_row["snap_unit"] = "beat"
    transition_row["transition_in"] = "coverage_handoff_in"
    transition_row["transition_out"] = "coverage_handoff_out"
