from __future__ import annotations

from ai_mv.utils.text_utils import ascii_safe_text

AUDIO_TEXT = "94"
AUDIO_LATENT = "98"
AUDIO_KSAMPLER = "3"
AUDIO_SAVE = "104"


def map_audio_workflow(config: dict, plan: dict) -> dict:
    text_inputs = {
        "tags": ascii_safe_text(str(plan["genre_description"])),
        "lyrics": ascii_safe_text(str(plan["lyrics"])),
        "seed": int(plan["seed"]),
        "bpm": int(plan["bpm"]),
        "duration": int(plan["duration"]),
    }
    keyscale = str(plan.get("keyscale", "")).strip()
    if keyscale:
        text_inputs["keyscale"] = keyscale
    return {
        "node.inputs": {
            AUDIO_TEXT: text_inputs,
            AUDIO_LATENT: {"seconds": int(plan["duration"])},
            AUDIO_KSAMPLER: {"seed": int(plan["seed"])},
            AUDIO_SAVE: {
                "filename_prefix": str(plan["filename_prefix"]),
                "quality": str(plan["quality"]),
            },
        }
    }


def audio_required_inputs() -> dict[str, list[str]]:
    return {
        "TextEncodeAceStepAudio1.5": ["tags", "lyrics", "seed", "bpm", "duration"],
        "EmptyAceStep1.5LatentAudio": ["seconds"],
        "KSampler": ["seed"],
        "SaveAudioMP3": ["filename_prefix", "quality"],
    }
