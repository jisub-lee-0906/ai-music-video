from __future__ import annotations

from ai_mv.core.output_paths import wan_clip_prefix
from ai_mv.core.workflow_names import WAN_WORKFLOW
from ai_mv.engines.wan_2_2_flf2v.mapper import map_wan_workflow, wan_required_inputs
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.infra.comfy_outputs import pick_video_file
from ai_mv.utils.path_utils import resolve_generated_file, stage_image_for_comfy


def run_wan(config: dict, plan: dict) -> list[dict]:
    outputs: list[dict] = []
    clips = plan["clips"]
    if not clips:
        raise RuntimeError("WAN plan is empty")
    for clip in clips:
        result = _run_clip_wan(config, clip)
        video = pick_video_file(result["files"], f"WAN {clip['shot_id']}")
        outputs.append({"shot_id": clip["shot_id"], "video": _resolve_video_path(config, video), "retry": 0, "error_body": ""})
    return outputs


def _run_clip_wan(config: dict, clip: dict) -> dict:
    payload = _prepare_clip(config, clip)
    return run_workflow(
        config,
        WAN_WORKFLOW,
        map_wan_workflow(config, payload),
        wan_required_inputs(),
        timeout_override=_wan_timeout(config),
    )


def _prepare_clip(config: dict, clip: dict) -> dict:
    out = dict(clip)
    out["start"] = stage_image_for_comfy(config, str(out["start"]))
    out["end"] = stage_image_for_comfy(config, str(out["end"]))
    out["wan_size"] = str(config["render"]["wan_size"])
    out["filename_prefix"] = wan_clip_prefix(
        str(clip.get("start_ref_shot_id", "")).strip() or str(clip["shot_id"]).strip(),
        str(clip.get("end_ref_shot_id", "")).strip() or str(clip["shot_id"]).strip(),
    )
    return out


def _resolve_video_path(config: dict, name: str) -> str:
    path = resolve_generated_file(config, name, {".mp4", ".mov", ".mkv", ".webm"}, "video")
    return str(path)


def _wan_timeout(config: dict) -> int | None:
    limits = config.get("limits", {}) if isinstance(config, dict) else {}
    raw = limits.get("wan_timeout_seconds", 0) if isinstance(limits, dict) else 0
    try:
        value = int(raw)
    except Exception:
        return None
    return None if value <= 0 else value
