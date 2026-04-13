from __future__ import annotations

from ai_mv.engines.acestep_1_5_aio.prompting import _intent_clause, _language_clause


def _section_bar_count(plan: dict, block: dict) -> int:
    section_bars = plan.get("section_bars", {}) if isinstance(plan.get("section_bars", {}), dict) else {}
    section = str(block.get("section", "")).strip().lower()
    label = str(block.get("label", "")).strip().lower()
    if section == "chorus" and "final chorus" in label:
        final_direct = int(section_bars.get("final_chorus", 0) or 0)
        if final_direct > 0:
            return final_direct
        chorus_base = int(section_bars.get("chorus", 8) or 8)
        return chorus_base + int(section_bars.get("final_chorus_bonus", 0) or 0)
    if section in section_bars:
        return int(section_bars.get(section, 0) or 0)
    if section.startswith("verse_"):
        return int(section_bars.get("verse", 0) or 0)
    return 0


def _bar_feel_clause(plan: dict, block: dict) -> str:
    bars = _section_bar_count(plan, block)
    label = str(block.get("label", "")).strip()
    if bars <= 0:
        return ""
    if label == "Intro":
        return f"This Intro is locked to {bars} bars and should stay instrumental with zero lyric lines. "
    if label == "Outro":
        return f"This Outro is locked to {bars} bars and should stay instrumental or near-silent with zero lyric lines. "
    if bars == 4 and label == "Bridge":
        return "This Bridge is only 4 bars, so it must feel brief, compressed, and turning. Use very short lines and no explanation. "
    if bars == 8 and label in {"Pre-Chorus", "Pre-Chorus 2"}:
        return "This pre-chorus is 8 bars, so it should feel like pressure building upward. Keep it tighter than the chorus, do not fully release, and end by pushing into the next section. "
    if bars == 8 and label in {"Chorus", "Chorus 2"}:
        return "This chorus is 8 bars, so phrase it compactly. Lead with a hookable line, let it open more clearly than the pre-chorus, keep the lines short, and avoid a 12-bar feeling. "
    if bars == 8 and label in {"Verse 1", "Verse 2"}:
        return "This verse is 8 bars, so keep it lean and evenly breathing. Use concrete details without overpacking narrative clauses. "
    if bars >= 16 and label == "Final Chorus":
        return f"This Final Chorus opens across {bars} bars, so it should use that extra space for a bigger payoff. Let it widen beyond the earlier chorus, preferably with one more idea or line of release, while staying singable and clearly segmented. "
    return f"This section is locked to {bars} bars, so match that size with natural breathing and no overpacked phrasing. "


def _audio_lyrics_rules_qwen(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    base = (
        "Keep the exact block label and exact line count. "
        "Write singable finished lyric lines only. "
        "Do not output headers, numbering, notes, or blank filler lines. "
        "Avoid exact repeats across blocks unless a brief refrain is musically necessary. "
        "Stay inside the exact emotional situation and progression described by Audio intent; do not drift into a safer generic pop song. "
        "Verse 2 must change the situation, Bridge must reframe, and Final Chorus must resolve. "
        "Keep lines short and memorable. "
    )
    if lang == "ko":
        return base + (
            "Write fluent modern Korean only. "
            "Keep Hangul natural, direct, and breathable. "
            "Use English only as one very short hook fragment inside the chorus family if truly needed. "
        )
    if lang == "ja":
        return base + (
            "Write fluent modern Japanese only. "
            "Keep it natural, singable, and precise. "
            "Favor concrete, lived-in visual detail over abstract explanation. "
            "The song may be romance, breakup, memory, self-recovery, urban loneliness, or another coherent city-pop emotional mode. "
            "Avoid Korean-style direct confession, awkward slogan-like hooks, and dense literary phrasing. "
        )
    return base + "Write fluent English only. Keep it lyric-like and compact. "


def _audio_lyrics_block_prompt(plan: dict, outline: dict, completed: list[dict], block: dict) -> str:
    label = str(block.get("label", "")).strip()
    line_count = int(block.get("line_count", 1))
    return (
        _audio_lyrics_rules_qwen(plan)
        + _language_clause(plan)
        + _intent_clause(plan)
        + _bar_feel_clause(plan, block)
        + f"Current block=[{label}] line_count={line_count}. "
        + _current_block_constraints(completed, block)
        + f"Output exactly {line_count} lyric lines, one per line. "
    )


def _audio_lyrics_block_system_prompt(plan: dict, block: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    lang_name = {"ja": "Japanese", "ko": "Korean", "en": "English"}.get(lang, "the requested language")
    label = str(block.get("label", "")).strip()
    line_count = int(block.get("line_count", 1))
    return (
        f"Write exactly {line_count} lyric lines for [{label}] in natural {lang_name}. "
        + _bar_feel_clause(plan, block)
        + "No header. No explanation. No extra lines. "
    )


def _audio_lyrics_draft_prompt(plan: dict, outline: dict) -> str:
    sections = []
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        line_count = int(block.get("line_count", 0) or 0)
        role = str(block.get("role", "")).strip()
        change = str(block.get("change", "")).strip()
        if not label:
            continue
        summary = f"[{label}]={line_count} lines"
        bars = _section_bar_count(plan, block)
        if bars > 0:
            summary += f", {bars} bars"
        if role or change:
            details = []
            if role:
                details.append(f"role:{role}")
            if change:
                details.append(f"change:{change}")
            summary += " (" + "; ".join(details) + ")"
        sections.append(summary)
    return (
        _audio_lyrics_rules_qwen(plan)
        + _language_clause(plan)
        + _intent_clause(plan, include_selected_hook=False, include_hook_fragments=False)
        + "Write the full lyrics draft for the entire song in one pass so section progression feels connected. "
        + "Keep the locked section order and exact line counts from the outline. "
        + "Respect the locked bar sizes of each section so the phrasing feels like it actually fits the form instead of floating free from it. "
        + "Let early sections establish the state, middle sections develop or tighten it, and later sections release or resolve it. "
        + "Make Verse 2 change perspective, cost, or direction instead of restating Verse 1. "
        + "Make Bridge compress or reframe so the final return lands harder. A 4-bar bridge must feel brief and turning, not explanatory. "
        + "An 8-bar chorus must feel compact and hook-first. A 16-bar Final Chorus may open wider, but still needs clear internal breathing. "
        + "Keep each section distinct while preserving one shared emotional thread across the whole song. "
        + "Stay inside the world already implied by the audio intent. "
        + "Do not invent random nouns just to fake atmosphere. "
        + "Output bracketed section headers and lyric lines only. "
        + "Do not add [end], notes, numbering, or any text outside the song. "
        + "Locked outline: "
        + ", ".join(sections)
        + ". "
    )


def _audio_lyrics_draft_system_prompt(plan: dict, outline: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    lang_name = {"ja": "Japanese", "ko": "Korean", "en": "English"}.get(lang, "the requested language")
    section_count = len([row for row in outline.get("lyrics_blocks", []) if isinstance(row, dict)])
    return (
        f"Write the full song lyrics in natural {lang_name} for {section_count} locked sections. "
        "Use bracketed headers exactly as provided by the outline. "
        "After each header, write exactly the required number of lyric lines. "
        "No explanation. No markdown fences. No extra sections. No [end]. "
    )


def _parse_audio_lyrics_block_lines(block: dict, text: str) -> list[str]:
    lines = [line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    out = [line for line in lines if line]
    if any(line.startswith("[") and line.endswith("]") for line in out):
        raise RuntimeError("audio lyrics block output contained a forbidden header")
    expected = int(block.get("line_count", 0))
    if len(out) != expected:
        raise RuntimeError(f"audio lyrics fill line count mismatch under [{str(block.get('label', '')).strip()}]")
    return out


def _parse_audio_lyrics_draft(outline: dict, text: str) -> list[dict]:
    lines = [line.rstrip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    blocks = [row for row in outline.get("lyrics_blocks", []) if isinstance(row, dict)]
    parsed: list[dict] = []
    cursor = 0
    for spec in blocks:
        label = str(spec.get("label", "")).strip()
        line_count = int(spec.get("line_count", 0) or 0)
        while cursor < len(lines) and not str(lines[cursor]).strip():
            cursor += 1
        expected_header = f"[{label}]"
        if cursor >= len(lines) or str(lines[cursor]).strip() != expected_header:
            raise RuntimeError(f"audio lyrics draft missing expected header {expected_header}")
        cursor += 1
        body: list[str] = []
        while cursor < len(lines) and len(body) < line_count:
            current = str(lines[cursor]).strip()
            cursor += 1
            if not current:
                continue
            if current.startswith("[") and current.endswith("]"):
                raise RuntimeError(f"audio lyrics draft entered next section before filling {expected_header}")
            body.append(current)
        if len(body) != line_count:
            raise RuntimeError(f"audio lyrics draft line count mismatch under {expected_header}")
        parsed.append(
            {
                "section": str(spec.get("section", "")).strip(),
                "label": label,
                "style": str(spec.get("style", "")).strip(),
                "lines": body,
            }
        )
    trailing = [str(line).strip() for line in lines[cursor:] if str(line).strip()]
    if trailing:
        raise RuntimeError("audio lyrics draft contained unexpected trailing text")
    return parsed


def _current_block_constraints(completed: list[dict], block: dict) -> str:
    label = str(block.get("label", "")).strip()
    chorus = next((row for row in completed if str(row.get("label", "")).strip() == "Chorus"), None)
    rules = {
        "Intro": "Intro should be empty or a very short setup. ",
        "Verse 1": "Verse 1 should establish the state with concrete details. ",
        "Pre-Chorus": "Pre-Chorus should tighten anticipation without spending the hook and should feel tighter than the Chorus. ",
        "Chorus": "Chorus should deliver the clearest hook and first release, opening wider than the Pre-Chorus. ",
        "Verse 2": "Verse 2 must add change, cost, or contradiction. ",
        "Pre-Chorus 2": "Pre-Chorus 2 should escalate rather than repeat Pre-Chorus and should still stay tighter than the Chorus return. ",
        "Bridge": "Bridge should interrupt or reframe before the last return. ",
        "Final Chorus": "Final Chorus should feel like the answer and strongest payoff, using its extra space instead of repeating the first chorus shape. ",
        "Outro": "Outro should be terminal and very short. ",
    }
    if label == "Chorus 2" and chorus:
        chorus_lines = "; ".join(str(line).strip() for line in chorus.get("lines", []) if str(line).strip())
        return "Chorus 2 must keep the same hook center but rewrite most lines. " + f"Avoid copying Chorus verbatim: {chorus_lines}. "
    if label == "Final Chorus" and chorus:
        chorus_lines = "; ".join(str(line).strip() for line in chorus.get("lines", []) if str(line).strip())
        return rules.get(label, "") + f"Keep at most two short reused lines. Avoid copying Chorus verbatim: {chorus_lines}. "
    return rules.get(label, "")


def _validate_generated_block(plan: dict, completed: list[dict], block: dict) -> None:
    label = str(block.get("label", "")).strip()
    chorus = next((row for row in completed if str(row.get("label", "")).strip() == "Chorus"), None)
    lang = str(plan.get("language", "")).strip().lower()
    _validate_block_density(label, block.get("lines", []), lang)
    _validate_block_hook_quality(label, block.get("lines", []), lang)
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


def _validate_block_density(label: str, lines: list[object], language: str) -> None:
    max_chars = 52 if language == "en" else 22 if language == "ko" else 34
    max_commas = 2 if language == "en" else 1
    for line in lines:
        text = str(line).strip()
        if not text:
            continue
        visible = _visible_char_count(text)
        if visible > max_chars:
            raise RuntimeError(f"audio lyrics quality mismatch: line too dense for singing in {label}")
        comma_count = text.count(",") + text.count("，")
        if comma_count > max_commas:
            raise RuntimeError(f"audio lyrics quality mismatch: line too clause-heavy in {label}")


def _validate_block_hook_quality(label: str, lines: list[object], language: str) -> None:
    if label not in {"Chorus", "Chorus 2", "Final Chorus"}:
        return
    short_limit = 28 if language == "en" else 14 if language == "ko" else 18
    rendered = [str(line).strip() for line in lines if str(line).strip()]
    if not any(_visible_char_count(line) <= short_limit for line in rendered):
        raise RuntimeError(f"audio lyrics quality mismatch: {label} lacks a short memorable hook line")


def _visible_char_count(text: str) -> int:
    cleaned = "".join(str(text).split())
    for token in [",", "，", "."]:
        cleaned = cleaned.replace(token, "")
    return len(cleaned)


def _audio_retry_clause(plan: dict) -> str:
    attempt = int(plan.get("audio_retry_attempt", 0) or 0)
    feedback = str(plan.get("audio_retry_feedback", "")).strip()
    if attempt <= 0:
        return ""
    clause = f"Rewrite attempt {attempt + 1}. Regenerate from scratch with fresher lines and clearer section separation. "
    if feedback:
        clause += f"Previous issue: {feedback}. "
    return clause
