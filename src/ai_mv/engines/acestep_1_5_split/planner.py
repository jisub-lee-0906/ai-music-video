from __future__ import annotations

from ai_mv.engines.acestep_1_5_split.policy import audio_policy


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = config.get("audio", {})
    plan = {"source_wav": audio.get("source_wav", ""), "sample_rate": audio.get("sample_rate", 48000)}
    plan.update(audio_policy(config))
    return plan

