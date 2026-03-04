from __future__ import annotations


def audio_policy(config: dict) -> dict:
    audio = config.get("audio", {})
    return {
        "duration": int(audio.get("target_duration_sec", 160)),
        "seed": int(audio.get("seed", 31)),
        "bpm": int(audio.get("bpm", 120)),
        "quality": str(audio.get("quality", "V0")),
    }
