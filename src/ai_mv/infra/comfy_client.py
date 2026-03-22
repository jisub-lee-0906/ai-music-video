from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from ai_mv.infra.comfy_transport import ping_comfy as transport_ping_comfy, submit_workflow
from ai_mv.infra.comfy_local import validate_local_comfy_config
from ai_mv.infra.timeout_policy import resolve_timeout
from ai_mv.infra.workflow_patcher import patch_workflow, preflight_workflow, validate_node_bindings
from ai_mv.utils.path_utils import resolve_project_path


def run_workflow(
    config: dict,
    workflow_name: str,
    bindings: dict[str, Any],
    required: dict[str, list[str]] | None = None,
    timeout_override: int | None = None,
) -> dict:
    validate_local_comfy_config(config)
    base = str(config["integrations"]["workflows_dir"])
    wf_path = resolve_project_path(base) / workflow_name
    workflow = deepcopy(_load_workflow_template(str(wf_path)))
    if required:
        preflight_workflow(workflow, required)
    validate_node_bindings(workflow, bindings)
    patched = patch_workflow(workflow, bindings)
    return submit(config, patched, timeout_override=timeout_override)

def _load_workflow_template(path: str) -> dict[str, Any]:
    return json.loads(resolve_project_path(path).read_text(encoding="utf-8"))


def submit(config: dict, workflow: dict[str, Any], timeout_override: int | None = None) -> dict:
    validate_local_comfy_config(config)
    base_url = str(config["integrations"]["comfyui_base_url"])
    timeout = timeout_override if timeout_override is not None else resolve_timeout(config)
    return submit_workflow(base_url, workflow, timeout)


def ping_comfy(base_url: str) -> bool:
    return transport_ping_comfy(base_url)
