from __future__ import annotations

from typing import Any

from ai_mv.core.contracts.errors import WorkflowValidationError


def patch_workflow(workflow: dict[str, Any], bindings: dict[str, Any]) -> dict[str, Any]:
    node_inputs = _node_inputs(bindings)
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            raise WorkflowValidationError(f"invalid workflow node: {node_id}")
        if "inputs" not in node or not isinstance(node["inputs"], dict):
            raise WorkflowValidationError(f"invalid node inputs: {node_id}")
        inputs = node["inputs"]
        _apply_node_inputs(node_id, inputs, node_inputs)
    return workflow


def preflight_workflow(workflow: dict[str, Any], required: dict[str, list[str]]) -> None:
    for class_type, keys in required.items():
        node = _first_node_by_class(workflow, class_type)
        if not node:
            raise WorkflowValidationError(f"missing class_type: {class_type}")
        if "inputs" not in node or not isinstance(node["inputs"], dict):
            raise WorkflowValidationError(f"invalid node inputs for class_type: {class_type}")
        inputs = node["inputs"]
        missing = [k for k in keys if k not in inputs]
        if missing:
            raise WorkflowValidationError(f"missing inputs in {class_type}: {missing}")


def validate_node_bindings(workflow: dict[str, Any], bindings: dict[str, Any]) -> None:
    node_inputs = _node_inputs(bindings)
    if not node_inputs:
        return
    for node_id, patch in node_inputs.items():
        node = workflow[node_id] if node_id in workflow else None
        if not isinstance(node, dict):
            raise WorkflowValidationError(f"missing node id: {node_id}")
        if "inputs" not in node or not isinstance(node["inputs"], dict):
            raise WorkflowValidationError(f"invalid node inputs in {node_id}")
        inputs = node["inputs"]
        missing = [k for k in patch.keys() if k not in inputs]
        if missing:
            raise WorkflowValidationError(f"missing node inputs in {node_id}: {missing}")


def _node_inputs(bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if "node.inputs" not in bindings:
        return {}
    raw = bindings["node.inputs"]
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _apply_node_inputs(node_id: str, inputs: dict, node_inputs: dict[str, dict[str, Any]]) -> None:
    patch = node_inputs[str(node_id)] if str(node_id) in node_inputs else {}
    for key, val in patch.items():
        if key in inputs:
            inputs[key] = val


def _first_node_by_class(workflow: dict[str, Any], class_type: str) -> dict | None:
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if "class_type" in node and node["class_type"] == class_type:
            return node
    return None
