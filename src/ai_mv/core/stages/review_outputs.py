from __future__ import annotations

import json
from pathlib import Path

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
    quality_findings = _collect_quality_findings(stage_input.payload)
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
        quality_findings=quality_findings,
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
        quality_findings=quality_findings,
    )
    review_inputs = stage_input.payload.get("review_inputs") if isinstance(stage_input.payload, dict) else None
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
        shot_plan=[row for row in stage_input.payload.get("shot_plan", []) if isinstance(row, dict)],
        render_plan=[row for row in stage_input.payload.get("render_plan", []) if isinstance(row, dict)],
        music_file=str(stage_input.payload.get("music_file", "")).strip(),
        edit_intent_by_shot=review_inputs.get("edit_intent_by_shot", {}) if isinstance(review_inputs, dict) else {},
    )
    return StageOutput("review_outputs", "done", {"review_report": report}, [])



def _collect_quality_findings(payload: dict) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {}
    for key in ("still_results", "clip_results"):
        for row in payload.get(key, []):
            if not isinstance(row, dict):
                continue
            shot_id = str(row.get("shot_id", "")).strip()
            if not shot_id:
                continue
            _extend_unique(findings.setdefault(shot_id, []), row.get("quality_issues", []))
    review_inputs = payload.get("review_inputs")
    if isinstance(review_inputs, dict):
        explicit = review_inputs.get("quality_findings")
        if isinstance(explicit, dict):
            for shot_id, reasons in explicit.items():
                normalized_shot_id = str(shot_id or "").strip()
                if not normalized_shot_id:
                    continue
                _extend_unique(findings.setdefault(normalized_shot_id, []), reasons)
        file_findings = _load_quality_findings_from_path(review_inputs.get("quality_findings_path"))
        for shot_id, reasons in file_findings.items():
            _extend_unique(findings.setdefault(shot_id, []), reasons)
    return {shot_id: reasons for shot_id, reasons in findings.items() if reasons}



def _load_quality_findings_from_path(path_value: object) -> dict[str, list[str]]:
    path_str = str(path_value or "").strip()
    if not path_str:
        return {}
    try:
        payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid review quality findings file: {path_str}") from exc
    explicit = _explicit_quality_findings(payload)
    findings: dict[str, list[str]] = {}
    for shot_id, reasons in explicit.items():
        normalized_shot_id = str(shot_id or "").strip()
        if not normalized_shot_id:
            continue
        _extend_unique(findings.setdefault(normalized_shot_id, []), reasons)
    return {shot_id: reasons for shot_id, reasons in findings.items() if reasons}



def _explicit_quality_findings(payload: object) -> dict:
    if not isinstance(payload, dict):
        return {}
    review_inputs = payload.get("review_inputs")
    if isinstance(review_inputs, dict) and isinstance(review_inputs.get("quality_findings"), dict):
        return review_inputs.get("quality_findings")
    if isinstance(payload.get("quality_findings"), dict):
        return payload.get("quality_findings")
    if payload and all(isinstance(key, str) for key in payload):
        return payload
    return {}



def _extend_unique(target: list[str], reasons: object) -> None:
    if not isinstance(reasons, (list, tuple, set)):
        return
    for reason in reasons:
        value = str(reason or "").strip()
        if value and value not in target:
            target.append(value)
