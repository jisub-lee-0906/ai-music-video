from __future__ import annotations

from ai_mv.engines.common.runner_exec import call_with_retries
from ai_mv.engines.flux_1_dev_uso.mapper import map_uso_workflow, uso_required_inputs
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.utils.path_utils import stage_image_for_comfy


def run_uso(config: dict, plan: dict) -> list[dict]:
    out: list[dict] = []
    items = plan.get("items", [])
    if not items:
        raise RuntimeError("USO plan is empty")
    for item in items:
        frames = _frame_names(item.get("mode", "double"))
        rendered = [_render_frame(config, item, name, idx) for idx, name in enumerate(frames)]
        out.append(_pack_item(item, rendered))
    return out


def _render_frame(config: dict, item: dict, frame_name: str, idx: int) -> str:
    payload = dict(item)
    payload["frame_name"] = frame_name
    payload["frame_idx"] = idx
    payload["ref"] = stage_image_for_comfy(config, payload.get("ref") or payload.get("anchor", ""))
    payload["filename_prefix"] = f"uso/{item['shot_id']}_{frame_name}"
    result = _run_shot_uso(config, payload)
    files = result.get("files", [])
    return files[0] if files else f"{item['shot_id']}_{frame_name}.png"


def _run_shot_uso(config: dict, item: dict) -> dict:
    attempts = int(config.get("limits", {}).get("max_retries_per_shot", 3))
    def _call(retry: int) -> dict:
        payload = dict(item)
        payload["frame_idx"] = int(item.get("frame_idx", 0)) + retry
        return run_workflow(config, "image_flux1_dev_uso.api.json", map_uso_workflow(config, payload), uso_required_inputs())

    return call_with_retries(attempts, _call, "USO", item["shot_id"])


def _frame_names(mode: str) -> list[str]:
    return ["start", "mid", "end"] if mode == "triple" else ["start", "end"]


def _pack_item(item: dict, frames: list[str]) -> dict:
    out = {
        "shot_id": item["shot_id"],
        "keyframe_mode": item.get("mode", "double"),
        "duration_sec": item["duration_sec"],
        "retry": 0,
        "error_body": "",
    }
    out["start"] = frames[0]
    out["end"] = frames[-1]
    if len(frames) == 3:
        out["mid"] = frames[1]
    return out
