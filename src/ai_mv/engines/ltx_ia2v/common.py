from __future__ import annotations

import logging

from ai_mv.utils.text_utils import ensure_positive_size, parse_size, parse_target


def ltx_size(config: dict, item: dict, key: str = "ltx_ia2v_size") -> tuple[int, int]:
    size = str(item.get("ltx_size") or config.get("render", {}).get(key, "")).strip()
    width, height = parse_size(size)
    ensure_positive_size(width, height)
    _warn_if_aspect_mismatch(config, width, height, key)
    return width, height



def ltx_frame_count(item: dict, fps: int, duration_sec: float) -> int:
    raw = item.get("frame_count")
    if isinstance(raw, int) and raw > 0:
        return raw
    if isinstance(raw, float) and raw > 0:
        return max(1, int(round(raw)))
    return max(1, int(round(float(fps) * duration_sec)) + 1)



def ltx_timeout(config: dict) -> int | None:
    limits = config.get("limits", {}) if isinstance(config, dict) else {}
    raw = limits.get("ltx_timeout_seconds", 0) if isinstance(limits, dict) else 0
    try:
        value = int(raw)
    except Exception:
        return None
    return None if value <= 0 else value



def int_value(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(1, parsed)



def float_value(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.1, parsed)



def non_negative_float(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, parsed)



def _warn_if_aspect_mismatch(config: dict, width: int, height: int, label: str) -> None:
    video = config.get("video", {}) if isinstance(config, dict) else {}
    target = str(video.get("target", "")).strip() if isinstance(video, dict) else ""
    if not target:
        return
    target_width, target_height, _ = parse_target(target)
    ratio = float(width) / float(max(1, height))
    target_ratio = float(target_width) / float(max(1, target_height))
    if abs(ratio - target_ratio) > 0.05:
        logging.warning(
            "Aspect ratio mismatch: ffmpeg may stretch/crop the output (%s=%sx%s vs video.target=%sx%s)",
            label,
            width,
            height,
            target_width,
            target_height,
        )
