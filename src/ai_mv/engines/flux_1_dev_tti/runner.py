from __future__ import annotations

from ai_mv.engines.flux_1_dev_tti.mapper import map_tti_workflow
from ai_mv.infra.comfy_client import run_workflow


def run_tti(config: dict, plan: dict) -> list[dict]:
    outputs: list[dict] = []
    for shot in plan.get("shots", []):
        result = _run_shot_tti(config, shot)
        files = result.get("files", [])
        anchor = files[0] if files else f"{shot['shot_id']}.png"
        outputs.append({"shot_id": shot["shot_id"], "anchor": anchor})
    return outputs


def _run_shot_tti(config: dict, shot: dict) -> dict:
    attempts = int(config.get("limits", {}).get("max_retries_per_shot", 3))
    last: Exception | None = None
    for retry in range(attempts):
        bindings = map_tti_workflow(config, _mutate_shot(shot, retry))
        try:
            return run_workflow(config, "image_flux1_dev_tti.api.json", bindings)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"TTI failed for {shot['shot_id']}: {last}")


def _mutate_shot(shot: dict, retry: int) -> dict:
    if retry == 0:
        return dict(shot)
    out = dict(shot)
    out["seed"] = int(out.get("seed", 0)) + retry * 1009
    return out
