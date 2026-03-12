from __future__ import annotations

from ai_mv.core.workflow_names import USO_WORKFLOW
from ai_mv.engines.common.runner_exec import call_with_retries
from ai_mv.engines.flux_1_dev_uso.mapper import map_uso_workflow, uso_required_inputs
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_image_file
from ai_mv.utils.path_utils import stage_image_for_comfy


def run_uso(config: dict, plan: dict) -> list[dict]:
    out: list[dict] = []
    items = plan["items"]
    if not items:
        raise RuntimeError("USO plan is empty")
    for item in items:
        start = _render_start(config, item)
        end = _render_end(config, item)
        out.append(_pack_item(item, start, end))
    return out


def _render_start(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["frame_name"] = "start"
    payload["frame_idx"] = 0
    payload["ref"] = stage_image_for_comfy(config, payload["ref"])
    payload["filename_prefix"] = f"uso/{item['shot_id']}_start"
    result = _run_shot_uso(config, payload)
    return pick_image_file(result["files"], f"USO {item['shot_id']}/start")


def _render_end(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["frame_name"] = "end"
    payload["frame_idx"] = 1
    payload["ref"] = stage_image_for_comfy(config, payload["ref"])
    payload["filename_prefix"] = f"uso/{item['shot_id']}_end"
    result = _run_shot_uso(config, payload)
    return pick_image_file(result["files"], f"USO {item['shot_id']}/end")


def _run_shot_uso(config: dict, item: dict) -> dict:
    attempts = int(config["limits"]["max_retries_per_shot"])

    def _call(retry: int) -> dict:
        payload = dict(item)
        payload["frame_idx"] = int(item["frame_idx"]) + retry
        return run_workflow(config, USO_WORKFLOW, map_uso_workflow(config, payload), uso_required_inputs())

    return call_with_retries(attempts, _call, "USO", item["shot_id"])


def _pack_item(item: dict, start: str, end: str) -> dict:
    return {
        "shot_id": item["shot_id"],
        "section_name": str(item.get("section_name", "section")),
        "section_label": str(item.get("section_label", item.get("section_name", "section"))),
        "shot_type": str(item.get("shot_type", "CHAR_MASTER")),
        "is_chorus": bool(item.get("is_chorus", False)),
        "duration_sec": item["duration_sec"],
        "camera_language": str(item.get("camera_language", "")),
        "pose_delta": str(item.get("pose_delta", "")),
        "emotion": str(item.get("emotion", "")),
        "scene_detail": str(item.get("scene_detail", "")),
        "motion_hint": str(item.get("motion_hint", "")),
        "retry": 0,
        "error_body": "",
        "start": start,
        "end": end,
    }
