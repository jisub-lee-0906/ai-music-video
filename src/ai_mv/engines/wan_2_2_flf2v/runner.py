from __future__ import annotations

from ai_mv.engines.common.runner_exec import call_with_retries
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
    attempts = int(config["limits"]["max_retries_per_shot"])
    def _call(retry: int) -> dict:
        payload = _mutate_clip(config, clip, retry)
        return run_workflow(
            config,
            "video_wan_2_2_flf2v.api.json",
            map_wan_workflow(config, payload),
            wan_required_inputs(),
        )

    return call_with_retries(attempts, _call, "WAN", clip["shot_id"])


def _mutate_clip(config: dict, clip: dict, retry: int) -> dict:
    out = dict(clip)
    out["start"] = stage_image_for_comfy(config, str(out["start"]))
    out["end"] = stage_image_for_comfy(config, str(out["end"]))
    out["seed_offset"] = retry * 101
    out["wan_size"] = str(config["render"]["wan_size"])
    out["filename_prefix"] = f"clips/{clip['shot_id']}"
    return out


def _resolve_video_path(config: dict, name: str) -> str:
    path = resolve_generated_file(config, name, {".mp4", ".mov", ".mkv", ".webm"}, "video")
    return str(path)
