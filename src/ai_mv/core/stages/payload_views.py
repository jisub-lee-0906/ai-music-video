from __future__ import annotations


def merge_preview(payload: dict, key: str, value: dict) -> dict:
    root = "planner_prompts" if "prompt" in value or "batches" in value else "workflow_inputs_preview"
    out = dict(payload.get(root, {}))
    out[key] = value
    return out


def merge_planner_prompt(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out


def merge_workflow_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("workflow_inputs_preview", {}))
    out[key] = value
    return out
