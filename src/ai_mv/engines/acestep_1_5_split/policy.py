from __future__ import annotations


def audio_policy(config: dict) -> dict:
    audio = config["audio"]
    return {
        "duration": int(audio["target_duration_sec"]),
        "seed": int(audio["seed"]),
        "bpm": int(audio["bpm"]),
        "quality": str(audio["quality"]),
    }
