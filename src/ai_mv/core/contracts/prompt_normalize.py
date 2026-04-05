from __future__ import annotations

import re
import string

from ai_mv.core.contracts.prompt_schema import (
    ANCHOR_STRATEGIES,
    CONTINUITY_BASES,
    KINETIC_INTENSITIES,
    KINETIC_TRANSITIONS,
    SCENE_CHANGE_LEVELS,
    SHOT_TYPES,
)


def normalize_tti_shot(raw: dict, idx: int) -> dict:
    stype = str(raw["shot_type"])
    if stype not in SHOT_TYPES:
        raise RuntimeError(f"invalid shot_type at {idx}: {stype}")
    out = {
        "shot_id": str(raw["shot_id"]).strip(),
        "shot_type": stype,
        "is_chorus": bool(raw["is_chorus"]),
        "camera_language": str(raw["camera_language"]).strip(),
        "pose_delta": str(raw["pose_delta"]).strip(),
        "emotion": str(raw["emotion"]).strip(),
        "scene_detail": str(raw["scene_detail"]).strip(),
        "motion_hint": str(raw["motion_hint"]).strip(),
        "space_relation": str(raw["space_relation"]).strip(),
    }
    if not all(
        out[key]
        for key in ("shot_id", "camera_language", "pose_delta", "emotion", "scene_detail", "motion_hint", "space_relation")
    ):
        raise RuntimeError(f"incomplete TTI shot blueprint at {idx}")
    return out


def normalize_tti_master(raw: dict) -> dict:
    text = str(raw["prompt_text"]).strip()
    if not text:
        raise RuntimeError("invalid TTI master anchor")
    return {"prompt_text": text, "seed": int(raw["seed"])}


def normalize_audio_fields(raw: dict) -> dict:
    blocks = raw["lyrics_blocks"]
    if not isinstance(blocks, list) or not blocks:
        raise RuntimeError("lyrics_blocks missing")
    return {
        "genre_description": str(raw["genre_description"]).strip(),
        "lyrics_blocks": blocks,
        "lyrics": _render_lyrics_blocks(blocks),
        "bpm": int(raw["bpm"]),
        "keyscale": _normalize_keyscale(str(raw.get("keyscale", "")).strip()),
        "seed": int(raw["seed"]),
        "duration": int(raw["duration"]),
    }


def validate_audio_lyrics_language(lyrics: str, language: str) -> None:
    lang = str(language).strip().lower()
    if lang not in {"ja", "ko", "en"}:
        return
    counts = _script_counts(lyrics)
    if lang == "ja" and counts["jp"] < max(8, int(counts["latin"] * 0.6)):
        raise RuntimeError("audio lyrics language mismatch: expected ja-dominant lyrics")
    if lang == "ko" and counts["ko"] < max(8, int(counts["latin"] * 0.6)):
        raise RuntimeError("audio lyrics language mismatch: expected ko-dominant lyrics")
    if lang == "en" and counts["latin"] < max(8, int((counts["jp"] + counts["ko"]) * 1.5)):
        raise RuntimeError("audio lyrics language mismatch: expected en-dominant lyrics")


def validate_audio_lyrics_quality(blocks: list[dict], language: str, line_budgets: dict | None = None) -> None:
    rows = [row for row in blocks if isinstance(row, dict)]
    if not rows:
        raise RuntimeError("audio lyrics blocks missing")
    lang = str(language).strip().lower()
    lines = _lyrics_body_lines(rows)
    if not lines:
        raise RuntimeError("audio lyrics body empty")
    for line in lines:
        _validate_line_language(line, lang)
    _validate_line_density(rows, lang)
    _validate_duplicate_lines(rows)
    _validate_chorus_growth(rows, lang)
    _validate_hook_quality(rows, lang)
    _validate_section_role_minimums(rows, line_budgets or {})


def validate_audio_genre_description_language(text: str) -> None:
    counts = _script_counts(text)
    non_latin = counts["jp"] + counts["ko"]
    if non_latin > max(2, int(counts["latin"] * 0.15)):
        raise RuntimeError("audio genre_description language mismatch: expected English production brief")


def normalize_flux2_ref_items(raw_items: list[dict], anchors: list[dict]) -> dict[str, dict]:
    keyed = _strict_keyed_rows(raw_items, "Flux2 reference planner")
    _validate_expected_ids(keyed, anchors, "Flux2 reference planner")
    out: dict[str, dict] = {}
    for anchor in anchors:
        sid = str(anchor["shot_id"])
        row = keyed.get(sid)
        if row is None:
            raise RuntimeError(f"Flux2 reference planner missing shot_id: {sid}")
        out[sid] = {
            "prompt_text": _normalize_prompt_text(row["prompt_text"], sid, "prompt_text"),
            "subject_clause": _normalize_atom_clause(row["subject_clause"], sid, "subject_clause", 24),
            "action_clause": _normalize_atom_clause(row["action_clause"], sid, "action_clause", 16),
            "camera_clause": _normalize_atom_clause(row["camera_clause"], sid, "camera_clause", 12),
            "continuity_clause": _normalize_atom_clause(row["continuity_clause"], sid, "continuity_clause", 22),
        }
    return out


def normalize_wan_clips(raw_clips: list[dict], clips: list[dict]) -> dict[str, dict]:
    keyed = _strict_keyed_rows(raw_clips, "WAN planner")
    _validate_expected_ids(keyed, clips, "WAN planner")
    out: dict[str, dict] = {}
    for clip in clips:
        sid = str(clip["shot_id"])
        row = keyed.get(sid)
        if row is None:
            raise RuntimeError(f"WAN planner missing shot_id: {sid}")
        energy = str(row["energy"])
        if energy not in {"low", "normal", "high"}:
            raise RuntimeError(f"invalid wan energy: {energy}")
        out[sid] = {
            "positive_prompt": _normalize_prompt_text(row["positive_prompt"], sid, "positive_prompt"),
            "subject_motion": _normalize_subject_motion(row["subject_motion"], sid),
            "camera_relation": _normalize_camera_relation(row["camera_relation"], sid),
            "environment_detail": _normalize_optional_clause(row["environment_detail"], 16),
            "negative_prompt": _normalize_negative_list(row["negative_prompt"], sid),
            "energy": energy,
        }
    return out


def normalize_lyrics_timeline(raw: dict, sections: list[dict]) -> dict:
    rows = [row for row in raw.get("sections", []) if isinstance(row, dict)]
    if len(rows) != len(sections):
        raise RuntimeError("lyrics timeline section count mismatch")
    out_sections: list[dict] = []
    for idx, (row, section) in enumerate(zip(rows, sections), start=1):
        section_name = str(section.get("name", "section")).strip()
        section_label = str(section.get("label", section_name)).strip()
        lines = [x for x in row.get("lines", []) if isinstance(x, dict)]
        if not lines:
            raise RuntimeError("lyrics timeline lines missing")
        parsed_lines = []
        valid_refs: set[int] = set()
        for line in lines:
            line_index = int(line.get("line_index", 0))
            text = str(line.get("text", "")).strip()
            if line_index <= 0 or not text:
                raise RuntimeError("lyrics timeline line missing index or text")
            parsed_lines.append({"line_index": line_index, "text": text})
            valid_refs.add(line_index)
        beats = [x for x in row.get("lyric_beats", []) if isinstance(x, dict)]
        if not beats:
            raise RuntimeError("lyrics timeline lyric_beats missing")
        parsed_beats = []
        for beat in beats:
            refs = [int(x) for x in beat.get("line_refs", []) if int(x) > 0]
            if not refs or any(ref not in valid_refs for ref in refs):
                raise RuntimeError(f"lyrics timeline beat refs invalid: {section_name}")
            parsed_beats.append(
                {
                    "beat_id": str(beat.get("beat_id", "")).strip() or f"LB{idx:02d}_{len(parsed_beats)+1:02d}",
                    "section_name": section_name,
                    "section_label": section_label,
                    "line_refs": refs,
                    "literal_image": _require_text(beat, "literal_image"),
                    "visible_action": _require_text(beat, "visible_action"),
                    "emotional_turn": _require_text(beat, "emotional_turn"),
                    "continuity_anchor": _require_text(beat, "continuity_anchor"),
                    "payoff_role": _require_text(beat, "payoff_role"),
                    "repeat_variant_of": _normalize_optional_clause(beat.get("repeat_variant_of", ""), 8),
                }
            )
        out_sections.append(
            {
                "section_name": section_name,
                "section_label": section_label,
                "lines": parsed_lines,
                "hook_lines": [int(x) for x in row.get("hook_lines", []) if int(x) in valid_refs],
                "lyric_beats": parsed_beats,
                "start_sec": float(section.get("start_sec", section.get("start", 0.0))),
                "end_sec": float(section.get("end_sec", section.get("end", 0.0))),
            }
        )
    _validate_repeated_hook_variation(out_sections)
    return {"sections": out_sections}


def _normalize_frame_anchor(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise RuntimeError(f"{label} missing")
    return {
        "composition": _optional_text(raw, "composition", ""),
        "subject_scale": _optional_text(raw, "subject_scale", ""),
        "camera_axis": _optional_text(raw, "camera_axis", ""),
        "lighting_state": _optional_text(raw, "lighting_state", ""),
    }


def _render_lyrics_blocks(blocks: list[dict]) -> str:
    lines: list[str] = []
    for row in blocks:
        label = str(row["label"]).strip()
        arr = [str(x).strip() for x in row["lines"] if str(x).strip()]
        if not label or not arr:
            raise RuntimeError("invalid lyrics block")
        lines.append(f"[{label}]")
        lines.extend(arr)
        lines.append("")
    text = "\n".join(lines).strip()
    if not text:
        raise RuntimeError("rendered lyrics empty")
    return text


def _normalize_text_list(raw: list[str], field: str) -> list[str]:
    vals = [str(x).strip() for x in raw if str(x).strip()] if isinstance(raw, list) else []
    if not vals:
        raise RuntimeError(f"{field} missing")
    return vals


def _require_text(raw: dict, field: str) -> str:
    text = str(raw[field]).strip()
    if not text:
        raise RuntimeError(f"{field} missing")
    return text


def _optional_text(raw: dict, field: str, default: str) -> str:
    text = str(raw.get(field, "")).strip() if isinstance(raw, dict) else ""
    return text or default


def _require_enum(raw: dict, field: str, allowed: set[str] | tuple[str, ...] | list[str], default: str = "") -> str:
    text = str(raw.get(field, "")).strip().lower()
    if text not in set(allowed):
        raise RuntimeError(f"{field} missing or invalid")
    return text


def _validate_repeated_hook_variation(section_rows: list[dict]) -> None:
    repeated: dict[tuple[str, tuple[int, ...]], list[dict]] = {}
    for section in section_rows:
        for beat in section.get("lyric_beats", []):
            key = (str(section.get("section_name", "")), tuple(int(x) for x in beat.get("line_refs", [])))
            repeated.setdefault(key, []).append(beat)
    for key, beats in repeated.items():
        if len(beats) <= 1:
            continue
        signatures = {
            (
                str(beat.get("emotional_turn", "")).strip().lower(),
                str(beat.get("payoff_role", "")).strip().lower(),
                str(beat.get("visible_action", "")).strip().lower(),
            )
            for beat in beats
        }
        if len(signatures) <= 1:
            raise RuntimeError(f"repeated lyric beat lacks variation: {key[0]}")


def _is_chorus_section(section_name: str) -> bool:
    sec = str(section_name).strip().lower()
    return sec == "chorus" or sec.startswith("chorus_")


def _normalize_keyscale(text: str) -> str:
    raw = str(text).strip()
    if not raw:
        return ""
    tokens = raw.replace("-", " ").split()
    if len(tokens) < 2:
        return raw
    tonic = tokens[0].upper().replace("\u266f", "#").replace("\u266d", "b")
    mode = tokens[1].lower()
    if mode in {"major", "minor"}:
        return f"{tonic} {mode}"
    return raw


def _normalize_atom_clause(raw: object, shot_id: str, field: str, max_words: int) -> str:
    text = str(raw).strip()
    words = [x for x in text.replace(",", " ").split() if x]
    has_alpha = any(ch.isalpha() for ch in text)
    if len(words) < 2 or not has_alpha:
        raise RuntimeError(f"invalid {field}: {shot_id}")
    return text


def _normalize_optional_clause(raw: object, max_words: int) -> str:
    return str(raw).strip()


def _normalize_subject_motion(raw: object, shot_id: str) -> str:
    return _normalize_atom_clause(raw, shot_id, "subject_motion", 28)


def _normalize_camera_relation(raw: object, shot_id: str) -> str:
    return _normalize_atom_clause(raw, shot_id, "camera_relation", 16)


def _normalize_negative_list(raw: object, shot_id: str) -> str:
    text = " ".join(str(raw).strip().split())
    if not text:
        raise RuntimeError(f"negative_prompt missing: {shot_id}")
    if "." in text and "," not in text:
        raise RuntimeError(f"negative_prompt must be suppression list: {shot_id}")
    return text


def _normalize_prompt_text(raw: object, shot_id: str, field: str) -> str:
    text = " ".join(str(raw).strip().split())
    if not text:
        raise RuntimeError(f"{field} missing: {shot_id}")
    if len([x for x in text.split() if x]) < 4:
        raise RuntimeError(f"invalid {field}: {shot_id}")
    return text


def _strict_keyed_rows(rows: list[dict], label: str) -> dict[str, dict]:
    keyed: dict[str, dict] = {}
    raw_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_count += 1
        sid = str(row.get("shot_id", "")).strip()
        if not sid:
            raise RuntimeError(f"{label} missing shot_id")
        if sid in keyed:
            raise RuntimeError(f"{label} duplicate shot_id: {sid}")
        keyed[sid] = row
    if raw_count != len(keyed):
        raise RuntimeError(f"{label} shot_id count mismatch")
    return keyed


def _validate_expected_ids(keyed: dict[str, dict], expected_rows: list[dict], label: str) -> None:
    expected = [str(row["shot_id"]) for row in expected_rows]
    actual = list(keyed.keys())
    expected_set = set(expected)
    missing = [sid for sid in expected if sid not in keyed]
    extra = [sid for sid in actual if sid not in expected_set]
    if missing:
        raise RuntimeError(f"{label} missing shot_id: {missing[0]}")
    if extra:
        raise RuntimeError(f"{label} unknown shot_id: {extra[0]}")
    if len(actual) != len(expected):
        raise RuntimeError(f"{label} shot_id count mismatch: expected={len(expected)} actual={len(actual)}")


def _script_counts(text: str) -> dict[str, int]:
    counts = {"latin": 0, "jp": 0, "ko": 0}
    for ch in str(text):
        if ch in string.ascii_letters:
            counts["latin"] += 1
            continue
        code = ord(ch)
        if _is_japanese(code):
            counts["jp"] += 1
            continue
        if _is_korean(code):
            counts["ko"] += 1
    return counts


def _lyrics_body_lines(blocks: list[dict]) -> list[str]:
    out: list[str] = []
    for row in blocks:
        for line in row.get("lines", []):
            text = str(line).strip()
            if text:
                out.append(text)
    return out


def _validate_line_language(line: str, language: str) -> None:
    counts = _script_counts(line)
    latin_words = _latin_words(line)
    if language == "ja":
        if counts["jp"] < 2:
            raise RuntimeError("audio lyrics quality mismatch: expected readable Japanese lines")
        if len(latin_words) > 0:
            raise RuntimeError("audio lyrics quality mismatch: Japanese lyrics leaked English words")
    elif language == "ko":
        if counts["ko"] < 2:
            raise RuntimeError("audio lyrics quality mismatch: expected readable Korean lines")
        if not _allow_limited_korean_english_hook(line, latin_words):
            raise RuntimeError("audio lyrics quality mismatch: Korean lyrics leaked too much English")
    elif language == "en":
        if counts["latin"] < max(4, counts["jp"] + counts["ko"]):
            raise RuntimeError("audio lyrics quality mismatch: expected readable English lines")


def _validate_duplicate_lines(blocks: list[dict]) -> None:
    filtered: list[str] = []
    for row in blocks:
        label = str(row.get("label", "")).strip().lower()
        if label in {"chorus", "chorus 2", "final chorus"}:
            continue
        for line in row.get("lines", []):
            text = str(line).strip()
            if text:
                filtered.append(text)
    all_lines = filtered
    if not all_lines:
        return
    normalized = [re.sub(r"\s+", " ", line).strip().lower() for line in all_lines]
    counts: dict[str, int] = {}
    for line in normalized:
        counts[line] = counts.get(line, 0) + 1
    repeated = [line for line, count in counts.items() if count >= 4]
    if repeated:
        raise RuntimeError("audio lyrics quality mismatch: too many repeated lines")


def _validate_chorus_growth(blocks: list[dict], language: str) -> None:
    by_label = {str(row.get("label", "")).strip(): row for row in blocks}
    chorus = by_label.get("Chorus")
    chorus2 = by_label.get("Chorus 2")
    final_chorus = by_label.get("Final Chorus")
    if chorus and chorus2:
        chorus2_limit = max(0, len(chorus.get("lines", [])) - 4)
        if language == "en":
            chorus2_limit = max(chorus2_limit, len(chorus.get("lines", [])) // 2 + 1)
        if _shared_line_count(chorus, chorus2) > chorus2_limit:
            raise RuntimeError("audio lyrics quality mismatch: Chorus 2 repeats Chorus too closely")
    if chorus and final_chorus:
        final_limit = max(2, len(chorus.get("lines", [])) // 2)
        if language == "en":
            final_limit = max(final_limit, len(chorus.get("lines", [])) - 2)
        if _shared_line_count(chorus, final_chorus) > final_limit:
            raise RuntimeError("audio lyrics quality mismatch: Final Chorus repeats Chorus too closely")


def _validate_line_density(blocks: list[dict], language: str) -> None:
    max_chars = 52 if language == "en" else 22 if language == "ko" else 34
    max_commas = 2 if language == "en" else 1
    for row in blocks:
        label = str(row.get("label", "")).strip() or str(row.get("section", "")).strip()
        for line in row.get("lines", []):
            text = str(line).strip()
            if not text:
                continue
            visible = _visible_char_count(text)
            if visible > max_chars:
                raise RuntimeError(f"audio lyrics quality mismatch: line too dense for singing in {label}")
            comma_count = text.count(",") + text.count("，")
            if comma_count > max_commas:
                raise RuntimeError(f"audio lyrics quality mismatch: line too clause-heavy in {label}")


def _validate_hook_quality(blocks: list[dict], language: str) -> None:
    short_limit = 28 if language == "en" else 14 if language == "ko" else 18
    for row in blocks:
        label = str(row.get("label", "")).strip()
        if label not in {"Chorus", "Chorus 2", "Final Chorus"}:
            continue
        lines = [str(line).strip() for line in row.get("lines", []) if str(line).strip()]
        if not lines:
            raise RuntimeError(f"audio lyrics quality mismatch: {label} missing lines")
        if not any(_visible_char_count(line) <= short_limit for line in lines):
            raise RuntimeError(f"audio lyrics quality mismatch: {label} lacks a short memorable hook line")


def _validate_section_role_minimums(blocks: list[dict], line_budgets: dict) -> None:
    if not line_budgets:
        return
    minimums = {
        "Intro": 1,
        "Verse 1": 4,
        "Verse 2": 4,
        "Pre-Chorus": 3,
        "Pre-Chorus 2": 3,
        "Chorus": 4,
        "Chorus 2": 4,
        "Final Chorus": 4,
        "Bridge": 2,
    }
    for row in blocks:
        label = str(row.get("label", "")).strip()
        lines = [str(line).strip() for line in row.get("lines", []) if str(line).strip()]
        if label in minimums and len(lines) < minimums[label]:
            raise RuntimeError(f"audio lyrics quality mismatch: {label} underdelivers its section role")
        max_allowed = int(line_budgets.get(label, 0) or 0)
        if max_allowed > 0 and len(lines) > max_allowed:
            raise RuntimeError(f"audio lyrics quality mismatch: {label} exceeds line budget")


def _shared_line_count(left: dict, right: dict) -> int:
    a = {re.sub(r"\s+", " ", str(line).strip()).lower() for line in left.get("lines", []) if str(line).strip()}
    b = {re.sub(r"\s+", " ", str(line).strip()).lower() for line in right.get("lines", []) if str(line).strip()}
    return len(a & b)


def _visible_char_count(text: str) -> int:
    cleaned = re.sub(r"\s+", "", str(text))
    cleaned = cleaned.replace(",", "").replace("，", "").replace(".", "")
    return len(cleaned)


def _latin_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]{2,}", str(text))


def _allow_limited_korean_english_hook(text: str, latin_words: list[str]) -> bool:
    if not latin_words:
        return True
    if len(latin_words) > 3:
        return False
    joined = " ".join(latin_words)
    if len(joined) > 16:
        return False
    line = str(text).strip()
    latin_chars = sum(1 for ch in line if ch in string.ascii_letters)
    korean_chars = _script_counts(line)["ko"]
    if latin_chars > max(16, korean_chars):
        return False
    return True


def _is_japanese(code: int) -> bool:
    return (
        0x3040 <= code <= 0x309F
        or 0x30A0 <= code <= 0x30FF
        or 0x4E00 <= code <= 0x9FFF
    )


def _is_korean(code: int) -> bool:
    return 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF
