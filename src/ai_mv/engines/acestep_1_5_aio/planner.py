from __future__ import annotations

from ai_mv.core.output_paths import audio_prefix
from ai_mv.core.profile_brief import build_profile_intent
from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
)
from ai_mv.core.contracts.prompt_schema import audio_outline_schema
from ai_mv.engines.acestep_1_5_aio.policy import audio_policy
from ai_mv.infra.codex_cli_client import generate_structured
from ai_mv.infra.ollama_client import generate_text as generate_ollama_text


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
    return _audio_outline_prompt(plan)


def _plan_with_llm(config: dict, plan: dict) -> dict:
    outline = _plan_outline_with_llm(config, plan)
    return _plan_lyrics_with_llm(config, plan, outline)


def _audio_prompt(plan: dict) -> str:
    return _audio_outline_prompt(plan)


def _audio_outline_prompt(plan: dict) -> str:
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
        _audio_outline_output_contract()
        + _audio_song_craft_brief(plan)
        + _audio_artist_direction(plan)
        + _audio_description_rules(plan)
        + _audio_field_boundary_rules()
        + _language_style_rules(plan)
    )


def _audio_outline_output_contract() -> str:
    return (
        "Write a release-ready song plan for the AceStep workflow. "
        "Return JSON only. No markdown. No prose outside JSON. "
        "Required top-level keys: genre_description,bpm,keyscale,seed,duration,lyrics_blocks. "
        "Required lyrics_blocks item keys: section,label,style,line_count. "
        "For this planning step, do not write lyric lines yet. "
        "line_count must be the exact number of sung lyric lines wanted for that block. "
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
        "Make every section melodically and lyrically legible; do not output corrupted text, broken symbols, or unreadable character noise. "
        "Favor concise, memorable lyric lines with a clean hook shape over vague impressionistic fragments. "
        "Prefer plain readable diction over rare, ornate, or hard-to-parse character choices. "
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
        "lyrics_blocks in the planning step describe structure only. "
        "Do not put planning notes, camera language, or placeholders inside labels or style fields. "
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
            "Prefer common modern Japanese wording with natural hiragana, katakana, and common-use kanji. "
            "Do not invent unreadable compounds, corrupted glyph strings, or mixed-script noise. "
            "If a line becomes visually messy, rewrite it in simpler Japanese. "
            "Bad example: broken mixed glyph noise or unreadable symbol soup. "
            "Good example: short, singable, emotionally clear Japanese lines that can be read at a glance. "
        )
    if lang == "ko":
        return (
            "Write fluent modern Korean lyrics. "
            "Keep Hangul phrasing natural and singable. "
            "Use English only as a short intentional accent if needed. "
            "Every lyric line must look like valid Hangul text, not broken symbols or corrupted characters. "
            "If a line becomes visually messy, rewrite it in simpler Korean. "
        )
    return ""


def _audio_lyrics_prompt(plan: dict, outline: dict) -> str:
    language_clause = _language_clause(plan)
    intent_clause = _intent_clause(plan)
    outline_text = _outline_text(outline)
    output_template = _outline_fill_template(outline)
    allowed_headers = " | ".join(
        f"[{str(block.get('label', '')).strip()}]"
        for block in outline.get("lyrics_blocks", [])
        if isinstance(block, dict) and str(block.get("label", "")).strip()
    )
    return (
        _audio_lyrics_output_contract()
        + _audio_lyrics_rules(plan)
        + f"{language_clause}{intent_clause}"
        + f"Locked outline:\n{outline_text}\n"
        + f"Output skeleton:\n{output_template}\n"
        + (f"Allowed headers only: {allowed_headers}. " if allowed_headers else "")
        +
        "Write plain text only. Do not output JSON. "
        "For each block, write the label in square brackets on its own line, then write exactly the required number of lyric lines, then a blank line. "
        "Replace every placeholder line in the output skeleton with one finished lyric line and preserve the exact total line count. "
        "Do not copy placeholder tokens such as <line 1> into the final answer. "
        "Keep the block order exactly the same as the outline. "
        "Copy each header verbatim from the locked outline. Do not invent or rename headers. "
        "Do not add commentary, numbering, bullets, code fences, or prose outside the lyrics. "
    )


def _audio_lyrics_output_contract() -> str:
    return (
        "Write finished sung lyrics for the locked song outline. "
        "Do not add or remove blocks. Do not rename labels. Do not change styles. "
    )


def _audio_lyrics_rules(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    common = (
        "Every lyric line must be valid readable text in the requested language, not mojibake, not corrupted Unicode, and not random symbol noise. "
        "If you cannot produce a strong line, choose simpler clear words in the requested language instead of broken text. "
        "Favor singable, emotionally legible, hook-friendly lines over ornate wording. "
        "Do not pad the song with generic filler lines that repeat the same weak idea. "
        "Avoid overusing patterns like 'light sways', 'night continues', 'voice is heard', or other empty stock phrases in multiple blocks. "
        "Verse lines should introduce concrete images, motions, or emotional details instead of repeating one vague image. "
        "Only the chorus may deliberately reuse a hook line, and even then keep the rest of the chorus lines fresh. "
        "Do not let Verse 2 recycle Verse 1 wording unless a hook is intentionally echoed. "
        "Make the final chorus feel more resolved or more intense than Chorus 1. "
        "Section roles must differ: intro sets the scene, verses add detail, pre-chorus raises anticipation, chorus delivers the hook, bridge reframes or opens the meaning, outro leaves one last image. "
        "Do not make every section say the same thing with minor wording changes. "
    )
    if lang == "ja":
        return common + (
            "Write fluent modern Japanese lyric lines only. "
            "Use natural hiragana, katakana, and common-use kanji. "
            "Do not invent unreadable compounds, mixed-script gibberish, or corrupted glyph strings. "
            "If a line becomes visually messy, rewrite it in simpler Japanese immediately. "
            "Write polished city-pop lyrics with adult tone, urban imagery, and memorable but readable diction. "
            "Prefer distinct concrete images such as train glass, ticket gate, wet curb, timetable glow, vending light, or reflected neon over abstract repetition. "
            "Bad pattern: many lines ending with the same weak verb like 続く or 揺れる without new meaning. "
            "Good pattern: each line adds one new image, gesture, or emotional shift while staying singable. "
            "Bad pattern: repeated lines like 光が揺れる, 夜が続く, 足音が響く across multiple sections without a new twist. "
            "Good pattern: each section keeps one city-night motif but changes the angle, object, gesture, or emotional meaning. "
            "Pre-chorus lines should feel like momentum and anticipation, not static description. "
            "Bridge lines should reveal a larger system, memory, or emotional turn rather than repeating the chorus hook. "
            "Final Chorus may reuse one hook line, but at least half of its lines should expand or intensify the image set. "
            "Do not use awkward katakana transliterations for simple words when normal Japanese wording exists. "
            "Avoid strange spellings like ポッケット; use natural Japanese such as ポケット. "
            "Do not leave English words like curb in the lyrics; express them naturally in Japanese such as 縁石 or curb-like wording in Japanese. "
            "Chorus 2 and Final Chorus must not be exact copies of Chorus 1. "
            "At least four lines in Final Chorus should be newly written or clearly intensified relative to Chorus 1. "
        )
    if lang == "ko":
        return common + (
            "Write fluent modern Korean lyric lines only. "
            "Use natural Hangul phrasing and keep lines easy to sing. "
            "If a line becomes visually messy, rewrite it in simpler Korean immediately. "
            "Prefer distinct concrete urban images and avoid repeating the same weak ending or stock phrase across many lines. "
        )
    return common + "Write fluent lyric lines only in the requested language. "


def _audio_lyrics_system_prompt(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    lang_name = {"ja": "Japanese", "ko": "Korean"}.get(lang, "the requested language")
    return (
        "You are a precise lyric block writer. "
        "Follow the supplied block order and exact line counts without deviation. "
        "Return only the requested block headers and lyric lines. "
        "Do not add explanations, apologies, bullets, numbering, code fences, markdown, or notes. "
        "Do not omit blocks. Do not add extra lines. "
        "Header text must match the locked outline exactly. "
        "Count the required lyric lines silently before answering. "
        "Never output placeholder markers like <line 1>; replace them with real lyric lines. "
        f"Write every lyric line in natural {lang_name}. "
        "Keep exact hook reuse limited to chorus sections. "
        "Avoid generic filler, repetitive weak verbs, and near-duplicate lines across the song. "
        "Prefer one clear image or emotional move per line. "
        "Make section functions clearly different from each other. "
        "If two lines feel too similar, rewrite the later line with a new image or action. "
        "For Japanese output, prefer natural contemporary Japanese wording over awkward loanword spellings. "
        "Do not copy Chorus 1 into Chorus 2 or Final Chorus verbatim. "
        "If a line is weak, simplify it instead of adding commentary. "
    )


def _outline_text(outline: dict) -> str:
    rows: list[str] = []
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        rows.append(
            f"[{str(block.get('label', '')).strip()}] section={str(block.get('section', '')).strip()} style={str(block.get('style', '')).strip()} line_count={int(block.get('line_count', 1))}"
        )
    return "\n".join(rows)


def _outline_fill_template(outline: dict) -> str:
    rows: list[str] = []
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        if not label:
            continue
        rows.append(f"[{label}]")
        line_count = max(1, int(block.get("line_count", 1)))
        for idx in range(1, line_count + 1):
            rows.append(f"<line {idx}>")
        rows.append("")
    return "\n".join(rows).strip()


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
    validate_audio_genre_description_language(normalized["genre_description"])
    validate_audio_lyrics_language(normalized["lyrics"], str(plan.get("language", "")).strip())
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


def _plan_outline_with_llm(config: dict, plan: dict) -> dict:
    prompt = _audio_outline_prompt(plan)
    outline = generate_structured(config, prompt, audio_outline_schema())
    return _normalize_audio_outline(outline)


def _plan_lyrics_with_llm(config: dict, plan: dict, outline: dict) -> dict:
    prompt = _audio_lyrics_prompt(plan, outline)
    last_exc: Exception | None = None
    attempt_prompt = prompt
    for _ in range(3):
        filled = generate_ollama_text(
            config,
            attempt_prompt,
            system=_audio_lyrics_system_prompt(plan),
            options={"temperature": 0.1, "top_p": 0.8},
        )
        try:
            return _merge_audio_outline_and_lyrics(outline, _parse_audio_lyrics_text(outline, filled))
        except RuntimeError as exc:
            last_exc = exc
            attempt_prompt = (
                prompt
                + f"\nCorrection note: your previous answer failed validation with this exact error: {exc}. "
                + "Rewrite the entire lyrics output from scratch and satisfy every header and exact line count."
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("audio lyrics fill failed without a captured error")


def _normalize_audio_outline(raw: dict) -> dict:
    blocks = []
    for row in raw.get("lyrics_blocks", []):
        if not isinstance(row, dict):
            continue
        blocks.append(
            {
                "section": str(row.get("section", "")).strip(),
                "label": str(row.get("label", "")).strip(),
                "style": str(row.get("style", "")).strip(),
                "line_count": max(1, int(row.get("line_count", 1))),
            }
        )
    return {
        "genre_description": str(raw.get("genre_description", "")).strip(),
        "bpm": int(raw.get("bpm", 0)),
        "keyscale": str(raw.get("keyscale", "")).strip(),
        "seed": int(raw.get("seed", 0)),
        "duration": int(raw.get("duration", 0)),
        "lyrics_blocks": blocks,
    }


def _merge_audio_outline_and_lyrics(outline: dict, filled: dict) -> dict:
    keyed = [
        row for row in filled.get("lyrics_blocks", []) if isinstance(row, dict)
    ]
    if len(keyed) != len(outline.get("lyrics_blocks", [])):
        raise RuntimeError("audio lyrics fill block count mismatch")
    blocks: list[dict] = []
    for spec, row in zip(outline.get("lyrics_blocks", []), keyed):
        section = str(row.get("section", "")).strip()
        label = str(row.get("label", "")).strip()
        style = str(row.get("style", "")).strip()
        if section != spec["section"] or label != spec["label"] or style != spec["style"]:
            raise RuntimeError("audio lyrics fill diverged from locked outline")
        lines = [str(x).strip() for x in row.get("lines", []) if str(x).strip()]
        if len(lines) != int(spec["line_count"]):
            raise RuntimeError("audio lyrics fill line count mismatch")
        blocks.append({"section": section, "label": label, "style": style, "lines": lines})
    return {
        "genre_description": outline["genre_description"],
        "bpm": outline["bpm"],
        "keyscale": outline["keyscale"],
        "seed": outline["seed"],
        "duration": outline["duration"],
        "lyrics_blocks": blocks,
    }


def _parse_audio_lyrics_text(outline: dict, text: str) -> dict:
    expected = [block for block in outline.get("lyrics_blocks", []) if isinstance(block, dict)]
    lines = [line.rstrip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    idx = 0
    parsed: list[dict] = []
    for block in expected:
        label = str(block.get("label", "")).strip()
        header = f"[{label}]"
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines) or lines[idx].strip() != header:
            raise RuntimeError(f"audio lyrics fill missing header: {header}")
        idx += 1
        block_lines: list[str] = []
        while idx < len(lines) and len(block_lines) < int(block.get("line_count", 1)):
            cur = lines[idx].strip()
            idx += 1
            if not cur:
                continue
            if cur.startswith("[") and cur.endswith("]"):
                raise RuntimeError(f"audio lyrics fill line count mismatch under {header}")
            block_lines.append(cur)
        if len(block_lines) != int(block.get("line_count", 1)):
            raise RuntimeError(f"audio lyrics fill line count mismatch under {header}")
        parsed.append(
            {
                "section": str(block.get("section", "")).strip(),
                "label": label,
                "style": str(block.get("style", "")).strip(),
                "lines": block_lines,
            }
        )
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines):
        raise RuntimeError("audio lyrics fill produced extra trailing content")
    return {"lyrics_blocks": parsed}


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
