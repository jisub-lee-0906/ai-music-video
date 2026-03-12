from __future__ import annotations

from ai_mv.core.profile_brief import build_profile_brief
from ai_mv.core.output_paths import audio_prefix
from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
)
from ai_mv.core.contracts.prompt_schema import audio_schema
from ai_mv.engines.acestep_1_5_split.policy import audio_policy
from ai_mv.infra.codex_cli_client import generate_structured

_GENERIC_HOOK_FRAGMENTS = (
    "look at me",
    "stay with me",
    "call my name",
    "hold me",
    "all night",
)
_WEAK_JA_HOOK_ENDINGS = (
    "まだ揺れてる",
    "まだ光ってる",
    "まだ消えない",
)


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = _audio_config(config)
    tags = _audio_tags(audio)
    guidance = _style_guidance(config)
    profile = build_profile_brief(tags, guidance)
    plan = {
        "tags": tags,
        "style_guidance": guidance,
        "language": _audio_language(audio),
        "filename_prefix": audio_prefix(payload["run_id"]),
    }
    plan.update(profile)
    plan.update(audio_policy(config))
    return _plan_with_quality_attempts(config, plan)


def _plan_with_llm(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    tags = str(plan["tags"]).strip()
    guidance = str(plan["style_guidance"]).strip()
    tags_clause = f"Input tags={tags}. " if tags else ""
    guidance_clause = f"Style guidance={guidance}. " if guidance else ""
    language_clause = _language_clause(plan)
    profile_clause = _profile_clause(plan)
    hook_shape_clause = _hook_shape_clause(plan)
    bpm_clause = _target_bpm_clause(plan)
    seed_clause = f"Creative seed={int(plan.get('seed', 31))}. "
    return _audio_prompt_rules(plan) + (
        f"Target duration={int(plan['duration'])} sec. "
        f"{bpm_clause}{seed_clause}{tags_clause}{guidance_clause}{language_clause}{profile_clause}{hook_shape_clause}"
    )


def _audio_prompt_rules(plan: dict) -> str:
    return _audio_structure_rules() + _audio_form_rules() + _audio_description_rules() + _language_style_rules(plan)


def _audio_structure_rules() -> str:
    return (
        "You are an elite songwriter-producer. Return JSON only. "
        "No markdown. No prose outside JSON. "
        "Required top-level keys: genre_description,bpm,keyscale,seed,duration,lyrics_blocks. "
        "Required lyrics_blocks item keys: section,label,style,lines. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
        "Composition target must follow input reference strictly. "
        "Design aggressive section contrast with distinct diction per section. "
        "Give each section a clearly different job in the emotional arc so the song feels staged and cumulative. "
        "Intro should open atmosphere with minimal language and immediate tone-setting. "
        "Intro should stay sparse and usually fit in 2-3 short lines unless the style strongly demands more. "
        "Verse: forward motion, clear imagery, memorable cadence, and strong lyrical specificity. "
        "Verse should include concrete sensory or scene details without copying examples, and should advance the scene rather than summarizing emotion. "
        "Prefer fuller line density in verses than in pre-chorus or outro. "
        "Keep line endings clear and singable; avoid vague filler. "
        "Pre-chorus: emotional lift, tension, breath-space, smoother vowel flow and intimacy, with language that clearly prepares a release. "
        "Pre-chorus should feel slightly more open and less crowded than the verse. "
        "Pre-chorus usually works best in 2-3 concise lines unless the song clearly needs an extra pickup line. "
        "Chorus: high-impact hook, chant-ready phrasing, immediate recall, strong emotional release, and the clearest central idea of the song. "
        "Chorus should simplify language compared with the verse so the hook lands instantly. "
        "Post-chorus: very short callback lines built around the same hook phrase, acting as a lingering afterglow rather than a new verse. "
        "Even when short, post-chorus should contain at least one complete melodic thought or image tail, not only chopped slogan fragments. "
        "Bridge should create a genuine contrast in perspective, energy, or emotional framing before the final return, and should redirect or thin the language instead of stacking more imagery. "
        "Bridge should feel like a real turn of the song, with choice, consequence, confession, or irreversible emotional recognition rather than only pretty atmosphere. "
        "Bridge should usually be sparser than the verse and should not feel lyrically crowded. "
        "Outro should feel like a real landing after the final chorus, not just a leftover fragment. "
        "Outro should usually keep 2-3 concise lines, with one residue image and one clear closure line that settles the song. "
    )


def _audio_form_rules() -> str:
    return (
        "Target a complete pop song arc rather than a fragment. "
        "Preferred block order is intro, verse_1, pre_chorus, chorus, post_chorus, verse_2, pre_chorus, chorus, bridge, chorus, outro. "
        "If duration forces compression, keep at minimum intro, verse_1, pre_chorus, chorus, verse_2, bridge, final chorus, outro. "
        "A bridge must never be the final large section; it must be followed by another chorus block. "
        "Use repeated chorus blocks when the song returns, and label the last one as Final Chorus while keeping section='chorus'. "
        "A normal chorus should usually land in 6 lines so the hook, response, support, and payoff all have room to breathe. "
        "Keep the first line of each chorus in the same hook family so recall stays immediate. "
        "The second line of a chorus must answer, tilt, or intensify the hook; do not copy the opening line verbatim into line two. "
        "In every chorus, line 1 should act as the hook anchor, line 2 should answer or intensify it, and later lines should carry scene detail, payoff, or emotional consequence. "
        "Do not let every chorus line perform the same job or repeat the same phrase shape. "
        "Do not repeat the exact hook-anchor line again as line 3 unless it is clearly transformed; a chorus should move forward, not stall. "
        "Within a chorus, the listener should feel progression from hook to answer to consequence; avoid making line 3 or line 4 feel like a simple second hook start. "
        "If a second chorus appears before the bridge, keep the same hook family but change at least one support line and one payoff/callback line so it does not read as an exact duplicate. "
        "The final chorus must feel bigger than the first chorus by adding payoff, lift, or a fresh line turn instead of simple copy-paste. "
        "The final chorus should usually open into 7 or 8 lines so the payoff can actually expand rather than merely repeat the first chorus. "
        "The final chorus should preserve the hook opening but introduce at least two new lines or one new image turn that was not used in the first chorus. "
        "At least half of the non-opening lines in the final chorus should differ from the first chorus. "
        "Use the bridge as the setup for the final chorus payoff, so the final chorus answers or releases the bridge tension. "
        "The final chorus should contain one concrete visual or emotional payoff line that sounds like the line listeners wait for. "
        "The final chorus should contain at least one line that would feel impossible or unearned earlier in the song. "
        "Do not repeat the exact same six chorus lines three times across the song. "
        "Verse_2 must advance the scene or relationship, not paraphrase verse_1. "
        "Post-chorus should usually stay at 2-3 short lines and behave like an echo, not a new verse, but it still needs one melodic tail or image turn so it does not feel empty. "
        "Outro must not end on a bare noun fragment or unresolved slogan; the last line should land like a gentle final sentence or emotional settling. "
        "Aim for 9-11 lyrics_blocks for a full song whenever duration allows. "
    )


def _audio_description_rules() -> str:
    return (
        "genre_description must be one compact production paragraph including arrangement cues "
        "(808/bass, synth layers, harmonies, transitions, impact), in 2-3 sentences only. "
        "genre_description is written directly into the AceStep tags text field, so it must stay plain production language with no bullets, labels, or markdown. "
        "genre_description must always be written in English, even when the lyrics language is Japanese or Korean. "
        "genre_description must explicitly cover groove foundation, lead vocal character, and hook instrumentation. "
        "genre_description should also describe pocket, rhythm feel, or timing character in concrete production terms when relevant. "
        "Mention at least one clear groove behavior such as bounce, glide, pulse, sway, swing, push, or restraint. "
        "Prefer tangible musical language like swing, bounce, pulse, breath, glide, shimmer, punch, or restraint over generic adjectives. "
        "Prefer one coherent production identity instead of mixing many genres. "
        "Keep genre_description reusable as a downstream audio-direction brief, not a poetic review. "
        "For each block, lines must be 2-4 short singable lines with concrete imagery and cadence. "
        "Only chorus may expand beyond 4 lines when needed for hook repetition or chant response. "
        "Prefer vivid action verbs and sonic words over abstract statements. "
        "Write lines with clear mouth-feel and internal rhythm suitable for topline melody. "
        "Keep 1-3 recurring concept words or images alive across verse, pre-chorus, and chorus so the song identity stays glued together. "
        "Include one repeatable hook phrase in chorus/post-chorus for recall and repeat it at least twice in chorus lines. "
        "Chorus must include at least one call-and-response or chant-like fragment. "
        "Make the hook phrase title-worthy: short, singable, and easy to remember after one listen. "
        "The hook phrase should usually contain one concrete image, object, place, weather cue, or physical sensation instead of a generic romance placeholder. "
        "Prefer a distinctive hook phrase built from the song's actual world instead of generic love-song filler. "
        "Use one concrete world element already implied by profile_summary, audio_direction, or hook_direction, then keep returning to that same world with small variations. "
        "Make the chorus opening feel like a plausible song title: one concrete world anchor plus one specific emotional, temporal, or motion twist. "
        "Prefer a phrase that listeners could quote as the song title, not just a safe description line. "
        "Different good hooks may use different contours such as image plus destination, image plus afterglow, reflection plus motion, or place plus echo; keep the contour coherent within one song. "
        "Avoid fallback hook language like 'call my name', 'hold me', 'stay with me', 'all night', or repeated hey-oh syllables unless the surrounding line adds a fresh concrete twist. "
        "Avoid letting a generic English fragment become the main hook anchor when a stronger world-specific phrase is available. "
        "Avoid using the same generic imperative in multiple chorus lines. "
        "Do not let every chorus line carry the same weight; support lines should set up the hook and payoff lines should feel earned. "
        "Avoid ending the song with a weak comedown if the chorus has not fully paid off yet. "
        "Avoid generic filler and repeated empty slogans. "
        "Treat profile_summary, audio_direction, and hook_direction as the source of truth for genre lane, vocal attitude, and recurring imagery. "
        "When tags grow longer in future profiles, compress them into one coherent producer brief instead of listing every tag back. "
        "Do not invent extra sections or fields. "
    )


def _language_style_rules(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    if lang == "ja":
        return (
            "Write fluent modern Japanese lyrics with a natural mix of kanji, hiragana, and katakana. "
            "Keep the diction elegant, adult, and singable rather than childish, slangy, or anime-coded. "
            "Use English only for very short fashionable hook fragments when they sharpen recall. "
            "Prefer natural Japanese phrasing built from the profile's concrete world over awkward loanword-heavy wording. "
            "Avoid forced transliterations when a natural Japanese phrase would sing more smoothly. "
            "In Japanese songs, the main chorus opening should be led by Japanese phrasing; do not let an English fragment dominate the hook anchor. "
            "Give the Japanese chorus opening title-worthiness: it should sound like a phrase people could remember as the song name, not just a safe mood sentence. "
            "Avoid generic safe endings like a bare 'still swaying' line unless the concrete image and twist are unusually specific. "
            "If you use an English fragment, keep it to two to four words and weave it into a fuller Japanese line. "
            "If you use an English fragment inside Japanese lyrics, embed it inside a fuller line instead of leaving it as a standalone line. "
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


def _style_guidance(config: dict) -> str:
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


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


def _profile_clause(plan: dict) -> str:
    parts = [
        _profile_line("Profile steering", plan.get("profile_summary", "")),
        _profile_line("Audio direction", plan.get("audio_direction", "")),
        _profile_line("Hook direction", plan.get("hook_direction", "")),
        _profile_line("Visual carryover", plan.get("visual_direction", "")),
        _profile_line("Avoid", plan.get("negative_direction", "")),
    ]
    return "".join(parts)


def _hook_shape_clause(plan: dict) -> str:
    text = str(plan.get("hook_shape_bias", "")).strip()
    return f"Preferred hook contour={text}. " if text else ""


def _profile_line(label: str, text: object) -> str:
    val = str(text).strip()
    return f"{label}={val}. " if val else ""


def _validate_audio_plan_quality(plan: dict) -> None:
    choruses = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "chorus"]
    posts = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "post_chorus"]
    bridges = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "bridge"]
    outros = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "outro"]
    if len(choruses) < 2:
        return
    _validate_chorus_lengths(choruses)
    _validate_chorus_opening_pairs(choruses)
    _validate_chorus_line_functions(choruses)
    _validate_generic_hook_fragments(choruses)
    _validate_language_specific_hook_style(choruses, str(plan.get("language", "")).strip().lower())
    _validate_hook_title_worthiness(choruses, plan)
    _validate_second_chorus(choruses)
    _validate_post_chorus(posts, choruses[0] if choruses else {})
    _validate_bridge(bridges)
    _validate_final_chorus(choruses, bridges[-1] if bridges else {})
    _validate_outro(outros)


def _validate_chorus_lengths(choruses: list[dict]) -> None:
    first = _clean_lines(choruses[0])
    if len(first) < 6:
        raise RuntimeError("audio planner quality failure: first chorus too short")
    if len(choruses) > 1:
        second = _clean_lines(choruses[1])
        if len(second) < 6:
            raise RuntimeError("audio planner quality failure: second chorus too short")


def _validate_chorus_opening_pairs(choruses: list[dict]) -> None:
    for block in choruses:
        lines = _clean_lines(block)
        if len(lines) >= 2 and lines[0].lower() == lines[1].lower():
            raise RuntimeError("audio planner quality failure: chorus opening pair duplicates verbatim")


def _validate_chorus_line_functions(choruses: list[dict]) -> None:
    for block in choruses:
        lines = _clean_lines(block)
        if len(lines) < 4:
            continue
        opening = lines[0].lower()
        if len(lines) >= 3 and lines[2].lower() == opening:
            raise RuntimeError("audio planner quality failure: chorus stalls by repeating the hook anchor too early")
        repeated_opening = sum(1 for line in lines if line.lower() == opening)
        if repeated_opening > 2:
            raise RuntimeError("audio planner quality failure: chorus anchor repeated too many times")
        support = [line for line in lines[2:] if line.lower() not in {opening, lines[1].lower()}]
        if len(support) < 2:
            raise RuntimeError("audio planner quality failure: chorus lacks support or payoff lines")


def _validate_second_chorus(choruses: list[dict]) -> None:
    first = _clean_lines(choruses[0])
    second = _clean_lines(choruses[1])
    if first and second and first == second:
        raise RuntimeError("audio planner quality failure: second chorus duplicates first chorus exactly")


def _validate_post_chorus(posts: list[dict], first_chorus: dict) -> None:
    if not posts:
        return
    hook_lines = _clean_lines(first_chorus)[:4]
    hook_tokens = _hook_callback_tokens(hook_lines)
    for block in posts:
        lines = _clean_lines(block)
        if len(lines) < 2:
            raise RuntimeError("audio planner quality failure: post-chorus too short")
        if len(lines) > 3:
            raise RuntimeError("audio planner quality failure: post-chorus too long")
        if not _post_chorus_has_callback(lines, hook_lines, hook_tokens):
            raise RuntimeError("audio planner quality failure: post-chorus misses direct hook callback")
        if _is_fragmentary_post_chorus(lines):
            raise RuntimeError("audio planner quality failure: post-chorus feels too fragmentary")


def _validate_generic_hook_fragments(choruses: list[dict]) -> None:
    for block in choruses:
        for line in _clean_lines(block):
            low = line.lower()
            for frag in _GENERIC_HOOK_FRAGMENTS:
                if frag in low:
                    raise RuntimeError(f"audio planner quality failure: generic hook fragment '{frag}'")


def _validate_language_specific_hook_style(choruses: list[dict], language: str) -> None:
    if language != "ja":
        return
    for block in choruses:
        lines = _clean_lines(block)
        if not lines:
            continue
        opening = lines[0]
        if _is_english_heavy_japanese_hook(opening):
            raise RuntimeError("audio planner quality failure: japanese hook anchor leans too heavily on English fragment")


def _validate_hook_title_worthiness(choruses: list[dict], plan: dict) -> None:
    opening = _clean_lines(choruses[0])[0] if _clean_lines(choruses[0]) else ""
    if not opening:
        return
    if _opening_lacks_concrete_world(opening, plan):
        raise RuntimeError("audio planner quality failure: chorus opening lacks a concrete world anchor")
    language = str(plan.get("language", "")).strip().lower()
    if language == "ja" and _is_weak_japanese_hook_opening(opening):
        raise RuntimeError("audio planner quality failure: japanese hook opening feels too generic")


def _validate_bridge(bridges: list[dict]) -> None:
    if not bridges:
        return
    lines = _clean_lines(bridges[-1])
    if len(lines) < 3:
        raise RuntimeError("audio planner quality failure: bridge too short")
    if not _bridge_has_turn(lines):
        raise RuntimeError("audio planner quality failure: bridge lacks a real emotional turn")


def _validate_final_chorus(choruses: list[dict], bridge_block: dict) -> None:
    first = _clean_lines(choruses[0])
    final_block = choruses[-1]
    final = _clean_lines(final_block)
    label = str(final_block.get("label", "")).strip().lower()
    if len(choruses) >= 3 and "final chorus" not in label:
        raise RuntimeError("audio planner quality failure: final chorus label missing")
    if len(final) < 7:
        raise RuntimeError("audio planner quality failure: final chorus too short for payoff")
    if not _has_final_chorus_payoff(first, final):
        raise RuntimeError("audio planner quality failure: final chorus payoff too weak")
    if bridge_block and not _final_answers_bridge(final, _clean_lines(bridge_block)):
        raise RuntimeError("audio planner quality failure: final chorus does not answer the bridge strongly enough")


def _validate_outro(outros: list[dict]) -> None:
    if not outros:
        return
    lines = _clean_lines(outros[-1])
    if len(lines) < 2:
        raise RuntimeError("audio planner quality failure: outro too short")
    last = lines[-1]
    if _looks_like_fragment_ending(last):
        raise RuntimeError("audio planner quality failure: outro ending feels too fragmentary")


def _has_final_chorus_payoff(first: list[str], final: list[str]) -> bool:
    if not first or not final:
        return False
    if len(final) <= len(first):
        return False
    opening = first[0].lower()
    new_lines = [x for x in final[1:] if x.lower() not in {y.lower() for y in first[1:]}]
    if len(new_lines) >= 3 and final[0].lower() == opening:
        return True
    if len(final) >= 8 and len(new_lines) >= 2 and any(len(line) >= 12 for line in new_lines):
        return True
    return False


def _bridge_has_turn(lines: list[str]) -> bool:
    joined = " ".join(lines).lower()
    turn_markers = (
        "もし",
        "でも",
        "だから",
        "なのに",
        "rather",
        "even if",
        "if ",
        "but ",
        "so ",
        "still ",
        "choose",
        "選ぶ",
        "離れても",
        "戻れない",
        "言えない",
        "決めた",
    )
    return any(marker in joined for marker in turn_markers)


def _final_answers_bridge(final: list[str], bridge: list[str]) -> bool:
    if not final or not bridge:
        return True
    bridge_text = " ".join(bridge)
    if any(token in bridge_text for token in ("離れて", "帰る", "背中", "選び")):
        final_text = " ".join(final)
        answer_markers = (
            "帰さない",
            "選ぶ",
            "追いかける",
            "連れてって",
            "連れて帰る",
            "やさしい",
            "答え",
            "綺麗",
            "消えない",
            "届きたい",
            "朝",
            "隣",
            "残る",
            "待ちたい",
            "行く",
        )
        return any(marker in final_text for marker in answer_markers)
    return True


def _clean_lines(block: dict) -> list[str]:
    lines = block.get("lines", [])
    if not isinstance(lines, list):
        return []
    return [str(x).strip() for x in lines if str(x).strip()]


def _is_english_heavy_japanese_hook(text: str) -> bool:
    jp = 0
    latin_words = 0
    current_latin = []
    for ch in str(text):
        if ch.isascii() and ch.isalpha():
            current_latin.append(ch)
        else:
            if current_latin:
                latin_words += 1
                current_latin = []
            code = ord(ch)
            if (
                0x3040 <= code <= 0x309F
                or 0x30A0 <= code <= 0x30FF
                or 0x4E00 <= code <= 0x9FFF
            ):
                jp += 1
    if current_latin:
        latin_words += 1
    if latin_words == 0:
        return False
    return jp < 6 or latin_words > 2


def _opening_lacks_concrete_world(text: str, plan: dict) -> bool:
    opening = str(text).strip()
    hook_direction = str(plan.get("hook_direction", "")).strip()
    profile_summary = str(plan.get("profile_summary", "")).strip()
    candidates = _collect_world_tokens(hook_direction) | _collect_world_tokens(profile_summary)
    if not candidates:
        return False
    return not any(token in opening for token in candidates)


def _collect_world_tokens(text: str) -> set[str]:
    out: set[str] = set()
    buf = []
    for ch in str(text):
        code = ord(ch)
        is_jp = (
            0x3040 <= code <= 0x309F
            or 0x30A0 <= code <= 0x30FF
            or 0x4E00 <= code <= 0x9FFF
        )
        if is_jp:
            buf.append(ch)
            continue
        if buf:
            token = "".join(buf)
            if len(token) >= 2:
                out.add(token)
            buf = []
    if buf:
        token = "".join(buf)
        if len(token) >= 2:
            out.add(token)
    return out


def _is_weak_japanese_hook_opening(text: str) -> bool:
    opening = str(text).strip()
    for ending in _WEAK_JA_HOOK_ENDINGS:
        if opening.endswith(ending):
            return True
    return False


def _post_chorus_has_callback(lines: list[str], hook_lines: list[str], hook_tokens: set[str]) -> bool:
    lowered = [line.lower() for line in lines]
    if any(line in {x.lower() for x in hook_lines} for line in lowered):
        return True
    return any(any(token in line for token in hook_tokens) for line in lines)


def _hook_callback_tokens(lines: list[str]) -> set[str]:
    tokens: set[str] = set()
    for line in lines:
        tokens |= _collect_world_tokens(line)
        for word in str(line).lower().replace("?", " ").replace("!", " ").split():
            word = word.strip(".,:;-'\"")
            if len(word) >= 4 and word.isascii():
                tokens.add(word)
    return tokens


def _looks_like_fragment_ending(text: str) -> bool:
    line = str(text).strip()
    if not line:
        return True
    if "　" not in line and " " not in line:
        jp_tokens = _collect_world_tokens(line)
        if jp_tokens and next(iter(jp_tokens)) == line:
            return True
    low = line.lower()
    weak_suffixes = (
        "afterglow",
        "アフターグロウ",
        "余熱",
        "残像",
    )
    if any(low == suffix.lower() or low.endswith(" " + suffix.lower()) for suffix in weak_suffixes):
        return True
    return False


def _is_fragmentary_post_chorus(lines: list[str]) -> bool:
    if not lines:
        return True
    if any(len(line) >= 9 for line in lines):
        return False
    joined = " ".join(lines)
    if any(ch in joined for ch in ("、", "。", "，", ",")):
        return False
    return True


def _plan_with_quality_attempts(config: dict, plan: dict) -> dict:
    attempts = _planner_attempts(config)
    last: Exception | None = None
    passing: list[tuple[int, int, dict]] = []
    for idx in range(attempts):
        try:
            attempt_plan = _attempt_plan(plan, idx)
            normalized = _normalize_and_validate(config, attempt_plan)
            passing.append((_score_audio_candidate(normalized), idx, normalized))
        except RuntimeError as exc:
            last = exc
    if passing:
        return _best_passing_candidate(passing)
    raise last if last else RuntimeError("audio planner failed")


def _normalize_and_validate(config: dict, plan: dict) -> dict:
    planned = _plan_with_llm(config, plan)
    normalized = normalize_audio_fields(planned)
    normalized["tags"] = plan["tags"]
    normalized["style_guidance"] = plan["style_guidance"]
    normalized["language"] = plan["language"]
    normalized["profile_summary"] = plan["profile_summary"]
    normalized["audio_direction"] = plan["audio_direction"]
    normalized["hook_direction"] = plan["hook_direction"]
    normalized["visual_direction"] = plan["visual_direction"]
    normalized["negative_direction"] = plan["negative_direction"]
    normalized["filename_prefix"] = plan["filename_prefix"]
    normalized["quality"] = plan["quality"]
    if not str(normalized.get("keyscale", "")).strip():
        normalized["keyscale"] = str(plan.get("keyscale", "")).strip()
    validate_audio_genre_description_language(normalized["genre_description"])
    validate_audio_lyrics_language(normalized["lyrics"], plan["language"])
    _validate_audio_plan_quality(normalized)
    return normalized


def _attempt_plan(plan: dict, idx: int) -> dict:
    out = dict(plan)
    seed = int(plan.get("seed", 31)) + (idx * 1009)
    out["seed"] = seed
    out["hook_shape_bias"] = _hook_shape_bias(seed, str(plan.get("language", "")).strip().lower())
    return out


def _planner_attempts(config: dict) -> int:
    audio = _audio_config(config)
    raw = audio.get("planner_attempts", 3) if isinstance(audio, dict) else 3
    try:
        return max(1, int(raw))
    except Exception:
        return 3


def _best_passing_candidate(passing: list[tuple[int, int, dict]]) -> dict:
    ranked = sorted(passing, key=lambda item: (item[0], -item[1]), reverse=True)
    return ranked[0][2]


def _score_audio_candidate(plan: dict) -> int:
    return (
        _score_chorus_progression(plan)
        + _score_final_payoff(plan)
        + _score_bridge_turn(plan)
        + _score_outro_closure(plan)
    )


def _score_chorus_progression(plan: dict) -> int:
    choruses = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "chorus"]
    if len(choruses) < 2:
        return 0
    first = _clean_lines(choruses[0])
    second = _clean_lines(choruses[1])
    first_support = {line.lower() for line in first[2:]}
    second_support = {line.lower() for line in second[2:]}
    changed = len(second_support - first_support)
    return min(4, changed * 2)


def _score_final_payoff(plan: dict) -> int:
    choruses = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "chorus"]
    if len(choruses) < 2:
        return 0
    first = _clean_lines(choruses[0])
    final = _clean_lines(choruses[-1])
    base = 2 if len(final) >= 8 else 1
    first_tail = {line.lower() for line in first[1:]}
    new_lines = sum(1 for line in final[1:] if line.lower() not in first_tail)
    vivid = sum(1 for line in final if len(line.strip()) >= 12)
    return base + min(4, new_lines) + min(2, vivid // 2)


def _score_bridge_turn(plan: dict) -> int:
    bridges = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "bridge"]
    if not bridges:
        return 0
    lines = _clean_lines(bridges[-1])
    text = " ".join(lines)
    weight = 2 if _bridge_has_turn(lines) else 0
    markers = ("でも", "もし", "選び", "足りない", "戻れない", "言えない", "決めた")
    return weight + sum(1 for marker in markers if marker in text)


def _score_outro_closure(plan: dict) -> int:
    outros = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "outro"]
    if not outros:
        return 0
    lines = _clean_lines(outros[-1])
    if len(lines) < 2:
        return 0
    last = lines[-1]
    if _looks_like_fragment_ending(last):
        return 0
    settle_markers = ("着いた", "終わる", "ほどける", "残る", "静か", "朝", "隣", "着く")
    return 2 + sum(1 for marker in settle_markers if marker in last)


def _hook_shape_bias(seed: int, language: str) -> str:
    if language == "ja":
        shapes = (
            "concrete image plus destination or ride noun",
            "street object plus emotional echo",
            "reflection cue plus afterglow or remaining heat",
            "weather or light cue plus reaching motion",
        )
        return shapes[seed % len(shapes)]
    shapes = (
        "concrete image plus destination",
        "place cue plus emotional echo",
        "reflection cue plus afterglow",
        "weather cue plus motion",
    )
    return shapes[seed % len(shapes)]
