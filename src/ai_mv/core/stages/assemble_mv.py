from __future__ import annotations

from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import final_video_path
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.utils.path_utils import resolve_generated_file


def run_assemble_mv(stage_input: StageInput) -> StageOutput:
    clips = _resolve_clip_results(stage_input.config, stage_input.payload)
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
    quality_findings_path = _review_quality_findings_path(stage_input.config)
    if quality_findings_path:
        review_inputs["quality_findings_path"] = quality_findings_path
    return StageOutput(
        "assemble_mv",
        "done",
        {
            "final_video": str(final_video),
            "review_inputs": review_inputs,
        },
        [str(final_video)],
    )


def _resolve_clip_results(config: dict, payload: dict) -> list[Path]:
    out: list[Path] = []
    for row in payload.get("clip_results", []):
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
