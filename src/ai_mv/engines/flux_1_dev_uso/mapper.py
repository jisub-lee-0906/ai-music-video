from __future__ import annotations

from ai_mv.utils.text_utils import ensure_16_9

USO_LOAD_IMAGE = "47"
USO_TEXT_POS = "112:6"
USO_LATENT = "112:110"
USO_KSAMPLER = "112:31"
USO_SAVE = "9"


def map_uso_workflow(config: dict, item: dict) -> dict:
    idx = _shot_index(str(item["shot_id"])) + int(item["frame_idx"])
    width, height = _uso_size(config)
    prompt = _uso_prompt(item)
    return {
        "node.inputs": {
            USO_LOAD_IMAGE: {"image": item["ref"]},
            USO_TEXT_POS: {"text": prompt},
            USO_LATENT: {"width": width, "height": height},
            USO_KSAMPLER: {"seed": 2000 + idx},
            USO_SAVE: {"filename_prefix": item["filename_prefix"]},
        },
    }


def uso_required_inputs() -> dict[str, list[str]]:
    return {
        "LoadImage": ["image"],
        "CLIPTextEncode": ["text"],
        "KSampler": ["seed"],
        "EmptySD3LatentImage": ["width", "height"],
        "SaveImage": ["filename_prefix"],
    }


def _shot_index(shot_id: str) -> int:
    token = str(shot_id).split("_")[-1]
    digits = "".join(ch for ch in token if ch.isdigit())
    return int(digits) if digits else 0


def _uso_prompt(item: dict) -> str:
    guidance = str(item["style_guidance"]).strip()
    base = f"consistent portrait for {item['shot_id']}"
    stype = str(item["shot_type"])
    style = str(item["style_ref"])
    delta = str(item["delta"])
    return (
        f"{base}, shot_type={stype}, keyframe={item['frame_name']}, "
        f"delta={delta}, style_ref={style}, guidance={guidance}"
    )


def _uso_size(config: dict) -> tuple[int, int]:
    size = str(config.get("render", {}).get("uso_size", "1024x576"))
    w, h = size.split("x", 1)
    iw, ih = int(w), int(h)
    ensure_16_9(iw, ih)
    return iw, ih
