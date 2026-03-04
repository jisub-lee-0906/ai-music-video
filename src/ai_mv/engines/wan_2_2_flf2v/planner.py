from __future__ import annotations

from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config.get("video", {}).get("target", "1920x1080@24"))[2]
    clips: list[dict] = []
    for item in payload.get("uso_images", []):
        clips.extend(_item_to_clips(item, fps))
    return {"clips": clips}


def _item_to_clips(item: dict, fps: int) -> list[dict]:
    duration = float(item.get("duration_sec", 4.0))
    total = max(24, int(round(duration * fps)))
    if item.get("keyframe_mode") != "triple" or "mid" not in item:
        return [_clip(item["shot_id"], item["start"], item["end"], fps, total)]
    first = max(12, total // 2)
    second = max(12, total - first)
    return [
        _clip(f"{item['shot_id']}__a", item["start"], item["mid"], fps, first),
        _clip(f"{item['shot_id']}__b", item["mid"], item["end"], fps, second),
    ]


def _clip(shot_id: str, start: str, end: str, fps: int, frames: int) -> dict:
    return {"shot_id": shot_id, "start": start, "end": end, "fps": fps, "frames": frames}
