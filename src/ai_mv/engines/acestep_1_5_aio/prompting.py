from __future__ import annotations

from ai_mv.engines.acestep_1_5_aio.policy import preferred_songform_rows


def _audio_prompt(plan: dict) -> str:
    return _audio_outline_prompt(plan)


def _audio_outline_prompt(plan: dict) -> str:
    return (
        _audio_prompt_rules(plan)
        + _target_duration_clause(plan)
        + _target_bpm_clause(plan)
        + f"Seed={int(plan.get('seed', 31))}. "
        + _language_clause(plan)
        + _intent_clause(plan)
        + _outline_label_clause_qwen(plan)
    )


def _audio_prompt_rules(plan: dict) -> str:
    return (
        _audio_outline_output_contract()
        + _audio_conditioning_contract_rules(plan)
        + _audio_songform_rules(plan)
        + _audio_line_budget_rules(plan)
        + _language_style_rules(plan)
    )


def _audio_outline_output_contract() -> str:
    return (
        "Plan an AceStep song as strict JSON only. "
        "Return keys genre_description,bpm,keyscale,seed,duration,lyrics_blocks. "
        "Each lyrics_blocks item must contain section,label,style,role,change,line_count. "
        "Do not write lyric lines in this step. "
        "line_count may be 0 only for Intro or Outro. "
        "The final render format is [tags], then bracketed lyrics, then [Outro], then [end]. "
        "Use only these section values: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
        "Use canonical English labels only. "
    )


def _audio_conditioning_contract_rules(plan: dict) -> str:
    return (
        "genre_description is the future [tags] block. "
        "Write it in English as one compact production paragraph starting with a genre label and colon. "
        "Include core instruments, arrangement energy, and vocal character. "
        "Do not use artist references, camera language, or visual wording. "
        "Treat Audio intent as the source of truth for the song's emotional meaning and progression; genre and voice only shape presentation. "
        "If bpm is not fixed, choose it from genre, line density, and breathing room. "
    )


def _audio_songform_rules(plan: dict) -> str:
    ending = _ending_policy(plan)
    rules = [
        "Write a full song, not a fragment. ",
        "Keep a clear arc across the song: early sections establish the state, middle sections develop or tighten it, and later sections resolve or release it. ",
        "Use a songform that fits the genre and duration instead of forcing one fixed template. ",
        "For each section, role should say what that section must do, and change should say what becomes different from the previous section. ",
        "Use Chorus 2 only if it is clearly needed. ",
        "Do not make Verse 2 a copy of Verse 1. ",
        "If you use Final Chorus, make it feel like an answer, not a repeat. ",
        "Keep Intro and Outro instrumental unless a very short sung line is clearly necessary. ",
    ]
    if bool(ending.get("final_chorus_required", False)):
        rules.append("Use a distinct final return labeled Final Chorus. ")
    if bool(ending.get("outro_required", False)):
        rules.append("If you include Outro, keep it very short and terminal. ")
    return "".join(rules)


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
    pairs = [f"{label}<= {int(budgets[label])}" for label in ordered if label in budgets]
    return "Respect these maximum line counts: " + ", ".join(pairs) + ". Prefer fewer stronger lines. "


def _language_style_rules(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    if lang == "ja":
        return "Write fluent modern Japanese lyrics later. Keep them natural, compact, and singable. "
    if lang == "ko":
        return "Write fluent modern Korean lyrics later. Keep them short, singable, and direct. "
    if lang == "en":
        return "Write fluent English lyrics later. Keep them lyric-like, compact, and memorable. "
    return ""


def _outline_label_clause_qwen(plan: dict) -> str:
    rows = preferred_songform_rows()
    pairs = [f"{row['section']}=>{str(row['label']).strip()}" for row in rows]
    return "Canonical labels: " + ", ".join(pairs) + ". "


def _audio_tags(audio: dict) -> str:
    raw = audio.get("tags", []) if isinstance(audio, dict) else []
    vals = [str(x).strip() for x in raw if str(x).strip()]
    if vals:
        return ", ".join(vals)
    genre = str(audio.get("genre_head", "")).strip()
    voice = _join_unique_parts(
        str(audio.get("vocal_profile", "")).strip(),
        str(audio.get("vocal_tone", "")).strip(),
    )
    return ", ".join(part for part in (genre, voice) if part)


def _audio_config(config: dict) -> dict:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    return audio if isinstance(audio, dict) else {}


def _audio_language(audio: dict) -> str:
    raw = str(audio.get("language", "en")).strip().lower() if isinstance(audio, dict) else "en"
    return raw if raw in {"en", "ja", "ko"} else "en"


def _target_bpm_clause(plan: dict) -> str:
    bpm = int(plan.get("bpm", 0))
    if bpm > 0:
        return f"Target bpm={bpm}. "
    return "Target bpm is not fixed. Choose it yourself from genre, songform, and breathing room. "


def _target_duration_clause(plan: dict) -> str:
    duration = int(plan.get("duration", 0) or 0)
    return f"Target duration={duration} sec. " if duration > 0 else ""


def _language_clause(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    return f"Lyrics language={lang}. " if lang else ""


def _intent_clause(
    plan: dict,
    *,
    include_selected_hook: bool = True,
    include_hook_fragments: bool = True,
) -> str:
    hook_fragments = (
        [str(x).strip() for x in plan.get("hook_english_fragments", []) if str(x).strip()]
        if isinstance(plan.get("hook_english_fragments", []), list)
        else []
    )
    audio_intent = str(plan.get("audio_direction", "")).strip()
    hook_intent = str(plan.get("hook_direction", "")).strip()
    parts = [
        _profile_line("Audio intent", audio_intent),
        _profile_line("Hook intent", hook_intent if hook_intent and hook_intent != audio_intent else ""),
        _profile_line("Hook English fragments", ", ".join(hook_fragments) if include_hook_fragments else ""),
        _profile_line(
            "Selected chorus hook",
            str(plan.get("selected_hook_candidate", {}).get("fragment", "")).strip() if include_selected_hook else "",
        ),
        _profile_line("Genre", plan.get("genre_head", "")),
        _profile_line("Voice", _join_unique_parts(plan.get("vocal_profile", ""), plan.get("vocal_tone", ""))),
        _profile_line("Avoid", _merged_avoid_text(plan)),
    ]
    return "".join(parts)


def _profile_line(label: str, text: object) -> str:
    val = str(text).strip().rstrip(". ")
    return f"{label}={val}. " if val else ""


def _merged_avoid_text(plan: dict) -> str:
    return str(plan.get("negative_direction", "")).strip().rstrip(". ")


def _join_unique_parts(*parts: object) -> str:
    out: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        text = str(raw).strip()
        low = text.lower()
        if text and low not in seen:
            seen.add(low)
            out.append(text)
    return ", ".join(out)


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


def _ending_policy_digest(policy: dict) -> str:
    if not isinstance(policy, dict):
        return ""
    parts = [
        f"mode={str(policy.get('ending_mode', '')).strip()}",
        f"terminal_end_tag={bool(policy.get('terminal_end_tag', False))}",
        f"final_chorus_required={bool(policy.get('final_chorus_required', False))}",
        f"outro_required={bool(policy.get('outro_required', False))}",
        f"vocal_density={str(policy.get('ending_vocal_density', '')).strip()}",
    ]
    return "; ".join(part for part in parts if not part.endswith("="))
