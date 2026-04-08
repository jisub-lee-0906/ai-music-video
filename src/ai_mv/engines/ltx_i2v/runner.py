from __future__ import annotations

from ai_mv.core.workflow_names import LTX_I2V_WORKFLOW
from ai_mv.engines.ltx_i2v.mapper import ltx_i2v_required_inputs, map_ltx_i2v_workflow
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_video_file
from ai_mv.utils.path_utils import resolve_generated_file, stage_image_for_comfy


def run_ltx_i2v(config: dict, item: dict) -> str:
    payload = dict(item)
    payload["image"] = stage_image_for_comfy(config, str(item["image"]))
    result = run_workflow(
        config,
        LTX_I2V_WORKFLOW,
        map_ltx_i2v_workflow(config, payload),
        ltx_i2v_required_inputs(),
        timeout_override=_ltx_timeout(config),
    )
    video_name = pick_video_file(result["files"], f"LTX i2v {item['shot_id']}")
    video_path = resolve_generated_file(config, video_name, {".mp4", ".mov", ".mkv", ".webm"}, "video")
    return str(video_path)


def _ltx_timeout(config: dict) -> int | None:
    limits = config.get("limits", {}) if isinstance(config, dict) else {}
    raw = limits.get("ltx_timeout_seconds", 0) if isinstance(limits, dict) else 0
    try:
        value = int(raw)
    except Exception:
        return None
    return None if value <= 0 else value
