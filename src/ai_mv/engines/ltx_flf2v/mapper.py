from __future__ import annotations

from ai_mv.engines.ltx_i2v.mapper import _ltx_size, _int_value, _float_value, _frame_count

LTX_FLF2V_FIRST = "31"
LTX_FLF2V_LAST = "39"
LTX_FLF2V_SAVE = "68"
LTX_FLF2V_HEIGHT = "129:98"
LTX_FLF2V_DURATION = "129:102"
LTX_FLF2V_NEG = "129:112"
LTX_FLF2V_WIDTH = "129:113"
LTX_FLF2V_FPS = "129:114"
LTX_FLF2V_POS = "129:128"


def map_ltx_flf2v_workflow(config: dict, item: dict) -> dict:
    width, height = _ltx_size(config, item, "ltx_flf2v_size")
    fps = _int_value(item.get("fps") or config.get("render", {}).get("ltx_fps"), 24)
    duration_sec = _float_value(item.get("duration_sec"), 5.0)
    frame_count = _frame_count(item, fps, duration_sec)
    positive_prompt = str(item.get("clip_positive_prompt") or item.get("positive_prompt") or "").strip()
    return {
        "node.inputs": {
            LTX_FLF2V_FIRST: {"image": str(item["first_image"]).strip()},
            LTX_FLF2V_LAST: {"image": str(item["last_image"]).strip()},
            LTX_FLF2V_POS: {"text": positive_prompt},
            LTX_FLF2V_NEG: {"text": str(item.get("negative_prompt", "")).strip()},
            LTX_FLF2V_WIDTH: {"value": width},
            LTX_FLF2V_HEIGHT: {"value": height},
            LTX_FLF2V_FPS: {"value": fps},
            LTX_FLF2V_DURATION: {"value": frame_count},
            LTX_FLF2V_SAVE: {"filename_prefix": str(item["filename_prefix"]).strip()},
        }
    }


def ltx_flf2v_required_inputs() -> dict[str, list[str]]:
    return {
        "SaveVideo": ["filename_prefix"],
        "LoadImage": ["image"],
        "PrimitiveInt": ["value"],
        "CLIPTextEncode": ["text"],
    }
