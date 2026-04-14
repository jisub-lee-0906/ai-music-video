from __future__ import annotations

import re
from collections import Counter

from ai_mv.core.output_paths import audio_prefix
from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
    validate_audio_lyrics_quality,
)
from ai_mv.core.contracts.prompt_schema import audio_outline_schema
from ai_mv.engines.acestep_1_5_aio.policy import audio_policy, bar_lane_summary, preferred_songform_rows
from ai_mv.engines.acestep_1_5_aio.prompting import (
    _audio_config,
    _audio_language,
    _audio_outline_prompt,
    _audio_prompt,
    _audio_tags,
    _ending_policy,
    _ending_policy_digest,
    _intent_clause,
    _language_clause,
)
from ai_mv.engines.acestep_1_5_aio.lyric_blocks import (
    _audio_lyrics_draft_prompt,
    _audio_lyrics_draft_system_prompt,
    _audio_lyrics_block_prompt,
    _audio_lyrics_block_system_prompt,
    _audio_lyrics_rules_qwen,
    _parse_audio_lyrics_draft,
    _audio_retry_clause,
    _current_block_constraints,
    _normalize_lyric_line,
    _parse_audio_lyrics_block_lines,
    _shared_lyric_line_count,
    _validate_generated_block,
)
from ai_mv.infra.codex_cli_client import generate_structured, generate_text


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = _audio_source(config)
    tags = _audio_tags(audio)
    plan = {
        "tags": tags,
        "filename_prefix": audio_prefix(payload["run_id"]),
    }
    plan.update(_audio_fixed_fields(audio))
    plan.update(_audio_intent_fields(audio))
    plan.update(audio_policy({"audio": audio}))
    return _plan_once(config, plan)


def build_audio_preview_prompt(plan: dict) -> str:
    return _audio_outline_prompt(plan)


def _plan_with_llm(config: dict, plan: dict) -> dict:
    outline = _plan_outline_with_llm(config, plan)
    return _plan_lyrics_with_llm(config, plan, outline)


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
    validate_audio_lyrics_quality(
        normalized["lyrics_blocks"],
        str(plan.get("language", "")).strip(),
        dict(plan.get("line_budgets", {})) if isinstance(plan.get("line_budgets", {}), dict) else {},
        dict(plan.get("section_bars", {})) if isinstance(plan.get("section_bars", {}), dict) else {},
    )
    _validate_ending_contract(plan, normalized)
    normalized["lyrics_blocks"] = _attach_line_indexes(normalized.get("lyrics_blocks", []))
    normalized["lyrics"] = _render_final_lyrics(plan, normalized.get("lyrics_blocks", []))
    normalized["duration"] = _resolved_duration(plan, normalized)
    normalized.update(_audio_runtime_context(plan))
    normalized["beats_per_bar"] = int(plan.get("beats_per_bar", 4))
    normalized["section_bars"] = dict(plan.get("section_bars", {}))
    normalized["bar_lane"] = bar_lane_summary(
        normalized.get("lyrics_blocks", []),
        dict(plan.get("section_bars", {})) if isinstance(plan.get("section_bars", {}), dict) else {},
    )
    normalized["ending_mode"] = str(plan.get("ending_mode", "")).strip()
    normalized["terminal_end_tag"] = bool(plan.get("terminal_end_tag", False))
    normalized["final_chorus_required"] = bool(plan.get("final_chorus_required", False))
    normalized["outro_required"] = bool(plan.get("outro_required", False))
    normalized["ending_vocal_density"] = str(plan.get("ending_vocal_density", "")).strip()
    normalized["ending_tags"] = list(plan.get("ending_tags", [])) if isinstance(plan.get("ending_tags", []), list) else []
    normalized["line_budgets"] = dict(plan.get("line_budgets", {})) if isinstance(plan.get("line_budgets", {}), dict) else {}
    normalized["bpm"] = int(normalized.get("bpm", 0) or int(plan.get("bpm", 0) or 0))
    normalized["keyscale"] = str(normalized.get("keyscale", "")).strip() or str(plan.get("keyscale", "")).strip()
    return normalized


def _audio_fixed_fields(audio: dict) -> dict:
    return {
        "language": _audio_language(audio),
        "genre_head": str(audio.get("genre_head", "")).strip(),
        "vocal_profile": str(audio.get("vocal_profile", "")).strip(),
        "vocal_tone": str(audio.get("vocal_tone", "")).strip(),
    }


def _audio_intent_fields(audio: dict) -> dict:
    return {
        "audio_direction": str(audio.get("brief", "")).strip(),
        "hook_brief": str(audio.get("hook_brief", "")).strip(),
        "negative_direction": " ".join(
            part for part in [str(audio.get("negative_direction", "")).strip(), str(audio.get("avoid", "")).strip()] if part
            ).strip(),
    }


def _audio_source(config: dict) -> dict:
    audio = _audio_config(config)
    prompt = str(config.get("prompt", "")).strip() if isinstance(config, dict) else ""
    concept_text = str(config.get("concept_text", "")).strip() if isinstance(config, dict) else ""
    genre = str(config.get("genre", "")).strip() if isinstance(config, dict) else ""
    voice = str(config.get("voice", "")).strip() if isinstance(config, dict) else ""
    profile, tone = _split_voice(voice or str(audio.get("vocal_profile", "")).strip())
    merged = dict(audio)
    audio_brief = str(audio.get("brief", "")).strip()
    selected_prompt = audio_brief or prompt or concept_text
    selected_hook_brief = str(audio.get("hook_brief", "")).strip() or audio_brief or prompt or concept_text
    merged["language"] = "ja"
    if selected_prompt:
        merged["brief"] = selected_prompt
    if selected_hook_brief:
        merged["hook_brief"] = selected_hook_brief
    if not genre and _looks_like_citypop(concept_text):
        genre = "city pop"
    if genre:
        merged["genre_head"] = genre
    if profile:
        merged["vocal_profile"] = profile
    if tone:
        merged["vocal_tone"] = tone
    return merged


def _split_voice(text: str) -> tuple[str, str]:
    cleaned = " ".join(str(text).strip().split())
    if not cleaned:
        return "", ""
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if len(parts) <= 1:
        return cleaned, ""
    return parts[0], ", ".join(parts[1:])


def _looks_like_citypop(text: str) -> bool:
    low = str(text).strip().lower()
    return "city pop" in low or "citypop" in low


def _audio_runtime_context(plan: dict) -> dict:
    return {
        "tags": plan["tags"],
        "language": str(plan.get("language", "")).strip(),
        "filename_prefix": str(plan.get("filename_prefix", "")).strip(),
        "songform_variants": list(plan.get("songform_variants", [])) if isinstance(plan.get("songform_variants", []), list) else [],
        "genre_head": str(plan.get("genre_head", "")).strip(),
        "vocal_profile": str(plan.get("vocal_profile", "")).strip(),
        "vocal_tone": str(plan.get("vocal_tone", "")).strip(),
        "quality": plan["quality"],
        "audio_direction": str(plan.get("audio_direction", "")).strip(),
        "hook_brief": str(plan.get("hook_brief", "")).strip(),
        "negative_direction": str(plan.get("negative_direction", "")).strip(),
    }


def _render_final_lyrics(plan: dict, blocks: list[dict]) -> str:
    lines: list[str] = []
    for row in blocks:
        label = str(row.get("label", "")).strip()
        body = [str(x).strip() for x in row.get("lines", []) if str(x).strip()]
        if not label:
            continue
        if not body and label.lower() not in {"intro", "outro"}:
            continue
        lines.append(f"[{label}]")
        if body:
            lines.extend(body)
        lines.append("")
    text = "\n".join(lines).strip()
    if bool(plan.get("terminal_end_tag", False)):
        return f"{text}\n\n[end]" if text else "[end]"
    return text


def _plan_outline_with_llm(config: dict, plan: dict) -> dict:
    prompt = _audio_outline_prompt(plan)
    last_exc: Exception | None = None
    attempt_prompt = prompt
    for _ in range(3):
        outline = generate_structured(config, attempt_prompt, audio_outline_schema())
        normalized = _normalize_audio_outline(outline)
        try:
            _validate_outline_labels(normalized)
            _validate_outline_line_budgets(plan, normalized)
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


def _plan_hook_candidates_with_llm(config: dict, plan: dict) -> dict:
    fallback = _fallback_hook_state(plan)
    try:
        raw = generate_structured(config, _hook_candidates_prompt(plan), _hook_candidates_schema())
        candidates = _normalize_hook_candidates(raw)
        selected = _select_best_hook_candidate(candidates, plan)
        return {
            "hook_candidates": candidates,
            "selected_hook_candidate": selected,
        }
    except Exception:
        return fallback


def _plan_lyrics_with_llm(config: dict, plan: dict, outline: dict) -> dict:
    completed = _generate_lyrics_draft(config, plan, outline)
    completed = _polish_lyrics_sections(config, plan, outline, completed)
    return _merge_audio_outline_and_lyrics(outline, {"lyrics_blocks": completed})


def _normalize_audio_outline(raw: dict) -> dict:
    raw_rows = [row for row in raw.get("lyrics_blocks", []) if isinstance(row, dict)]
    chorus_indexes = [idx for idx, row in enumerate(raw_rows) if str(row.get("section", "")).strip() == "chorus"]
    pre_count = 0
    chorus_seen = 0
    blocks = []
    for idx, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            continue
        section = str(row.get("section", "")).strip()
        if section == "pre_chorus":
            pre_count += 1
        if section == "chorus":
            chorus_seen += 1
        label = _canonical_outline_label(section, str(row.get("label", "")).strip(), idx, chorus_indexes, pre_count, chorus_seen)
        line_count = int(row.get("line_count", 0))
        blocks.append(
            {
                "section": section,
                "label": label,
                "style": str(row.get("style", "")).strip(),
                "role": str(row.get("role", "")).strip(),
                "change": str(row.get("change", "")).strip(),
                "line_count": max(0, line_count),
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


def _canonical_outline_label(
    section: str,
    label: str,
    idx: int,
    chorus_indexes: list[int],
    pre_count: int,
    chorus_seen: int,
) -> str:
    if section == "intro":
        return "Intro"
    if section == "verse_1":
        return "Verse 1"
    if section == "verse_2":
        return "Verse 2"
    if section == "pre_chorus":
        return "Pre-Chorus" if pre_count <= 1 else "Pre-Chorus 2"
    if section == "chorus":
        if chorus_indexes and idx == chorus_indexes[-1] and len(chorus_indexes) >= 2:
            return "Final Chorus"
        return "Chorus" if chorus_seen <= 1 else "Chorus 2"
    if section == "post_chorus":
        return "Post-Chorus"
    if section == "bridge":
        return "Bridge"
    if section == "outro":
        return "Outro"
    return label


def _validate_outline_labels(outline: dict) -> None:
    allowed = {
        "Intro",
        "Verse 1",
        "Verse 2",
        "Pre-Chorus",
        "Pre-Chorus 2",
        "Chorus",
        "Chorus 2",
        "Post-Chorus",
        "Bridge",
        "Final Chorus",
        "Outro",
    }
    labels: list[str] = []
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        if label and label not in allowed:
            raise RuntimeError(f"invalid section label: {label}")
        if label:
            labels.append(label)
        if not str(block.get("role", "")).strip():
            raise RuntimeError(f"outline role missing for {label}")
        if not str(block.get("change", "")).strip():
            raise RuntimeError(f"outline change missing for {label}")
        line_count = int(block.get("line_count", 0) or 0)
        if line_count <= 0 and not _allows_zero_line_block(block):
            raise RuntimeError(f"zero-line block allowed only for Intro or Outro: {label}")
    _validate_outline_special_label_shape(outline.get("lyrics_blocks", []), labels)


def _validate_outline_special_label_shape(blocks: object, labels: list[str]) -> None:
    final_count = sum(1 for label in labels if label == "Final Chorus")
    if final_count > 1:
        raise RuntimeError("invalid section label sequence: Final Chorus may appear only once")
    chorus_family = [
        str(block.get("label", "")).strip()
        for block in blocks
        if isinstance(block, dict) and str(block.get("section", "")).strip().lower() == "chorus"
    ]
    if "Final Chorus" in chorus_family and chorus_family[-1] != "Final Chorus":
        raise RuntimeError("invalid section label sequence: Final Chorus must be the last chorus-family block")


def _validate_outline_line_budgets(plan: dict, outline: dict) -> None:
    budgets = plan.get("line_budgets", {}) if isinstance(plan.get("line_budgets", {}), dict) else {}
    bpm = int(outline.get("bpm", 0) or 0)
    if bpm <= 0:
        raise RuntimeError("bpm must be a positive integer")
    if not budgets:
        return
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        max_lines = int(budgets.get(label, 0) or 0)
        line_count = int(block.get("line_count", 0) or 0)
        if max_lines <= 0:
            if label in budgets and line_count != 0:
                raise RuntimeError(f"line_count must stay instrumental for {label}: {line_count} > 0")
            continue
        if line_count > max_lines:
            raise RuntimeError(f"line_count too dense for {label}: {line_count} > {max_lines}")
    _validate_short_form_songform(plan, outline)


def _validate_short_form_songform(plan: dict, outline: dict) -> None:
    max_sec = int(plan.get("duration_max_sec", 0) or 0)
    labels = [str(block.get("label", "")).strip() for block in outline.get("lyrics_blocks", []) if isinstance(block, dict)]
    if max_sec <= 0 or max_sec > 180:
        return
    crowded = {"Post-Chorus", "Chorus 2", "Pre-Chorus 2"} & set(labels)
    if len(crowded) >= 3:
        raise RuntimeError("short-form city pop outline too crowded: avoid using Post-Chorus, Pre-Chorus 2, and Chorus 2 together")
    if "Post-Chorus" in labels and "Chorus 2" in labels and "Bridge" in labels:
        raise RuntimeError("short-form city pop outline too crowded: avoid combining Post-Chorus, Chorus 2, and Bridge in one under-3-minute song")


def _hook_candidates_prompt(plan: dict) -> str:
    fragments = [str(x).strip() for x in plan.get("hook_english_fragments", []) if str(x).strip()]
    fragment_text = ", ".join(fragments)
    language = str(plan.get("language", "")).strip() or "the requested language"
    genre = str(plan.get("genre", "")).strip() or "the requested genre"
    return (
        "Generate chorus hook candidates for a song. "
        "Return JSON only. No markdown. "
        "Make 6 candidates for chorus-family use only. "
        "Each candidate must be a short hook fragment, not a full sentence. "
        "Good candidates are easy to chant, easy to remember, and can sit at the start of a chorus line. "
        f"Keep the requested language dominant overall. Requested language={language}. "
        "A secondary language is optional and, if used, must stay within one to three words. "
        "Do not write long cross-language phrases. "
        "Prefer hooks tied to the song's emotional turn or central image over generic slogans. "
        "Bad candidates: vague phrases like all night, forever, stay with me, call my name when they are not anchored to this song's own meaning. "
        "Good candidates: short phrases that can become title-worthy because they belong to this exact song. "
        f"Genre={genre}. "
        f"Hook intent={str(plan.get('hook_direction', '')).strip()}. "
        + (f"Preferred optional English fragments={fragment_text}. " if fragment_text else "")
        + "For each candidate, provide fragment, language_mode, placement, and why. "
        + "language_mode must be one of primary_only or mixed_language. "
        + "placement must be one of chorus, chorus2, final_chorus. "
    )


def _hook_candidates_schema() -> dict:
    item = {
        "type": "object",
        "required": ["fragment", "language_mode", "placement", "why"],
        "properties": {
            "fragment": {"type": "string"},
            "language_mode": {"type": "string", "enum": ["primary_only", "mixed_language"]},
            "placement": {"type": "string", "enum": ["chorus", "chorus2", "final_chorus"]},
            "why": {"type": "string"},
        },
    }
    return {
        "type": "object",
        "required": ["candidates"],
        "properties": {
            "candidates": {"type": "array", "items": item, "minItems": 4, "maxItems": 8}
        },
    }


def _normalize_hook_candidates(raw: dict) -> list[dict]:
    out: list[dict] = []
    for row in raw.get("candidates", []) if isinstance(raw, dict) else []:
        if not isinstance(row, dict):
            continue
        fragment = " ".join(str(row.get("fragment", "")).strip().split())
        language_mode = str(row.get("language_mode", "")).strip()
        placement = str(row.get("placement", "")).strip()
        why = " ".join(str(row.get("why", "")).strip().split())
        if not fragment or language_mode not in {"primary_only", "mixed_language"} or placement not in {"chorus", "chorus2", "final_chorus"}:
            continue
        out.append(
            {
                "fragment": fragment,
                "language_mode": language_mode,
                "placement": placement,
                "why": why,
            }
        )
    if not out:
        raise RuntimeError("hook candidates missing")
    return out


def _select_best_hook_candidate(candidates: list[dict], plan: dict) -> dict:
    scored = sorted(
        (( _score_hook_candidate(row, plan), row) for row in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return dict(scored[0][1]) if scored else {}


def _score_hook_candidate(row: dict, plan: dict) -> int:
    fragment = str(row.get("fragment", "")).strip()
    language_mode = str(row.get("language_mode", "")).strip()
    placement = str(row.get("placement", "")).strip()
    lower = fragment.lower()
    english_fragments = [str(x).strip().lower() for x in plan.get("hook_english_fragments", []) if str(x).strip()]
    intent_keywords = _intent_keywords(str(plan.get("audio_direction", "")).strip())
    words = [token for token in re.split(r"\s+", fragment) if token]
    score = 0
    if placement == "chorus":
        score += 3
    elif placement == "final_chorus":
        score += 2
    if len(fragment) <= 14:
        score += 3
    elif len(fragment) <= 20:
        score += 1
    if language_mode == "primary_only":
        score += 4
    elif language_mode == "mixed_language":
        score += 1
    if any(frag == lower for frag in english_fragments):
        score -= 2
    if len(words) <= 3:
        score += 2
    if "," not in fragment and "." not in fragment:
        score += 1
    if re.search(r"[가-힣]", fragment):
        score += 2
    if any(token in fragment for token in ("밤", "심장", "불꽃", "기억", "끝", "너머", "숨", "빛")):
        score += 3
    if any(keyword and keyword in fragment for keyword in intent_keywords):
        score += 5
    score -= _generic_hook_penalty(fragment, plan)
    return score


def _generic_hook_penalty(fragment: str, plan: dict) -> int:
    lower = str(fragment).strip().lower()
    tokens = [token for token in re.findall(r"[가-힣]{1,}|[a-z]+", lower) if token]
    penalty = 0
    generic_phrases = {
        "all night", "forever", "stay with me", "call my name", "hold on", "let it go", "run it back",
        "baby", "tonight", "my heart",
        "사랑해", "영원히", "다시 다시", "놓지 마", "돌아와", "잊지 마",
    }
    if lower in generic_phrases:
        penalty += 6
    generic_tokens = {
        "baby", "tonight", "forever", "heart", "love", "all", "night", "hold", "stay", "call",
        "다시", "영원", "사랑", "마음", "너", "우리",
    }
    generic_count = sum(1 for token in tokens if token in generic_tokens)
    if generic_count >= max(2, len(tokens)):
        penalty += 4
    intent_keywords = set(_intent_keywords(str(plan.get("audio_direction", "")).strip()))
    if intent_keywords and not any(token in intent_keywords for token in tokens):
        penalty += 1
    if len(tokens) >= 2 and len(set(tokens)) == 1:
        penalty += 3
    return penalty


def _intent_keywords(text: str) -> list[str]:
    lowered = str(text).strip().lower()
    if not lowered:
        return []
    blocked = {
        "song", "about", "that", "with", "from", "into", "through", "while", "the", "and", "late", "night",
        "emotion", "starts", "start", "grows", "more", "direct", "before", "bridge", "resolves", "clear", "forward",
        "release", "instead", "collapsing", "despair", "relationship", "walking",
        "song", "pop", "korean", "language",
    }
    found: list[str] = []
    for token in re.findall(r"[가-힣]{2,}|[a-z]{3,}", lowered):
        if token in blocked:
            continue
        if token not in found:
            found.append(token)
    return found[:8]


def _fallback_hook_state(plan: dict) -> dict:
    fragments = [str(x).strip() for x in plan.get("hook_english_fragments", []) if str(x).strip()]
    candidates: list[dict] = []
    for idx, fragment in enumerate(fragments[:3], start=1):
        placement = "chorus" if idx == 1 else "chorus2" if idx == 2 else "final_chorus"
        candidates.append(
            {
                "fragment": fragment,
                "language_mode": "mixed_language",
                "placement": placement,
                "why": "Profile-guided short English hook fragment.",
            }
        )
    if not candidates:
        language = str(plan.get("language", "")).strip().lower()
        fallback_fragment = "残る灯り" if language == "ja" else "남은 불빛" if language == "ko" else "remaining light"
        fallback_why = (
            "Fallback Japanese chorus hook from the song profile."
            if language == "ja"
            else "Fallback Korean chorus hook from the song profile."
            if language == "ko"
            else "Fallback English chorus hook from the song profile."
        )
        candidates.append(
            {
                "fragment": fallback_fragment,
                "language_mode": "primary_only",
                "placement": "chorus",
                "why": fallback_why,
            }
        )
    return {
        "hook_candidates": candidates,
        "selected_hook_candidate": dict(candidates[0]),
    }


def _merge_audio_outline_and_lyrics(outline: dict, filled: dict) -> dict:
    keyed = [row for row in filled.get("lyrics_blocks", []) if isinstance(row, dict)]
    if len(keyed) != len(outline.get("lyrics_blocks", [])):
        raise RuntimeError("audio lyrics fill block count mismatch")
    blocks: list[dict] = []
    for spec, row in zip(outline.get("lyrics_blocks", []), keyed):
        section = str(row.get("section", "")).strip()
        label = str(row.get("label", "")).strip()
        style = str(row.get("style", "")).strip()
        role = str(spec.get("role", "")).strip()
        change = str(spec.get("change", "")).strip()
        if section != spec["section"] or label != spec["label"] or style != spec["style"]:
            raise RuntimeError("audio lyrics fill diverged from locked outline")
        lines = [str(x).strip() for x in row.get("lines", []) if str(x).strip()]
        if len(lines) != int(spec["line_count"]):
            raise RuntimeError("audio lyrics fill line count mismatch")
        blocks.append({"section": section, "label": label, "style": style, "role": role, "change": change, "lines": lines})
    return {
        "genre_description": outline["genre_description"],
        "bpm": outline["bpm"],
        "keyscale": outline["keyscale"],
        "seed": outline["seed"],
        "duration": outline["duration"],
        "lyrics_blocks": blocks,
    }


def _generate_lyrics_block(config: dict, plan: dict, outline: dict, completed: list[dict], block: dict) -> dict:
    return _generate_lyrics_block_with_note(config, plan, outline, completed, block, "")


def _generate_lyrics_block_with_note(
    config: dict,
    plan: dict,
    outline: dict,
    completed: list[dict],
    block: dict,
    revision_note: str,
) -> dict:
    if int(block.get("line_count", 0) or 0) == 0:
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": [],
        }
    prompt = _audio_lyrics_block_prompt(plan, outline, completed, block)
    if revision_note:
        prompt += revision_note.strip() + " "
    last_exc: Exception | None = None
    attempt_prompt = prompt
    for _ in range(4):
        filled = generate_text(
            config,
            _audio_lyrics_block_system_prompt(plan, block) + "\n\n" + attempt_prompt,
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


def _generate_lyrics_draft(config: dict, plan: dict, outline: dict) -> list[dict]:
    prompt = _audio_lyrics_draft_prompt(plan, outline)
    last_exc: Exception | None = None
    attempt_prompt = prompt
    parsed: list[dict] | None = None
    for _ in range(4):
        drafted = generate_text(
            config,
            _audio_lyrics_draft_system_prompt(plan, outline) + "\n\n" + attempt_prompt,
        )
        try:
            parsed = _parse_audio_lyrics_draft(outline, drafted)
            break
        except RuntimeError as exc:
            last_exc = exc
            previous_attempt = "\n".join(line.strip() for line in str(drafted).splitlines() if line.strip())
            attempt_prompt = (
                prompt
                + f"\nCorrection note: your previous full draft failed validation with this exact error: {exc}. "
                + (f"\nPrevious invalid attempt:\n{previous_attempt}\n" if previous_attempt else "")
                + "\nRewrite the full song from scratch using the exact locked headers and exact line counts."
            )
    if parsed is None:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("audio lyrics draft failed without a captured error")
    completed: list[dict] = []
    for spec, candidate in zip(outline.get("lyrics_blocks", []), parsed):
        block = dict(spec)
        if int(block.get("line_count", 0) or 0) == 0:
            completed.append(candidate)
            continue
        try:
            _validate_generated_block(plan, completed, candidate)
            completed.append(candidate)
        except RuntimeError:
            completed.append(_generate_lyrics_block(config, plan, outline, completed, block))
    return completed


def _refresh_overused_imagery(config: dict, plan: dict, outline: dict, blocks: list[dict]) -> list[dict]:
    overused = _find_overused_image_tokens(plan, blocks)
    if not overused:
        return blocks
    refreshed: list[dict] = []
    refreshable_labels = {"Verse 2", "Pre-Chorus 2", "Chorus 2", "Bridge", "Final Chorus"}
    rewrites = 0
    for block in blocks:
        label = str(block.get("label", "")).strip()
        repeated = _block_overused_tokens(block, overused)
        if rewrites < 2 and label in refreshable_labels and len(repeated) >= 2:
            block_spec = next(
                (
                    dict(row)
                    for row in outline.get("lyrics_blocks", [])
                    if str(row.get("label", "")).strip() == label
                ),
                {
                    "section": str(block.get("section", "")).strip(),
                    "label": label,
                    "style": str(block.get("style", "")).strip(),
                    "line_count": len([str(x).strip() for x in block.get("lines", []) if str(x).strip()]),
                },
            )
            carry = _carry_world_tokens(blocks, block)
            note = (
                "Refresh this section with more varied concrete imagery. "
                f"Avoid leaning again on these overused words or image anchors: {', '.join(repeated)}. "
                + (f"Stay inside the established world and reuse only already-grounded image anchors such as: {', '.join(carry)}. " if carry else "")
                + "Do not invent a brand-new place, prop, or scene object that has not already been grounded by the song draft. "
                "Keep the same emotional role and section function. "
            )
            rewritten = _generate_lyrics_block_with_note(config, plan, outline, refreshed, block_spec, note)
            refreshed.append(rewritten)
            rewrites += 1
            continue
        refreshed.append(block)
    return refreshed


def _find_overused_image_tokens(plan: dict, blocks: list[dict]) -> set[str]:
    counts: Counter[str] = Counter()
    for block in blocks:
        counts.update(set(_block_image_tokens(plan, block)))
    return {
        token
        for token, count in counts.items()
        if count >= 3
    }


def _block_overused_tokens(block: dict, overused: set[str]) -> list[str]:
    found: list[str] = []
    for token in _block_image_tokens({}, block):
        if token in overused and token not in found:
            found.append(token)
    return found


def _block_image_tokens(plan: dict, block: dict) -> list[str]:
    text = " ".join(str(line).strip().lower() for line in block.get("lines", []) if str(line).strip())
    hook = str(plan.get("selected_hook_candidate", {}).get("fragment", "")).strip().lower()
    excluded = set(_intent_keywords(hook))
    excluded.update(
        {
            "나는", "너를", "너의", "이제는", "아직도", "오늘은", "오늘의", "다시", "마음", "사랑", "도시",
            "walk", "night", "heart", "love", "city", "again", "still", "into", "through",
        }
    )
    tokens: list[str] = []
    for token in re.findall(r"[가-힣]{2,}|[a-z]{3,}", text):
        if token in excluded:
            continue
        tokens.append(token)
    return tokens


def _carry_world_tokens(blocks: list[dict], current_block: dict) -> list[str]:
    current_label = str(current_block.get("label", "")).strip()
    carry: list[str] = []
    for block in blocks:
        label = str(block.get("label", "")).strip()
        if label == current_label:
            break
        for token in _block_image_tokens({}, block):
            if token not in carry:
                carry.append(token)
    return carry[:8]


def _refresh_hook_fit(config: dict, plan: dict, outline: dict, blocks: list[dict]) -> list[dict]:
    selected_hook = str(plan.get("selected_hook_candidate", {}).get("fragment", "")).strip()
    if not selected_hook:
        return blocks
    refreshed = list(blocks)
    rewrites = 0
    for idx, block in enumerate(refreshed):
        label = str(block.get("label", "")).strip()
        if label not in {"Chorus", "Chorus 2", "Final Chorus"}:
            continue
        if not _chorus_hook_fit_needs_refresh(plan, block):
            continue
        if rewrites >= 3:
            break
        carry = _carry_world_tokens(refreshed, block)
        block_spec = next(
            (
                dict(row)
                for row in outline.get("lyrics_blocks", [])
                if str(row.get("label", "")).strip() == label
            ),
            {
                "section": str(block.get("section", "")).strip(),
                "label": label,
                "style": str(block.get("style", "")).strip(),
                "line_count": len([str(x).strip() for x in block.get("lines", []) if str(x).strip()]),
            },
        )
        note = (
            f"Refresh this {label} so the hook feels native to this song's world. "
            f"Use the exact selected hook '{selected_hook}' once in this section. "
            + (
                "Put it in the first line or the last line so the section lands clearly. "
                if label == "Chorus"
                else "Keep the exact hook center while rewriting the surrounding lines so this section still evolves. "
            )
            + (
                "This final return should still contain the exact hook once, but the surrounding lines must feel like resolution rather than repetition. "
                if label == "Final Chorus"
                else ""
            )
            + "Make the hook feel emotionally and sonically natural instead of slogan-like. "
            "Do not drop in an imported catchphrase that feels disconnected from the rest of the lyric language. "
            + (f"Keep continuity with these already-grounded image anchors: {', '.join(carry)}. " if carry else "")
            + "Keep the same section function and exact line count. "
        )
        refreshed[idx] = _generate_lyrics_block_with_note(
            config,
            plan,
            outline,
            refreshed[:idx],
            block_spec,
            note,
        )
        rewrites += 1
    return refreshed


def _chorus_hook_fit_needs_refresh(plan: dict, block: dict) -> bool:
    lines = [str(line).strip() for line in block.get("lines", []) if str(line).strip()]
    if not lines:
        return False
    text = " ".join(lines).lower()
    selected_hook = str(plan.get("selected_hook_candidate", {}).get("fragment", "")).strip().lower()
    english_fragments = [str(x).strip().lower() for x in plan.get("hook_english_fragments", []) if str(x).strip()]
    if selected_hook and selected_hook not in text:
        return True
    if str(plan.get("language", "")).strip().lower() == "ko" and any(fragment and fragment in text for fragment in english_fragments):
        return True
    return False


def _polish_lyrics_sections(config: dict, plan: dict, outline: dict, blocks: list[dict]) -> list[dict]:
    targets = _plan_lyrics_rewrite_targets_with_llm(config, plan, blocks)
    if not targets:
        return blocks
    refreshed = list(blocks)
    target_map = {str(row.get("label", "")).strip(): str(row.get("reason", "")).strip() for row in targets if str(row.get("label", "")).strip()}
    for idx, block in enumerate(refreshed):
        label = str(block.get("label", "")).strip()
        reason = target_map.get(label, "")
        if not reason:
            continue
        block_spec = next(
            (
                dict(row)
                for row in outline.get("lyrics_blocks", [])
                if str(row.get("label", "")).strip() == label
            ),
            {
                "section": str(block.get("section", "")).strip(),
                "label": label,
                "style": str(block.get("style", "")).strip(),
                "line_count": len([str(x).strip() for x in block.get("lines", []) if str(x).strip()]),
            },
        )
        note = (
            f"Polish this {label}. "
            f"Primary goal: {reason}. "
            "Keep the exact line count, section function, and established song world. "
            "Make the Japanese feel more naturally singable and better fitted to the section's bar length and breathing. "
            "Prefer lines that feel more lived-in, specific, and memorable over safe generic phrasing. "
            "Replace explanation with stronger lyric detail where possible, but keep the section easy to sing in time. "
        )
        refreshed[idx] = _generate_lyrics_block_with_note(
            config,
            plan,
            outline,
            refreshed[:idx],
            block_spec,
            note,
        )
    return refreshed


def _plan_lyrics_rewrite_targets_with_llm(config: dict, plan: dict, blocks: list[dict]) -> list[dict]:
    allowed_labels = [str(row.get("label", "")).strip() for row in blocks if isinstance(row, dict) and str(row.get("label", "")).strip()]
    if not allowed_labels:
        return []
    try:
        raw = generate_structured(config, _lyrics_rewrite_targets_prompt(plan, blocks), _lyrics_rewrite_targets_schema(allowed_labels))
        return _normalize_lyrics_rewrite_targets(raw, allowed_labels)
    except Exception:
        return []


def _lyrics_rewrite_targets_prompt(plan: dict, blocks: list[dict]) -> str:
    rendered: list[str] = []
    for block in blocks:
        label = str(block.get("label", "")).strip()
        lines = [str(x).strip() for x in block.get("lines", []) if str(x).strip()]
        if not label:
            continue
        rendered.append(f"[{label}] " + " / ".join(lines))
    return (
        "Review these song sections and choose at most 2 sections that would most benefit from a rewrite. "
        "Focus only on Japanese lyric naturalness, singability, bar-fit, section-role contrast, lyrical specificity, world consistency, and final payoff. "
        "Check whether each section really sounds singable at its locked size instead of reading like free text. "
        "A 4-bar Bridge must stay brief and turning. "
        "An 8-bar Pre-Chorus should stay tighter than the Chorus. "
        "An 8-bar Chorus should feel hook-first and clearly opened. "
        "A 16-bar Final Chorus should use its extra space for a bigger release. "
        "Flag sections that invent a new sharply specific place, shop, vehicle, or prop without grounding it elsewhere in the song. "
        "Flag sections that use a catchy English phrase that feels imported from outside the song rather than growing naturally from the lyric language. "
        "Flag sections whose lines feel generic, over-explained, too familiar, not memorable enough, too dense for the bar count, or too flat for the section payoff. "
        "Prefer sections that would benefit from more lived-in detail, stronger physicality, a cleaner singing rhythm, or a more personal final payoff. "
        "Do not choose sections that already work. "
        "Prefer rewriting the minimum number of sections needed. "
        + f"Locked bar lane={str(plan.get('bar_lane', '')).strip()}. "
        + _language_clause(plan)
        + _intent_clause(plan)
        + "Return strict JSON only. "
        + "Sections: "
        + " || ".join(rendered)
    )


def _lyrics_rewrite_targets_schema(allowed_labels: list[str]) -> dict:
    return {
        "type": "object",
        "required": ["rewrites"],
        "properties": {
            "rewrites": {
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "required": ["label", "reason"],
                    "properties": {
                        "label": {"type": "string", "enum": allowed_labels},
                        "reason": {"type": "string"},
                    },
                },
            }
        },
    }


def _normalize_lyrics_rewrite_targets(raw: dict, allowed_labels: list[str]) -> list[dict]:
    allowed = set(allowed_labels)
    out: list[dict] = []
    seen: set[str] = set()
    for row in raw.get("rewrites", []) if isinstance(raw, dict) else []:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label", "")).strip()
        reason = " ".join(str(row.get("reason", "")).strip().split())
        if not label or label not in allowed or label in seen or not reason:
            continue
        seen.add(label)
        out.append({"label": label, "reason": reason})
    return out




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
    if duration <= 0:
        duration = 165
    min_sec = int(plan.get("duration_min_sec", 150) or 150)
    max_sec = int(plan.get("duration_max_sec", 180) or 180)
    if max_sec < min_sec:
        max_sec = min_sec
    return max(min_sec, min(duration, max_sec))


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
        ending_mode = str(ending.get("ending_mode", "")).strip().lower()
        max_lines = {"tail_only": 1, "low": 2, "medium": 4}.get(density)
        if ending_mode == "clean_resolve" and density in {"low", "tail_only"}:
            max_lines = 1
        if max_lines is not None and line_count > max_lines:
            raise RuntimeError(f"audio ending contract failed: outro too long for ending_vocal_density={density}")


def _allows_zero_line_block(block: dict) -> bool:
    section = str(block.get("section", "")).strip().lower()
    label = str(block.get("label", "")).strip().lower()
    return section in {"intro", "outro"} or label in {"intro", "outro"}
