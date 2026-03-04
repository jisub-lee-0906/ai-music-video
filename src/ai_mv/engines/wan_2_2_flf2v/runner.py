from __future__ import annotations

from ai_mv.engines.wan_2_2_flf2v.mapper import map_wan_workflow, wan_required_inputs
from ai_mv.infra.comfy_client import run_workflow


def run_wan(config: dict, plan: dict) -> list[dict]:
    outputs: list[dict] = []
    for clip in plan.get("clips", []):
        result = _run_clip_wan(config, clip)
        files = result.get("files", [])
        outputs.append({"shot_id": clip["shot_id"], "video": _pick_video(files, clip["shot_id"]), "retry": 0, "error_body": ""})
    return outputs


def _run_clip_wan(config: dict, clip: dict) -> dict:
    attempts = int(config.get("limits", {}).get("max_retries_per_shot", 3))
    last: Exception | None = None
    for retry in range(attempts):
        payload = _mutate_clip(config, clip, retry)
        try:
            return run_workflow(
                config,
                "video_wan_2_2_flf2v.api.json",
                map_wan_workflow(config, payload),
                wan_required_inputs(),
            )
        except Exception as exc:
            last = exc
    raise RuntimeError(f"WAN failed for {clip['shot_id']}: {last}")


def _mutate_clip(config: dict, clip: dict, retry: int) -> dict:
    out = dict(clip)
    out["seed_offset"] = retry * 101
    out["filename_prefix"] = f"clips/{clip['shot_id']}"
    if retry >= 1:
        out["fps"] = max(18, int(out.get("fps", 24)) - 2)
    if retry >= 2:
        out["wan_size"] = str(config.get("render", {}).get("wan_fallback_size", "640x360"))
        out["frames"] = max(24, int(out.get("frames", 96)) - 12)
    return out


def _pick_video(files: list[str], shot_id: str) -> str:
    videos = [f for f in files if f.lower().endswith((".mp4", ".mov", ".mkv"))]
    return videos[0] if videos else f"{shot_id}.mp4"
