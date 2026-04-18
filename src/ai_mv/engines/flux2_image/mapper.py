from __future__ import annotations

import logging
import zlib

from ai_mv.utils.text_utils import ensure_positive_size, parse_size, parse_target

T2I_SAVE = "9"
T2I_TEXT = "98:6"
T2I_LATENT = "98:47"
T2I_SCHEDULER = "98:48"
T2I_NOISE = "98:25"
T2I_GUIDANCE = "98:26"

REF_SAVE = "9"
REF_LOAD_IMAGE = "46"
REF_TEXT = "68:6"
REF_LATENT = "68:47"
REF_SCHEDULER = "68:48"
REF_NOISE = "68:25"
REF_GUIDANCE = "68:26"


def map_flux2_workflow(config: dict, item: dict) -> dict:
    width, height = _flux2_size(config, item)
    seed = _seed_for_item(item)
    steps = _int_value(item.get("steps"), 20)
    guidance = _float_value(item.get("guidance"), _float_value(item.get("cfg"), 4.0))
    reference_image = str(item.get("reference_image", "")).strip()
    if reference_image:
        return {
            "node.inputs": {
                REF_LOAD_IMAGE: {"image": reference_image},
                REF_TEXT: {"text": str(item["positive_prompt"]).strip()},
                REF_LATENT: {"width": width, "height": height},
                REF_SCHEDULER: {"steps": steps, "width": width, "height": height},
                REF_NOISE: {"noise_seed": seed},
                REF_GUIDANCE: {"guidance": guidance},
                REF_SAVE: {"filename_prefix": str(item["filename_prefix"]).strip()},
            }
        }
    return {
        "node.inputs": {
            T2I_TEXT: {"text": str(item["positive_prompt"]).strip()},
            T2I_LATENT: {"width": width, "height": height},
            T2I_SCHEDULER: {"steps": steps, "width": width, "height": height},
            T2I_NOISE: {"noise_seed": seed},
            T2I_GUIDANCE: {"guidance": guidance},
            T2I_SAVE: {"filename_prefix": str(item["filename_prefix"]).strip()},
        }
    }


def flux2_required_inputs(item: dict | None = None) -> dict[str, list[str]]:
    payload = item if isinstance(item, dict) else {}
    required = {
        "SaveImage": ["filename_prefix"],
        "CLIPTextEncode": ["text"],
        "FluxGuidance": ["guidance"],
        "RandomNoise": ["noise_seed"],
        "Flux2Scheduler": ["steps", "width", "height"],
        "EmptyFlux2LatentImage": ["width", "height"],
    }
    if str(payload.get("reference_image", "")).strip():
        required["LoadImage"] = ["image"]
    return required


def _flux2_size(config: dict, item: dict) -> tuple[int, int]:
    size = str(item.get("flux2_size") or config.get("render", {}).get("flux2_size", "")).strip()
    width, height = parse_size(size)
    ensure_positive_size(width, height)
    _warn_if_aspect_mismatch(config, width, height, "flux2_size")
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
