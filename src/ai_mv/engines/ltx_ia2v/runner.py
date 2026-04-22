from __future__ import annotations

from ai_mv.core.workflow_names import LTX_IA2V_WORKFLOW
from ai_mv.engines.ltx_ia2v.common import ltx_timeout
from ai_mv.engines.ltx_ia2v.mapper import ltx_ia2v_required_inputs, map_ltx_ia2v_workflow
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_video_file
from ai_mv.utils.path_utils import resolve_generated_file, stage_audio_for_comfy, stage_image_for_comfy



def run_ltx_ia2v(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["image"] = stage_image_for_comfy(config, str(item["image"]))
    payload["audio"] = stage_audio_for_comfy(config, str(item["audio"]))
    result = run_workflow(
        config,
        LTX_IA2V_WORKFLOW,
        map_ltx_ia2v_workflow(config, payload),
        ltx_ia2v_required_inputs(),
        timeout_override=ltx_timeout(config),
    )
    video_name = pick_video_file(result["files"], f"LTX ia2v {item['shot_id']}")
    video_path = resolve_generated_file(config, video_name, {".mp4", ".mov", ".mkv", ".webm"}, "video")
    return str(video_path)
