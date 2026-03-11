from __future__ import annotations

import zlib

from ai_mv.utils.text_utils import ensure_positive_size

USO_LOAD_IMAGE = "47"
USO_TEXT_POS = "112:6"
USO_LATENT = "112:110"
USO_KSAMPLER = "112:31"
USO_SAVE = "9"


def map_uso_workflow(config: dict, item: dict) -> dict:
    idx = _shot_seed(str(item["shot_id"])) + int(item["frame_idx"])
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


def _shot_seed(shot_id: str) -> int:
    text = str(shot_id).strip().encode("utf-8")
    return int(zlib.crc32(text) % 1_000_000)


def _uso_prompt(item: dict) -> str:
    text = str(item["prompt_text"]).strip()
    if not text:
        raise RuntimeError(f"empty USO prompt_text: {item['shot_id']}")
    parts = [text, _frame_clause(item), _intent_clause(item)]
    return " ".join(x for x in parts if x).strip()


def _frame_clause(item: dict) -> str:
    frame = str(item.get("frame_name", "")).strip().lower()
    delta = str(item.get("delta", "")).strip()
    if not delta:
        return ""
    if frame == "start":
        return f"Start frame only; show the poised setup before {delta}."
    if frame == "end":
        return f"End frame only; clearly land after {delta}."
    return f"Show the moment around {delta}."


def _intent_clause(item: dict) -> str:
    vals = [
        str(item.get("style_guidance", "")).strip(),
        str(item.get("camera_language", "")).strip(),
        str(item.get("emotion", "")).strip(),
        str(item.get("scene_detail", "")).strip(),
        str(item.get("motion_hint", "")).strip(),
    ]
    text = ", ".join(x for x in vals if x)
    return f"Keep {text}." if text else ""


def _uso_size(config: dict) -> tuple[int, int]:
    size = str(config["render"]["uso_size"])
    w, h = size.split("x", 1)
    iw, ih = int(w), int(h)
    ensure_positive_size(iw, ih)
    return iw, ih
