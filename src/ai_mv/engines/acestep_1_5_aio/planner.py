from __future__ import annotations

from ai_mv.core.output_paths import audio_prefix
from ai_mv.core.profile_brief import build_profile_intent
from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
)
from ai_mv.core.contracts.prompt_schema import audio_schema
from ai_mv.engines.acestep_1_5_aio.policy import audio_policy
from ai_mv.infra.codex_cli_client import generate_structured


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = _audio_config(config)
    tags = _audio_tags(audio)
    intent = build_profile_intent(config)
    plan = {
        "tags": tags,
        "profile_intent": intent,
        "language": _audio_language(audio),
        "filename_prefix": audio_prefix(payload["run_id"]),
    }
    plan.update(audio_policy(config))
    plan["hook_shape_bias"] = _hook_shape_bias(int(plan.get("seed", 31)), str(plan.get("language", "")).strip().lower())
    return _plan_once(config, plan)


def _plan_with_llm(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    tags = str(plan["tags"]).strip()
    tags_clause = f"Input tags={tags}. " if tags else ""
    language_clause = _language_clause(plan)
    hook_shape_clause = _hook_shape_clause(plan)
    bar_lane_clause = _bar_lane_clause(plan)
    bpm_clause = _target_bpm_clause(plan)
    seed_clause = f"Creative seed={int(plan.get('seed', 31))}. "
    intent_clause = _intent_clause(plan)
    return _audio_prompt_rules(plan) + (
        f"Target duration={int(plan['duration'])} sec. "
        f"{bpm_clause}{bar_lane_clause}{seed_clause}{tags_clause}{language_clause}{intent_clause}{hook_shape_clause}"
    )


def _audio_prompt_rules(plan: dict) -> str:
    return (
        _audio_output_contract()
        + _audio_song_craft_brief()
        + _audio_artist_direction()
        + _audio_description_rules()
        + _language_style_rules(plan)
    )


def _audio_output_contract() -> str:
    return (
        "You are an elite songwriter-producer shaping a release-ready song plan. "
        "Return JSON only. No markdown. No prose outside JSON. "
        "Required top-level keys: genre_description,bpm,keyscale,seed,duration,lyrics_blocks. "
        "Required lyrics_blocks item keys: section,label,style,lines. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
    )


def _audio_song_craft_brief() -> str:
    return (
        "Build a complete track, not a fragment. "
        "Preferred arc is intro, verse_1, pre_chorus, chorus, post_chorus, verse_2, pre_chorus, chorus, bridge, final chorus, outro. "
        "A bridge must never be the last major section; the track must return to chorus after it. "
        "Label the last chorus as Final Chorus while keeping section='chorus'. "
        "Keep section jobs clear: intro sets atmosphere, verses move the scene, pre-chorus lifts tension, chorus carries the title-worthy idea, bridge turns the perspective, and outro lands the song. "
        "Let Chorus 2 feel like a true return rather than a copy, and let the Final Chorus feel earned by the bridge. "
        "Post-chorus may be brief, but it should echo the hook with one complete melodic thought. "
    )


def _audio_artist_direction() -> str:
    return (
        "Write like a finished record, not like an exercise. "
        "Aim for a short production-minded brief plus lyric blocks that are immediately singable and emotionally inevitable. "
        "Front-load memorability: give the chorus opening a title-worthy phrase with clean mouth-feel, easy rhythmic lift, and a topline a vocalist would want to repeat. "
        "Give the lead vocal a real performance arc: more contained in the early sections, more open through the lift, and more expansive when the hook arrives. "
        "Each major return should create a new emotional release, not just restate the same information. "
        "Use the bridge to make a choice, confession, rupture, or reveal that changes how the Final Chorus lands. "
        "Treat the Final Chorus as the emotional arrival shot, and let the outro feel fully settled rather than abruptly cut off. "
        "Keep the prompt centered on songwriting, topline, arrangement, and lyrical world; do not solve music-video staging inside the song plan. "
    )


def _audio_description_rules() -> str:
    return (
        "genre_description must be one compact production paragraph in plain language for the AceStep tags text field. "
        "genre_description must always be written in English, even when the lyrics language is Japanese or Korean. "
        "Keep it to 2-3 sentences covering groove foundation, vocal character, hook instrumentation, and pocket. "
        "Prefer a coherent producer brief over a long list of tags. "
        "For lyrics_blocks, keep lines short, concrete, and melodic. "
        "Only chorus may expand beyond 4 lines when the payoff needs extra room. "
        "Keep 1-3 recurring world images alive across sections so the song feels glued together. "
        "Avoid generic filler, empty slogans, placeholder romance language, and hooks that could belong to any song. "
        "Prefer concrete nouns, directional motion, physical sensation, or scene detail over vague abstraction. "
        "Make the chorus easy to sing back after one listen, and make the later returns feel more released, more specific, or more committed. "
        "Treat the provided audio intent, hook intent, world intent, and negative intent as the source of truth. "
        "Do not invent extra sections or fields. "
    )


def _language_style_rules(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    if lang == "ja":
        return (
            "Write fluent modern Japanese lyrics with a natural mix of kanji, hiragana, and katakana. "
            "Keep the diction elegant, adult, and singable rather than childish, slangy, or anime-coded. "
            "Prefer natural Japanese phrasing built from the profile's concrete world over awkward loanword-heavy wording. "
            "Avoid forced transliterations when a natural Japanese phrase would sing more smoothly. "
            "In Japanese songs, the main chorus opening should be led by Japanese phrasing; do not let an English fragment dominate the hook anchor. "
            "Keep English rare and intentional in chorus support or callback lines. "
            "Do not let a short English phrase become the emotional center of a chorus line. "
            "If you use an English fragment, weave it into a fuller Japanese line instead of leaving it as a standalone slogan. "
            "Do not use romaji, broken mojibake-like text, or fake Japanese-looking fragments. "
        )
    if lang == "ko":
        return (
            "Write fluent modern Korean lyrics with natural Hangul phrasing and clean singable cadence. "
            "Keep English limited to very short intentional hook fragments. "
            "Do not use broken transliteration, fake Korean-looking fragments, or noisy filler syllables. "
        )
    return ""


def _audio_tags(audio: dict) -> str:
    raw = audio.get("tags", []) if isinstance(audio, dict) else []
    vals = [str(x).strip() for x in raw if str(x).strip()]
    return ", ".join(vals)


def _audio_config(config: dict) -> dict:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    return audio if isinstance(audio, dict) else {}


def _audio_language(audio: dict) -> str:
    raw = str(audio.get("language", "en")).strip().lower() if isinstance(audio, dict) else "en"
    return raw if raw in {"en", "ja", "ko"} else "en"


def _target_bpm_clause(plan: dict) -> str:
    bpm = int(plan.get("bpm", 0))
    return f"Target bpm={bpm}. " if bpm > 0 else ""


def _language_clause(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    if not lang:
        return ""
    return f"Lyrics language={lang}. "


def _intent_clause(plan: dict) -> str:
    intent = plan.get("profile_intent", {}) if isinstance(plan.get("profile_intent", {}), dict) else {}
    audio = intent.get("audio_intent", {}) if isinstance(intent, dict) else {}
    world = intent.get("world_intent", {}) if isinstance(intent, dict) else {}
    negative = intent.get("negative_intent", {}) if isinstance(intent, dict) else {}
    parts = [
        _profile_line("Audio intent", audio.get("brief", "")),
        _profile_line("Hook intent", audio.get("hook_brief", "")),
        _profile_line("World intent", world.get("visual_intent", "")),
        _profile_line("Story world", world.get("story_world", "")),
        _profile_line("Avoid", " ".join([str(negative.get("visual_negative", "")).strip(), str(negative.get("mv_avoid", "")).strip()]).strip()),
    ]
    return "".join(parts)


def _hook_shape_clause(plan: dict) -> str:
    text = str(plan.get("hook_shape_bias", "")).strip()
    return f"Hook contour bias={text}. " if text else ""


def _bar_lane_clause(plan: dict) -> str:
    text = str(plan.get("bar_lane", "")).strip()
    return f"Bar lane={text}. " if text else ""


def _profile_line(label: str, text: object) -> str:
    val = str(text).strip()
    return f"{label}={val}. " if val else ""


def _plan_once(config: dict, plan: dict) -> dict:
    normalized = _normalize_and_validate(config, plan)
    return normalized


def _normalize_and_validate(config: dict, plan: dict) -> dict:
    planned = _plan_with_llm(config, plan)
    normalized = normalize_audio_fields(planned)
    normalized["lyrics_blocks"] = _attach_line_indexes(normalized.get("lyrics_blocks", []))
    normalized["duration"] = _resolved_duration(plan, normalized)
    normalized["tags"] = plan["tags"]
    normalized["profile_intent"] = dict(plan.get("profile_intent", {}))
    normalized["language"] = plan["language"]
    normalized["filename_prefix"] = plan["filename_prefix"]
    normalized["quality"] = plan["quality"]
    normalized["beats_per_bar"] = int(plan.get("beats_per_bar", 4))
    normalized["section_bars"] = dict(plan.get("section_bars", {}))
    normalized["bar_lane"] = str(plan.get("bar_lane", "")).strip()
    if not str(normalized.get("keyscale", "")).strip():
        normalized["keyscale"] = str(plan.get("keyscale", "")).strip()
    return normalized


def _attach_line_indexes(blocks: list[dict]) -> list[dict]:
    out: list[dict] = []
    for block in blocks:
        row = dict(block)
        lines = [str(x).strip() for x in block.get("lines", []) if str(x).strip()]
        row["indexed_lines"] = [{"line_index": idx, "text": text} for idx, text in enumerate(lines, start=1)]
        out.append(row)
    return out


def _resolved_duration(plan: dict, normalized: dict) -> int:
    if bool(plan.get("duration_override")):
        return int(plan["duration"])
    from ai_mv.engines.acestep_1_5_aio.policy import compute_duration_from_blocks, resolve_section_bars

    return compute_duration_from_blocks(
        normalized.get("lyrics_blocks", []),
        int(normalized.get("bpm", 0)),
        int(plan.get("beats_per_bar", 4)),
        resolve_section_bars({"section_bars": plan.get("section_bars", {})}),
    )


def _hook_shape_bias(seed: int, language: str) -> str:
    if language == "ja":
        shapes = (
            "concrete image with destination or last-ride motion",
            "street object with emotional echo",
            "reflection cue with afterglow or remaining heat",
            "weather or light cue with reaching motion",
        )
        return shapes[seed % len(shapes)]
    shapes = (
        "concrete image with destination",
        "place cue with emotional echo",
        "reflection cue with afterglow",
        "weather cue with motion",
    )
    return shapes[seed % len(shapes)]
