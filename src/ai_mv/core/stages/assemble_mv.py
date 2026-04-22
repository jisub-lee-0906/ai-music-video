from __future__ import annotations

from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import final_video_path
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.utils.path_utils import resolve_generated_file


def run_assemble_mv(stage_input: StageInput) -> StageOutput:
    ordered_clip_rows = _ordered_clip_rows(stage_input.payload)
    clips = _resolve_clip_results(stage_input.config, ordered_clip_rows)
    audio = Path(
        resolve_generated_file(
            stage_input.config,
            str(stage_input.payload.get("music_file", "")).strip(),
            {".wav", ".mp3", ".flac", ".m4a"},
            "audio",
        )
    )
    final_video = final_video_path(stage_input.config, stage_input.run_id)
    ok = run_ffmpeg_mux(clips, audio, final_video, stage_input.config)
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


def _resolve_clip_results(config: dict, clip_rows: list[dict]) -> list[Path]:
    out: list[Path] = []
    for row in clip_rows:
        if not isinstance(row, dict):
            continue
        video = str(row.get("video", "")).strip()
        if not video:
            continue
        out.append(Path(resolve_generated_file(config, video, {".mp4", ".mov", ".mkv", ".webm"}, "video")))
    if not out:
        raise RuntimeError("assemble requires at least one rendered clip")
    return out



def _review_quality_findings_path(config: object) -> str:
    review_cfg = config.get("review") if isinstance(config, dict) else None
    if not isinstance(review_cfg, dict):
        return ""
    return str(review_cfg.get("quality_findings_path", "")).strip()



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
