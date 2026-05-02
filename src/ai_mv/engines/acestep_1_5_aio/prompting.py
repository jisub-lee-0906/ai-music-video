from __future__ import annotations

from ai_mv.engines.acestep_1_5_aio.policy import preferred_songform_rows


def _audio_prompt(plan: dict) -> str:
    return _audio_outline_prompt(plan)


def _audio_outline_prompt(plan: dict) -> str:
    return (
        _audio_prompt_rules(plan)
        + _target_duration_clause(plan)
        + _target_bpm_clause(plan)
        + f"Planner seed={int(plan.get('seed', 31))}. This is a planning hint, not the workflow execution seed. "
        + _audio_retry_clause(plan)
        + _language_clause(plan)
        + _intent_clause(plan)
        + _outline_label_clause(plan)
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
        "Treat Audio intent as the source of truth; genre and voice only shape presentation. "
        "If bpm is not fixed, choose it from genre, line density, and breathing room. "
        "For brighter, hook-forward, moving-forward, or more energetic concepts, prefer a noticeably quicker pulse instead of defaulting to mellow midtempo. "
    )


def _audio_songform_rules(plan: dict) -> str:
    ending = _ending_policy(plan)
    variant_text = _songform_variant_clause(plan)
    if str(plan.get("songform_mode", "")).strip().lower() == "hook_validation":
        return (
            "Write a compact hook-validation songlet, not a compressed full song. "
            "Use only enough structure to test genre, lead vocal, lyric hook, and clean ending inside the requested short duration. "
            + variant_text
            + "Do not include Verse 1 or Pre-Chorus in a thirty-second validation take; ACE-Step often collapses them into the hook at this length. "
            "Do not force Verse 2, Bridge, or Final Chorus into a thirty-second validation take. "
            "Make this a chorus-only proof of genre, vocal, hook, and clean ending. "
            "Use exactly two Chorus lyric lines: line one should be the title-grade hook, line two should repeat or lightly vary that hook within the same melodic idea. "
            "Keep both Chorus lines as one-breath phrases, six words or fewer, with simple open vowels. "
            "Avoid cramming syllables, long clauses, stacked images, or fast internal rhyme into either Chorus line. "
            "Do not add a third narrative payoff line; late new story lines can make ACE-Step jump into a different chorus idea. "
            "Keep Intro and Outro short and mostly instrumental. "
            "Outro must feel like a terminal ending, not a pickup into another section. "
            "Do not use a drum fill, riser, crash pickup, or unresolved transition gesture before [end]. "
            "Land on a final cadence or decaying chord before [end]. "
            "Make the first Chorus line feel title-worthy and instantly memorable. "
            "For each section, role should say what that section must do, and change should say what becomes different from the previous section. "
        )
    rules = [
        "Write a full song, not a fragment. ",
        "Choose a songform that fits a modern short-form song around two and a half to three minutes instead of forcing one fixed template. ",
        variant_text,
        "Prefer compact, natural section flow. ",
        "Prefer a strong beginning-middle-turn-resolution arc, such as Intro -> Verse 1 -> Pre-Chorus -> Chorus -> Verse 2 -> Bridge -> Final Chorus -> Outro. ",
        "For each section, role should say what that section must do, and change should say what becomes different from the previous section. ",
        "Use Chorus 2, Pre-Chorus 2, or Post-Chorus only if the song truly needs them, and avoid crowding a short song with all of them at once. ",
        "Do not make Verse 2 a copy of Verse 1. ",
        "Make Bridge the emotional turn when it appears, and make Final Chorus feel earned after that turn. ",
        "If you use Final Chorus, make it feel like an answer, not a repeat. ",
        "Make the first Chorus line feel title-worthy and instantly memorable. ",
        "Let the Final Chorus feel more decisive and more open than the first Chorus. ",
        "Keep Intro instrumental. Keep Outro instrumental unless a very short sung tail is clearly necessary. ",
    ]
    if bool(ending.get("final_chorus_required", False)):
        rules.append("Use a distinct final return labeled Final Chorus. ")
    if bool(ending.get("outro_required", False)):
        rules.append("If you include Outro, keep it very short and terminal. ")
    return "".join(rules)


def _songform_variant_clause(plan: dict) -> str:
    variants = plan.get("songform_variants", [])
    if not isinstance(variants, list) or not variants:
        return ""
    rendered: list[str] = []
    for variant in variants[:3]:
        if not isinstance(variant, list):
            continue
        labels = [str(row.get("label", "")).strip() for row in variant if isinstance(row, dict) and str(row.get("label", "")).strip()]
        if labels:
            rendered.append(" -> ".join(labels))
    if not rendered:
        return ""
    return "Choose one natural songform shape from these candidate patterns: " + " | ".join(rendered) + ". "


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
    base_minimums = {
        "Verse 1": 4,
        "Verse 2": 4,
        "Pre-Chorus": 3,
        "Pre-Chorus 2": 3,
        "Chorus": 4,
        "Chorus 2": 4,
        "Final Chorus": 4,
        "Bridge": 2,
    }
    minimums = {label: min(required, int(budgets.get(label, required) or 0)) for label, required in base_minimums.items()}
    if int(budgets.get("Final Chorus", 0) or 0) >= 5:
        minimums["Final Chorus"] = 5
    min_pairs = [f"{label}>= {minimums[label]}" for label in ordered if label in minimums and label in budgets and int(minimums[label]) > 0]
    text = "Respect these maximum line counts: " + ", ".join(pairs) + ". "
    if min_pairs:
        text += "Respect these minimum line counts for any included required section: " + ", ".join(min_pairs) + ". "
    return text + "Prefer fewer stronger lines, but never below a required section minimum. "


def _language_style_rules(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    if lang == "ja":
        return (
            "Write fluent modern Japanese lyrics later. Keep them natural, compact, singable, and emotionally precise. "
            "Favor concrete, lived-in visual detail over abstract explanation. "
            "Let the song choose whether it leans toward romance, breakup, longing, self-recovery, urban loneliness, or another fitting emotional mood. "
            "Prefer a short, title-grade hook line in the chorus family instead of a generic pretty sentence. "
            "Avoid Korean-style direct confession, overpacked literary metaphor, and awkward slogan-like hooks. "
        )
    if lang == "ko":
        return (
            "Write fluent modern Korean lyrics later. Keep them short, singable, and direct. "
            "Every non-empty lyric line must contain readable Hangul words. "
            "Do not output any English-only lyric lines. "
        )
    if lang == "en":
        return "Write fluent English lyrics later. Keep them lyric-like, compact, and memorable. "
    return ""


def _outline_label_clause(plan: dict) -> str:
    rows = preferred_songform_rows()
    labels: list[str] = []
    for row in rows:
        label = str(row["label"]).strip()
        if label and label not in labels:
            labels.append(label)
    optional = ["Pre-Chorus 2", "Chorus 2", "Post-Chorus"]
    for label in optional:
        if label not in labels:
            labels.append(label)
    return "Available canonical labels: " + ", ".join(labels) + ". "


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
    raw = str(audio.get("language", "")).strip().lower() if isinstance(audio, dict) else ""
    return raw if raw in {"en", "ja", "ko"} else ""


def _target_bpm_clause(plan: dict) -> str:
    bpm = int(plan.get("bpm", 0))
    if bpm > 0:
        return f"Target bpm={bpm}. "
    return "Target bpm is not fixed. Choose it yourself from genre, songform, and breathing room. "


def _target_duration_clause(plan: dict) -> str:
    duration = int(plan.get("duration", 0) or 0)
    min_sec = int(plan.get("duration_min_sec", 0) or 0)
    max_sec = int(plan.get("duration_max_sec", 0) or 0)
    if min_sec > 0 and max_sec >= min_sec:
        return f"Target duration between {min_sec} and {max_sec} sec. "
    return f"Target duration={duration} sec. " if duration > 0 else ""


def _language_clause(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    return f"Lyrics language={lang}. " if lang else ""


def _audio_retry_clause(plan: dict) -> str:
    attempt = int(plan.get("audio_retry_attempt", 0) or 0)
    feedback = str(plan.get("audio_retry_feedback", "")).strip()
    if attempt <= 0:
        return ""
    clause = f"Rewrite attempt {attempt + 1}. Regenerate from scratch with fresher lines and clearer section separation. "
    if feedback:
        clause += f"Previous issue: {feedback}. "
    lowered = feedback.lower()
    if "expected readable korean lines" in lowered:
        clause += (
            "Every non-empty lyric line must contain readable Hangul words. "
            "Do not output any English-only lyric lines. "
            "Keep any English to at most one very short hook fragment inside the chorus family. "
        )
    elif "leaked too much english" in lowered:
        clause += (
            "Reduce English sharply. "
            "Keep any English to at most one very short hook fragment inside the chorus family. "
        )
    elif "pre-chorus phrasing is too broad compared with chorus" in lowered:
        clause += (
            "Pre-Chorus lines must stay shorter and tighter than Chorus lines. "
            "Keep Pre-Chorus average visible length at least a few characters below Chorus average. "
            "Use more breath-led setup phrasing in Pre-Chorus and reserve broader release language for Chorus. "
            "If the contrast is at risk, shorten Pre-Chorus and make Chorus a little broader instead of opening Pre-Chorus. "
            "Make Chorus lines more open and hook-led than Pre-Chorus. "
        )
    elif "lacks a short memorable hook line" in lowered:
        clause += (
            "Chorus must include at least one very short title-grade hook line. "
            "For English, keep that hook line under 28 visible characters. "
            "For Korean, keep it under 14 visible characters; for Japanese, under 18. "
            "Put the short hook as the first or last Chorus line. "
            "Use a compact phrase, not a sentence-shaped explanation. "
        )
    elif "final chorus underuses its extended bar space" in lowered:
        clause += (
            "Final Chorus has the extended bar lane; write five lyric lines for it. "
            "Do not shorten Final Chorus to a four-line ordinary chorus. "
            "Use the extra line for resolution or a stronger final payoff rather than repetition. "
        )
    elif "underdelivers its section role" in lowered:
        clause += "Keep every required section at its locked line count; do not shorten or omit required lines. "
        if "pre-chorus" in lowered:
            clause += "Pre-Chorus must contain at least three compact build-up lyric lines. "
        if "verse" in lowered:
            clause += "Verse sections must contain at least four concrete story-detail lyric lines. "
        if "chorus" in lowered:
            clause += "Chorus sections must contain at least four hook-led release lyric lines. "
        if "bridge" in lowered:
            clause += "Bridge must contain at least two brief reframing lyric lines. "
    return clause


def _intent_clause(
    plan: dict,
    *,
    include_selected_hook: bool = True,
    include_hook_fragments: bool = True,
) -> str:
    audio_intent = str(plan.get("audio_direction", "")).strip()
    parts = [
        _profile_line("Audio intent", audio_intent),
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
