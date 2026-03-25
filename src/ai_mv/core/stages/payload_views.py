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


def merge_render_inputs(payload: dict, **updates: object) -> dict:
    out = dict(payload.get("render_inputs", {}))
    out.update(updates)
    return out


def build_stage_payload(
    payload: dict,
    *,
    planner_key: str,
    planner_value: dict,
    workflow_key: str,
    workflow_value: dict,
    render_updates: dict | None = None,
    **extra: object,
) -> dict:
    out = dict(extra)
    if render_updates is not None:
        out["render_inputs"] = merge_render_inputs(payload, **render_updates)
    out["planner_prompts"] = merge_planner_prompt(payload, planner_key, planner_value)
    out["workflow_inputs_preview"] = merge_workflow_preview(payload, workflow_key, workflow_value)
    return out
