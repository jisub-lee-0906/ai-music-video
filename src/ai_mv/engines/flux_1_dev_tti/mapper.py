from __future__ import annotations

from ai_mv.utils.text_utils import ensure_16_9, parse_size

TTI_TEXT = "41"
TTI_KSAMPLER = "31"
TTI_LATENT = "27"
TTI_SAVE = "9"


def map_tti_workflow(config: dict, shot: dict) -> dict:
    w, h = _tti_size(config)
    return {
        "node.inputs": {
            TTI_TEXT: {"clip_l": shot["prompt"], "t5xxl": shot["prompt"]},
            TTI_KSAMPLER: {"seed": int(shot["seed"])},
            TTI_LATENT: {"width": w, "height": h},
            TTI_SAVE: {"filename_prefix": shot["filename_prefix"]},
        }
    }


def tti_required_inputs() -> dict[str, list[str]]:
    return {
        "CLIPTextEncodeFlux": ["clip_l", "t5xxl"],
        "KSampler": ["seed"],
        "EmptySD3LatentImage": ["width", "height"],
        "SaveImage": ["filename_prefix"],
    }


def _tti_size(config: dict) -> tuple[int, int]:
    size = str(config.get("render", {}).get("tti_size", "1024x576"))
    w, h = parse_size(size)
    ensure_16_9(w, h)
    return w, h
