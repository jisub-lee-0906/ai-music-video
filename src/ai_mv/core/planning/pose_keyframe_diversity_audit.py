from __future__ import annotations

from collections import Counter
import re
from typing import Any


POSE_RISK_TIERS: dict[str, str] = {
    "ANCHOR_CHARACTER_FULL_BODY": "low",
    "ANCHOR_POSE_HERO_CLOSEUP": "low",
    "ANCHOR_POSE_THREE_QUARTER_MEDIUM": "low",
    "ANCHOR_POSE_FULL_BODY_STANDING": "low",
    "ANCHOR_POSE_FINAL_PAYOFF_FRONT": "low",
    "ANCHOR_POSE_WALKING_SIDE": "medium",
    "ANCHOR_POSE_WALKING_TOWARD": "medium",
    "ANCHOR_POSE_SEATED_WAITING": "medium",
    "ANCHOR_POSE_EXPRESSIVE_HAND_GESTURE": "medium",
    "ANCHOR_POSE_PROFILE_EMOTIONAL": "medium",
    "ANCHOR_POSE_MICROPHONE_PERFORMANCE": "high",
}


_CAMERA_RE = re.compile(r"\bcamera:\s*([^.;]+)", re.IGNORECASE)


def audit_pose_keyframe_diversity(preview: dict[str, Any], *, concentration_warn_ratio: float = 0.45) -> dict[str, Any]:
    """Summarize pose/keyframe diversity without invoking generation.

    The audit is intentionally static: it reads the already-built plan preview and
    checks whether shot-level selected pose anchors are diverse, materialized, and
    risk-tiered before a costly ComfyUI full run.
    """

    render_plan = [row for row in preview.get("render_plan", []) if isinstance(row, dict)] if isinstance(preview, dict) else []
    anchor_package = preview.get("anchor_package", {}) if isinstance(preview, dict) and isinstance(preview.get("anchor_package"), dict) else {}
    pose_anchor_bank = [row for row in anchor_package.get("pose_anchor_bank", []) if isinstance(row, dict)] if isinstance(anchor_package, dict) else []
    materialized_ids = _dedupe(str(row.get("anchor_id", "")).strip() for row in pose_anchor_bank if str(row.get("anchor_id", "")).strip())

    shot_by_id = _shot_plan_by_id(preview)
    rows = [_row_for_render_item(item, shot_by_id.get(str(item.get("shot_id", "")).strip(), {})) for item in render_plan]
    selected_ids = [row["selected_pose_anchor_id"] for row in rows if row["selected_pose_anchor_id"]]
    selected_counts = dict(Counter(selected_ids))
    risk_tier_counts = dict(Counter(row["risk_tier"] for row in rows if row["risk_tier"]))
    pose_action_need_world_interaction_counts = dict(
        Counter(row["pose_action_need_world_interaction"] for row in rows if row.get("pose_action_need_world_interaction"))
    )
    missing = sorted(anchor_id for anchor_id in set(selected_ids) if anchor_id not in set(materialized_ids))

    issues: list[dict[str, Any]] = []
    if missing:
        issues.append(
            {
                "code": "selected_pose_anchor_not_materialized",
                "severity": "fail",
                "message": "One or more shot-selected pose anchors are absent from the materialized pose anchor bank.",
                "anchor_ids": missing,
            }
        )
    issues.extend(_concentration_issues(selected_counts, len(selected_ids), concentration_warn_ratio))

    lint = preview.get("workflow_prompt_lint", {}) if isinstance(preview, dict) and isinstance(preview.get("workflow_prompt_lint"), dict) else {}
    return {
        "shot_count": len(render_plan),
        "selected_pose_anchor_counts": selected_counts,
        "materialized_pose_anchor_ids": materialized_ids,
        "missing_materialized_selected_pose_anchor_ids": missing,
        "risk_tier_counts": risk_tier_counts,
        "pose_action_need_world_interaction_counts": pose_action_need_world_interaction_counts,
        "workflow_prompt_lint_status": str(lint.get("status", "unknown")).strip() or "unknown",
        "issues": issues,
        "rows": rows,
    }


def format_pose_keyframe_diversity_markdown(audit: dict[str, Any], *, title: str) -> str:
    lines = [f"# {title}", ""]
    lines.append(f"shot_count: {audit.get('shot_count', 0)}")
    lines.append(f"workflow_prompt_lint_status: {audit.get('workflow_prompt_lint_status', 'unknown')}")
    lines.append("")
    lines.append("## selected_pose_anchor_counts")
    for key, value in sorted(dict(audit.get("selected_pose_anchor_counts", {})).items()):
        lines.append(f"- {key}: {value}")
    if not audit.get("selected_pose_anchor_counts"):
        lines.append("- none")
    lines.append("")
    lines.append("## risk_tier_counts")
    for key, value in sorted(dict(audit.get("risk_tier_counts", {})).items()):
        lines.append(f"- {key}: {value}")
    if not audit.get("risk_tier_counts"):
        lines.append("- none")
    lines.append("")
    lines.append("## pose_action_need_world_interaction_counts")
    for key, value in sorted(dict(audit.get("pose_action_need_world_interaction_counts", {})).items()):
        lines.append(f"- {key}: {value}")
    if not audit.get("pose_action_need_world_interaction_counts"):
        lines.append("- none")
    lines.append("")
    lines.append("## materialized_pose_anchor_ids")
    for anchor_id in audit.get("materialized_pose_anchor_ids", []):
        lines.append(f"- {anchor_id}")
    if not audit.get("materialized_pose_anchor_ids"):
        lines.append("- none")
    lines.append("")
    lines.append("## issues")
    issues = audit.get("issues", []) if isinstance(audit.get("issues"), list) else []
    if issues:
        for issue in issues:
            lines.append(f"- [{issue.get('severity', 'unknown')}] {issue.get('code', 'unknown')}: {issue.get('message', '')}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## shot rows")
    lines.append("| shot | section | function | role | selected_pose_anchor_id | risk | world_interaction | still_camera | clip_camera |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in audit.get("rows", []) if isinstance(audit.get("rows"), list) else []:
        lines.append(
            "| {shot_id} | {section_type} | {story_function} | {candidate_role} | {selected_pose_anchor_id} | {risk_tier} | {pose_action_need_world_interaction} | {still_camera} | {clip_camera} |".format(
                **{
                    key: _md_cell(row.get(key, ""))
                    for key in (
                        "shot_id",
                        "section_type",
                        "story_function",
                        "candidate_role",
                        "selected_pose_anchor_id",
                        "risk_tier",
                        "pose_action_need_world_interaction",
                        "still_camera",
                        "clip_camera",
                    )
                }
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _shot_plan_by_id(preview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    shot_plan = preview.get("shot_plan", []) if isinstance(preview, dict) else []
    out: dict[str, dict[str, Any]] = {}
    for row in shot_plan if isinstance(shot_plan, list) else []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if shot_id:
            out[shot_id] = row
    return out


def _row_for_render_item(item: dict[str, Any], shot: dict[str, Any] | None = None) -> dict[str, str]:
    shot = shot if isinstance(shot, dict) else {}
    anchor_id = str(item.get("selected_pose_anchor_id", "")).strip()
    prompts = item.get("workflow_prompts", {}) if isinstance(item.get("workflow_prompts"), dict) else {}
    still_positive = _prompt_text(prompts, "flux2_ref_still", "positive_text")
    clip_positive = _prompt_text(prompts, "ltx_ia2v", "positive_text")
    return {
        "shot_id": str(item.get("shot_id", "") or shot.get("shot_id", "")).strip(),
        "section_id": str(item.get("section_id", "") or shot.get("section_id", "")).strip(),
        "section_type": str(item.get("section_type", "") or shot.get("section_type", "")).strip(),
        "story_function": str(item.get("story_function", "") or shot.get("story_function", "")).strip(),
        "visual_mode": str(item.get("visual_mode", "") or shot.get("visual_mode", "")).strip(),
        "candidate_role": str(item.get("candidate_role", "")).strip(),
        "selected_pose_anchor_id": anchor_id,
        "risk_tier": _risk_tier(item, anchor_id),
        "pose_action_need_world_interaction": _pose_action_need_world_interaction(item),
        "still_camera": _extract_camera(still_positive, workflow="still"),
        "clip_camera": _extract_camera(clip_positive, workflow="clip"),
    }


def _prompt_text(prompts: dict[str, Any], workflow: str, field: str) -> str:
    payload = prompts.get(workflow, {}) if isinstance(prompts, dict) and isinstance(prompts.get(workflow), dict) else {}
    return str(payload.get(field, "")).strip()


def _risk_tier(item: dict[str, Any], anchor_id: str) -> str:
    need = item.get("pose_action_need", {}) if isinstance(item.get("pose_action_need"), dict) else {}
    need_risk = str(need.get("risk_tier", "")).strip()
    if need_risk:
        return need_risk
    return POSE_RISK_TIERS.get(anchor_id, "unknown" if anchor_id else "")


def _pose_action_need_world_interaction(item: dict[str, Any]) -> str:
    need = item.get("pose_action_need", {}) if isinstance(item.get("pose_action_need"), dict) else {}
    return str(need.get("world_interaction", "")).strip()


def _extract_camera(text: str, *, workflow: str = "") -> str:
    match = _CAMERA_RE.search(text)
    if match:
        return _clean_camera(match.group(1))
    if workflow == "still":
        lower = text.lower()
        for marker in (
            "medium close-up",
            "front-facing medium shot",
            "medium-wide three-quarter profile",
            "medium-wide cinematic composition",
            "medium-wide",
            "full-body",
        ):
            idx = lower.find(marker)
            if idx >= 0:
                fragment = text[idx:].split(".", 1)[0].split(",", 1)[0]
                return _clean_camera(fragment)
    return ""


def _clean_camera(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip(" ,.")


def _concentration_issues(counts: dict[str, int], total: int, threshold: float) -> list[dict[str, Any]]:
    if total <= 0 or not counts:
        return []
    anchor_id, count = max(counts.items(), key=lambda item: item[1])
    ratio = count / total
    if ratio <= threshold:
        return []
    return [
        {
            "code": "pose_anchor_concentration",
            "severity": "warn",
            "message": "One pose anchor dominates the plan; verify this is intentional before full generation.",
            "anchor_id": anchor_id,
            "count": count,
            "ratio": round(ratio, 3),
            "threshold": threshold,
        }
    ]


def _dedupe(values: Any) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in out:
            out.append(text)
    return out


def _md_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()
