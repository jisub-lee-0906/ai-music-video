from __future__ import annotations

from ai_mv.engines.common.runner_exec import call_with_retries
from ai_mv.engines.flux_1_dev_uso.mapper import map_uso_workflow, uso_required_inputs
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.utils.path_utils import stage_image_for_comfy


def run_uso(config: dict, plan: dict) -> list[dict]:
    out: list[dict] = []
    items = plan["items"]
    if not items:
        raise RuntimeError("USO plan is empty")
    prev_end = ""
    for item in items:
        start = _resolve_start(config, item, prev_end)
        end = _render_end(config, item, start)
        out.append(_pack_item(item, start, end))
        prev_end = end
    return out


def _resolve_start(config: dict, item: dict, prev_end: str) -> str:
    if prev_end:
        return prev_end
    return _render_start(config, item)


def _render_start(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["frame_name"] = "start"
    payload["frame_idx"] = 0
    payload["ref"] = stage_image_for_comfy(config, payload["ref"])
    payload["filename_prefix"] = f"uso/{item['shot_id']}_start"
    result = _run_shot_uso(config, payload)
    files = result["files"]
    if not files:
        raise RuntimeError(f"USO output missing for {item['shot_id']}/start")
    return files[0]


def _render_end(config: dict, item: dict, start_ref: str) -> str:
    payload = dict(item)
    payload["frame_name"] = "end"
    payload["frame_idx"] = 1
    payload["ref"] = stage_image_for_comfy(config, start_ref)
    payload["filename_prefix"] = f"uso/{item['shot_id']}_end"
    result = _run_shot_uso(config, payload)
    files = result["files"]
    if not files:
        raise RuntimeError(f"USO output missing for {item['shot_id']}/end")
    return files[0]


def _run_shot_uso(config: dict, item: dict) -> dict:
    attempts = int(config["limits"]["max_retries_per_shot"])
    def _call(retry: int) -> dict:
        payload = dict(item)
        payload["frame_idx"] = int(item["frame_idx"]) + retry
        return run_workflow(config, "image_flux1_dev_uso.api.json", map_uso_workflow(config, payload), uso_required_inputs())

    return call_with_retries(attempts, _call, "USO", item["shot_id"])


def _pack_item(item: dict, start: str, end: str) -> dict:
    out = {
        "shot_id": item["shot_id"],
        "duration_sec": item["duration_sec"],
        "retry": 0,
        "error_body": "",
    }
    out["start"] = start
    out["end"] = end
    return out
