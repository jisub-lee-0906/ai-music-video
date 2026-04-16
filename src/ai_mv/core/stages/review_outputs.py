from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.review.models import build_review_report, build_shot_quality_scores
from ai_mv.core.review.policy import audio_video_drift_sec, file_exists, shot_asset_status
from ai_mv.core.review.rerender_policy import rerender_reasons, rerender_targets
from ai_mv.utils.time_utils import ffprobe_duration


def run_review_outputs(stage_input: StageInput) -> StageOutput:
    still_results = [row for row in stage_input.payload.get("still_results", []) if isinstance(row, dict)]
    clip_results = [row for row in stage_input.payload.get("clip_results", []) if isinstance(row, dict)]
    final_video = str(stage_input.payload.get("final_video", "")).strip()
    planned_shot_ids = [str(row.get("shot_id", "")).strip() for row in stage_input.payload.get("shot_plan", []) if isinstance(row, dict)]
    still_status = shot_asset_status(still_results, "image")
    clip_status = shot_asset_status(clip_results, "video")
    drift = audio_video_drift_sec(
        str(stage_input.payload.get("music_file", "")).strip(),
        final_video,
        duration_fn=ffprobe_duration,
    )
    coverage = {
        "stills_ratio": round((sum(1 for shot_id in planned_shot_ids if still_status.get(shot_id, False)) / len(planned_shot_ids)), 3) if planned_shot_ids else 0.0,
        "clips_ratio": round((sum(1 for shot_id in planned_shot_ids if clip_status.get(shot_id, False)) / len(planned_shot_ids)), 3) if planned_shot_ids else 0.0,
    }
    all_rerender_reasons = rerender_reasons(
        planned_shot_ids,
        still_status,
        clip_status,
        final_video_exists=file_exists(final_video),
        audio_video_drift_sec=drift,
        coverage=coverage,
        config=stage_input.config,
    )
    provisional_shot_scores = build_shot_quality_scores(
        planned_shot_ids=planned_shot_ids,
        still_status=still_status,
        clip_status=clip_status,
        rerender_reasons=all_rerender_reasons,
    )
    selected_rerender_targets = rerender_targets(
        planned_shot_ids,
        still_status,
        clip_status,
        stage_input.config,
        final_video_exists=file_exists(final_video),
        audio_video_drift_sec=drift,
        coverage=coverage,
        shot_scores=provisional_shot_scores,
    )
    report = build_review_report(
        planned_shot_ids=planned_shot_ids,
        still_results=still_results,
        clip_results=clip_results,
        still_status=still_status,
        clip_status=clip_status,
        final_video_exists=file_exists(final_video),
        rerender_targets=selected_rerender_targets,
        rerender_reasons={shot_id: all_rerender_reasons[shot_id] for shot_id in selected_rerender_targets if shot_id in all_rerender_reasons},
        audio_video_drift_sec=drift,
        config=stage_input.config,
    )
    return StageOutput("review_outputs", "done", {"review_report": report}, [])
