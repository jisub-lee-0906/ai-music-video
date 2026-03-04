from __future__ import annotations


def map_wan_workflow(config: dict, clip: dict) -> dict:
    target = config.get("video", {}).get("target", "1920x1080@24")
    dims = target.split("@")[0]
    w, h = dims.split("x")
    idx = _shot_index(clip.get("shot_id", "0"))
    return {
        "shot.prompt": f"cinematic motion for {clip['shot_id']}",
        "shot.negative_prompt": "flicker, low quality",
        "shot.seed": 3000 + idx,
        "shot.start_image": clip["start"],
        "shot.end_image": clip["end"],
        "shot.length_frames": clip["fps"] * 4,
        "video.width": int(w),
        "video.height": int(h),
        "video.fps": clip["fps"],
    }


def build_concat_plan(config: dict, payload: dict) -> dict:
    clips = payload.get("clips", [])
    return {"ordered": [x["video"] for x in clips]}


def _shot_index(shot_id: str) -> int:
    token = str(shot_id).split("_")[-1]
    digits = "".join(ch for ch in token if ch.isdigit())
    return int(digits) if digits else 0
