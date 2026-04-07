from __future__ import annotations

from ai_mv.core.output_paths import master_anchor_prefix
from ai_mv.core.workflow_names import TTI_WORKFLOW
from ai_mv.infra.comfy_outputs import pick_image_file
from ai_mv.engines.flux_2_dev_tti.mapper import map_tti_workflow, tti_required_inputs
from ai_mv.infra.comfy_client import run_workflow


def run_tti(config: dict, plan: dict) -> list[dict]:
    master = plan["master_anchor"]
    out: list[dict] = []
    shots = plan["shots"]
    if not shots:
        raise RuntimeError("TTI plan is empty")
    identity_anchor = _run_master(config, master)
    for shot in shots:
        out.append(_pack_anchor(shot, identity_anchor))
    return out


def _run_master(config: dict, master: dict) -> str:
    payload = dict(master)
    payload["filename_prefix"] = master_anchor_prefix()
    result = _run_shot_tti(config, payload, "character_master")
    return pick_image_file(result["files"], "TTI character_master")


def _run_shot_tti(config: dict, shot: dict, shot_id: str) -> dict:
    return run_workflow(
        config,
        TTI_WORKFLOW,
        map_tti_workflow(config, dict(shot)),
        tti_required_inputs(),
    )


def _pack_anchor(shot: dict, identity_anchor: str, shot_anchor: str | None = None) -> dict:
    resolved_anchor = str(shot_anchor or identity_anchor)
    return {
        "shot_id": shot["shot_id"],
        "anchor": resolved_anchor,
        "shot_anchor": resolved_anchor,
        "identity_anchor": identity_anchor,
        "shot_type": shot["shot_type"],
        "section_name": str(shot.get("section_name", "section")),
        "section_label": str(shot.get("section_label", shot.get("section_name", "section"))),
        "duration_sec": float(shot["duration_sec"]),
        "is_chorus": bool(shot["is_chorus"]),
    }
