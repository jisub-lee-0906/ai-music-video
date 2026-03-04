from __future__ import annotations


def map_audio_workflow(config: dict, plan: dict) -> dict:
    return {
        "audio.source_wav": plan["source_wav"],
        "audio.sample_rate": plan["sample_rate"],
        "audio.duration": plan["duration"],
        "audio.seed": plan["seed"],
    }

