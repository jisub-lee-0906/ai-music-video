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
        candidates = _run_candidates(config, shot)
        selected = _select_candidate(candidates)
        out.append(
            {
                "shot_id": shot["shot_id"],
                "anchor": selected,
                "anchor_candidates": candidates,
                "anchor_selected": selected,
                "shot_type": shot["shot_type"],
                "duration_sec": float(shot["duration_sec"]),
                "is_chorus": bool(shot["is_chorus"]),
                "retry": 0,
                "error_body": "",
            }
        )
    return out


def _run_candidates(config: dict, shot: dict) -> list[str]:
    a = _run_one(config, shot, 0)
    b = _run_one(config, shot, 1)
    return [a, b]


def _run_one(config: dict, shot: dict, offset: int) -> str:
    payload = dict(shot)
    payload["seed"] = int(payload["seed"]) + (offset * 101)
    payload["filename_prefix"] = f"anchors/{shot['shot_id']}_{'a' if offset == 0 else 'b'}"
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


def _select_candidate(candidates: list[str]) -> str:
    return candidates[0]
