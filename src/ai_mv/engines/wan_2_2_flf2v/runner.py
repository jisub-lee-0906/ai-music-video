from __future__ import annotations

from ai_mv.engines.common.runner_exec import call_with_retries
from ai_mv.engines.wan_2_2_flf2v.mapper import map_wan_workflow, wan_required_inputs
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.utils.path_utils import stage_image_for_comfy


def run_wan(config: dict, plan: dict) -> list[dict]:
    outputs: list[dict] = []
    clips = plan["clips"]
    if not clips:
        raise RuntimeError("WAN plan is empty")
    for clip in clips:
        result = _run_clip_wan(config, clip)
        files = result["files"]
        outputs.append({"shot_id": clip["shot_id"], "video": _pick_video(files, clip["shot_id"]), "retry": 0, "error_body": ""})
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


def _pick_video(files: list[str], shot_id: str) -> str:
    videos = [f for f in files if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm"))]
    if not videos:
        raise RuntimeError(f"WAN output missing for {shot_id}")
    return videos[0]
