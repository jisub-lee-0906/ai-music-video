from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from typing import Any

from ai_mv.infra.comfy_transport import ping_comfy as transport_ping_comfy, submit_workflow
from ai_mv.infra.timeout_policy import resolve_timeout
from ai_mv.infra.workflow_patcher import patch_workflow, preflight_workflow, validate_node_bindings
from ai_mv.utils.path_utils import resolve_project_path


def run_workflow(
    config: dict,
    workflow_name: str,
    bindings: dict[str, Any],
    required: dict[str, list[str]] | None = None,
) -> dict:
    base = str(config["integrations"]["workflows_dir"])
    wf_path = resolve_project_path(base) / workflow_name
    workflow = deepcopy(_load_workflow_template(str(wf_path)))
    if required:
        preflight_workflow(workflow, required)
    validate_node_bindings(workflow, bindings)
    patched = patch_workflow(workflow, bindings)
    return submit(config, patched)


@lru_cache(maxsize=16)
def _load_workflow_template(path: str) -> dict[str, Any]:
    return json.loads(resolve_project_path(path).read_text(encoding="utf-8"))


def submit(config: dict, workflow: dict[str, Any]) -> dict:
    base_url = str(config["integrations"]["comfyui_base_url"])
    timeout = resolve_timeout(config)
    attempts = _comfy_retry_attempts(config)
    return submit_workflow(base_url, workflow, timeout, attempts=attempts)


def ping_comfy(base_url: str) -> bool:
    return transport_ping_comfy(base_url)


def _comfy_retry_attempts(config: dict) -> int:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("comfy_retry_attempts", 1) if isinstance(integ, dict) else 1
    try:
        n = int(raw)
    except Exception:
        return 1
    return max(1, n)
