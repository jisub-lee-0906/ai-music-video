from __future__ import annotations


def map_tti_workflow(config: dict, shot: dict) -> dict:
    target = config.get("video", {}).get("target", "1920x1080@24")
    dims = target.split("@")[0]
    w, h = dims.split("x")
    return {
        "shot.prompt": shot["prompt"],
        "shot.negative_prompt": shot["negative_prompt"],
        "shot.seed": shot["seed"],
        "video.width": int(w),
        "video.height": int(h),
    }

