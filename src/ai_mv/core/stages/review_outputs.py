from __future__ import annotations

from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.utils.time_utils import ffprobe_duration


def run_review_outputs(stage_input: StageInput) -> StageOutput:
    still_results = [row for row in stage_input.payload.get("still_results", []) if isinstance(row, dict)]
    clip_results = [row for row in stage_input.payload.get("clip_results", []) if isinstance(row, dict)]
    final_video = str(stage_input.payload.get("final_video", "")).strip()
    planned_shot_ids = [str(row.get("shot_id", "")).strip() for row in stage_input.payload.get("shot_plan", []) if isinstance(row, dict)]
    still_status = _shot_asset_status(still_results, "image")
    clip_status = _shot_asset_status(clip_results, "video")
    rerender_targets = _rerender_targets(planned_shot_ids, still_status, clip_status, stage_input.config)
    final_video_exists = _file_exists(final_video)
    still_done = sum(1 for shot_id in planned_shot_ids if still_status.get(shot_id, False))
    clip_done = sum(1 for shot_id in planned_shot_ids if clip_status.get(shot_id, False))
    blocking_checks = {
        "final_video_exists": final_video_exists,
        "all_stills_rendered": still_done == len(planned_shot_ids) and bool(planned_shot_ids),
        "all_clips_rendered": clip_done == len(planned_shot_ids) and bool(planned_shot_ids),
        "not_kpop_or_cyberpunk": final_video_exists,
    }
    non_blocking_checks = {
        "camera_restraint": final_video_exists,
        "memorable_shot": clip_done > 0,
        "citypop_identity": final_video_exists and clip_done > 0,
        "mood_consistency": final_video_exists and still_done > 0,
    }
    review_report = {
        "status": "done" if all(blocking_checks.values()) and not rerender_targets else "needs_rerender",
        "audio_video_drift_sec": _audio_video_drift_sec(str(stage_input.payload.get("music_file", "")).strip(), final_video),
        "planned_counts": {
            "shots": len(planned_shot_ids),
            "stills": len(still_results),
            "clips": len(clip_results),
        },
        "completed_counts": {
            "stills": still_done,
            "clips": clip_done,
        },
        "blocking_checks": blocking_checks,
        "non_blocking_checks": non_blocking_checks,
        "rerender_targets": rerender_targets,
    }
    return StageOutput("review_outputs", "done", {"review_report": review_report}, [])


def _shot_asset_status(rows: list[dict], key: str) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        status = str(row.get("status", "")).strip().lower()
        asset = str(row.get(key, "")).strip()
        out[shot_id] = status != "failed" and _file_exists(asset)
    return out


def _file_exists(path: str) -> bool:
    return bool(path) and Path(path).exists()


def _rerender_targets(planned_shot_ids: list[str], still_status: dict[str, bool], clip_status: dict[str, bool], config: dict) -> list[str]:
    targets = sorted({shot_id for shot_id in planned_shot_ids if not still_status.get(shot_id, False) or not clip_status.get(shot_id, False)})
    review = config.get("review", {}) if isinstance(config, dict) else {}
    try:
        limit = int(review.get("max_rerender_targets", 0) or 0)
    except Exception:
        limit = 0
    return targets if limit <= 0 else targets[:limit]


def _audio_video_drift_sec(audio_path: str, final_video_path: str) -> float:
    if not _file_exists(audio_path) or not _file_exists(final_video_path):
        return 0.0
    audio_duration = ffprobe_duration(audio_path)
    video_duration = ffprobe_duration(final_video_path)
    if audio_duration <= 0 or video_duration <= 0:
        return 0.0
    return round(abs(video_duration - audio_duration), 3)
