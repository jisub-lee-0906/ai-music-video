from __future__ import annotations

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
    previous_item: dict | None = None
    for item in items:
        current = dict(item)
        start = _render_start(config, current)
        start_source = "master_anchor"
        end_item = dict(current)
        end_item["ref"] = str(current.get("anchor") or current.get("ref", "")).strip()
        end = _render_end(config, end_item)
        packed = _pack_item(current, start, end, start_source, previous_item)
        out.append(packed)
        previous_item = packed
    return out


def run_flux2_ref_probe(
    config: dict,
    *,
    ref: str,
    prompt_text: str,
    shot_id: str = "ref_probe",
    frame_name: str = "end",
) -> str:
    payload = {
        "shot_id": str(shot_id).strip() or "ref_probe",
        "ref": str(ref).strip(),
        "prompt_text": str(prompt_text).strip(),
        "start_prompt_text": str(prompt_text).strip(),
        "end_prompt_text": str(prompt_text).strip(),
        "kinetic_transition": "probe",
    }
    clean_frame_name = str(frame_name).strip().lower() or "end"
    frame_idx = 0 if clean_frame_name == "start" else 1
    return _render_frame(config, payload, frame_name=clean_frame_name, frame_idx=frame_idx)


def _render_start(config: dict, item: dict) -> str:
    return _render_frame(config, item, frame_name="start", frame_idx=0)


def _render_end(config: dict, item: dict) -> str:
    return _render_frame(config, item, frame_name="end", frame_idx=1)


def _render_frame(config: dict, item: dict, *, frame_name: str, frame_idx: int) -> str:
    payload = dict(item)
    payload["frame_name"] = frame_name
    payload["frame_idx"] = frame_idx
    payload["ref"] = stage_image_for_comfy(config, payload["ref"])
    payload["filename_prefix"] = flux2_ref_frame_prefix(item["shot_id"], frame_name)
    result = _run_shot_flux2_ref(config, payload)
    return pick_image_file(result["files"], f"Flux2 reference {item['shot_id']}/{frame_name}")


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


