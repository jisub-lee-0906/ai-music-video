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
    normalized["description"] = normalized["genre_description"] or plan["description"]
    normalized["filename_prefix"] = plan["filename_prefix"]
    return normalized


def _plan_with_ollama(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    desc = str(plan["description"]).strip()
    return (
        "System role: You are a world-class K-pop/J-pop songwriter-producer and vocal director. "
        "Output JSON only. No markdown, no commentary. "
        "Schema keys: tags,genre_description,bpm,seed,duration,lyrics_blocks. "
        "lyrics_blocks[] keys: section,label,style,lines[]. "
        "Allowed sections: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,outro. "
        "Compose a radio-ready idol track concept with clear section contrast: "
        "punchy verse, emotional pre-chorus, explosive hook chorus. "
        "genre_description must mention arrangement and production choices in one compact paragraph. "
        "Each lines[] must contain 2-4 singable lines, concrete imagery, and strong hook phrasing. "
        "Avoid generic filler, profanity, and empty lines. "
        f"Target duration={int(plan['duration'])} sec, bpm={int(plan['bpm'])}, tags={plan['tags']}. "
        f"Creative reference: {desc}."
    )

