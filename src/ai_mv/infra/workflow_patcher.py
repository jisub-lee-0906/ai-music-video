from __future__ import annotations

from typing import Any

from ai_mv.core.contracts.errors import WorkflowValidationError


def patch_workflow(workflow: dict[str, Any], bindings: dict[str, Any]) -> dict[str, Any]:
    node_inputs = _node_inputs(bindings)
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        _apply_node_inputs(node_id, inputs, node_inputs)
    return workflow


def preflight_workflow(workflow: dict[str, Any], required: dict[str, list[str]]) -> None:
    for class_type, keys in (required or {}).items():
        node = _first_node_by_class(workflow, class_type)
        if not node:
            raise WorkflowValidationError(f"missing class_type: {class_type}")
        inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
        missing = [k for k in keys if k not in inputs]
        if missing:
            raise WorkflowValidationError(f"missing inputs in {class_type}: {missing}")


def validate_node_bindings(workflow: dict[str, Any], bindings: dict[str, Any]) -> None:
    node_inputs = _node_inputs(bindings)
    if not node_inputs:
        return
    for node_id, patch in node_inputs.items():
        node = workflow.get(node_id)
        if not isinstance(node, dict):
            raise WorkflowValidationError(f"missing node id: {node_id}")
        inputs = node.get("inputs", {}) if isinstance(node.get("inputs", {}), dict) else {}
        missing = [k for k in patch.keys() if k not in inputs]
        if missing:
            raise WorkflowValidationError(f"missing node inputs in {node_id}: {missing}")


def _node_inputs(bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = bindings.get("node.inputs", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _apply_node_inputs(node_id: str, inputs: dict, node_inputs: dict[str, dict[str, Any]]) -> None:
    patch = node_inputs.get(str(node_id), {})
    for key, val in patch.items():
        if key in inputs:
            inputs[key] = val


def _first_node_by_class(workflow: dict[str, Any], class_type: str) -> dict | None:
    for node in workflow.values():
        if isinstance(node, dict) and node.get("class_type") == class_type:
            return node
    return None

