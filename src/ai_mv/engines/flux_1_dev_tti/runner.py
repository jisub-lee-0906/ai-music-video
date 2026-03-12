from __future__ import annotations

from ai_mv.core.output_paths import tti_anchor_prefix
from ai_mv.core.workflow_names import TTI_WORKFLOW
from ai_mv.engines.common.runner_exec import call_with_retries
from ai_mv.infra.comfy_outputs import pick_image_file
from ai_mv.engines.flux_1_dev_tti.mapper import map_tti_workflow, tti_required_inputs
from ai_mv.infra.comfy_client import run_workflow


def run_tti(config: dict, plan: dict) -> list[dict]:
    master = plan["master_anchor"]
    out: list[dict] = []
    shots = plan["shots"]
    if not shots:
        raise RuntimeError("TTI plan is empty")
    anchor = _run_master(config, master)
    for shot in shots:
        out.append(_pack_anchor(shot, anchor))
    return out


def _run_master(config: dict, master: dict) -> str:
    payload = dict(master)
    payload["filename_prefix"] = tti_anchor_prefix()
    result = _run_shot_tti(config, payload, "character_master")
    return pick_image_file(result["files"], "TTI character_master")


def _run_shot_tti(config: dict, shot: dict, shot_id: str) -> dict:
    attempts = int(config["limits"]["max_retries_per_shot"])
    fn = lambda retry: run_workflow(
        config,
        TTI_WORKFLOW,
        map_tti_workflow(config, _mutate_shot(shot, retry)),
        tti_required_inputs(),
    )
    return call_with_retries(attempts, fn, "TTI", shot_id)


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
        "identity_anchor": anchor,
        "shot_type": shot["shot_type"],
        "section_name": str(shot.get("section_name", "section")),
        "section_label": str(shot.get("section_label", shot.get("section_name", "section"))),
        "duration_sec": float(shot["duration_sec"]),
        "is_chorus": bool(shot["is_chorus"]),
        "camera_language": str(shot.get("camera_language", "")),
        "pose_delta": str(shot.get("pose_delta", "")),
        "emotion": str(shot.get("emotion", "")),
        "scene_detail": str(shot.get("scene_detail", "")),
        "motion_hint": str(shot.get("motion_hint", "")),
        "space_relation": str(shot.get("space_relation", "")),
        "retry": 0,
        "error_body": "",
    }
