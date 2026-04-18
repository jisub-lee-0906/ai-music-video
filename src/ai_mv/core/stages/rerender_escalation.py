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
        "video_path": final_video,
        "review_packet_manifest_path": str(written["manifest_path"]),
        "quality_findings_path": str(written["quality_findings_path"]),
        "reviewer_notes_path": str(written["reviewer_notes_path"]),
        "contact_sheet_image_path": str(written["contact_sheet_image_path"]),
        "contact_sheet_manifest_path": str(written["contact_sheet_manifest_path"]),
    }
    report["artifacts"] = {
        "review_packet_manifest": report["review_packet_manifest_path"],
        "quality_findings": report["quality_findings_path"],
        "reviewer_notes": report["reviewer_notes_path"],
        "contact_sheet_image": report["contact_sheet_image_path"],
        "contact_sheet_manifest": report["contact_sheet_manifest_path"],
    }
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
