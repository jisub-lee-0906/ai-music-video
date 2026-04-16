from __future__ import annotations

from pathlib import Path

from ai_mv.core.review.rerender_policy import rerender_targets
from ai_mv.utils.time_utils import ffprobe_duration



def shot_asset_status(rows: list[dict], key: str) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        status = str(row.get("status", "")).strip().lower()
        asset = str(row.get(key, "")).strip()
        out[shot_id] = status != "failed" and file_exists(asset)
    return out



def file_exists(path: str) -> bool:
    return bool(path) and Path(path).exists()



def audio_video_drift_sec(audio_path: str, final_video_path: str, *, duration_fn=ffprobe_duration) -> float:
    if not file_exists(audio_path) or not file_exists(final_video_path):
        return 0.0
    audio_duration = duration_fn(audio_path)
    video_duration = duration_fn(final_video_path)
    if audio_duration <= 0 or video_duration <= 0:
        return 0.0
    return round(abs(video_duration - audio_duration), 3)
