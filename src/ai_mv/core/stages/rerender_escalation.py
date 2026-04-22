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
            {
                "rerender_escalation": {
                    "status": "not_required",
                    "shot_ids": [],
                    "shot_count": 0,
                    "summary_by_shot": [],
                    "video_path": final_video,
                    "reviewer_summary": "No manual review required",
                    "artifacts": {},
                }
            },
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
        escalation_context={
            "source_stage": "rerender_escalation",
            "run_id": stage_input.run_id,
            "status": "manual_review_required",
            "shot_ids": shot_ids,
        },
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
        review_report.get("rerender_execution_payloads") if isinstance(review_report.get("rerender_execution_payloads"), list) else [],
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
    rerender_execution_payloads: list[dict[str, object]],
) -> list[dict[str, object]]:
    normalized = [str(shot_id).strip() for shot_id in shot_ids if str(shot_id).strip()]
    plan_by_shot = {
        str(item.get("shot_id", "")).strip(): item
        for item in rerender_plan
        if isinstance(item, dict) and str(item.get("shot_id", "")).strip()
    }
    provenance_by_shot = _provenance_by_shot(rerender_execution_payloads)
    rows: list[dict[str, object]] = []
    for shot_id in normalized:
        reason_codes = [
            str(reason).strip()
            for reason in rerender_reasons.get(shot_id, [])
            if str(reason).strip()
        ]
        plan_item = plan_by_shot.get(shot_id, {})
        provenance = provenance_by_shot.get(shot_id, {})
        note = f"Inspect shot {shot_id} in the review packet artifacts"
        if reason_codes:
            note += f" (reasons: {', '.join(reason_codes)})"
        rows.append(
            {
                "shot_id": shot_id,
                "material_id": str(provenance.get("material_id", "")).strip(),
                "section_id": str(provenance.get("section_id", "")).strip(),
                "reason_codes": reason_codes,
                "priority_score": int(plan_item.get("priority_score", 0) or 0),
                "recommended_action": str(plan_item.get("recommended_action", "")).strip(),
                "rerender_prescription": dict(plan_item.get("rerender_prescription", {})) if isinstance(plan_item.get("rerender_prescription"), dict) else {},
                "packet_artifacts": dict(artifacts),
                "reviewer_note": note,
            }
        )
    return rows


def _provenance_by_shot(rerender_execution_payloads: list[dict[str, object]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for item in rerender_execution_payloads:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "")).strip()
        if not shot_id:
            continue
        stage_payloads = item.get("stage_payloads") if isinstance(item.get("stage_payloads"), dict) else {}
        material_id = ""
        section_id = ""
        review_payload = stage_payloads.get("review") if isinstance(stage_payloads.get("review"), dict) else {}
        if isinstance(review_payload, dict):
            review_target_materials = review_payload.get("target_material_ids") if isinstance(review_payload.get("target_material_ids"), list) else []
            review_target_sections = review_payload.get("target_section_ids") if isinstance(review_payload.get("target_section_ids"), list) else []
            material_id = next((str(value).strip() for value in review_target_materials if str(value).strip()), "")
            section_id = next((str(value).strip() for value in review_target_sections if str(value).strip()), "")
        if not material_id or not section_id:
            for stage_name in ("clips", "stills"):
                stage_payload = stage_payloads.get(stage_name) if isinstance(stage_payloads.get(stage_name), dict) else {}
                if not isinstance(stage_payload, dict):
                    continue
                shot_rows = stage_payload.get("shot_plan") if isinstance(stage_payload.get("shot_plan"), list) else []
                render_rows = stage_payload.get("render_plan") if isinstance(stage_payload.get("render_plan"), list) else []
                still_rows = stage_payload.get("still_results") if isinstance(stage_payload.get("still_results"), list) else []
                shot_row = next((row for row in shot_rows if isinstance(row, dict) and str(row.get("shot_id", "")).strip() == shot_id), {})
                render_row = next((row for row in render_rows if isinstance(row, dict) and str(row.get("shot_id", "")).strip() == shot_id), {})
                still_row = next((row for row in still_rows if isinstance(row, dict) and str(row.get("shot_id", "")).strip() == shot_id), {})
                if not material_id:
                    material_id = str(
                        still_row.get("material_id")
                        or render_row.get("material_id")
                        or shot_row.get("material_id")
                        or ""
                    ).strip()
                if not section_id:
                    section_id = str(
                        still_row.get("section_id")
                        or render_row.get("section_id")
                        or shot_row.get("section_id")
                        or ""
                    ).strip()
                if material_id and section_id:
                    break
        out[shot_id] = {
            "material_id": material_id,
            "section_id": section_id,
        }
    return out
