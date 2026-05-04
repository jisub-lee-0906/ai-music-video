from __future__ import annotations

import re
from collections.abc import Iterable

_PROMPT_BUDGETS = {
    "acestep": 500,
    "flux2_tti_anchor": 900,
    "flux2_ref_anchor": 1200,
    "flux2_ref_still": 1200,
    "ltx_ia2v": 900,
}
_POSITIVE_NEGATIVE_RE = re.compile(r"\b(no|avoid|do not|without|never|exclude|not a)\b", re.I)
_BAD_PUNCTUATION = ("not a .", "..", " ,")
_DIRECTOR_PLACEHOLDERS = (
    "clear section-specific visual progression",
    "concept-specific visual motif",
    "story-derived stable outfit silhouette",
)
_INTERNAL_TOKEN_RE = re.compile(r"\b(?:neon_highway|crosswalk_wait|live_house_entry|amp_corridor|window_haze)\b", re.I)


def lint_workflow_prompts(plan_payload: dict, audio_plan: dict | None = None) -> dict:
    rows = workflow_prompt_rows(plan_payload, audio_plan)
    violations: list[dict] = []
    max_chars: dict[str, int] = {}
    previous_positive_by_workflow: dict[str, str] = {}
    for row in rows:
        workflow = str(row.get("workflow", "")).strip()
        positive = str(row.get("positive_text", "")).strip()
        negative = str(row.get("negative_text", "")).strip()
        max_chars[workflow] = max(max_chars.get(workflow, 0), len(positive))
        if workflow in {"flux2_ref_still", "ltx_ia2v"} and previous_positive_by_workflow.get(workflow) == positive:
            violations.append(_violation(row, "duplicate adjacent positive_text"))
        if workflow in {"flux2_ref_still", "ltx_ia2v"}:
            previous_positive_by_workflow[workflow] = positive
        if not positive:
            violations.append(_violation(row, "missing positive_text"))
        budget = _PROMPT_BUDGETS.get(workflow)
        if budget is not None and len(positive) > budget:
            violations.append(_violation(row, f"positive_text exceeds {budget} chars"))
        lower_positive = positive.lower()
        if workflow in {"flux2_tti_anchor", "flux2_ref_anchor", "flux2_ref_still", "ltx_ia2v"} and _POSITIVE_NEGATIVE_RE.search(lower_positive):
            violations.append(_violation(row, "negative clause in positive_text"))
        for marker in (*_BAD_PUNCTUATION, ";."):
            if marker in lower_positive:
                violations.append(_violation(row, f"bad punctuation: {marker}"))
        if workflow in {"flux2_tti_anchor", "flux2_ref_anchor", "flux2_ref_still", "ltx_ia2v"}:
            for placeholder in _DIRECTOR_PLACEHOLDERS:
                if placeholder in lower_positive:
                    violations.append(_violation(row, f"director placeholder: {placeholder}"))
            if "jacket and sand" in lower_positive:
                violations.append(_violation(row, "generic desert motion cue"))
            for match in _INTERNAL_TOKEN_RE.finditer(positive):
                violations.append(_violation(row, f"internal planning token: {match.group(0)}"))
        if workflow == "ltx_ia2v" and negative:
            terms = [part.strip().lower() for part in negative.split(",") if part.strip()]
            if len(terms) != len(set(terms)):
                violations.append(_violation(row, "duplicate negative terms"))
    return {
        "status": "pass" if not violations else "fail",
        "workflow_rows": len(rows),
        "max_positive_chars_by_workflow": dict(sorted(max_chars.items())),
        "violations": violations,
    }


def workflow_prompt_rows(plan_payload: dict, audio_plan: dict | None = None) -> list[dict]:
    rows: list[dict] = []
    if isinstance(audio_plan, dict):
        ace = audio_plan.get("workflow_prompts", {}).get("acestep", {}) if isinstance(audio_plan.get("workflow_prompts"), dict) else {}
        if isinstance(ace, dict) and ace.get("tags"):
            rows.append({"workflow": "acestep", "id": "audio", "positive_text": str(ace.get("tags", "")), "negative_text": ""})
    anchor_package = plan_payload.get("anchor_package", {}) if isinstance(plan_payload, dict) else {}
    anchor_sources = []
    if isinstance(anchor_package, dict):
        for key in ("anchors", "pose_anchor_bank"):
            values = anchor_package.get(key, [])
            if isinstance(values, list):
                anchor_sources.extend(values)
    for anchor in anchor_sources:
        if not isinstance(anchor, dict):
            continue
        prompts = anchor.get("workflow_prompts", {}) if isinstance(anchor.get("workflow_prompts"), dict) else {}
        workflow_keys = ("flux2_tti_anchor", "flux2_ref_anchor")
        for workflow in workflow_keys:
            if workflow not in prompts:
                continue
            payload = prompts.get(workflow, {}) if isinstance(prompts, dict) else {}
            if isinstance(payload, dict):
                rows.append({
                    "workflow": workflow,
                    "id": str(anchor.get("anchor_id", "")),
                    "positive_text": str(payload.get("positive_text", "")),
                    "negative_text": "",
                })
    render_plan = plan_payload.get("render_plan", []) if isinstance(plan_payload, dict) else []
    for item in render_plan if isinstance(render_plan, list) else []:
        if not isinstance(item, dict):
            continue
        prompts = item.get("workflow_prompts", {}) if isinstance(item.get("workflow_prompts"), dict) else {}
        for workflow in ("flux2_ref_still", "ltx_ia2v"):
            payload = prompts.get(workflow, {}) if isinstance(prompts, dict) else {}
            if isinstance(payload, dict):
                rows.append({
                    "workflow": workflow,
                    "id": str(item.get("shot_id", "")),
                    "positive_text": str(payload.get("positive_text", "")),
                    "negative_text": str(payload.get("negative_text", "")),
                })
    return rows


def _violation(row: dict, issue: str) -> dict:
    return {"workflow": str(row.get("workflow", "")), "id": str(row.get("id", "")), "issue": issue}
