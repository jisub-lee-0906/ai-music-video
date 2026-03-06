from __future__ import annotations


def audio_policy(config: dict) -> dict:
    audio = config["audio"]
    bpm = int(audio["bpm"]) if str(audio.get("bpm", "")).strip() else 0
    return {
        "duration": int(audio["target_duration_sec"]),
        "seed": int(audio["seed"]),
        "bpm": bpm,
        "quality": str(audio["quality"]),
        "keyscale": str(audio.get("keyscale", "")).strip(),
    }
