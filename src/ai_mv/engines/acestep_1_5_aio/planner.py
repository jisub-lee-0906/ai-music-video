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
        + _audio_song_craft_brief(plan)
        + _audio_artist_direction(plan)
        + _audio_description_rules(plan)
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
        "All lyric lines must be valid readable text in the requested language, not mojibake, not corrupted Unicode, and not random symbol noise. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
    )


def _audio_song_craft_brief(plan: dict) -> str:
    ending = _ending_policy(plan)
    rules = [
        "Write a full song, not a fragment. "
        "Prefer a commercially strong but artistically polished form, not a mechanical template. "
        "Do not make Verse 2 feel like a copy-paste replay of Verse 1. "
        "Let Verse 2 act like a lifted verse: keep the structure readable but raise the detail, melodic tension, lyrical angle, or arrangement energy slightly. "
        "If you use a post-chorus, give it a real afterglow or rhythmic release function; do not insert one automatically if the chorus already resolves cleanly. "
        "Make the final chorus unmistakably bigger or more complete than earlier choruses through lyric twist, melodic lift, harmony expansion, arrangement opening, or emotional escalation. "
        "Avoid a formula where every return block repeats the same function with only new words. "
        "Prefer one or two smart form evolutions over needless extra sections. "
    ]
    if bool(ending.get("final_chorus_required", True)):
        rules.append("Use a distinct final return. Keep that block section='chorus' and label it 'Final Chorus'. ")
    else:
        rules.append("You may end without a labeled final chorus if the form resolves more cleanly that way. ")
    if bool(ending.get("outro_required", False)):
        rules.append("After the last chorus, include a final section='outro' block that clearly closes the song. ")
    else:
        rules.append("Do not force an outro if a decisive last chorus ending fits better. ")
    rules.append(
        "Only use post_chorus when the hook benefits from one extra tag, release tail, or rhythmic afterimage; otherwise move forward without it. "
    )
    rules.append(
        "If the song uses both Chorus 2 and Final Chorus, make the Final Chorus feel like a true payoff rather than a third copy of the same hook. "
    )
    rules.append(_ending_mode_rule(str(ending.get("ending_mode", ""))))
    rules.append(_ending_density_rule(str(ending.get("ending_vocal_density", ""))))
    return "".join(rules)


def _audio_artist_direction(plan: dict) -> str:
    ending = _ending_policy(plan)
    tags = ", ".join(str(x).strip() for x in ending.get("ending_tags", []) if str(x).strip())
    if not tags:
        return ""
    return f"Ending production intent={tags}. "


def _audio_description_rules(plan: dict) -> str:
    ending = _ending_policy(plan)
    ending_tags = ", ".join(str(x).strip() for x in ending.get("ending_tags", []) if str(x).strip())
    ending_clause = f"Encode the ending behavior in genre_description using short production phrases such as {ending_tags}. " if ending_tags else ""
    return (
        "genre_description is the AceStep tags text field. Write it in English as a short production brief starting with a genre label and colon. "
        "Treat the provided audio intent and hook intent as the source of truth. "
        + ending_clause
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
            "Every lyric line must look like valid modern Japanese text with readable kana or kanji, not broken symbols or corrupted characters. "
            "Prefer clear memorable phrases over opaque fragments. "
        )
    if lang == "ko":
        return (
            "Write fluent modern Korean lyrics. "
            "Keep Hangul phrasing natural and singable. "
            "Use English only as a short intentional accent if needed. "
            "Every lyric line must look like valid Hangul text, not broken symbols or corrupted characters. "
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
    escalation = intent.get("escalation_intent", {}) if isinstance(intent, dict) else {}
    parts = [
        _profile_line("Audio intent", audio.get("brief", "")),
        _profile_line("Hook intent", audio.get("hook_brief", "")),
        _profile_line("World intent", world.get("visual_intent", "")),
        _profile_line("Story world", world.get("story_world", "")),
        _profile_line("Payoff style", world.get("payoff_style", "")),
        _profile_line("Outro feel", escalation.get("outro_residue", "")),
        _profile_line("Audio ending policy", _ending_policy_digest(audio.get("ending_policy", {}))),
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
    _validate_ending_contract(plan, normalized)
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


def _ending_policy(plan: dict) -> dict:
    intent = plan.get("profile_intent", {}) if isinstance(plan.get("profile_intent", {}), dict) else {}
    audio = intent.get("audio_intent", {}) if isinstance(intent, dict) else {}
    policy = audio.get("ending_policy", {}) if isinstance(audio, dict) else {}
    return policy if isinstance(policy, dict) else {}


def _ending_mode_rule(mode: str) -> str:
    return {
        "hard_stop": "The ending should feel slammed shut, decisive, and non-fading. ",
        "clean_resolve": "The ending should resolve clearly and confidently without drifting. ",
        "glow_fade": "The ending should resolve with a graceful lingering glow and controlled fade. ",
        "bittersweet_tail": "The ending should leave a small emotional residue with a brief tail, not an abrupt cut. ",
        "anthem_lift": "The ending should feel uplifted and earned, with one final forward-moving release. ",
    }.get(mode, "")


def _ending_density_rule(density: str) -> str:
    return {
        "full": "The final section may keep a full vocal phrase count if it still lands decisively. ",
        "medium": "Keep the final section concise, usually shorter than a verse or chorus. ",
        "low": "Keep the final section sparse, usually one or two short sung lines. ",
        "tail_only": "Keep the final section extremely brief, ideally a single short line or tail phrase. ",
    }.get(density, "")


def _ending_policy_digest(policy: dict) -> str:
    if not isinstance(policy, dict):
        return ""
    parts = [
        f"mode={str(policy.get('ending_mode', '')).strip()}",
        f"final_chorus_required={bool(policy.get('final_chorus_required', False))}",
        f"outro_required={bool(policy.get('outro_required', False))}",
        f"energy_drop={str(policy.get('ending_energy_drop', '')).strip()}",
        f"vocal_density={str(policy.get('ending_vocal_density', '')).strip()}",
    ]
    tags = [str(x).strip() for x in policy.get("ending_tags", []) if str(x).strip()] if isinstance(policy.get("ending_tags", []), list) else []
    if tags:
        parts.append(f"ending_tags={', '.join(tags)}")
    return "; ".join(part for part in parts if not part.endswith("="))


def _validate_ending_contract(plan: dict, normalized: dict) -> None:
    ending = _ending_policy(plan)
    blocks = [row for row in normalized.get("lyrics_blocks", []) if isinstance(row, dict)]
    if not blocks:
        return
    if bool(ending.get("outro_required", False)):
        last_section = str(blocks[-1].get("section", "")).strip().lower()
        if last_section != "outro":
            raise RuntimeError("audio ending contract failed: outro_required but final block is not outro")
    if bool(ending.get("final_chorus_required", False)):
        choruses = [row for row in blocks if str(row.get("section", "")).strip().lower() == "chorus"]
        if not choruses:
            raise RuntimeError("audio ending contract failed: final_chorus_required but chorus is missing")
        last_chorus_label = str(choruses[-1].get("label", "")).strip().lower()
        if "final chorus" not in last_chorus_label:
            raise RuntimeError("audio ending contract failed: last chorus is not labeled Final Chorus")
    density = str(ending.get("ending_vocal_density", "")).strip().lower()
    if str(blocks[-1].get("section", "")).strip().lower() == "outro":
        line_count = len([str(x).strip() for x in blocks[-1].get("lines", []) if str(x).strip()])
        max_lines = {"tail_only": 1, "low": 2, "medium": 4}.get(density)
        if max_lines is not None and line_count > max_lines:
            raise RuntimeError(f"audio ending contract failed: outro too long for ending_vocal_density={density}")
