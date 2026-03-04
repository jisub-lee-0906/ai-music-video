from __future__ import annotations

from pathlib import Path

from ai_mv.core.contracts.prompt_contract import audio_schema, normalize_audio_fields
from ai_mv.engines.acestep_1_5_split.policy import audio_policy
from ai_mv.infra.ollama_client import generate_structured


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = config.get("audio", {})
    plan = {
        "source_wav": audio.get("source_wav", ""),
        "sample_rate": audio.get("sample_rate", 48000),
        "lyrics": _load_lyrics(audio.get("lyrics_file", "")),
        "tags": ", ".join(audio.get("keywords", [])),
        "filename_prefix": f"artifacts/runs_state/{payload.get('run_id', 'run')}/audio/music",
    }
    plan.update(audio_policy(config))
    planned = _plan_with_ollama(config, plan)
    return normalize_audio_fields(planned, plan)


def _plan_with_ollama(config: dict, fallback: dict) -> dict:
    prompt = _audio_prompt(fallback)
    try:
        return generate_structured(config, prompt, audio_schema())
    except Exception:
        return {}


def _audio_prompt(plan: dict) -> str:
    return (
        "Return JSON only with keys tags,lyrics,bpm,seed,duration. "
        f"Keep duration near {int(plan.get('duration', 160))} seconds. "
        f"Input tags={plan.get('tags','')}, bpm={plan.get('bpm',120)}."
    )


def _load_lyrics(path: str) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").strip()

