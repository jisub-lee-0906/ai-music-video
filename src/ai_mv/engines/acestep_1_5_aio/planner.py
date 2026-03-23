from __future__ import annotations

from ai_mv.core.output_paths import audio_prefix
from ai_mv.core.profile_brief import build_profile_intent
from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
    validate_audio_lyrics_quality,
)
from ai_mv.core.contracts.prompt_schema import audio_outline_schema
from ai_mv.engines.acestep_1_5_aio.policy import audio_policy, preferred_songform_rows
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
    labels_clause = _outline_label_clause_qwen(plan)
    return _audio_prompt_rules(plan) + (
        f"{_target_duration_clause(plan)}"
        f"{bpm_clause}{seed_clause}{tags_clause}{language_clause}{intent_clause}{labels_clause}"
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
        "label is the internal section header and must use the canonical English song labels only. "
    )


def _audio_song_craft_brief(plan: dict) -> str:
    ending = _ending_policy(plan)
    rules = [
        "Write a full song, not a fragment. "
        "Prefer a commercially strong but artistically polished form, not a mechanical template. "
        "Build the song around one dominant late-night city image and at most one or two supporting objects, instead of rotating through a long list of unrelated props. "
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
            "Keep lines easy to read at a glance. "
            "Use English sparingly and intentionally. "
            "Prefer clear city-night imagery and avoid untranslated English nouns. "
            "Keep the canonical English section labels exactly as provided in the outline. "
        )
    if lang == "ko":
        return (
            "Write fluent modern Korean lyrics. "
            "Keep Hangul phrasing natural, singable, and emotionally direct. "
            "Avoid translationese and awkward English noun leakage. "
            "Keep the canonical English section labels exactly as provided in the outline. "
        )
    if lang == "en":
        return (
            "Write fluent English lyrics with lyric-like cadence, not flat explanatory prose. "
            "Prefer concrete urban images and emotionally legible phrasing. "
            "Keep the canonical English section labels exactly as provided in the outline. "
        )
    return ""


def _outline_label_clause_qwen(plan: dict) -> str:
    rows = preferred_songform_rows()
    pairs = [f"{row['section']}=>{str(row['label']).strip()}" for row in rows]
    return (
        "Use these exact canonical English labels when those sections are present: "
        + ", ".join(pairs)
        + ". Do not invent alternative labels and do not translate the labels. "
    )


def _audio_lyrics_prompt(plan: dict, outline: dict) -> str:
    language_clause = _language_clause(plan)
    intent_clause = _intent_clause(plan)
    outline_text = _outline_text(outline)
    output_template = _outline_fill_template(outline)
    line_contract = _outline_line_contract(outline)
    chorus_contract = _chorus_rewrite_contract(outline)
    allowed_headers = " | ".join(
        f"[{str(block.get('label', '')).strip()}]"
        for block in outline.get("lyrics_blocks", [])
        if isinstance(block, dict) and str(block.get("label", "")).strip()
    )
    return (
        _audio_lyrics_output_contract()
        + _audio_lyrics_rules_qwen(plan)
        + f"{language_clause}{intent_clause}"
        + f"Locked outline:\n{outline_text}\n"
        + line_contract
        + chorus_contract
        + f"Output skeleton:\n{output_template}\n"
        + (f"Allowed headers only: {allowed_headers}. " if allowed_headers else "")
        +
        "Write plain text only. Do not output JSON. "
        "For each block, write the label in square brackets on its own line, then write exactly the required number of lyric lines, then a blank line. "
        "Replace every placeholder line in the output skeleton with one finished lyric line and preserve the exact total line count. "
        "Do not copy placeholder tokens such as <line 1> into the final answer. "
        "Keep the block order exactly the same as the outline. "
        "Copy each header verbatim from the locked outline. Do not invent or rename headers. "
        "Do not translate headers even when the lyric body is Japanese or Korean. "
        "Do not add commentary, numbering, bullets, code fences, or prose outside the lyrics. "
    )


def _audio_lyrics_output_contract() -> str:
    return (
        "Write finished sung lyrics for the locked song outline. "
        "Do not add or remove blocks. Do not rename labels. Do not change styles. "
    )


def _audio_lyrics_rules_qwen(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    retry_clause = _audio_retry_clause(plan)
    common = (
        "Every lyric line must be valid readable text in the requested language, not mojibake, not corrupted Unicode, and not random symbol noise. "
        "Keep the exact section skeleton, exact line count, and exact header text. "
        "Favor singable, emotionally legible lines over ornate wording. "
        "Choose one dominant song image for the chorus family and one or two supporting setup images for the verses. "
        "Do not keep introducing brand-new unrelated objects every section; deepen the same small image system instead. "
        "Do not pad the song with generic filler or duplicate weak phrases across sections. "
        "Outside of one intentional hook line, do not repeat a full lyric line in another block. "
        "Choose one short hook nucleus for the chorus family only, but that nucleus must be a short image fragment or phrase, not a full lyric sentence. "
        "If a hook nucleus returns, change the verb, surrounding object, or sentence ending so it feels like a variation rather than a copy. "
        "A hook nucleus should look like a small motif such as 'blue city', 'melted light', or 'cold key', not like a whole repeated line. "
        "Do not place the chorus hook nucleus inside Intro, Verse, or Pre-Chorus blocks. "
        "The opening setup must evolve as the song moves forward: Intro, Verse 1, Pre-Chorus, and Chorus should not recycle the same full line. "
        "Intro lines must never recur verbatim later in the song; later blocks may only transform the image into new sentences. "
        "Verse lines should add concrete images, tactile objects, visible motions, or emotional detail. "
        "Pre-chorus lines should raise anticipation and momentum. "
        "Chorus lines should deliver one memorable hook image or title-worthy phrase cleanly. "
        "Bridge lines should reframe the song with a wider system, memory, or emotional shift. "
        "Chorus 2 must keep the same emotional center as Chorus but change at least four full lines. "
        "Final Chorus must keep at most two reused lines from Chorus and rewrite the rest as the clearest payoff, warmest vow, or widest city-night resolution. "
        "Chorus 2 and Final Chorus should each introduce fresh nouns, verbs, or images instead of just paraphrasing the first chorus. "
        "Bad pattern: repeating the same weak stock phrase across Verse, Chorus, and Final Chorus. "
        "Good pattern: each section keeps one city-night motif but changes the angle, object, gesture, or emotional meaning. "
        f"{retry_clause}"
    )
    if lang == "ja":
        return common + (
            "Write fluent modern Japanese lyric lines only. "
            "Use natural hiragana, katakana, and common-use kanji. "
            "Do not leave any Latin alphabet words, romanized spellings, or English production terms in the final Japanese lyrics. "
            "Rewrite words like timetable, curb, platform, gate, or pocket into natural Japanese. "
            "Prefer polished adult city-pop diction with concrete images such as train glass, ticket gate, wet curb, vending glow, reflected neon, station clock, and apartment windows. "
            "Bad pattern: 光が揺れる, 夜が続く, 足音が響く repeated across multiple sections. "
            "Also avoid fallback lines like 鼓動が早くなる, もうすぐそこにある, このまま進んでいこう, 明日はまた新しい朝が来る unless a section absolutely demands that exact phrase once. "
            "Good pattern: 改札のガラスに青い街が流れる, 濡れた歩道へネオンが折り返す, 時計台の針だけが先に夜を越える. "
            "Avoid awkward katakana transliterations when natural Japanese wording exists. "
            "A good chorus should feel instantly singable and memorable on first listen, not like plain scene description. "
            "Keep the narrator intimate and elegant; avoid generic group-pop diction such as 僕ら unless the outline clearly demands a collective voice. "
            "Prefer one intimate narrator or scene-led gaze, not a generic collective anthem voice. "
            "Do not end multiple sections with the same generic hope, journey, or tomorrow line. "
            "Useful city-pop line shapes: 指先で鍵を返す, もう戻れない数を数える, 息を止めたまま一歩だけ出る, 溶けた光の輪が街を包む. "
            "If a chorus hook returns, do not repeat the exact same sentence such as もう戻れない数を静かに数える in multiple chorus-family blocks. "
            "Prefer tiny hook fragments such as 青い街, 溶けた光, 冷たい鍵, 雨の輪 instead of repeating a whole sentence. "
        )
    if lang == "ko":
        return common + (
            "Write fluent modern Korean lyric lines only. "
            "Use natural Hangul phrasing, natural particles, and singable endings. "
            "Avoid translationese, stiff written-language endings, and unnecessary English words. "
            "Prefer polished urban-pop diction with concrete images such as train window, ticket gate, wet curb, vending light, reflected neon, station clock, and apartment windows. "
            "Bad pattern: 빛이 흔들려, 밤이 계속돼, 발소리만 울려 repeated across many sections. "
            "Good pattern: 젖은 보도 위로 전광판 불빛이 접히고, 개찰구 유리에 늦은 숨이 닿고, 시계탑 그림자가 먼저 새벽으로 넘어간다. "
            "Keep the voice intimate, authored, and easy to sing. "
            "A good chorus should sound like a real hook someone would remember after one listen. "
            "Avoid idol-group filler diction like 우리를 반복해서 밀어 넣기보다, 장면을 살리는 1인칭 혹은 장면 중심 시선으로 써라. "
            "Do not end multiple sections with the same generic tomorrow, together, or keep-going slogan. "
        )
    return common + (
        "Write fluent English lyric lines only. "
        "Use lyric-like cadence, not flat explanatory prose. "
        "Prefer concrete city-night images, clear verbs, and memorable hook phrasing. "
        "Bad pattern: the light keeps moving, the night goes on, footsteps echo repeated across many sections. "
        "Good pattern: station glass catches the blue, wet pavement folds the neon back, a ticket warms inside my hand. "
        "Avoid overly literal scene description and avoid generic filler choruses. "
    )


def _audio_lyrics_system_prompt(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    lang_name = {"ja": "Japanese", "ko": "Korean", "en": "English"}.get(lang, "the requested language")
    return (
        "You are a precise lyric block writer. "
        "Follow the supplied block order and exact line counts without deviation. "
        "Return only the requested block headers and lyric lines. "
        "Do not add explanations, bullets, numbering, code fences, markdown, or notes. "
        "Do not omit blocks. Do not add extra lines. Header text must match the locked outline exactly. "
        "Headers stay in canonical English exactly as provided. Never translate a header. "
        "Count the required lyric lines silently before answering. "
        "Never output placeholder markers like <line 1>; replace them with real lyric lines. "
        f"Write every lyric line in natural {lang_name}. "
        "Make section functions clearly different from each other. "
        "If two lines feel too similar, rewrite the later line with a new image or action. "
        "Do not copy Chorus 1 into Chorus 2 or Final Chorus verbatim. "
        "Chorus 2 must feel like a lift. Final Chorus must feel like the emotional and lyrical culmination of the song. "
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


def _outline_line_contract(outline: dict) -> str:
    specs: list[str] = []
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        if not label:
            continue
        specs.append(f"[{label}]={int(block.get('line_count', 1))} lines")
    if not specs:
        return ""
    return "Exact line count contract: " + ", ".join(specs) + ". "


def _chorus_rewrite_contract(outline: dict) -> str:
    labels = [
        str(block.get("label", "")).strip()
        for block in outline.get("lyrics_blocks", [])
        if isinstance(block, dict)
    ]
    rules: list[str] = []
    if "Chorus" in labels and "Chorus 2" in labels:
        rules.append(
            "Chorus 2 must keep the emotional center of Chorus but change at least four full lyric lines so it reads like a lift, not a copy. "
        )
    if "Chorus" in labels and "Final Chorus" in labels:
        rules.append(
            "Final Chorus must not be a copy of Chorus. Keep at most two reused lines from Chorus and rewrite the rest as the clearest emotional payoff. "
        )
    if rules:
        rules.append(
            "If you accidentally repeat too much, rewrite Chorus 2 and Final Chorus before finishing. "
        )
    return "".join(rules)


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
    last_exc: Exception | None = None
    for attempt in range(4):
        attempt_plan = dict(plan)
        attempt_plan["audio_retry_attempt"] = attempt
        if last_exc is not None:
            attempt_plan["audio_retry_feedback"] = str(last_exc)
        try:
            normalized = _normalize_and_validate(config, attempt_plan)
            return normalized
        except RuntimeError as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("audio planning failed without a captured error")


def _normalize_and_validate(config: dict, plan: dict) -> dict:
    planned = _plan_with_llm(config, plan)
    normalized = normalize_audio_fields(planned)
    validate_audio_genre_description_language(normalized["genre_description"])
    validate_audio_lyrics_language(normalized["lyrics"], str(plan.get("language", "")).strip())
    validate_audio_lyrics_quality(normalized["lyrics_blocks"], str(plan.get("language", "")).strip())
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
    last_exc: Exception | None = None
    attempt_prompt = prompt
    for _ in range(3):
        outline = generate_structured(config, attempt_prompt, audio_outline_schema())
        normalized = _normalize_audio_outline(outline)
        try:
            _validate_outline_labels(plan, normalized)
            return normalized
        except RuntimeError as exc:
            last_exc = exc
            attempt_prompt = (
                prompt
                + f" Correction note: your previous outline failed validation with this exact error: {exc}. "
                + "Rewrite the entire outline from scratch and use only valid section labels."
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("audio outline generation failed without a captured error")


def _plan_lyrics_with_llm(config: dict, plan: dict, outline: dict) -> dict:
    completed: list[dict] = []
    for block in outline.get("lyrics_blocks", []):
        completed.append(_generate_lyrics_block(config, plan, outline, completed, dict(block)))
    return _merge_audio_outline_and_lyrics(outline, {"lyrics_blocks": completed})


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


def _validate_outline_labels(plan: dict, outline: dict) -> None:
    allowed = {str(row["label"]).strip() for row in preferred_songform_rows()}
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        if label and label not in allowed:
            raise RuntimeError(f"invalid section label: {label}")


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


def _generate_lyrics_block(config: dict, plan: dict, outline: dict, completed: list[dict], block: dict) -> dict:
    prompt = _audio_lyrics_block_prompt(plan, outline, completed, block)
    last_exc: Exception | None = None
    attempt_prompt = prompt
    for _ in range(4):
        filled = ""
        filled = generate_ollama_text(
            config,
            attempt_prompt,
            system=_audio_lyrics_block_system_prompt(plan, block),
            options=_lyrics_generation_options(config, plan, block),
        )
        try:
            lines = _parse_audio_lyrics_block_lines(block, filled)
            candidate = {
                "section": str(block.get("section", "")).strip(),
                "label": str(block.get("label", "")).strip(),
                "style": str(block.get("style", "")).strip(),
                "lines": lines,
            }
            _validate_generated_block(plan, completed, candidate)
            return candidate
        except RuntimeError as exc:
            last_exc = exc
            previous_attempt = "\n".join(line.strip() for line in str(filled).splitlines() if line.strip())
            attempt_prompt = (
                prompt
                + f"\nCorrection note: your previous answer failed validation with this exact error: {exc}. "
                + (f"\nPrevious invalid attempt:\n{previous_attempt}\n" if previous_attempt else "")
                + f"Rewrite only the body lines for [{str(block.get('label', '')).strip()}] and output exactly {int(block.get('line_count', 1))} lines."
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("audio lyrics block fill failed without a captured error")


def _audio_lyrics_block_prompt(plan: dict, outline: dict, completed: list[dict], block: dict) -> str:
    chorus_contract = _chorus_rewrite_contract(outline)
    label = str(block.get("label", "")).strip()
    line_count = int(block.get("line_count", 1))
    block_constraints = _current_block_constraints(completed, block)
    return (
        _audio_lyrics_rules_qwen(plan)
        + f"{_language_clause(plan)}{_intent_clause(plan)}"
        + f"Current block=[{label}] section={str(block.get('section', '')).strip()} style={str(block.get('style', '')).strip()} line_count={line_count}. "
        + chorus_contract
        + block_constraints
        + "Write only the lyric body for the current block. "
        + "Do not output the header. Do not output numbering, bullets, explanations, or blank filler lines. "
        + f"Output exactly {line_count} finished lyric lines, one per line. "
        + "Do not copy earlier blocks verbatim. Keep narrative continuity through shared world and emotion, not through recycled lines. "
        + "Before answering, silently check every line against earlier blocks and rewrite any exact match unless it is the one intentional hook nucleus. "
    )


def _audio_lyrics_block_system_prompt(plan: dict, block: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    lang_name = {"ja": "Japanese", "ko": "Korean", "en": "English"}.get(lang, "the requested language")
    label = str(block.get("label", "")).strip()
    line_count = int(block.get("line_count", 1))
    return (
        f"Write only the {line_count} lyric lines for [{label}]. "
        f"Write every line in natural {lang_name}. "
        "Do not output the section header. Do not output any prose outside the lyric lines. "
        "Keep each line concise, singable, image-rich, and easy to remember on first listen. "
        "Avoid writing two lines that say the same thing with only tiny wording changes. "
        "Before you finish, compare the lines against earlier sections in memory and rewrite any exact duplicate unless it is a single intentional hook line. "
        "Do not merge two lines into one. Do not exceed the requested line count. "
    )


def _parse_audio_lyrics_block_lines(block: dict, text: str) -> list[str]:
    lines = [line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    out = [line for line in lines if line]
    if any(line.startswith("[") and line.endswith("]") for line in out):
        raise RuntimeError("audio lyrics block output contained a forbidden header")
    expected = int(block.get("line_count", 1))
    if len(out) != expected:
        raise RuntimeError(f"audio lyrics fill line count mismatch under [{str(block.get('label', '')).strip()}]")
    return out


def _current_block_constraints(completed: list[dict], block: dict) -> str:
    label = str(block.get("label", "")).strip()
    intro = next((row for row in completed if str(row.get("label", "")).strip() == "Intro"), None)
    verse_1 = next((row for row in completed if str(row.get("label", "")).strip() == "Verse 1"), None)
    pre_1 = next((row for row in completed if str(row.get("label", "")).strip() == "Pre-Chorus"), None)
    chorus = next((row for row in completed if str(row.get("label", "")).strip() == "Chorus"), None)
    role_rules = {
        "Intro": "Intro should set the scene with one or two clean city-night images and no chorus-style payoff. ",
        "Verse 1": "Verse 1 should establish concrete city details, tactile objects, visible gestures, and motion. ",
        "Pre-Chorus": "Pre-Chorus should raise anticipation and momentum without repeating the coming hook. ",
        "Chorus": "Chorus should establish the central hook image in its clearest, most memorable, and most singable form. ",
        "Verse 2": "Verse 2 should stay in the same world but use different objects, gestures, or observations from Verse 1 and feel slightly closer to the heart. ",
        "Pre-Chorus 2": "Pre-Chorus 2 should feel like a lift from the first pre-chorus, not a copy. ",
        "Bridge": "Bridge should reframe the song with a new perspective, memory, or wider city/system image. ",
        "Final Chorus": "Final Chorus should sound like the emotional answer, clearest payoff, and most satisfying final resolution of the song. ",
        "Outro": "Outro should leave one last residue image and avoid restating the full chorus. ",
    }
    base = role_rules.get(label, "")
    if label == "Verse 1" and intro:
        intro_lines = "; ".join(str(line).strip() for line in intro.get("lines", []) if str(line).strip())
        return base + (
            "Do not simply expand the Intro by repeating its exact image sentence. "
            "Keep the same night and same world, but move from the opening image into new objects, surfaces, or gestures. "
            "Every Verse 1 line should push the camera one step deeper into the scene than Intro did. "
            "Verse 1 must not use the future chorus hook line; it should prepare the world, not arrive at the refrain. "
            "The first two Verse 1 lines must not repeat or lightly paraphrase the Intro lines; they should introduce different objects, actions, or surfaces immediately. "
            f"Existing Intro lines to avoid copying verbatim: {intro_lines}. "
        )
    if label == "Pre-Chorus" and verse_1:
        verse_lines = "; ".join(str(line).strip() for line in verse_1.get("lines", []) if str(line).strip())
        return base + (
            "Pre-Chorus must not restate Verse 1 line by line. "
            "It should compress the scene into anticipation, breath, timing, or a small turn before the hook. "
            "Avoid restating the same object stack from Verse 1; narrow it into tension or threshold instead. "
            "Pre-Chorus must not state the future chorus hook sentence yet. "
            f"Existing Verse 1 lines to avoid copying verbatim: {verse_lines}. "
        )
    if label == "Chorus" and pre_1:
        pre_lines = "; ".join(str(line).strip() for line in pre_1.get("lines", []) if str(line).strip())
        return base + (
            "Chorus must feel like the first true arrival of the hook, not a copy of the Pre-Chorus. "
            "Keep one hook nucleus if needed, but the section should widen the image and make it more memorable than the setup blocks. "
            "The most memorable line of the song should appear here first, not earlier. "
            "Do not copy any Intro line or Verse 1 line verbatim into Chorus; transform the motif into a new refrain sentence. "
            f"Existing Pre-Chorus lines to avoid copying verbatim: {pre_lines}. "
        )
    if label == "Verse 2" and verse_1:
        verse_lines = "; ".join(str(line).strip() for line in verse_1.get("lines", []) if str(line).strip())
        return base + (
            "Do not paraphrase Verse 1 line by line. "
            "Keep the same city and same night, but move to different objects, gestures, surfaces, or thoughts. "
            f"Existing Verse 1 lines to avoid copying verbatim: {verse_lines}. "
        )
    if label == "Pre-Chorus 2" and pre_1:
        pre_lines = "; ".join(str(line).strip() for line in pre_1.get("lines", []) if str(line).strip())
        return base + (
            "Pre-Chorus 2 must not repeat Pre-Chorus 1. "
            "It should tighten the breath, timing, or anticipation in a new way before the lift into Chorus 2. "
            "Do not reuse the first pre-chorus threshold setup. Instead, make this block about countdown, decision, body tension, or a last-second shift before the hook opens. "
            "Use a new body cue, a new time-pressure detail, or a new inner decision rather than the same setup lines. "
            "Pre-Chorus 2 must still stop short of the chorus hook sentence. "
            "Do not keep the same line order, same sentence skeleton, or same opening phrase as Pre-Chorus 1. "
            "Make Pre-Chorus 2 feel like a second intake of breath, not a replay. "
            "If Pre-Chorus 1 watched the scene, Pre-Chorus 2 should choose, brace, count down, or step. "
            "Good pattern for Pre-Chorus 2: 指先で鍵を返す / もう戻れない数を数える / 息を止めたまま一歩だけ出る. "
            "Also good: もう戻れない数を数える / 息を止めたまま一歩だけ出る / 次の駅へ向かう鼓動が静かに脈打つ. "
            "Strong mini-example for Pre-Chorus 2 tone: 指先で鍵を返す / もう戻れない数を数える / 息を止めたまま一歩だけ出る / 次の駅へ向かう鼓動が静かに脈打つ. "
            "Bad pattern for Pre-Chorus 2: reusing the same threshold image and same calm setup from the first pre-chorus. "
            f"Existing Pre-Chorus lines to avoid copying verbatim: {pre_lines}. "
        )
    if label == "Chorus 2" and chorus:
        chorus_lines = "; ".join(str(line).strip() for line in chorus.get("lines", []) if str(line).strip())
        return base + (
            "Chorus 2 must keep the same emotional center as Chorus but must not copy any Chorus line verbatim. "
            "Use a new angle, new verbs, or wider city details while preserving the hook feeling and making the section feel more lifted than Chorus. "
            "At least half of the lines should contain nouns or images that did not appear in Chorus 1. "
            "Do not fall back to generic uplift lines; keep the section specific to this song's city objects and gestures. "
            "Only one short hook fragment may be echoed; the surrounding lines must be newly written. "
            "If you echo a hook fragment, rewrite the sentence around it with a different verb or different object. "
            "Good pattern for Chorus 2: the chorus hook returns, but the city image widens through new objects like station signs, puddle rings, sleeve wind, or umbrella bones. "
            "Also good: 改札の向こうで明かりが揺れる / 濡れた縁石に傘骨が映る / 溶けた光の輪が街を包む. "
            "Strong mini-example for Chorus 2 tone: 改札の向こうで明かりが揺れる / 濡れた縁石に傘骨が映る / 溶けた光の輪が街を包む / 袖の風が冷たい空気を運ぶ. "
            "Bad pattern for Chorus 2: the same chorus lines reappear in a different order with only tiny wording changes. "
            f"Forbidden verbatim Chorus lines: {chorus_lines}. "
        )
    if label == "Final Chorus" and chorus:
        chorus_lines = "; ".join(str(line).strip() for line in chorus.get("lines", []) if str(line).strip())
        return base + (
            "Final Chorus must feel like the clearest payoff. "
            "Reuse at most two short hook lines from Chorus and rewrite all other lines with stronger closure, warmer commitment, or wider imagery. "
            "It should feel larger than Chorus 1 not by saying the same thing louder, but by resolving the city image, relationship, or promise more completely. "
            "Do not end in generic hope or generic forward-motion slogans; land on this song's own images. "
            "If Chorus 1 used one hook line, keep only that nucleus and rebuild the rest of the section around a fuller ending image. "
            "Do not reuse the exact Chorus 2 hook sentence in Final Chorus; intensify it or resolve it into a new sentence. "
            f"Existing Chorus lines to avoid copying verbatim: {chorus_lines}. "
        )
    return base


def _validate_generated_block(plan: dict, completed: list[dict], block: dict) -> None:
    label = str(block.get("label", "")).strip()
    chorus = next((row for row in completed if str(row.get("label", "")).strip() == "Chorus"), None)
    lang = str(plan.get("language", "")).strip().lower()
    if not chorus:
        return
    shared = _shared_lyric_line_count(chorus, block)
    if label == "Chorus 2":
        limit = max(0, len(chorus.get("lines", [])) - 4)
        if lang == "en":
            limit = max(limit, len(chorus.get("lines", [])) // 2 + 1)
        if shared > limit:
            raise RuntimeError("audio lyrics quality mismatch: Chorus 2 repeats Chorus too closely")
    if label == "Final Chorus":
        limit = max(2, len(chorus.get("lines", [])) // 2)
        if lang == "en":
            limit = max(limit, len(chorus.get("lines", [])) - 2)
        if shared > limit:
            raise RuntimeError("audio lyrics quality mismatch: Final Chorus repeats Chorus too closely")


def _shared_lyric_line_count(left: dict, right: dict) -> int:
    a = {_normalize_lyric_line(line) for line in left.get("lines", []) if str(line).strip()}
    b = {_normalize_lyric_line(line) for line in right.get("lines", []) if str(line).strip()}
    return len(a & b)


def _normalize_lyric_line(text: object) -> str:
    return " ".join(str(text).strip().lower().split())


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


def _lyrics_generation_options(config: dict, plan: dict, block: dict | None = None) -> dict:
    integrations = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integrations.get("ollama_lyrics_options", {}) if isinstance(integrations, dict) else {}
    options = dict(raw) if isinstance(raw, dict) else {}
    lang = str(plan.get("language", "")).strip().lower()
    label = str(block.get("label", "")).strip() if isinstance(block, dict) else ""
    retry_attempt = int(plan.get("audio_retry_attempt", 0) or 0)
    if not options:
        options = {"temperature": 0.2, "top_p": 0.85, "repeat_penalty": 1.15}
    if lang in {"ja", "ko"}:
        options["temperature"] = min(float(options.get("temperature", 0.2)), 0.1)
        options["top_p"] = min(float(options.get("top_p", 0.85)), 0.8)
        options["repeat_penalty"] = max(float(options.get("repeat_penalty", 1.15)), 1.18)
    if label in {"Pre-Chorus 2", "Chorus 2", "Final Chorus"}:
        options["temperature"] = max(float(options.get("temperature", 0.2)), 0.28)
        options["top_p"] = max(float(options.get("top_p", 0.85)), 0.92)
        options["repeat_penalty"] = max(float(options.get("repeat_penalty", 1.15)), 1.24)
    if retry_attempt > 0:
        options["temperature"] = min(0.45, float(options.get("temperature", 0.2)) + 0.05 * retry_attempt)
        options["top_p"] = min(0.97, float(options.get("top_p", 0.85)) + 0.03 * retry_attempt)
        options["repeat_penalty"] = max(float(options.get("repeat_penalty", 1.15)), 1.24 + 0.03 * retry_attempt)
    return options


def _audio_retry_clause(plan: dict) -> str:
    attempt = int(plan.get("audio_retry_attempt", 0) or 0)
    feedback = str(plan.get("audio_retry_feedback", "")).strip()
    if attempt <= 0:
        return ""
    clause = (
        f"This is rewrite attempt {attempt + 1}. "
        "Regenerate the song from scratch with fresher section wording, less reuse, and clearer separation between setup blocks and chorus-family blocks. "
    )
    if feedback:
        clause += f"Previous attempt failed with this exact issue: {feedback}. "
    return clause
