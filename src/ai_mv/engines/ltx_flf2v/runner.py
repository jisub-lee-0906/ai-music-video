from __future__ import annotations

from ai_mv.core.workflow_names import LTX_FLF2V_WORKFLOW
from ai_mv.engines.ltx_flf2v.mapper import ltx_flf2v_required_inputs, map_ltx_flf2v_workflow
from ai_mv.engines.ltx_i2v.runner import _ltx_timeout
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_video_file
from ai_mv.utils.path_utils import resolve_generated_file, stage_image_for_comfy


def run_ltx_flf2v(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["first_image"] = stage_image_for_comfy(config, str(item["first_image"]))
    payload["last_image"] = stage_image_for_comfy(config, str(item["last_image"]))
    result = run_workflow(
        config,
        LTX_FLF2V_WORKFLOW,
        map_ltx_flf2v_workflow(config, payload),
        ltx_flf2v_required_inputs(),
        timeout_override=_ltx_timeout(config),
    )
    video_name = pick_video_file(result["files"], f"LTX flf2v {item['shot_id']}")
    video_path = resolve_generated_file(config, video_name, {".mp4", ".mov", ".mkv", ".webm"}, "video")
    return str(video_path)
