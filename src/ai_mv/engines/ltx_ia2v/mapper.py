from __future__ import annotations

from ai_mv.engines.ltx_i2v.mapper import _ltx_size, _int_value, _float_value

LTX_IA2V_IMAGE = "269"
LTX_IA2V_AUDIO = "276"
LTX_IA2V_POS = "340:306"
LTX_IA2V_NEG = "340:314"
LTX_IA2V_SEED = "340:319"
LTX_IA2V_FPS = "340:323"
LTX_IA2V_DURATION = "340:331"
LTX_IA2V_TRIM = "340:332"
LTX_IA2V_SAVE = "341"


def map_ltx_ia2v_workflow(config: dict, item: dict) -> dict:
    _ltx_size(config, item, "ltx_ia2v_size")
    fps = _int_value(item.get("fps") or config.get("render", {}).get("ltx_fps"), 24)
    duration_sec = _float_value(item.get("duration_sec"), 4.0)
    start_sec = _non_negative_float(item.get("audio_start_sec"), 0.0)
    return {
        "node.inputs": {
            LTX_IA2V_IMAGE: {"image": str(item["image"]).strip()},
            LTX_IA2V_AUDIO: {"audio": str(item["audio"]).strip()},
            LTX_IA2V_POS: {"text": str(item.get("positive_prompt", "")).strip()},
            LTX_IA2V_NEG: {"text": str(item.get("negative_prompt", "")).strip()},
            LTX_IA2V_SEED: {"value": str(item["prompt_seed"]).strip()},
            LTX_IA2V_FPS: {"value": fps},
            LTX_IA2V_DURATION: {"value": duration_sec},
            LTX_IA2V_TRIM: {"start_index": start_sec, "duration": duration_sec},
            LTX_IA2V_SAVE: {"filename_prefix": str(item["filename_prefix"]).strip()},
        }
    }


def ltx_ia2v_required_inputs() -> dict[str, list[str]]:
    return {
        "SaveVideo": ["filename_prefix"],
        "LoadImage": ["image"],
        "LoadAudio": ["audio"],
        "PrimitiveStringMultiline": ["value"],
        "PrimitiveInt": ["value"],
        "PrimitiveFloat": ["value"],
        "TrimAudioDuration": ["start_index", "duration"],
        "CLIPTextEncode": ["text"],
    }


def _non_negative_float(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, parsed)
