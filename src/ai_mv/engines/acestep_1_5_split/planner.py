from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import audio_schema, normalize_audio_fields
from ai_mv.engines.acestep_1_5_split.policy import audio_policy
from ai_mv.infra.ollama_client import generate_structured


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = config["audio"]
    plan = {
        "source_wav": audio["source_wav"],
        "lyrics": str(audio["lyrics"]),
        "description": str(audio["song_description"]),
        "tags": ", ".join(audio["keywords"]),
        "filename_prefix": f"artifacts/runs_state/{payload['run_id']}/audio/music",
    }
    plan.update(audio_policy(config))
    planned = _plan_with_ollama(config, plan)
    normalized = normalize_audio_fields(planned)
    normalized["source_wav"] = plan["source_wav"]
    normalized["description"] = plan["description"]
    normalized["filename_prefix"] = plan["filename_prefix"]
    return normalized


def _plan_with_ollama(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    desc = str(plan["description"]).strip()
    return (
        "Return JSON only with keys tags,lyrics,bpm,seed,duration. "
        f"Keep duration near {int(plan['duration'])} seconds. "
        f"Input tags={plan['tags']}, bpm={plan['bpm']}, desc={desc}."
    )

