from __future__ import annotations


def evaluate_quality(payload: dict) -> float:
    checks = [
        _has_final_video(payload),
        _clip_count_matches(payload),
        _duration_in_sync(payload),
        _anchors_exist(payload),
    ]
    return sum(1.0 for ok in checks if ok) / float(len(checks))


def _has_final_video(payload: dict) -> bool:
    return bool(payload["final_video"])


def _clip_count_matches(payload: dict) -> bool:
    clips = payload["clips"]
    anchors = payload["anchors"]
    if not clips or not anchors:
        return False
    if len(clips) != len(anchors):
        return False
    clip_ids = [str(x.get("shot_id", "")).strip() for x in clips if isinstance(x, dict)]
    anchor_ids = [str(x.get("shot_id", "")).strip() for x in anchors if isinstance(x, dict)]
    if len(clip_ids) != len(clips) or len(anchor_ids) != len(anchors):
        return False
    if any(not x for x in clip_ids) or any(not x for x in anchor_ids):
        return False
    if len(set(clip_ids)) != len(clip_ids):
        return False
    return set(clip_ids) == set(anchor_ids)


def _duration_in_sync(payload: dict) -> bool:
    a = float(payload["audio_duration_sec"])
    v = float(payload["final_duration_sec"])
    return a > 0 and v > 0 and abs(a - v) <= 0.2


def _anchors_exist(payload: dict) -> bool:
    anchors = payload["anchors"]
    return bool(anchors) and all(bool(x["anchor_selected"]) for x in anchors)
