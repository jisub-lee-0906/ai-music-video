from __future__ import annotations


def map_audio_workflow(config: dict, plan: dict) -> dict:
    return {
        "audio.tags": plan.get("tags", ""),
        "audio.lyrics": plan.get("lyrics", ""),
        "audio.seed": int(plan.get("seed", 31)),
        "audio.bpm": int(plan.get("bpm", 120)),
        "audio.duration": plan["duration"],
        "audio.filename_prefix": plan.get("filename_prefix", "audio/ComfyUI"),
        "audio.quality": plan.get("quality", "V0"),
    }


def audio_required_inputs() -> dict[str, list[str]]:
    return {
        "TextEncodeAceStepAudio1.5": ["tags", "lyrics", "seed", "bpm", "duration"],
        "EmptyAceStep1.5LatentAudio": ["seconds"],
        "KSampler": ["seed"],
        "SaveAudioMP3": ["filename_prefix", "quality"],
    }
