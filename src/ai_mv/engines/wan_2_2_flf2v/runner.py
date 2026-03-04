from __future__ import annotations

from ai_mv.engines.wan_2_2_flf2v.mapper import map_wan_workflow
from ai_mv.infra.comfy_client import run_workflow


def run_wan(config: dict, plan: dict) -> list[dict]:
    outputs: list[dict] = []
    for clip in plan.get("clips", []):
        result = _run_clip_wan(config, clip)
        files = result.get("files", [])
        video = _pick_video(files, clip["shot_id"])
        outputs.append({"shot_id": clip["shot_id"], "video": video})
    return outputs


def _run_clip_wan(config: dict, clip: dict) -> dict:
    attempts = int(config.get("limits", {}).get("max_retries_per_shot", 3))
    last: Exception | None = None
    for retry in range(attempts):
        payload = _mutate_clip(clip, retry)
        try:
            return run_workflow(config, "video_wan_2_2_flf2v.api.json", map_wan_workflow(config, payload))
        except Exception as exc:
            last = exc
    raise RuntimeError(f"WAN failed for {clip['shot_id']}: {last}")


def _mutate_clip(clip: dict, retry: int) -> dict:
    if retry == 0:
        return dict(clip)
    out = dict(clip)
    out["fps"] = max(12, int(out.get("fps", 24)) - retry * 2)
    return out


def _pick_video(files: list[str], shot_id: str) -> str:
    videos = [f for f in files if f.lower().endswith((".mp4", ".mov", ".mkv"))]
    return videos[0] if videos else f"{shot_id}.mp4"
