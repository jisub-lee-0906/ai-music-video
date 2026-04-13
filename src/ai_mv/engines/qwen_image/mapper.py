from __future__ import annotations

import logging
import zlib

from ai_mv.utils.text_utils import ensure_positive_size, parse_size, parse_target

QWEN_SAVE = "60"
QWEN_KSAMPLER = "76:3"
QWEN_TEXT_POS = "76:6"
QWEN_TEXT_NEG = "76:7"
QWEN_LATENT = "76:58"


def map_qwen_workflow(config: dict, item: dict) -> dict:
    width, height = _qwen_size(config, item)
    seed = _seed_for_item(item)
    steps = _int_value(item.get("steps"), 45)
    cfg_scale = _float_value(item.get("cfg"), 3.5)
    return {
        "node.inputs": {
            QWEN_TEXT_POS: {"text": str(item["positive_prompt"]).strip()},
            QWEN_TEXT_NEG: {"text": str(item.get("negative_prompt", "")).strip()},
            QWEN_LATENT: {"width": width, "height": height},
            QWEN_KSAMPLER: {
                "seed": seed,
                "steps": steps,
                "cfg": cfg_scale,
            },
            QWEN_SAVE: {"filename_prefix": str(item["filename_prefix"]).strip()},
        }
    }


def qwen_required_inputs() -> dict[str, list[str]]:
    return {
        "SaveImage": ["filename_prefix"],
        "KSampler": ["seed", "steps", "cfg"],
        "CLIPTextEncode": ["text"],
        "EmptySD3LatentImage": ["width", "height"],
    }


def _qwen_size(config: dict, item: dict) -> tuple[int, int]:
    size = str(item.get("qwen_size") or config.get("render", {}).get("qwen_size", "")).strip()
    width, height = parse_size(size)
    ensure_positive_size(width, height)
    _warn_if_aspect_mismatch(config, width, height, "qwen_size")
    return width, height


def _seed_for_item(item: dict) -> int:
    raw = item.get("seed")
    if isinstance(raw, int) and raw >= 0:
        return raw
    text = "|".join(
        [
            str(item.get("shot_id", "")).strip(),
            str(item.get("retry", 0)).strip(),
            str(item.get("filename_prefix", "")).strip(),
        ]
    ).encode("utf-8")
    return 1000 + int(zlib.crc32(text) % 1_000_000)


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
