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
    return _plan_once(config, plan)


def build_audio_preview_prompt(plan: dict) -> str:
    return _audio_prompt(plan)


def _plan_with_llm(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    tags = str(plan["tags"]).strip()
    tags_clause = f"Input tags={tags}. " if tags else ""
    language_clause = _language_clause(plan)
    bpm_clause = _target_bpm_clause(plan)
    seed_clause = f"Creative seed={int(plan.get('seed', 31))}. "
    intent_clause = _intent_clause(plan)
    return _audio_prompt_rules(plan) + (
        f"{_target_duration_clause(plan)}"
        f"{bpm_clause}{seed_clause}{tags_clause}{language_clause}{intent_clause}"
    )


def _audio_prompt_rules(plan: dict) -> str:
    return (
        _audio_output_contract()
        + _audio_song_craft_brief()
        + _audio_artist_direction()
        + _audio_description_rules()
        + _audio_field_boundary_rules()
        + _language_style_rules(plan)
    )


def _audio_output_contract() -> str:
    return (
        "Write a release-ready song plan for the AceStep workflow. "
        "Return JSON only. No markdown. No prose outside JSON. "
        "Required top-level keys: genre_description,bpm,keyscale,seed,duration,lyrics_blocks. "
        "Required lyrics_blocks item keys: section,label,style,lines. "
        "lyrics_blocks.lines must be finished sung lyric lines only. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
    )


def _audio_song_craft_brief() -> str:
    return (
        "Write a full song, not a fragment. "
        "If there is a final chorus, keep section='chorus' and label it 'Final Chorus'. "
    )


def _audio_artist_direction() -> str:
    return ""


def _audio_description_rules() -> str:
    return (
        "genre_description is the AceStep tags text field. Write it in English as a short production brief starting with a genre label and colon. "
        "Treat the provided audio intent and hook intent as the source of truth. "
    )


def _audio_field_boundary_rules() -> str:
    return (
        "Keep fields separated. "
        "genre_description is production language only. "
        "lyrics_blocks.lines are sung lyrics only. "
        "Do not put planning notes, camera language, or placeholders inside lyrics. "
    )


def _language_style_rules(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    if lang == "ja":
        return (
            "Write fluent modern Japanese lyrics. "
            "Keep phrasing natural and singable. "
            "Use English sparingly and intentionally. "
        )
    if lang == "ko":
        return (
            "Write fluent modern Korean lyrics. "
            "Keep Hangul phrasing natural and singable. "
            "Use English only as a short intentional accent if needed. "
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


def _target_duration_clause(plan: dict) -> str:
    duration = int(plan.get("duration", 0) or 0)
    return f"Target duration={duration} sec. " if duration > 0 else ""


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
    duration = int(normalized.get("duration", 0) or 0)
    if duration > 0:
        return duration
    from ai_mv.engines.acestep_1_5_aio.policy import compute_duration_from_blocks, resolve_section_bars

    return compute_duration_from_blocks(
        normalized.get("lyrics_blocks", []),
        int(normalized.get("bpm", 0)),
        int(plan.get("beats_per_bar", 4)),
        resolve_section_bars({"section_bars": plan.get("section_bars", {})}),
    )
