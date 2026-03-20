from __future__ import annotations

from pathlib import Path

from ai_mv.core.output_paths import flux2_ref_frame_prefix
from ai_mv.core.workflow_names import FLUX2_REF_WORKFLOW
from ai_mv.engines.flux_2_dev_ref.mapper import map_flux2_ref_workflow, flux2_ref_required_inputs
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_image_file
from ai_mv.utils.path_utils import stage_image_for_comfy


def run_flux2_ref(config: dict, plan: dict) -> list[dict]:
    out: list[dict] = []
    items = plan["items"]
    if not items:
        return out
    prev_item: dict | None = None
    prev_end: str = ""
    for item in items:
        if _should_reuse_previous_end(prev_item, item, prev_end):
            start = prev_end
            start_source = "previous_end"
        else:
            start = _render_start(config, item)
            start_source = "rendered_start"
        end = _render_end(config, item)
        out.append(_pack_item(item, start, end, start_source, prev_item))
        prev_item = item
        prev_end = end
    return out


def _render_start(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["frame_name"] = "start"
    payload["frame_idx"] = 0
    payload["ref"] = stage_image_for_comfy(config, payload["ref"])
    payload["filename_prefix"] = flux2_ref_frame_prefix(item["shot_id"], "start")
    result = _run_shot_flux2_ref(config, payload)
    return pick_image_file(result["files"], f"Flux2 reference {item['shot_id']}/start")


def _render_end(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["frame_name"] = "end"
    payload["frame_idx"] = 1
    payload["ref"] = stage_image_for_comfy(config, payload["ref"])
    payload["filename_prefix"] = flux2_ref_frame_prefix(item["shot_id"], "end")
    result = _run_shot_flux2_ref(config, payload)
    return pick_image_file(result["files"], f"Flux2 reference {item['shot_id']}/end")


def _run_shot_flux2_ref(config: dict, item: dict) -> dict:
    return run_workflow(
        config,
        FLUX2_REF_WORKFLOW,
        map_flux2_ref_workflow(config, dict(item)),
        flux2_ref_required_inputs(),
    )


def _pack_item(
    item: dict,
    start: str,
    end: str,
    start_source: str = "rendered_start",
    prev_item: dict | None = None,
) -> dict:
    return {
        "shot_id": item["shot_id"],
        "chain_key": str(item.get("chain_key", "")),
        "timeline_index": int(item.get("timeline_index", 0)),
        "clip_index": int(item.get("clip_index", 1)),
        "clip_count": int(item.get("clip_count", 1)),
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
        "space_relation": str(item.get("space_relation", "")),
        "scene_change_level": str(item.get("scene_change_level", "evolve")),
        "anchor_strategy": str(item.get("anchor_strategy", "refine_anchor")),
        "continuity_basis": str(item.get("continuity_basis", "world")),
        "retry": 0,
        "error_body": "",
        "start": start,
        "end": end,
        "start_source": start_source,
        "prev_chain_key": str(prev_item.get("chain_key", "")) if isinstance(prev_item, dict) else "",
    }


def _should_reuse_previous_end(prev_item: dict | None, item: dict, prev_end: str) -> bool:
    if not prev_end or not isinstance(prev_item, dict):
        return False
    if not Path(prev_end).suffix:
        return False
    if int(item.get("clip_count", 1)) <= 1:
        return False
    if _chain_break(item, prev_item):
        return False
    return True


def _chain_break(item: dict, prev_item: dict) -> bool:
    if str(item.get("anchor_strategy", "")).strip().lower() == "new_anchor" and int(item.get("clip_index", 1)) <= 1:
        return True
    if str(item.get("kinetic_transition", "")).strip().lower() == "smash_reframe":
        return True
    if _starts_new_major_section(item, prev_item) and int(item.get("clip_index", 1)) <= 1:
        return True
    return False


def _starts_new_major_section(item: dict, prev_item: dict) -> bool:
    current = _section_token(item)
    previous = _section_token(prev_item)
    if not current or current == previous:
        return False
    return _is_major_reset_section(current)


def _section_token(item: dict) -> str:
    return str(item.get("section_name", item.get("section_label", ""))).strip().lower()


def _is_major_reset_section(section: str) -> bool:
    sec = str(section).strip().lower()
    return "verse" in sec or sec == "chorus"
