from __future__ import annotations

from ai_mv.core.workflow_names import QWEN_STILL_WORKFLOW
from ai_mv.engines.qwen_image.mapper import map_qwen_workflow, qwen_required_inputs
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_image_file
from ai_mv.utils.path_utils import resolve_generated_file


def run_qwen_still(config: dict, item: dict) -> str:
    result = run_workflow(
        config,
        QWEN_STILL_WORKFLOW,
        map_qwen_workflow(config, item),
        qwen_required_inputs(),
    )
    image_name = pick_image_file(result["files"], f"Qwen still {item['shot_id']}")
    image_path = resolve_generated_file(config, image_name, {".png", ".jpg", ".jpeg", ".webp"}, "image")
    return str(image_path)
