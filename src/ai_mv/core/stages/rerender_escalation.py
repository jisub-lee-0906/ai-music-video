from __future__ import annotations

from ai_mv.analysis.review_packet import write_review_packet
from ai_mv.core.artifacts.paths import run_file
from ai_mv.core.contracts.stage_io import StageInput, StageOutput


_DEFAULT_SAMPLE_COUNT = 8


def run_rerender_escalation(stage_input: StageInput) -> StageOutput:
    payload = stage_input.payload if isinstance(stage_input.payload, dict) else {}
    outcome = payload.get("rerender_outcome") if isinstance(payload.get("rerender_outcome"), dict) else {}
    review_report = payload.get("review_report") if isinstance(payload.get("review_report"), dict) else {}
    final_video = str(payload.get("final_video", "")).strip()
    exhausted = bool(outcome.get("exhausted"))
    shot_ids = [str(shot_id).strip() for shot_id in review_report.get("rerender_targets", []) if str(shot_id).strip()] if isinstance(review_report.get("rerender_targets"), list) else []
    if not exhausted:
        return StageOutput(
            "rerender_escalation",
            "done",
            {"rerender_escalation": {"status": "not_required", "shot_ids": [], "video_path": final_video}},
            [],
        )

    output_dir = run_file(stage_input.run_id, "rerender-escalation")
    output_dir.mkdir(parents=True, exist_ok=True)
    written = write_review_packet(
        video_path=final_video,
        output_dir=output_dir,
        kind="final",
        sample_count=_DEFAULT_SAMPLE_COUNT,
        shot_ids=shot_ids,
    )
    report = {
        "status": "manual_review_required",
        "shot_ids": shot_ids,
        "shot_count": len(shot_ids),
        "video_path": final_video,
        "review_packet_manifest_path": str(written["manifest_path"]),
        "quality_findings_path": str(written["quality_findings_path"]),
        "reviewer_notes_path": str(written["reviewer_notes_path"]),
        "contact_sheet_image_path": str(written["contact_sheet_image_path"]),
        "contact_sheet_manifest_path": str(written["contact_sheet_manifest_path"]),
    }
    report["reviewer_summary"] = _reviewer_summary(shot_ids)
    report["artifacts"] = {
        "review_packet_manifest": report["review_packet_manifest_path"],
        "quality_findings": report["quality_findings_path"],
        "reviewer_notes": report["reviewer_notes_path"],
        "contact_sheet_image": report["contact_sheet_image_path"],
        "contact_sheet_manifest": report["contact_sheet_manifest_path"],
    }
    report["summary_by_shot"] = _summary_by_shot(
        shot_ids,
        report["artifacts"],
        review_report.get("rerender_reasons") if isinstance(review_report.get("rerender_reasons"), dict) else {},
        review_report.get("rerender_plan") if isinstance(review_report.get("rerender_plan"), list) else [],
    )
    return StageOutput(
        "rerender_escalation",
        "done",
        {"rerender_escalation": report},
        [
            report["review_packet_manifest_path"],
            report["quality_findings_path"],
            report["reviewer_notes_path"],
            report["contact_sheet_image_path"],
            report["contact_sheet_manifest_path"],
        ],
    )


def _reviewer_summary(shot_ids: list[str]) -> str:
    normalized = [str(shot_id).strip() for shot_id in shot_ids if str(shot_id).strip()]
    if not normalized:
        return "Manual review required"
    return f"Manual review required for {len(normalized)} shots: {', '.join(normalized)}"


def _summary_by_shot(
    shot_ids: list[str],
    artifacts: dict[str, str],
    rerender_reasons: dict[str, list[str]],
    rerender_plan: list[dict[str, object]],
) -> list[dict[str, object]]:
    normalized = [str(shot_id).strip() for shot_id in shot_ids if str(shot_id).strip()]
    plan_by_shot = {
        str(item.get("shot_id", "")).strip(): item
        for item in rerender_plan
        if isinstance(item, dict) and str(item.get("shot_id", "")).strip()
    }
    rows: list[dict[str, object]] = []
    for shot_id in normalized:
        reason_codes = [
            str(reason).strip()
            for reason in rerender_reasons.get(shot_id, [])
            if str(reason).strip()
        ]
        plan_item = plan_by_shot.get(shot_id, {})
        note = f"Inspect shot {shot_id} in the review packet artifacts"
        if reason_codes:
            note += f" (reasons: {', '.join(reason_codes)})"
        rows.append(
            {
                "shot_id": shot_id,
                "reason_codes": reason_codes,
                "priority_score": int(plan_item.get("priority_score", 0) or 0),
                "recommended_action": str(plan_item.get("recommended_action", "")).strip(),
                "packet_artifacts": dict(artifacts),
                "reviewer_note": note,
            }
        )
    return rows
