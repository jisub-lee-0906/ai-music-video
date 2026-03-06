from __future__ import annotations


def audio_policy(config: dict) -> dict:
    audio = _audio_config(config)
    bpm = int(audio["bpm"]) if str(audio.get("bpm", "")).strip() else 0
    return {
        "duration": int(audio.get("target_duration_sec", 160)),
        "seed": int(audio.get("seed", 31)),
        "bpm": bpm,
        "quality": str(audio.get("quality", "V0")),
        "keyscale": str(audio.get("keyscale", "")).strip(),
    }


def _audio_config(config: dict) -> dict:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    return audio if isinstance(audio, dict) else {}
