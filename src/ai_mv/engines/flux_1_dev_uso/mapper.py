from __future__ import annotations

from ai_mv.utils.text_utils import ensure_16_9


def map_uso_workflow(config: dict, item: dict) -> dict:
    idx = _shot_index(item.get("shot_id", "0")) + int(item.get("frame_idx", 0))
    width, height = _uso_size(config)
    return {
        "shot.prompt": _uso_prompt(item),
        "shot.seed": 2000 + idx,
        "shot.reference_image": item["ref"],
        "video.width": width,
        "video.height": height,
        "image.filename_prefix": item.get("filename_prefix", "ComfyUI"),
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
    guidance = str(item.get("style_guidance", "")).strip()
    base = f"consistent portrait for {item['shot_id']}"
    stype = str(item.get("shot_type", "CHAR_MASTER"))
    style = str(item.get("style_ref", ""))
    delta = str(item.get("delta", "small pose shift"))
    return (
        f"{base}, shot_type={stype}, keyframe={item.get('frame_name', 'start')}, "
        f"delta={delta}, style_ref={style}, guidance={guidance}"
    )


def _uso_size(config: dict) -> tuple[int, int]:
    size = str(config.get("render", {}).get("uso_size", "1024x576"))
    w, h = size.split("x", 1)
    iw, ih = int(w), int(h)
    ensure_16_9(iw, ih)
    return iw, ih
