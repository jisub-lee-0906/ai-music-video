from __future__ import annotations


def build_wan_plan(config: dict, payload: dict) -> dict:
    uso_images = payload.get("uso_images", [])
    target = config.get("video", {}).get("target", "1920x1080@24")
    fps = int(target.split("@")[1])
    return {"clips": [{"shot_id": x["shot_id"], "start": x["uso"], "end": x["uso"], "fps": fps} for x in uso_images]}

