from __future__ import annotations

import json
from typing import Any

from ai_mv.infra.comfy_transport import ping_comfy, submit_workflow
from ai_mv.infra.timeout_policy import resolve_timeout
from ai_mv.infra.workflow_patcher import patch_workflow, preflight_workflow, validate_node_bindings
from ai_mv.utils.path_utils import resolve_project_path


def run_workflow(
    config: dict,
    workflow_name: str,
    bindings: dict[str, Any],
    required: dict[str, list[str]] | None = None,
) -> dict:
    base = config.get("integrations", {}).get("workflows_dir", "workflows")
    wf_path = resolve_project_path(base) / workflow_name
    workflow = json.loads(wf_path.read_text(encoding="utf-8"))
    if required:
        preflight_workflow(workflow, required)
    validate_node_bindings(workflow, bindings)
    patched = patch_workflow(workflow, bindings)
    return submit(config, patched)


def submit(config: dict, workflow: dict[str, Any]) -> dict:
    base_url = config.get("integrations", {}).get("comfyui_base_url", "")
    timeout = resolve_timeout(config)
    strict = bool(config.get("integrations", {}).get("strict_remote", False))
    if not strict:
        return {"prompt_id": "mock", "mock": True}
    return submit_workflow(base_url, workflow, timeout)
