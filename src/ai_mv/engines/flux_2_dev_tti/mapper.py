from __future__ import annotations

from ai_mv.utils.text_utils import parse_size

TTI_TEXT = "98:6"
TTI_NOISE = "98:25"
TTI_LATENT = "98:47"
TTI_SAVE = "9"


def map_tti_workflow(config: dict, shot: dict) -> dict:
    w, h = _tti_size(config)
    return {
        "node.inputs": {
            TTI_TEXT: {"text": shot["prompt_text"]},
            TTI_NOISE: {"noise_seed": int(shot["seed"])},
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
    return w, h
