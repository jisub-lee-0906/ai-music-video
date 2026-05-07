from __future__ import annotations

from ai_mv.engines.ltx_ia2v.common import float_value, int_value, ltx_size, non_negative_float

LTX_IA2V_IMAGE = "269"
LTX_IA2V_AUDIO = "276"
LTX_IA2V_POS = "340:306"
LTX_IA2V_NEG = "340:314"
LTX_IA2V_SEED = "340:319"
LTX_IA2V_FPS = "340:323"
LTX_IA2V_HEIGHT = "340:324"
LTX_IA2V_WIDTH = "340:330"
LTX_IA2V_DURATION = "340:331"
LTX_IA2V_TRIM = "340:332"
LTX_IA2V_SAVE = "341"



def map_ltx_ia2v_workflow(config: dict, item: dict) -> dict:
    width, height = ltx_size(config, item, "ltx_ia2v_size")
    fps = int_value(item.get("fps") or config.get("render", {}).get("ltx_fps"), 24)
    duration_sec = float_value(item.get("duration_sec"), 4.0)
    start_sec = non_negative_float(item.get("audio_start_sec"), 0.0)
    prompt_seed = str(item.get("prompt_seed") or "").strip()
    positive_prompt = str(item.get("positive_prompt") or "").strip()
    return {
        "node.inputs": {
            LTX_IA2V_IMAGE: {"image": str(item["image"]).strip()},
            LTX_IA2V_AUDIO: {"audio": str(item["audio"]).strip()},
            LTX_IA2V_POS: {"text": positive_prompt},
            LTX_IA2V_NEG: {"text": str(item.get("negative_prompt", "")).strip()},
            LTX_IA2V_SEED: {"value": prompt_seed},
            LTX_IA2V_FPS: {"value": fps},
            LTX_IA2V_HEIGHT: {"value": height},
            LTX_IA2V_WIDTH: {"value": width},
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
