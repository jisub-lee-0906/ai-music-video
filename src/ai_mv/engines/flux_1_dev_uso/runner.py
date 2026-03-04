from __future__ import annotations

from ai_mv.engines.flux_1_dev_uso.mapper import map_uso_workflow
from ai_mv.infra.comfy_client import run_workflow


def run_uso(config: dict, plan: dict) -> list[dict]:
    out = []
    for item in plan.get("items", []):
        result = _run_shot_uso(config, item)
        files = result.get("files", [])
        uso = files[0] if files else f"{item['shot_id']}_uso.png"
        out.append({"shot_id": item["shot_id"], "uso": uso})
    return out


def _run_shot_uso(config: dict, item: dict) -> dict:
    attempts = int(config.get("limits", {}).get("max_retries_per_shot", 3))
    last: Exception | None = None
    for retry in range(attempts):
        payload = dict(item)
        payload["shot_id"] = item["shot_id"]
        if retry > 0:
            payload["shot_id"] = f"{item['shot_id']}"
        try:
            return run_workflow(config, "image_flux1_dev_uso.api.json", map_uso_workflow(config, payload))
        except Exception as exc:
            last = exc
    raise RuntimeError(f"USO failed for {item['shot_id']}: {last}")
