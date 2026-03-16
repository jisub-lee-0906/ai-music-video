from __future__ import annotations

import logging
import zlib

from ai_mv.utils.text_utils import ensure_positive_size, parse_size, parse_target

WAN_TEXT_NEG = "78"
WAN_LOAD_START = "80"
WAN_LOAD_END = "89"
WAN_FLF2V = "81"
WAN_KSAMPLER_A = "84"
WAN_CREATE = "86"
WAN_KSAMPLER_B = "87"
WAN_SAVE = "83"
WAN_TEXT_POS = "90"


def map_wan_workflow(config: dict, clip: dict) -> dict:
    w, h = _wan_size(config, clip)
    idx = _shot_seed(
        str(clip["shot_id"]),
        variant=str(clip.get("kinetic_transition", "")),
        retry=int(clip.get("retry", 0)),
    )
    seed = 3000 + idx
    steps = _steps_for_energy(str(clip["energy"]))
    neg = str(clip["negative_prompt"])
    pos = str(clip["positive_prompt"])
    return {
        "node.inputs": {
            WAN_TEXT_NEG: {"text": neg},
            WAN_TEXT_POS: {"text": pos},
            WAN_LOAD_START: {"image": clip["start"]},
            WAN_LOAD_END: {"image": clip["end"]},
            WAN_FLF2V: {
                "width": w,
                "height": h,
                "length": int(clip["frames"]),
            },
            WAN_KSAMPLER_A: {"noise_seed": seed, "steps": steps},
            WAN_KSAMPLER_B: {"noise_seed": seed, "steps": steps},
            WAN_CREATE: {"fps": int(clip["fps"])},
            WAN_SAVE: {"filename_prefix": str(clip["filename_prefix"])},
        },
    }


def _shot_seed(shot_id: str, variant: str = "", retry: int = 0) -> int:
    text = f"{str(shot_id).strip()}|{str(variant).strip()}|{int(retry)}".encode("utf-8")
    return int(zlib.crc32(text) % 1_000_000)


def _wan_size(config: dict, clip: dict) -> tuple[int, int]:
    size = str(clip["wan_size"])
    w, h = parse_size(size)
    ensure_positive_size(w, h)
    vw, vh, _ = parse_target(str(config["video"]["target"]))
    ratio = float(w) / float(max(1, h))
    target_ratio = float(vw) / float(max(1, vh))
    if abs(ratio - target_ratio) > 0.05:
        logging.warning(
            "Aspect ratio mismatch: ffmpeg will stretch/crop the output (%s=%sx%s vs video.target=%sx%s)",
            "wan_size",
            w,
            h,
            vw,
            vh,
        )
    return w, h


def wan_required_inputs() -> dict[str, list[str]]:
    return {
        "LoadImage": ["image"],
        "CLIPTextEncode": ["text"],
        "WanFirstLastFrameToVideo": ["width", "height", "length", "start_image", "end_image"],
        "KSamplerAdvanced": ["noise_seed", "steps"],
        "CreateVideo": ["fps"],
        "SaveVideo": ["filename_prefix"],
    }


def _steps_for_energy(energy: str) -> int:
    if energy == "low":
        return 14
    if energy == "high":
        return 22
    if energy == "normal":
        return 18
    raise ValueError(f"invalid energy: {energy}")
