from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_mv.core.artifacts.paths import preflight_root
from ai_mv.core.workflow_prompt_contracts import leaked_house_phrases
from ai_mv.utils.json_utils import read_json


_STAGES = ("shot_timeline", "flux2_ref_chain", "wan_interpolation")


def write_prompt_compare_report(before_run_id: str, after_run_id: str, profile_name: str, selected_profile: dict) -> dict[str, Any]:
    before_prompt_preview = _load_preview(before_run_id, "prompt_preview.json")
    after_prompt_preview = _load_preview(after_run_id, "prompt_preview.json")
    before_workflow_preview = _load_preview(before_run_id, "workflow_inputs_preview.json")
    after_workflow_preview = _load_preview(after_run_id, "workflow_inputs_preview.json")

    profile_text = _flatten_text(selected_profile)
    profile_text = f"{profile_name} {profile_text}".strip()

    stages: list[dict[str, Any]] = []
    aligned = True
    for stage in _STAGES:
        before_prompt_data = before_prompt_preview.get("prompts", {}).get(stage, {})
        after_prompt_data = after_prompt_preview.get("prompts", {}).get(stage, {})
        before_inputs = before_workflow_preview.get("workflow_inputs", {}).get(stage, {})
        after_inputs = after_workflow_preview.get("workflow_inputs", {}).get(stage, {})
        before_prompt = _extract_prompt_text(stage, before_prompt_data, before_inputs)
        after_prompt = _extract_prompt_text(stage, after_prompt_data, after_inputs)
        before_leaks = leaked_house_phrases(before_prompt, profile_text)
        after_leaks = leaked_house_phrases(after_prompt, profile_text)
        removed_leaks = [item for item in before_leaks if item not in after_leaks]
        introduced_leaks = [item for item in after_leaks if item not in before_leaks]
        stage_aligned = "aligned" if (not introduced_leaks and bool(before_prompt) and bool(after_prompt)) else "needs_review"
        if introduced_leaks:
            aligned = False
        retained_profile_backing = any(token in str(before_inputs).lower() or token in str(after_inputs).lower() for token in _profile_tokens(profile_text))
        stages.append(
            {
                "stage": stage,
                "alignment": stage_aligned,
                "removed_house_style_leaks": removed_leaks,
                "introduced_house_style_leaks": introduced_leaks,
                "retained_profile_backing": retained_profile_backing,
            }
        )

    return {
        "overall_alignment": "aligned" if aligned else "needs_review",
        "profile_name": profile_name,
        "stages": stages,
    }


def _load_preview(run_id: str, filename: str) -> dict[str, Any]:
    path = preflight_root() / str(run_id).strip() / filename
    if not path.is_file():
        return {}
    return read_json(path)


def _extract_prompt_text(stage: str, prompts: dict[str, Any], workflow_payload: dict[str, Any]) -> str:
    if stage == "shot_timeline":
        return str(prompts.get("prompt", "") or workflow_payload.get("master_anchor", {}).get("text", ""))
    if stage in {"flux2_ref_chain", "wan_interpolation"}:
        for row in prompts.get("batches", []) or []:
            text = str(row.get("prompt", ""))
            if text:
                return text
        for row in workflow_payload.get("items", []) or workflow_payload.get("clips", []):
            if not isinstance(row, dict):
                continue
            for key in ("start_text", "end_text", "positive_prompt", "prompt"):
                text = str(row.get(key, "")).strip()
                if text:
                    return text
    return str(prompts.get("prompt", "") or workflow_payload.get("prompt", "") or "")


def _profile_tokens(profile_text: str) -> list[str]:
    text = str(profile_text or "").lower()
    return [token.strip() for token in text.replace(",", " ").split() if token.strip()]


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_text(v) for v in value)
    return str(value)
