from __future__ import annotations

from ai_mv.engines.acestep_1_5_aio.policy import preferred_songform_rows


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
        + _audio_line_budget_rules(plan)
        + _audio_conditioning_contract_rules(plan)
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
        "Treat lyrics_blocks as the future bracketed lyric markup skeleton that AceStep will receive. "
        "The exported lyrics may append a final [End] marker after the last block, so the final block must already feel like the true musical finish. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
        "label is the internal section header and must use the canonical English song labels only. "
    )


def _audio_song_craft_brief(plan: dict) -> str:
    ending = _ending_policy(plan)
    rules = [
        "Write a full song, not a fragment. ",
        "Prefer a commercially strong but artistically polished form, not a mechanical template. ",
        "Build the song around one dominant late-night city image and at most one or two supporting objects, instead of rotating through a long list of unrelated props. ",
        "Do not make Verse 2 feel like a copy-paste replay of Verse 1. ",
        "Let Verse 2 act like a lifted verse: keep the structure readable but raise the detail, melodic tension, lyrical angle, or arrangement energy slightly. ",
        "If you use a post-chorus, give it a real afterglow or rhythmic release function; do not insert one automatically if the chorus already resolves cleanly. ",
        "Make the final chorus unmistakably bigger or more complete than earlier choruses through lyric twist, melodic lift, harmony expansion, arrangement opening, or emotional escalation. ",
        "Avoid a formula where every return block repeats the same function with only new words. ",
        "Prefer one or two smart form evolutions over needless extra sections. ",
        "Make every section melodically and lyrically legible; do not output corrupted text, broken symbols, or unreadable character noise. ",
        "Favor concise, memorable lyric lines with a clean hook shape over vague impressionistic fragments. ",
        "Prefer plain readable diction over rare, ornate, or hard-to-parse character choices. ",
    ]
    if bool(ending.get("final_chorus_required", True)):
        rules.append("Use a distinct final return. Keep that block section='chorus' and label it 'Final Chorus'. ")
    else:
        rules.append("You may end without a labeled final chorus if the form resolves more cleanly that way. ")
    if bool(ending.get("outro_required", False)):
        rules.append("After the last chorus, include a final section='outro' block that clearly closes the song. Keep the outro very short and terminal rather than reopening the arrangement. ")
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
    rules.append(
        "Keep Intro instrumental-friendly by default: use no sung line or one very short opening line unless a stronger sung pickup is clearly necessary. "
    )
    return "".join(rules)


def _audio_artist_direction(plan: dict) -> str:
    ending = _ending_policy(plan)
    tags = ", ".join(str(x).strip() for x in ending.get("ending_tags", []) if str(x).strip())
    if not tags:
        return ""
    return f"Ending production intent={tags}. "


def _audio_line_budget_rules(plan: dict) -> str:
    budgets = plan.get("line_budgets", {}) if isinstance(plan.get("line_budgets", {}), dict) else {}
    if not budgets:
        return ""
    ordered = [
        "Intro",
        "Verse 1",
        "Verse 2",
        "Pre-Chorus",
        "Pre-Chorus 2",
        "Chorus",
        "Chorus 2",
        "Final Chorus",
        "Post-Chorus",
        "Bridge",
        "Outro",
    ]
    pairs = [f"{label}<= {int(budgets[label])} lines" for label in ordered if label in budgets]
    return (
        "Protect vocal breathing room. "
        "Do not overpack lyric blocks just because the section is musically large. "
        "Use these maximum line budgets unless a smaller count lands more cleanly: "
        + ", ".join(pairs)
        + ". "
        "Favor fewer, stronger lines over dense wording that leaves the singer no air. "
        "In clean-resolve songs, prefer a sparse Intro and a terminal Outro rather than full lyric density at both ends. "
    )


def _audio_conditioning_contract_rules(plan: dict) -> str:
    ending = _ending_policy(plan)
    ending_digest = _ending_policy_digest(ending)
    return (
        "AceStep tags should read like a compact English production brief, not a bag of loose keywords. "
        "Do not rely on artist-name shorthand such as 'in the style of' or celebrity comparisons; translate the sound into concrete production language instead. "
        "Build genre_description in this order when possible: mix texture, lead vocal profile, genre or groove identity, arrangement highlights, and ending behavior. "
        "Prefer concrete musical language such as synth bass, bright piano melody, live drums, warm pads, clipped guitar, or euphoric chorus lift over vague mood-only writing. "
        "Keep genre_description compact and radio-usable rather than long-form criticism. "
        "If bpm or keyscale are provided, treat them as fixed musical targets and do not describe a contradictory tempo feel or tonal center. "
        "Keep camera language, visual direction, and film-shot wording out of genre_description. "
        + (f"Ending contract={ending_digest}. " if ending_digest else "")
    )


def _audio_description_rules(plan: dict) -> str:
    ending = _ending_policy(plan)
    ending_tags = ", ".join(str(x).strip() for x in ending.get("ending_tags", []) if str(x).strip())
    ending_clause = f"Encode the ending behavior in genre_description using short production phrases such as {ending_tags}. " if ending_tags else ""
    return (
        "genre_description is the AceStep tags text field. Write it in English as a short production brief starting with a genre label and colon. "
        "Treat the provided audio intent and hook intent as the source of truth. "
        + ("Aim for a short Outro followed by a terminal [End] close. " if bool(ending.get("terminal_end_tag", False)) else "")
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
    intent = plan.get("director_brief_intent", {}) if isinstance(plan.get("director_brief_intent", {}), dict) else {}
    story_world = str(intent.get("story_world", "")).strip()
    world_core = str(intent.get("world_core", "")).strip()
    merged_avoid = _merged_avoid_text(intent)
    parts = [
        _profile_line("Audio intent", intent.get("audio_brief", "")),
        _profile_line("Hook intent", intent.get("audio_hook_brief", "")),
        _profile_line("Hook English fragments", ", ".join(str(x).strip() for x in plan.get("hook_english_fragments", []) if str(x).strip())),
        _profile_line("Visual intent", intent.get("visual_brief", "")),
        _profile_line("Story world", story_world),
        _profile_line("World core", world_core if world_core and world_core != story_world else ""),
        _profile_line("Payoff style", intent.get("payoff_style", "")),
        _profile_line("Outro feel", intent.get("outro_feel", "")),
        _profile_line("Character identity", intent.get("identity_core", "")),
        _profile_line("Avoid", merged_avoid),
    ]
    return "".join(parts)


def _profile_line(label: str, text: object) -> str:
    val = str(text).strip().rstrip(". ")
    return f"{label}={val}. " if val else ""


def _merged_avoid_text(intent: dict) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for raw in (intent.get("visual_negative", ""), intent.get("avoid", "")):
        text = str(raw).strip().rstrip(". ")
        if text and text not in seen:
            seen.add(text)
            parts.append(text)
    return " ".join(parts)


def _ending_policy(plan: dict) -> dict:
    return {
        "ending_mode": str(plan.get("ending_mode", "")).strip(),
        "terminal_end_tag": bool(plan.get("terminal_end_tag", False)),
        "final_chorus_required": bool(plan.get("final_chorus_required", False)),
        "outro_required": bool(plan.get("outro_required", False)),
        "ending_vocal_density": str(plan.get("ending_vocal_density", "")).strip(),
        "ending_tags": [
            str(item).strip()
            for item in plan.get("ending_tags", [])
            if str(item).strip()
        ]
        if isinstance(plan.get("ending_tags", []), list)
        else [],
    }


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
        "low": "Keep the final section sparse, ideally one short sung line and never more than two. ",
        "tail_only": "Keep the final section extremely brief, ideally a single short line or tail phrase. ",
    }.get(density, "")


def _ending_policy_digest(policy: dict) -> str:
    if not isinstance(policy, dict):
        return ""
    parts = [
        f"mode={str(policy.get('ending_mode', '')).strip()}",
        f"terminal_end_tag={bool(policy.get('terminal_end_tag', False))}",
        f"final_chorus_required={bool(policy.get('final_chorus_required', False))}",
        f"outro_required={bool(policy.get('outro_required', False))}",
        f"energy_drop={str(policy.get('ending_energy_drop', '')).strip()}",
        f"vocal_density={str(policy.get('ending_vocal_density', '')).strip()}",
    ]
    tags = [str(x).strip() for x in policy.get("ending_tags", []) if str(x).strip()] if isinstance(policy.get("ending_tags", []), list) else []
    if tags:
        parts.append(f"ending_tags={', '.join(tags)}")
    return "; ".join(part for part in parts if not part.endswith("="))
