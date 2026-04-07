from __future__ import annotations

import re

from ai_mv.core.output_paths import audio_prefix
from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
    validate_audio_lyrics_quality,
)
from ai_mv.core.contracts.prompt_schema import audio_outline_schema
from ai_mv.engines.acestep_1_5_aio.policy import audio_policy, preferred_songform_rows
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
    _audio_lyrics_block_prompt,
    _audio_lyrics_block_system_prompt,
    _audio_lyrics_rules_qwen,
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
    hook_state = _fallback_hook_state(plan)
    hooked_plan = dict(plan)
    hooked_plan.update(hook_state)
    outline = _plan_outline_with_llm(config, hooked_plan)
    merged = _plan_lyrics_with_llm(config, hooked_plan, outline)
    merged["hook_candidates"] = list(hook_state.get("hook_candidates", []))
    merged["selected_hook_candidate"] = dict(hook_state.get("selected_hook_candidate", {}))
    return merged


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
    )
    _validate_ending_contract(plan, normalized)
    normalized["lyrics_blocks"] = _attach_line_indexes(normalized.get("lyrics_blocks", []))
    normalized["lyrics"] = _render_final_lyrics(plan, normalized.get("lyrics_blocks", []))
    normalized["duration"] = _resolved_duration(plan, normalized)
    normalized.update(_audio_runtime_context(plan))
    normalized["beats_per_bar"] = int(plan.get("beats_per_bar", 4))
    normalized["section_bars"] = dict(plan.get("section_bars", {}))
    normalized["bar_lane"] = str(plan.get("bar_lane", "")).strip()
    normalized["ending_mode"] = str(plan.get("ending_mode", "")).strip()
    normalized["terminal_end_tag"] = bool(plan.get("terminal_end_tag", False))
    normalized["final_chorus_required"] = bool(plan.get("final_chorus_required", False))
    normalized["outro_required"] = bool(plan.get("outro_required", False))
    normalized["ending_vocal_density"] = str(plan.get("ending_vocal_density", "")).strip()
    normalized["ending_tags"] = list(plan.get("ending_tags", [])) if isinstance(plan.get("ending_tags", []), list) else []
    normalized["line_budgets"] = dict(plan.get("line_budgets", {})) if isinstance(plan.get("line_budgets", {}), dict) else {}
    normalized["hook_candidates"] = list(planned.get("hook_candidates", [])) if isinstance(planned.get("hook_candidates", []), list) else []
    normalized["selected_hook_candidate"] = dict(planned.get("selected_hook_candidate", {})) if isinstance(planned.get("selected_hook_candidate", {}), dict) else {}
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
        "hook_direction": str(audio.get("hook_brief", "")).strip() or str(audio.get("brief", "")).strip(),
        "hook_english_fragments": list(audio.get("hook_english_fragments", []))
        if isinstance(audio.get("hook_english_fragments", []), list)
        else [],
        "negative_direction": " ".join(
            part for part in [str(audio.get("negative_direction", "")).strip(), str(audio.get("avoid", "")).strip()] if part
            ).strip(),
    }


def _audio_source(config: dict) -> dict:
    audio = _audio_config(config)
    prompt = str(config.get("prompt", "")).strip() if isinstance(config, dict) else ""
    genre = str(config.get("genre", "")).strip() if isinstance(config, dict) else ""
    voice = str(config.get("voice", "")).strip() if isinstance(config, dict) else ""
    language = str(config.get("language", "")).strip() if isinstance(config, dict) else ""
    profile, tone = _split_voice(voice or str(audio.get("vocal_profile", "")).strip())
    merged = dict(audio)
    if language:
        merged["language"] = str(audio.get("language", "")).strip() or language
    if prompt:
        merged["brief"] = str(audio.get("brief", "")).strip() or prompt
        merged["hook_brief"] = str(audio.get("hook_brief", "")).strip() or prompt
    if genre:
        merged["genre_head"] = str(audio.get("genre_head", "")).strip() or genre
    if profile:
        merged["vocal_profile"] = str(audio.get("vocal_profile", "")).strip() or profile
    if tone:
        merged["vocal_tone"] = str(audio.get("vocal_tone", "")).strip() or tone
    return merged


def _split_voice(text: str) -> tuple[str, str]:
    cleaned = " ".join(str(text).strip().split())
    if not cleaned:
        return "", ""
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if len(parts) <= 1:
        return cleaned, ""
    return parts[0], ", ".join(parts[1:])


def _audio_runtime_context(plan: dict) -> dict:
    return {
        "tags": plan["tags"],
        "language": str(plan.get("language", "")).strip(),
        "filename_prefix": str(plan.get("filename_prefix", "")).strip(),
        "genre_head": str(plan.get("genre_head", "")).strip(),
        "vocal_profile": str(plan.get("vocal_profile", "")).strip(),
        "vocal_tone": str(plan.get("vocal_tone", "")).strip(),
        "quality": plan["quality"],
        "audio_direction": str(plan.get("audio_direction", "")).strip(),
        "hook_direction": str(plan.get("hook_direction", "")).strip(),
        "hook_english_fragments": list(plan.get("hook_english_fragments", []))
        if isinstance(plan.get("hook_english_fragments", []), list)
        else [],
        "hook_candidates": list(plan.get("hook_candidates", []))
        if isinstance(plan.get("hook_candidates", []), list)
        else [],
        "selected_hook_candidate": dict(plan.get("selected_hook_candidate", {}))
        if isinstance(plan.get("selected_hook_candidate", {}), dict)
        else {},
        "negative_direction": str(plan.get("negative_direction", "")).strip(),
    }


def _render_final_lyrics(plan: dict, blocks: list[dict]) -> str:
    lines: list[str] = []
    for row in blocks:
        label = str(row.get("label", "")).strip()
        body = [str(x).strip() for x in row.get("lines", []) if str(x).strip()]
        if not label:
            continue
        if not body and label.lower() != "outro":
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
    completed: list[dict] = []
    for block in outline.get("lyrics_blocks", []):
        completed.append(_generate_lyrics_block(config, plan, outline, completed, dict(block)))
    return _merge_audio_outline_and_lyrics(outline, {"lyrics_blocks": completed})


def _normalize_audio_outline(raw: dict) -> dict:
    blocks = []
    for row in raw.get("lyrics_blocks", []):
        if not isinstance(row, dict):
            continue
        section = str(row.get("section", "")).strip()
        label = str(row.get("label", "")).strip()
        line_count = int(row.get("line_count", 0))
        blocks.append(
            {
                "section": section,
                "label": label,
                "style": str(row.get("style", "")).strip(),
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


def _validate_outline_labels(outline: dict) -> None:
    allowed = {str(row["label"]).strip() for row in preferred_songform_rows()}
    for block in outline.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        if label and label not in allowed:
            raise RuntimeError(f"invalid section label: {label}")
        line_count = int(block.get("line_count", 0) or 0)
        if line_count <= 0 and not _allows_zero_line_block(block):
            raise RuntimeError(f"zero-line block allowed only for Intro or Outro: {label}")


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


def _hook_candidates_prompt(plan: dict) -> str:
    fragments = [str(x).strip() for x in plan.get("hook_english_fragments", []) if str(x).strip()]
    fragment_text = ", ".join(fragments)
    return (
        "Generate chorus hook candidates for a Korean pop song. "
        "Return JSON only. No markdown. "
        "Make 6 candidates for chorus-family use only. "
        "Each candidate must be a short hook fragment, not a full sentence. "
        "Good candidates are easy to chant, easy to remember, and can sit at the start of a chorus line. "
        "Keep Korean dominant overall. "
        "English is optional and must stay within one to three words. "
        "Do not write long English sentences. "
        "Prefer Korean-led hooks tied to the song's emotional turn or central image over generic English slogans. "
        "Bad candidates: vague phrases like all night, forever, stay with me, call my name when they are not anchored to this song's own meaning. "
        "Good candidates: short phrases that can become title-worthy because they belong to this exact song. "
        f"Hook intent={str(plan.get('hook_direction', '')).strip()}. "
        + (f"Preferred optional English fragments={fragment_text}. " if fragment_text else "")
        + "For each candidate, provide fragment, language_mode, placement, and why. "
        + "language_mode must be one of ko_only or mixed_ko_en. "
        + "placement must be one of chorus, chorus2, final_chorus. "
    )


def _hook_candidates_schema() -> dict:
    item = {
        "type": "object",
        "required": ["fragment", "language_mode", "placement", "why"],
        "properties": {
            "fragment": {"type": "string"},
            "language_mode": {"type": "string", "enum": ["ko_only", "mixed_ko_en"]},
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
        if not fragment or language_mode not in {"ko_only", "mixed_ko_en"} or placement not in {"chorus", "chorus2", "final_chorus"}:
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
    if language_mode == "ko_only":
        score += 4
    elif language_mode == "mixed_ko_en":
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
    return score


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
                "language_mode": "mixed_ko_en",
                "placement": placement,
                "why": "Profile-guided short English hook fragment.",
            }
        )
    if not candidates:
        candidates.append(
            {
                "fragment": "남은 불빛",
                "language_mode": "ko_only",
                "placement": "chorus",
                "why": "Fallback Korean chorus hook from the song profile.",
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


def _generate_lyrics_block(config: dict, plan: dict, outline: dict, completed: list[dict], block: dict) -> dict:
    if int(block.get("line_count", 0) or 0) == 0:
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": [],
        }
    prompt = _audio_lyrics_block_prompt(plan, outline, completed, block)
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
