from __future__ import annotations

AUDIO_TEXT = "94"
AUDIO_LATENT = "98"
AUDIO_KSAMPLER = "3"
AUDIO_SAVE = "104"


def map_audio_workflow(config: dict, plan: dict) -> dict:
    text_inputs = {
        "tags": _audio_conditioning_text(plan),
        "lyrics": str(plan["lyrics"]),
        "seed": int(plan["seed"]),
        "bpm": int(plan["bpm"]),
        "duration": int(plan["duration"]),
        "language": _audio_language(plan),
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
        "TextEncodeAceStepAudio1.5": ["tags", "lyrics", "seed", "bpm", "duration", "language"],
        "EmptyAceStep1.5LatentAudio": ["seconds"],
        "KSampler": ["seed"],
        "SaveAudioMP3": ["filename_prefix", "quality"],
    }


def _audio_language(plan: dict) -> str:
    raw = str(plan.get("language", "en")).strip().lower()
    return raw if raw in {"en", "ja", "ko"} else "en"


def _audio_conditioning_text(plan: dict) -> str:
    tags = str(plan.get("tags", "")).strip()
    desc = str(plan.get("genre_description", "")).strip()
    if tags and desc:
        return f"{tags}. {desc}"
    return tags or desc
