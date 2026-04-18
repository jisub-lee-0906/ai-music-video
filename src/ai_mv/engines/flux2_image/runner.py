from __future__ import annotations

from ai_mv.core.workflow_names import FLUX2_KEYFRAME_WORKFLOW, FLUX2_STILL_WORKFLOW
from ai_mv.engines.flux2_image.mapper import flux2_required_inputs, map_flux2_workflow
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_image_file
from ai_mv.utils.path_utils import resolve_generated_file, stage_image_for_comfy


def run_flux2_still(config: dict, item: dict) -> str:
    payload = dict(item)
    workflow_name = FLUX2_STILL_WORKFLOW
    if str(payload.get("reference_image", "")).strip():
        payload["reference_image"] = stage_image_for_comfy(config, str(payload["reference_image"]))
        workflow_name = FLUX2_KEYFRAME_WORKFLOW
    result = run_workflow(
        config,
        workflow_name,
        map_flux2_workflow(config, payload),
        flux2_required_inputs(payload),
    )
    image_name = pick_image_file(result["files"], f"Flux2 still {item['shot_id']}")
    image_path = resolve_generated_file(config, image_name, {".png", ".jpg", ".jpeg", ".webp"}, "image")
    return str(image_path)
