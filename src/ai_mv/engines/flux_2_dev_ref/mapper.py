from __future__ import annotations

import logging
import zlib

from ai_mv.utils.text_utils import parse_size, parse_target

FLUX2_REF_LOAD_IMAGE = "46"
FLUX2_REF_TEXT_POS = "68:6"
FLUX2_REF_NOISE = "68:25"
FLUX2_REF_LATENT = "68:47"
FLUX2_REF_SCHEDULER = "68:48"
FLUX2_REF_SAVE = "9"
NO_TEXT_SUFFIX = (
    ", no text, no typography, no watermark, no logo, no signage, no ui overlay"
    ", ugly, deformed, distorted, low quality, blurry face"
)


def map_flux2_ref_workflow(config: dict, item: dict) -> dict:
    idx = _shot_seed(
        str(item["shot_id"]),
        variant=str(item.get("kinetic_transition", "")),
        retry=int(item.get("retry", 0)),
    ) + int(item["frame_idx"])
    width, height = _flux2_ref_size(config)
    prompt = _flux2_ref_prompt(item)
    return {
        "node.inputs": {
            FLUX2_REF_LOAD_IMAGE: {"image": item["ref"]},
            FLUX2_REF_TEXT_POS: {"text": prompt},
            FLUX2_REF_LATENT: {"width": width, "height": height},
            FLUX2_REF_SCHEDULER: {"width": width, "height": height},
            FLUX2_REF_NOISE: {"noise_seed": 2000 + idx},
            FLUX2_REF_SAVE: {"filename_prefix": item["filename_prefix"]},
        },
    }


def flux2_ref_required_inputs() -> dict[str, list[str]]:
    return {
        "LoadImage": ["image"],
        "CLIPTextEncode": ["text"],
        "RandomNoise": ["noise_seed"],
        "EmptyFlux2LatentImage": ["width", "height"],
        "SaveImage": ["filename_prefix"],
    }


def _shot_seed(shot_id: str, variant: str = "", retry: int = 0) -> int:
    text = f"{str(shot_id).strip()}|{str(variant).strip()}|{int(retry)}".encode("utf-8")
    return int(zlib.crc32(text) % 1_000_000)


def _flux2_ref_prompt(item: dict) -> str:
    text = str(item["prompt_text"]).strip()
    if not text:
        raise RuntimeError(f"empty Flux2 reference prompt_text: {item['shot_id']}")
    return f"{text}{NO_TEXT_SUFFIX}"


def _flux2_ref_size(config: dict) -> tuple[int, int]:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    size = str(render.get("ref_size", render.get("tti_size", "")))
    w, h = parse_size(size)
    video = config.get("video", {}) if isinstance(config, dict) else {}
    target = str(video.get("target", "")).strip() if isinstance(video, dict) else ""
    if not target:
        return w, h
    vw, vh, _ = parse_target(target)
    ratio = float(w) / float(max(1, h))
    target_ratio = float(vw) / float(max(1, vh))
    if abs(ratio - target_ratio) > 0.05:
        logging.warning(
            "Aspect ratio mismatch: ffmpeg will stretch/crop the output (%s=%sx%s vs video.target=%sx%s)",
            "ref_size",
            w,
            h,
            vw,
            vh,
        )
    return w, h
