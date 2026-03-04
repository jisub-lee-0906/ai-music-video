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
    return bool(payload.get("final_video"))


def _clip_count_matches(payload: dict) -> bool:
    clips = payload.get("clips", [])
    plan = payload.get("merge_plan", {}).get("ordered", [])
    return bool(clips) and len(clips) == len(plan)


def _duration_in_sync(payload: dict) -> bool:
    a = float(payload.get("audio_duration_sec", 0.0))
    v = float(payload.get("final_duration_sec", 0.0))
    return a > 0 and v > 0 and abs(a - v) <= 0.2


def _anchors_exist(payload: dict) -> bool:
    anchors = payload.get("anchors", [])
    return bool(anchors) and all(bool(x.get("anchor_selected") or x.get("anchor")) for x in anchors)
