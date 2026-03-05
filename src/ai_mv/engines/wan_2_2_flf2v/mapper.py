from __future__ import annotations

from ai_mv.utils.text_utils import ensure_16_9, parse_size

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
    idx = _shot_index(str(clip["shot_id"]))
    seed = 3000 + idx + int(clip["seed_offset"])
    steps = _steps_for_energy(str(clip["energy"]))
    neg = str(clip["negative_prompt"])
    pos = str(clip["prompt"])
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
                "start_image": clip["start"],
                "end_image": clip["end"],
            },
            WAN_KSAMPLER_A: {"noise_seed": seed, "steps": steps},
            WAN_KSAMPLER_B: {"noise_seed": seed, "steps": steps},
            WAN_CREATE: {"fps": int(clip["fps"])},
            WAN_SAVE: {"filename_prefix": str(clip["filename_prefix"])},
        },
    }


def _shot_index(shot_id: str) -> int:
    token = str(shot_id).split("_")[-1]
    digits = "".join(ch for ch in token if ch.isdigit())
    return int(digits) if digits else 0


def _wan_size(config: dict, clip: dict) -> tuple[int, int]:
    size = str(clip["wan_size"])
    w, h = parse_size(size)
    ensure_16_9(w, h)
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
    if energy == "mid":
        return 18
    raise ValueError(f"invalid energy: {energy}")
