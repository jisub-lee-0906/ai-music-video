from __future__ import annotations

import zlib

FLUX2_REF_LOAD_IMAGE = "46"
FLUX2_REF_TEXT_POS = "68:6"
FLUX2_REF_NOISE = "68:25"
FLUX2_REF_LATENT = "68:47"
FLUX2_REF_SAVE = "9"


def map_flux2_ref_workflow(config: dict, item: dict) -> dict:
    idx = _shot_seed(str(item["shot_id"])) + int(item["frame_idx"])
    width, height = _flux2_ref_size(config)
    prompt = _flux2_ref_prompt(item)
    return {
        "node.inputs": {
            FLUX2_REF_LOAD_IMAGE: {"image": item["ref"]},
            FLUX2_REF_TEXT_POS: {"text": prompt},
            FLUX2_REF_LATENT: {"width": width, "height": height},
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


def _shot_seed(shot_id: str) -> int:
    text = str(shot_id).strip().encode("utf-8")
    return int(zlib.crc32(text) % 1_000_000)


def _flux2_ref_prompt(item: dict) -> str:
    text = str(item["prompt_text"]).strip()
    if not text:
        raise RuntimeError(f"empty Flux2 reference prompt_text: {item['shot_id']}")
    return text


def _flux2_ref_size(config: dict) -> tuple[int, int]:
    size = str(config["render"]["tti_size"])
    w, h = size.split("x", 1)
    return int(w), int(h)
