from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import audio_schema, normalize_audio_fields
from ai_mv.engines.acestep_1_5_split.policy import audio_policy
from ai_mv.infra.ollama_client import generate_structured


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = config["audio"]
    plan = {
        "lyrics": str(audio["lyrics"]),
        "description": str(audio["song_description"]),
        "tags": _audio_tags(audio),
        "filename_prefix": f"artifacts/runs_state/{payload['run_id']}/audio/music",
    }
    plan.update(audio_policy(config))
    planned = _plan_with_ollama(config, plan)
    normalized = normalize_audio_fields(planned)
    normalized["description"] = normalized["genre_description"] or plan["description"]
    normalized["filename_prefix"] = plan["filename_prefix"]
    normalized["quality"] = plan["quality"]
    return normalized


def _plan_with_ollama(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    desc = str(plan["description"]).strip()
    tags = str(plan["tags"]).strip()
    tags_clause = f"Input tags={tags}. " if tags else ""
    return (
        "You are an elite songwriter-producer. Return JSON only. "
        "No markdown. No prose outside JSON. "
        "Required top-level keys: genre_description,bpm,seed,duration,lyrics_blocks. "
        "Required lyrics_blocks item keys: section,label,style,lines. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,outro. "
        "Composition target must follow input reference strictly. "
        "Design aggressive section contrast with distinct diction per section. "
        "Verse: momentum-forward, rhythmic punch, percussive wording, compact bar-like phrasing. "
        "Verse should include concrete sonic/action terms (e.g., click, flash, bass, drop, ignite) without copying examples. "
        "For verse lines, prefer hard consonants, internal rhyme, and rapid-fire flow suitable for rap delivery. "
        "Keep line endings punchy and avoid soft abstract endings. "
        "Pre-chorus: emotional lift, tension, breath-space, smoother vowel flow and intimacy. "
        "Chorus: high-impact hook, chant-ready phrasing, immediate recall, crowd-shout energy. "
        "Post-chorus: very short callback lines built around the same hook phrase. "
        "genre_description must be one compact production paragraph including arrangement cues "
        "(808/bass, synth layers, harmonies, transitions, impact), in 2-3 sentences only. "
        "For each block, lines must be 2-4 short singable lines with concrete imagery and cadence. "
        "Prefer vivid action verbs and sonic words over abstract statements. "
        "Write lines with clear mouth-feel and internal rhythm suitable for topline melody. "
        "Include one repeatable hook phrase in chorus/post-chorus for recall and repeat it at least twice in chorus lines. "
        "Chorus must include at least one call-and-response or chant-like fragment. "
        "Avoid generic filler and repeated empty slogans. "
        "Do not invent extra sections or fields. "
        f"Target duration={int(plan['duration'])} sec, bpm={int(plan['bpm'])}. "
        f"{tags_clause}Creative reference={desc}."
    )


def _audio_tags(audio: dict) -> str:
    raw = audio.get("tags", []) if isinstance(audio, dict) else []
    vals = [str(x).strip() for x in raw if str(x).strip()]
    return ", ".join(vals)
