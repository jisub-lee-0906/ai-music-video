from __future__ import annotations

import logging
import zlib

from ai_mv.utils.text_utils import ensure_positive_size, parse_size, parse_target

LTX_I2V_SAVE = "75"
LTX_I2V_IMAGE = "269"
LTX_I2V_LENGTH = "267:225"
LTX_I2V_POS = "267:240"
LTX_I2V_NEG = "267:247"
LTX_I2V_WIDTH = "267:257"
LTX_I2V_HEIGHT = "267:258"
LTX_I2V_FPS = "267:260"
LTX_I2V_SEED = "267:266"


def map_ltx_i2v_workflow(config: dict, item: dict) -> dict:
    width, height = _ltx_size(config, item, "ltx_i2v_size")
    fps = _int_value(item.get("fps") or config.get("render", {}).get("ltx_fps"), 24)
    duration = _float_value(item.get("duration_sec"), 4.0)
    frame_count = _frame_count(item, fps, duration)
    prompt_seed = str(item.get("clip_prompt_seed") or item.get("prompt_seed") or "").strip()
    positive_prompt = str(item.get("clip_positive_prompt") or item.get("positive_prompt") or "").strip()
    return {
        "node.inputs": {
            LTX_I2V_SEED: {"value": prompt_seed},
            LTX_I2V_POS: {"text": positive_prompt},
            LTX_I2V_NEG: {"text": str(item.get("negative_prompt", "")).strip()},
            LTX_I2V_IMAGE: {"image": str(item["image"]).strip()},
            LTX_I2V_WIDTH: {"value": width},
            LTX_I2V_HEIGHT: {"value": height},
            LTX_I2V_FPS: {"value": fps},
            LTX_I2V_LENGTH: {"value": frame_count},
            LTX_I2V_SAVE: {"filename_prefix": str(item["filename_prefix"]).strip()},
        }
    }


def ltx_i2v_required_inputs() -> dict[str, list[str]]:
    return {
        "SaveVideo": ["filename_prefix"],
        "LoadImage": ["image"],
        "PrimitiveStringMultiline": ["value"],
        "PrimitiveInt": ["value"],
        "CLIPTextEncode": ["text"],
    }


def _ltx_size(config: dict, item: dict, key: str) -> tuple[int, int]:
    size = str(item.get("ltx_size") or config.get("render", {}).get(key, "")).strip()
    width, height = parse_size(size)
    ensure_positive_size(width, height)
    _warn_if_aspect_mismatch(config, width, height, key)
    return width, height


def _frame_count(item: dict, fps: int, duration_sec: float) -> int:
    raw = item.get("frame_count")
    if isinstance(raw, int) and raw > 0:
        return raw
    if isinstance(raw, float) and raw > 0:
        return max(1, int(round(raw)))
    return max(1, int(round(float(fps) * duration_sec)) + 1)


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


def _int_value(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(1, parsed)


def _float_value(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.1, parsed)
