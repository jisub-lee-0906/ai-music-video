from __future__ import annotations

from ai_mv.engines.acestep_1_5_aio.prompting import _intent_clause, _language_clause


def _audio_lyrics_rules_qwen(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    retry_clause = _audio_retry_clause(plan)
    common = (
        "Every lyric line must be valid readable text in the requested language, not mojibake, not corrupted Unicode, and not random symbol noise. "
        "Keep the exact section skeleton, exact line count, and exact header text. "
        "Favor singable, emotionally legible lines over ornate wording. "
        "Choose one dominant emotional or visual motif for the chorus family and one or two supporting setup motifs for the verses. "
        "Do not keep introducing brand-new unrelated objects every section; deepen the same small image system instead. "
        "Do not pad the song with generic filler or duplicate weak phrases across sections. "
        "Outside of one intentional hook line, do not repeat a full lyric line in another block. "
        "Choose one short chorus hook for the chorus family only, and do not place the chorus hook inside Intro, Verse, or Pre-Chorus blocks. "
        "The opening setup must evolve as the song moves forward: Intro, Verse 1, Pre-Chorus, and Chorus should not recycle the same full line. "
        "Intro lines must never recur verbatim later in the song; later blocks may only transform the image into new sentences. "
        "Verse lines should add concrete images, tactile objects, visible motions, or emotional detail. "
        "Prefer a small recurring image system over random new props. "
        "Avoid disposable filler props such as convenience stores, phone screens, random taxis, random drinks, or throwaway street objects unless they become central and recur with purpose. "
        "Pre-chorus lines should raise anticipation and momentum. "
        "Chorus lines should deliver one memorable hook image or title-worthy phrase cleanly. "
        "Bridge lines should reframe the song with a wider system, memory, or emotional shift. "
        "Chorus 2 must keep the same emotional center as Chorus but change at least four full lines. "
        "Final Chorus must keep at most two reused lines from Chorus and rewrite the rest as the clearest payoff or most complete answer. "
        "Chorus 2 and Final Chorus should each introduce fresh nouns, verbs, or images instead of just paraphrasing the first chorus. "
        "The whole song must change state over time: setup, pressure, decision, complication, answer. "
        "Good pattern: Verse 1 observes, Pre-Chorus tightens, Chorus chooses, Verse 2 complicates, Bridge breaks or reframes, Final Chorus resolves. "
        "If the form is compact, keep Bridge very short rather than deleting the low point entirely. "
        "If the form is compact, it is acceptable to skip Chorus 2 entirely and move from Pre-Chorus 2 into a short Bridge before Final Chorus. "
        "Bad pattern: repeating the same weak stock phrase across Verse, Chorus, and Final Chorus. "
        "Good pattern: each section keeps one motif but changes the angle, gesture, or emotional meaning. "
        f"{retry_clause}"
    )
    if lang == "ja":
        return common + (
            "Write fluent modern Japanese lyric lines only. "
            "Use natural hiragana, katakana, and common-use kanji. "
            "Do not leave any Latin alphabet words, romanized spellings, or English production terms in the final Japanese lyrics. "
            "Rewrite concrete nouns into natural Japanese. "
        )
    if lang == "ko":
        return common + (
            "Write fluent modern Korean lyric lines only. "
            "Use natural Hangul phrasing, natural particles, and singable endings. "
            "Avoid translationese and stiff written-language endings. "
            "Keep the voice intimate, authored, and easy to sing. "
            "A good chorus should sound like a real hook someone would remember after one listen. "
            "Do not end multiple sections with the same generic tomorrow, together, or keep-going slogan. "
            "Keep Korean lines especially short and breathable. Favor one clean image or one direct action per line. "
            "Avoid chaining two or three clauses into one Korean line. "
            "A very short English hook fragment is allowed only when it is catchy, intentional, and blended into otherwise Korean-dominant lyrics. "
            "Do not let a weak English fragment become the title or whole payoff unless it is genuinely undeniable. "
            "Do not write long English sentences inside Korean lyrics. "
        )
    return common + (
        "Write fluent English lyric lines only. "
        "Use lyric-like cadence, not flat explanatory prose. "
        "Prefer concrete images, clear verbs, and memorable hook phrasing. "
        "Avoid overly literal scene description and avoid generic filler choruses. "
    )


def _audio_lyrics_block_prompt(plan: dict, outline: dict, completed: list[dict], block: dict) -> str:
    label = str(block.get("label", "")).strip()
    line_count = int(block.get("line_count", 1))
    block_constraints = _current_block_constraints(completed, block)
    hook_fragments = [str(x).strip() for x in plan.get("hook_english_fragments", []) if str(x).strip()]
    selected_hook = str(plan.get("selected_hook_candidate", {}).get("fragment", "")).strip()
    selected_hook_clause = ""
    if label in {"Chorus", "Chorus 2", "Final Chorus"} and selected_hook:
        selected_hook_clause = (
            f"Center this block around the selected hook='{selected_hook}' or a close variation of it. "
        )
    hook_fragment_clause = ""
    if str(plan.get("language", "")).strip().lower() == "ko" and label in {"Chorus", "Chorus 2", "Final Chorus"} and hook_fragments:
        hook_fragment_clause = (
            "If it fits naturally, you may use exactly one short English hook fragment in this block. "
            f"Preferred fragments: {', '.join(hook_fragments)}. "
            "Do not use more than one English fragment line in the block. "
        )
    return (
        _audio_lyrics_rules_qwen(plan)
        + f"{_language_clause(plan)}{_intent_clause(plan)}"
        + f"Current block=[{label}] section={str(block.get('section', '')).strip()} style={str(block.get('style', '')).strip()} line_count={line_count}. "
        + block_constraints
        + selected_hook_clause
        + hook_fragment_clause
        + "Write only the lyric body for the current block. "
        + "Do not output the header. Do not output numbering, bullets, explanations, or blank filler lines. "
        + f"Output exactly {line_count} finished lyric lines, one per line. "
        + "Do not copy earlier blocks verbatim. Keep narrative continuity through shared world and emotion, not through recycled lines. "
        + "Before answering, silently check every line against earlier blocks and rewrite any exact match unless it is the one intentional hook line. "
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
    expected = int(block.get("line_count", 0))
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
        "Intro": "Intro should set the scene with no sung line or one very short clean setup image and no chorus-style payoff. ",
        "Verse 1": "Verse 1 should establish concrete city details, tactile objects, visible gestures, motion, and the initial lack or distance the song needs to overcome. ",
        "Pre-Chorus": "Pre-Chorus should raise anticipation and momentum without repeating the coming hook, and it should make a decision feel imminent. ",
        "Chorus": "Chorus should establish the central hook image in its clearest, most memorable, and most singable form, and it should feel like the first true decision or emotional commitment. ",
        "Verse 2": "Verse 2 should stay in the same world but add complication, contradiction, cost, or a sharper confession instead of just more scenery. ",
        "Pre-Chorus 2": "Pre-Chorus 2 should feel like a lift from the first pre-chorus, not a copy, and it should make the second choice more active and irreversible. ",
        "Bridge": "Bridge should create the lowest point, biggest interruption, clearest doubt, or widest reframe in the song rather than another descriptive transit line. ",
        "Final Chorus": "Final Chorus should sound like the emotional answer, clearest payoff, and most satisfying final resolution of the song. ",
        "Outro": "Outro should leave one last residue image, avoid restating the full chorus, and feel short enough that the song can stop immediately after it, ideally in a single short line. ",
    }
    base = role_rules.get(label, "")
    if label == "Verse 1" and intro:
        intro_lines = "; ".join(str(line).strip() for line in intro.get("lines", []) if str(line).strip())
        return base + (
            "Do not simply expand the Intro by repeating its exact image sentence. "
            "Keep the same night and same world, but move from the opening image into new objects, surfaces, or gestures. "
            "Every Verse 1 line should push the song one step deeper into the scene than Intro did. "
            "Verse 1 must not use the future chorus hook line; it should prepare the world, not arrive at the refrain. "
            "The first two Verse 1 lines must not repeat or lightly paraphrase the Intro lines; they should introduce different objects, actions, or surfaces immediately. "
            "Keep Verse 1 inside the same tight image family instead of reaching for random filler props or disconnected scenery. "
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
            "Keep one chorus hook if needed, but the section should widen the image and make it more memorable than the setup blocks. "
            "The most memorable line of the song should appear here first, not earlier. "
            "Do not copy any Intro line or Verse 1 line verbatim into Chorus; transform the motif into a new refrain sentence. "
            f"Existing Pre-Chorus lines to avoid copying verbatim: {pre_lines}. "
        )
    if label == "Verse 2" and verse_1:
        verse_lines = "; ".join(str(line).strip() for line in verse_1.get("lines", []) if str(line).strip())
        return base + (
            "Do not paraphrase Verse 1 line by line. "
            "Keep the same city and same night, but move to different objects, gestures, surfaces, thoughts, or consequences. "
            "Verse 2 must not feel like more B-roll. It should reveal what became harder, riskier, closer, or more honest after Chorus 1. "
            "At least one Verse 2 line should introduce tension, contradiction, or an action that changes the emotional situation. "
            "Do not fall back to generic filler imagery; stay inside the song's chosen image system. "
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
            f"Forbidden verbatim Chorus lines: {chorus_lines}. "
        )
    if label == "Bridge" and chorus:
        chorus_lines = "; ".join(str(line).strip() for line in chorus.get("lines", []) if str(line).strip())
        return base + (
            "Bridge must not function like another route description or another mini-chorus. "
            "It should widen the emotional frame, introduce absence, doubt, memory, cost, or suspended time, and make the final return feel necessary. "
            "A good bridge changes the meaning of the chorus when the chorus comes back. "
            "Avoid generic movement verbs unless they clearly signal interruption or collapse. "
            f"Existing Chorus lines to avoid copying verbatim: {chorus_lines}. "
        )
    if label == "Final Chorus" and chorus:
        chorus_lines = "; ".join(str(line).strip() for line in chorus.get("lines", []) if str(line).strip())
        return base + (
            "Final Chorus must feel like the clearest payoff. "
            "Reuse at most two short hook lines from Chorus and rewrite all other lines with stronger closure, warmer commitment, or wider imagery. "
            "It should feel larger than Chorus 1 not by saying the same thing louder, but by resolving the city image, relationship, or promise more completely. "
            "Show what changed because of the journey. The emotional state after Final Chorus must be clearly different from Verse 1. "
            "Do not end in generic hope or generic forward-motion slogans; land on this song's own images. "
            "Keep Final Chorus syntax cleaner than Chorus 1. Prefer short decisive Korean lines over long explanatory clauses. "
            "At least two lines in Final Chorus should be short enough to feel instantly chantable. "
            "If Chorus 1 used one hook line, keep only that nucleus and rebuild the rest of the section around a fuller ending image. "
            "Do not reuse the exact Chorus 2 hook sentence in Final Chorus; intensify it or resolve it into a new sentence. "
            f"Existing Chorus lines to avoid copying verbatim: {chorus_lines}. "
        )
    return base


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
    clause = (
        f"This is rewrite attempt {attempt + 1}. "
        "Regenerate the song from scratch with fresher section wording, less reuse, and clearer separation between setup blocks and chorus-family blocks. "
    )
    if feedback:
        clause += f"Previous attempt failed with this exact issue: {feedback}. "
    return clause
