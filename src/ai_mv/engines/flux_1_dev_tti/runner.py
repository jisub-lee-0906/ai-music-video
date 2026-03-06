from __future__ import annotations

from ai_mv.engines.common.runner_exec import call_with_retries
from ai_mv.engines.flux_1_dev_tti.mapper import map_tti_workflow, tti_required_inputs
from ai_mv.infra.comfy_client import run_workflow


def run_tti(config: dict, plan: dict) -> list[dict]:
    out: list[dict] = []
    shots = plan["shots"]
    if not shots:
        raise RuntimeError("TTI plan is empty")
    for shot in shots:
        anchor = _run_one(config, shot)
        out.append(_pack_anchor(shot, anchor))
    return out


def _run_one(config: dict, shot: dict) -> str:
    payload = dict(shot)
    payload["filename_prefix"] = f"anchors/{shot['shot_id']}"
    result = _run_shot_tti(config, payload)
    files = result["files"]
    if not files:
        raise RuntimeError(f"TTI output missing for {shot['shot_id']}")
    return files[0]


def _run_shot_tti(config: dict, shot: dict) -> dict:
    attempts = int(config["limits"]["max_retries_per_shot"])
    fn = lambda retry: run_workflow(
        config,
        "image_flux1_dev_tti.api.json",
        map_tti_workflow(config, _mutate_shot(shot, retry)),
        tti_required_inputs(),
    )
    return call_with_retries(attempts, fn, "TTI", shot["shot_id"])


def _mutate_shot(shot: dict, retry: int) -> dict:
    if retry == 0:
        return dict(shot)
    out = dict(shot)
    out["seed"] = int(out["seed"]) + retry * 1009
    return out


def _pack_anchor(shot: dict, anchor: str) -> dict:
    return {
        "shot_id": shot["shot_id"],
        "anchor": anchor,
        "anchor_selected": anchor,
        "shot_type": shot["shot_type"],
        "section_name": str(shot.get("section_name", "section")),
        "duration_sec": float(shot["duration_sec"]),
        "is_chorus": bool(shot["is_chorus"]),
        "retry": 0,
        "error_body": "",
    }
