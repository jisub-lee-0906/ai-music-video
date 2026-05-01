from __future__ import annotations

import json
from pathlib import Path

from ai_mv.analysis.contact_sheet import build_contact_sheet_manifest, write_contact_sheet_image
from ai_mv.analysis.frame_extract import extract_frames, representative_frame_plan
from ai_mv.core.review.quality_findings import (
    quality_findings_review_input_template,
    _reference_review_hints,
)
from ai_mv.utils.time_utils import ffprobe_duration



def build_review_packet_manifest(
    *,
    video_path: str | Path,
    output_dir: str | Path,
    kind: str,
    shot_ids: list[str] | tuple[str, ...],
    sample_count: int = 6,
    duration_fn=ffprobe_duration,
    escalation_context: dict[str, object] | None = None,
) -> dict[str, object]:
    output_root = Path(output_dir)
    frames_dir = output_root / "frames"
    plan = representative_frame_plan(
        video_path=video_path,
        output_dir=frames_dir,
        kind=kind,
        sample_count=sample_count,
        duration_fn=duration_fn,
    )
    normalized_shot_ids = _normalize_shot_ids(shot_ids)
    return {
        "video_path": str(Path(video_path)),
        "kind": str(kind),
        "sample_count": int(sample_count or 0),
        "shot_ids": normalized_shot_ids,
        "frame_paths": [str(Path(row["output_path"])) for row in plan],
        "frame_labels": [str(row["label"]) for row in plan],
        "frame_count": len(plan),
        "reviewer_summary": f"Review packet for {len(normalized_shot_ids)} shots with {len(plan)} extracted frames",
        "escalation_context": _normalize_escalation_context(escalation_context),
        "quality_findings_path": str(output_root / "review-findings.json"),
        "reviewer_notes_path": str(output_root / "review-notes.md"),
        "contact_sheet_image_path": str(output_root / "contact-sheet.png"),
        "contact_sheet_manifest_path": str(output_root / "contact-sheet.json"),
    }



def write_review_packet(
    *,
    video_path: str | Path,
    output_dir: str | Path,
    kind: str,
    shot_ids: list[str] | tuple[str, ...],
    sample_count: int = 6,
    duration_fn=ffprobe_duration,
    escalation_context: dict[str, object] | None = None,
    extract_frames_fn=extract_frames,
    contact_sheet_image_fn=write_contact_sheet_image,
) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = build_review_packet_manifest(
        video_path=video_path,
        output_dir=output_root,
        kind=kind,
        shot_ids=shot_ids,
        sample_count=sample_count,
        duration_fn=duration_fn,
        escalation_context=escalation_context,
    )
    manifest_path = output_root / "review-packet.json"
    quality_findings_path = Path(manifest["quality_findings_path"])
    reviewer_notes_path = Path(manifest["reviewer_notes_path"])
    contact_sheet_manifest_path = Path(manifest["contact_sheet_manifest_path"])
    written_frame_paths = [
        Path(path)
        for path in extract_frames_fn(
            video_path=video_path,
            output_dir=output_root / "frames",
            kind=kind,
            sample_count=sample_count,
            duration_fn=duration_fn,
        )
    ]
    contact_sheet_manifest = build_contact_sheet_manifest(
        frame_paths=written_frame_paths,
        frame_labels=list(manifest["frame_labels"]),
        output_image_path=manifest["contact_sheet_image_path"],
        escalation_context=manifest.get("escalation_context") if isinstance(manifest.get("escalation_context"), dict) else None,
    )
    contact_sheet_image_fn(
        frame_paths=written_frame_paths,
        output_image_path=manifest["contact_sheet_image_path"],
        columns=int(contact_sheet_manifest.get("columns", 1) or 1),
        rows=int(contact_sheet_manifest.get("rows", 1) or 1),
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    quality_findings_path.write_text(
        json.dumps(
            quality_findings_review_input_template(
                list(manifest["shot_ids"]),
                escalation_context=manifest.get("escalation_context") if isinstance(manifest.get("escalation_context"), dict) else None,
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    reviewer_notes_path.write_text(_reviewer_notes_template(manifest), encoding="utf-8")
    contact_sheet_manifest_path.write_text(
        json.dumps(
            build_contact_sheet_manifest(
                frame_paths=list(manifest["frame_paths"]),
                frame_labels=list(manifest["frame_labels"]),
                output_image_path=manifest["contact_sheet_image_path"],
                escalation_context=manifest.get("escalation_context") if isinstance(manifest.get("escalation_context"), dict) else None,
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "manifest_path": manifest_path,
        "quality_findings_path": quality_findings_path,
        "reviewer_notes_path": reviewer_notes_path,
        "contact_sheet_image_path": Path(manifest["contact_sheet_image_path"]),
        "contact_sheet_manifest_path": contact_sheet_manifest_path,
    }



def _normalize_shot_ids(shot_ids: list[str] | tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for shot_id in shot_ids if isinstance(shot_ids, (list, tuple)) else []:
        value = str(shot_id or "").strip()
        if value and value not in out:
            out.append(value)
    return out



def _normalize_escalation_context(context: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(context, dict):
        return {}
    normalized = {
        "source_stage": str(context.get("source_stage", "")).strip(),
        "run_id": str(context.get("run_id", "")).strip(),
        "status": str(context.get("status", "")).strip(),
        "shot_ids": [
            str(shot_id).strip()
            for shot_id in context.get("shot_ids", [])
            if str(shot_id).strip()
        ]
        if isinstance(context.get("shot_ids"), list)
        else [],
        "material_ids": [
            str(material_id).strip()
            for material_id in context.get("material_ids", [])
            if str(material_id).strip()
        ]
        if isinstance(context.get("material_ids"), list)
        else [],
        "section_ids": [
            str(section_id).strip()
            for section_id in context.get("section_ids", [])
            if str(section_id).strip()
        ]
        if isinstance(context.get("section_ids"), list)
        else [],
    }
    reference_modes = [
        str(reference_mode).strip()
        for reference_mode in context.get("reference_modes", [])
        if str(reference_mode).strip()
    ] if isinstance(context.get("reference_modes"), list) else []
    anchor_source_shot_ids = [
        str(shot_id).strip()
        for shot_id in context.get("anchor_source_shot_ids", [])
        if str(shot_id).strip()
    ] if isinstance(context.get("anchor_source_shot_ids"), list) else []
    followup_shot_ids = [
        str(shot_id).strip()
        for shot_id in context.get("followup_shot_ids", [])
        if str(shot_id).strip()
    ] if isinstance(context.get("followup_shot_ids"), list) else []
    production_policy_by_shot = _normalize_production_policy_by_shot(
        context.get("production_policy_by_shot") if isinstance(context.get("production_policy_by_shot"), dict) else {}
    )
    reference_review_hints = _reference_review_hints(
        {
            "reference_modes": reference_modes,
            "anchor_source_shot_ids": anchor_source_shot_ids,
            "followup_shot_ids": followup_shot_ids,
        }
    )
    if reference_modes:
        normalized["reference_modes"] = reference_modes
    if anchor_source_shot_ids or "anchor_source_shot_ids" in context:
        normalized["anchor_source_shot_ids"] = anchor_source_shot_ids
    if followup_shot_ids:
        normalized["followup_shot_ids"] = followup_shot_ids
    if reference_review_hints:
        normalized["reference_review_hints"] = reference_review_hints
    if production_policy_by_shot:
        normalized["production_policy_by_shot"] = production_policy_by_shot
    if not any(normalized.values()):
        return {}
    return normalized



def _reviewer_notes_template(manifest: dict[str, object]) -> str:
    frame_labels = manifest.get("frame_labels", []) if isinstance(manifest, dict) else []
    escalation_context = manifest.get("escalation_context") if isinstance(manifest, dict) and isinstance(manifest.get("escalation_context"), dict) else {}
    reference_review_hints = [
        str(value).strip()
        for value in escalation_context.get("reference_review_hints", [])
        if str(value).strip()
    ] if isinstance(escalation_context.get("reference_review_hints"), list) else []
    lines = [
        "# Review Notes",
        "",
        f"- video_path: {manifest.get('video_path', '')}",
        f"- kind: {manifest.get('kind', '')}",
        f"- shot_ids: {', '.join(manifest.get('shot_ids', [])) if isinstance(manifest.get('shot_ids'), list) else ''}",
        f"- frame_labels: {', '.join(frame_labels) if isinstance(frame_labels, list) else ''}",
    ]
    if reference_review_hints:
        lines.extend([
            "",
            "## Reference continuity context",
            *[f"- {hint}" for hint in reference_review_hints],
        ])
        shot_roles = _shot_specific_reference_roles(
            shot_ids=manifest.get("shot_ids", []) if isinstance(manifest.get("shot_ids"), list) else [],
            escalation_context=escalation_context,
        )
        if shot_roles:
            lines.extend([
                "",
                "## Shot-specific continuity roles",
                *[f"- {line}" for line in shot_roles],
            ])
    production_policy_lines = _production_policy_context_lines(
        shot_ids=manifest.get("shot_ids", []) if isinstance(manifest.get("shot_ids"), list) else [],
        escalation_context=escalation_context,
    )
    if production_policy_lines:
        lines.extend([
            "",
            "## Production policy context",
            *[f"- {line}" for line in production_policy_lines],
        ])
    lines.extend([
        "",
        "## Observed issues",
        "- ",
        "",
        "## Notes",
        "- ",
    ])
    return "\n".join(lines) + "\n"


def _normalize_production_policy_by_shot(raw: dict[object, object]) -> dict[str, dict[str, object]]:
    normalized: dict[str, dict[str, object]] = {}
    for shot_id, policy in raw.items():
        normalized_shot_id = str(shot_id or "").strip()
        if not normalized_shot_id or not isinstance(policy, dict):
            continue
        row: dict[str, object] = {}
        for key in ("candidate_role", "ia2v_risk_class", "anchor_reference_arm"):
            value = str(policy.get(key, "")).strip()
            if value:
                row[key] = value
        duration = policy.get("recommended_duration_sec")
        if isinstance(duration, dict):
            row["recommended_duration_sec"] = {
                key: float(duration[key])
                for key in ("min", "max")
                if key in duration and _is_number(duration[key])
            }
        for key in ("safety_rules", "review_focus"):
            values = [str(value).strip() for value in policy.get(key, []) if str(value).strip()] if isinstance(policy.get(key), list) else []
            if values:
                row[key] = values
        if row:
            normalized[normalized_shot_id] = row
    return normalized


def _production_policy_context_lines(*, shot_ids: list[object], escalation_context: dict[str, object]) -> list[str]:
    policies = escalation_context.get("production_policy_by_shot")
    if not isinstance(policies, dict):
        return []
    normalized_shot_ids = [str(shot_id).strip() for shot_id in shot_ids if str(shot_id).strip()]
    selected_shot_ids = normalized_shot_ids or [str(shot_id).strip() for shot_id in policies if str(shot_id).strip()]
    lines: list[str] = []
    for shot_id in selected_shot_ids:
        policy = policies.get(shot_id)
        if not isinstance(policy, dict):
            continue
        role = str(policy.get("candidate_role", "")).strip() or "unknown_role"
        risk = str(policy.get("ia2v_risk_class", "")).strip() or "unknown_risk"
        anchor = str(policy.get("anchor_reference_arm", "")).strip() or "unknown_anchor"
        line = f"{shot_id}: {role} / {risk} / {anchor}"
        duration = policy.get("recommended_duration_sec")
        if isinstance(duration, dict) and _is_number(duration.get("min")) and _is_number(duration.get("max")):
            line += f"; recommended duration {duration['min']}-{duration['max']}s"
        review_focus = policy.get("review_focus")
        if isinstance(review_focus, list) and review_focus:
            line += "; review focus: " + ", ".join(str(value).strip() for value in review_focus if str(value).strip())
        safety_rules = policy.get("safety_rules")
        if isinstance(safety_rules, list) and safety_rules:
            line += "; safety: " + ", ".join(str(value).strip() for value in safety_rules if str(value).strip())
        lines.append(line)
    return lines


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _shot_specific_reference_roles(*, shot_ids: list[object], escalation_context: dict[str, object]) -> list[str]:
    normalized_shot_ids = [str(shot_id).strip() for shot_id in shot_ids if str(shot_id).strip()]
    anchor_source_shot_ids = {
        str(shot_id).strip()
        for shot_id in escalation_context.get("anchor_source_shot_ids", [])
        if str(shot_id).strip()
    } if isinstance(escalation_context.get("anchor_source_shot_ids"), list) else set()
    followup_shot_ids = {
        str(shot_id).strip()
        for shot_id in escalation_context.get("followup_shot_ids", [])
        if str(shot_id).strip()
    } if isinstance(escalation_context.get("followup_shot_ids"), list) else set()
    roles: list[str] = []
    for shot_id in normalized_shot_ids:
        if shot_id in anchor_source_shot_ids:
            roles.append(f"{shot_id}: anchor-source continuity baseline")
        elif shot_id in followup_shot_ids:
            roles.append(f"{shot_id}: follow-up continuity shot")
    return roles
