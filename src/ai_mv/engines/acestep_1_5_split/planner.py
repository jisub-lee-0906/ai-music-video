from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_audio_fields
from ai_mv.core.contracts.prompt_schema import audio_schema
from ai_mv.engines.acestep_1_5_split.policy import audio_policy
from ai_mv.infra.ollama_client import generate_structured


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = _audio_config(config)
    plan = {
        "tags": _audio_tags(audio),
        "style_guidance": _style_guidance(config),
        "filename_prefix": f"artifacts/runs_state/{payload['run_id']}/audio/music",
    }
    plan.update(audio_policy(config))
    planned = _plan_with_ollama(config, plan)
    normalized = normalize_audio_fields(planned)
    normalized["tags"] = plan["tags"]
    normalized["style_guidance"] = plan["style_guidance"]
    normalized["filename_prefix"] = plan["filename_prefix"]
    normalized["quality"] = plan["quality"]
    if not str(normalized.get("keyscale", "")).strip():
        normalized["keyscale"] = str(plan.get("keyscale", "")).strip()
    return normalized


def _plan_with_ollama(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    tags = str(plan["tags"]).strip()
    guidance = str(plan["style_guidance"]).strip()
    tags_clause = f"Input tags={tags}. " if tags else ""
    guidance_clause = f"Style guidance={guidance}. " if guidance else ""
    bpm_clause = _target_bpm_clause(plan)
    return _audio_prompt_rules() + (
        f"Target duration={int(plan['duration'])} sec. "
        f"{bpm_clause}{tags_clause}{guidance_clause}"
    )


def _audio_prompt_rules() -> str:
    return _audio_structure_rules() + _audio_description_rules()


def _audio_structure_rules() -> str:
    return (
        "You are an elite songwriter-producer. Return JSON only. "
        "No markdown. No prose outside JSON. "
        "Required top-level keys: genre_description,bpm,keyscale,seed,duration,lyrics_blocks. "
        "Required lyrics_blocks item keys: section,label,style,lines. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
        "Composition target must follow input reference strictly. "
        "Design aggressive section contrast with distinct diction per section. "
        "Give each section a clearly different job in the emotional arc so the song feels staged and cumulative. "
        "Intro should open atmosphere with minimal language and immediate tone-setting. "
        "Intro should stay sparse and usually fit in 2-3 short lines unless the style strongly demands more. "
        "Verse: forward motion, clear imagery, memorable cadence, and strong lyrical specificity. "
        "Verse should include concrete sensory or scene details without copying examples, and should advance the scene rather than summarizing emotion. "
        "Prefer fuller line density in verses than in pre-chorus or outro. "
        "Keep line endings clear and singable; avoid vague filler. "
        "Pre-chorus: emotional lift, tension, breath-space, smoother vowel flow and intimacy, with language that clearly prepares a release. "
        "Pre-chorus should feel slightly more open and less crowded than the verse. "
        "Pre-chorus usually works best in 2-3 concise lines unless the song clearly needs an extra pickup line. "
        "Chorus: high-impact hook, chant-ready phrasing, immediate recall, strong emotional release, and the clearest central idea of the song. "
        "Chorus should simplify language compared with the verse so the hook lands instantly. "
        "Post-chorus: very short callback lines built around the same hook phrase, acting as a lingering afterglow rather than a new verse. "
        "Bridge should create a genuine contrast in perspective, energy, or emotional framing before the final return, and should redirect or thin the language instead of stacking more imagery. "
        "Bridge should usually be sparser than the verse and should not feel lyrically crowded. "
    )


def _audio_description_rules() -> str:
    return (
        "genre_description must be one compact production paragraph including arrangement cues "
        "(808/bass, synth layers, harmonies, transitions, impact), in 2-3 sentences only. "
        "genre_description must explicitly cover groove foundation, lead vocal character, and hook instrumentation. "
        "genre_description should also describe pocket, rhythm feel, or timing character in concrete production terms when relevant. "
        "Mention at least one clear groove behavior such as bounce, glide, pulse, sway, swing, push, or restraint. "
        "Prefer tangible musical language like swing, bounce, pulse, breath, glide, shimmer, punch, or restraint over generic adjectives. "
        "Prefer one coherent production identity instead of mixing many genres. "
        "Keep genre_description reusable as a downstream audio-direction brief, not a poetic review. "
        "For each block, lines must be 2-4 short singable lines with concrete imagery and cadence. "
        "Only chorus may expand beyond 4 lines when needed for hook repetition or chant response. "
        "Prefer vivid action verbs and sonic words over abstract statements. "
        "Write lines with clear mouth-feel and internal rhythm suitable for topline melody. "
        "Keep 1-3 recurring concept words or images alive across verse, pre-chorus, and chorus so the song identity stays glued together. "
        "Include one repeatable hook phrase in chorus/post-chorus for recall and repeat it at least twice in chorus lines. "
        "Chorus must include at least one call-and-response or chant-like fragment. "
        "Avoid generic filler and repeated empty slogans. "
        "Do not invent extra sections or fields. "
    )


def _audio_tags(audio: dict) -> str:
    raw = audio.get("tags", []) if isinstance(audio, dict) else []
    vals = [str(x).strip() for x in raw if str(x).strip()]
    return ", ".join(vals)


def _audio_config(config: dict) -> dict:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    return audio if isinstance(audio, dict) else {}


def _style_guidance(config: dict) -> str:
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


def _target_bpm_clause(plan: dict) -> str:
    bpm = int(plan.get("bpm", 0))
    return f"Target bpm={bpm}. " if bpm > 0 else ""
