from __future__ import annotations

from ai_mv.engines.flux_1_dev_tti.mapper import map_tti_workflow, tti_required_inputs
from ai_mv.infra.comfy_client import run_workflow


def run_tti(config: dict, plan: dict) -> list[dict]:
    out: list[dict] = []
    for shot in plan.get("shots", []):
        candidates = _run_candidates(config, shot)
        selected = _select_candidate(candidates)
        out.append(
            {
                "shot_id": shot["shot_id"],
                "anchor": selected,
                "anchor_candidates": candidates,
                "anchor_selected": selected,
                "shot_type": shot.get("shot_type", "CHAR_MASTER"),
                "duration_sec": float(shot.get("duration_sec", 4.0)),
                "is_chorus": bool(shot.get("is_chorus", False)),
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
    payload["seed"] = int(payload.get("seed", 0)) + (offset * 101)
    payload["filename_prefix"] = f"anchors/{shot['shot_id']}_{'a' if offset == 0 else 'b'}"
    result = _run_shot_tti(config, payload)
    files = result.get("files", [])
    if files:
        return files[0]
    suffix = "a" if offset == 0 else "b"
    return f"{shot['shot_id']}_{suffix}.png"


def _run_shot_tti(config: dict, shot: dict) -> dict:
    attempts = int(config.get("limits", {}).get("max_retries_per_shot", 3))
    last: Exception | None = None
    for retry in range(attempts):
        bindings = map_tti_workflow(config, _mutate_shot(shot, retry))
        try:
            return run_workflow(config, "image_flux1_dev_tti.api.json", bindings, tti_required_inputs())
        except Exception as exc:
            last = exc
    raise RuntimeError(f"TTI failed for {shot['shot_id']}: {last}")


def _mutate_shot(shot: dict, retry: int) -> dict:
    if retry == 0:
        return dict(shot)
    out = dict(shot)
    out["seed"] = int(out.get("seed", 0)) + retry * 1009
    return out


def _select_candidate(candidates: list[str]) -> str:
    usable = [x for x in candidates if x and not x.endswith("_missing.png")]
    return usable[0] if usable else candidates[0]
