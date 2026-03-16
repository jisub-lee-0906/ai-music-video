from __future__ import annotations

import logging
import zlib

from ai_mv.utils.text_utils import parse_size, parse_target

TTI_TEXT = "98:6"
TTI_NOISE = "98:25"
TTI_LATENT = "98:47"
TTI_SAVE = "9"
NO_TEXT_SUFFIX = ", no text, no typography, no watermark, no logo, no signage, no ui overlay"


def map_tti_workflow(config: dict, shot: dict) -> dict:
    w, h = _tti_size(config)
    seed = _tti_seed(shot)
    return {
        "node.inputs": {
            TTI_TEXT: {"text": _tti_prompt_text(shot)},
            TTI_NOISE: {"noise_seed": seed},
            TTI_LATENT: {"width": w, "height": h},
            TTI_SAVE: {"filename_prefix": shot["filename_prefix"]},
        }
    }


def tti_required_inputs() -> dict[str, list[str]]:
    return {
        "CLIPTextEncode": ["text"],
        "RandomNoise": ["noise_seed"],
        "EmptyFlux2LatentImage": ["width", "height"],
        "SaveImage": ["filename_prefix"],
    }


def _tti_size(config: dict) -> tuple[int, int]:
    size = str(config["render"]["tti_size"])
    w, h = parse_size(size)
    _validate_aspect_ratio(config, w, h, "tti_size")
    return w, h


def _tti_prompt_text(shot: dict) -> str:
    text = str(shot["prompt_text"]).strip()
    if not text:
        raise RuntimeError("empty Flux TTI prompt_text")
    return f"{text}{NO_TEXT_SUFFIX}"


def _tti_seed(shot: dict) -> int:
    base = int(shot.get("seed", 0))
    variant = str(shot.get("kinetic_transition", "")).strip()
    retry = int(shot.get("retry", 0))
    text = f"{base}|{variant}|{retry}".encode("utf-8")
    return 1000 + int(zlib.crc32(text) % 1_000_000)


def _validate_aspect_ratio(config: dict, width: int, height: int, label: str) -> None:
    vw, vh, _ = parse_target(str(config["video"]["target"]))
    ratio = float(width) / float(max(1, height))
    target_ratio = float(vw) / float(max(1, vh))
    if abs(ratio - target_ratio) > 0.05:
        logging.warning(
            "Aspect ratio mismatch: ffmpeg will stretch/crop the output (%s=%sx%s vs video.target=%sx%s)",
            label,
            width,
            height,
            vw,
            vh,
        )
