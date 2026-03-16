from __future__ import annotations

import string

from ai_mv.core.contracts.prompt_schema import SHOT_TYPES


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
            "subject_clause": _normalize_atom_clause(row["subject_clause"], sid, "subject_clause", 24),
            "action_clause": _normalize_atom_clause(row["action_clause"], sid, "action_clause", 16),
            "environment_clause": _normalize_atom_clause(row["environment_clause"], sid, "environment_clause", 20),
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
            "subject_motion": _normalize_subject_motion(row["subject_motion"], sid),
            "camera_relation": _normalize_camera_relation(row["camera_relation"], sid),
            "environment_detail": _normalize_optional_clause(row["environment_detail"], 16),
            "negative_prompt": _normalize_negative_list(row["negative_prompt"], sid),
            "energy": energy,
        }
    return out


def normalize_visual_brief(raw: dict, sections: list[dict]) -> dict:
    if not sections:
        raise RuntimeError("visual brief sections missing")
    fallback_section_rows = [x for x in raw.get("section_briefs", []) if isinstance(x, dict)]
    fallback_families = [str(row.get("location_anchor", "")).strip() for row in fallback_section_rows if str(row.get("location_anchor", "")).strip()]
    recurring_families = _normalize_text_list(raw.get("recurring_location_families", fallback_families), "recurring_location_families")
    fallback_variation = [str(row.get("staging_hint", "")).strip() for row in fallback_section_rows if str(row.get("staging_hint", "")).strip()]
    allowed_variation = _normalize_text_list(raw.get("allowed_visual_variation", fallback_variation or ["section-level framing variation"]), "allowed_visual_variation")
    out = {
        "hero_identity": _require_text(raw, "hero_identity"),
        "world_rules": _require_text(raw, "world_rules"),
        "recurring_location_families": recurring_families,
        "allowed_visual_variation": allowed_variation,
        "visual_motifs": _normalize_text_list(raw.get("visual_motifs", []), "visual_motifs") if raw.get("visual_motifs", []) else list(recurring_families),
        "negative_constraints": _normalize_text_list(raw["negative_constraints"], "negative_constraints"),
        "section_briefs": _normalize_section_briefs(raw["section_briefs"], sections),
    }
    recurring_spaces = _recurring_spaces(out["section_briefs"])
    out["world_bible"] = {
        "hero_identity": out["hero_identity"],
        "world_rules": out["world_rules"],
        "recurring_location_families": list(out["recurring_location_families"]),
        "allowed_visual_variation": list(out["allowed_visual_variation"]),
        "visual_motifs": list(out["visual_motifs"]),
        "negative_constraints": list(out["negative_constraints"]),
    }
    out["section_dramaturgy"] = [dict(row) for row in out["section_briefs"]]
    out["hero_identity_lock"] = out["hero_identity"]
    out["world_lock"] = {
        "master_setting": out["world_rules"],
        "palette_baseline": out["world_rules"],
        "lighting_baseline": out["world_rules"],
        "recurring_spaces": recurring_spaces,
    }
    out["section_locks"] = [
        {
            "section_name": row["section_name"],
            "story_beat": row["story_beat"],
            "location_anchor": row["location_anchor"],
        }
        for row in out["section_briefs"]
    ]
    return out


def _render_lyrics_blocks(blocks: list[dict]) -> str:
    lines: list[str] = []
    for row in blocks:
        label = str(row["label"]).strip()
        style = str(row["style"]).strip()
        arr = [str(x).strip() for x in row["lines"] if str(x).strip()]
        if not label or not style or not arr:
            raise RuntimeError("invalid lyrics block")
        lines.append(f"[{label} - {style}]")
        lines.extend(arr)
        lines.append("")
    text = "\n".join(lines).strip()
    if not text:
        raise RuntimeError("rendered lyrics empty")
    return text


def _normalize_section_briefs(raw: list[dict], sections: list[dict]) -> list[dict]:
    rows = [x for x in raw if isinstance(x, dict)]
    if len(rows) != len(sections):
        raise RuntimeError("visual brief section count mismatch")
    return [_normalize_visual_section(row, str(section.get("name", "section"))) for row, section in zip(rows, sections)]


def _normalize_visual_section(row: dict, expected_name: str) -> dict:
    actual = _require_text(row, "section_name")
    if actual != expected_name:
        raise RuntimeError(f"visual brief section mismatch: expected={expected_name} actual={actual}")
    story_beat = _require_text(row, "story_beat")
    location_anchor = _require_text(row, "location_anchor")
    _validate_story_beat(story_beat)
    _validate_location_anchor(location_anchor)
    return {
        "section_name": actual,
        "emotional_arc": _require_text(row, "emotional_arc"),
        "palette_hint": _require_text(row, "palette_hint"),
        "lighting_hint": _require_text(row, "lighting_hint"),
        "staging_hint": _require_text(row, "staging_hint"),
        "story_beat": story_beat,
        "location_anchor": location_anchor,
        "escalation_level": _normalize_optional_clause(row.get("escalation_level", ""), 8) or _default_escalation_level(expected_name),
        "motion_axis": _normalize_optional_clause(row.get("motion_axis", ""), 10) or _default_motion_axis(story_beat),
    }


def _normalize_text_list(raw: list[str], field: str) -> list[str]:
    vals = [str(x).strip() for x in raw if str(x).strip()] if isinstance(raw, list) else []
    if not vals:
        raise RuntimeError(f"{field} missing")
    return vals


def _recurring_spaces(section_briefs: list[dict]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in section_briefs:
        text = str(row.get("location_anchor", "")).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _require_text(raw: dict, field: str) -> str:
    text = str(raw[field]).strip()
    if not text:
        raise RuntimeError(f"{field} missing")
    return text


def _validate_story_beat(text: str) -> None:
    low = str(text).strip().lower()
    mood_only = {
        "searching",
        "passing by",
        "hesitating",
        "opening up",
        "moving on",
        "circling back",
        "leaning in",
        "converging",
        "separating",
        "arriving",
        "receding",
    }
    if low in mood_only:
        raise RuntimeError("visual brief story_beat must describe a visible action, not only a mood label")
    if len(low.split()) < 2:
        raise RuntimeError("visual brief story_beat too thin")


def _validate_location_anchor(text: str) -> None:
    low = str(text).strip().lower()
    if len(low.split()) < 1 or not any(ch.isalpha() for ch in low):
        raise RuntimeError("visual brief location_anchor too thin")


def _default_escalation_level(section_name: str) -> str:
    sec = str(section_name).strip().lower()
    if sec == "chorus":
        return "payoff"
    if sec == "bridge":
        return "interrupt"
    if sec == "outro":
        return "residue"
    if sec == "pre_chorus":
        return "lift"
    return "steady"


def _default_motion_axis(story_beat: str) -> str:
    low = str(story_beat).strip().lower()
    if "turn" in low or "glance" in low or "gaze" in low:
        return "gaze shift"
    if "step" in low or "walk" in low or "cross" in low or "pass" in low:
        return "travel line"
    if "hold" in low or "pause" in low or "stop" in low:
        return "stillness hold"
    return "pose shift"


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
    text = " ".join(str(raw).strip().split())
    words = [x for x in text.replace(",", " ").split() if x]
    has_alpha = any(ch.isalpha() for ch in text)
    if len(words) < 2 or not has_alpha:
        raise RuntimeError(f"invalid {field}: {shot_id}")
    if len(words) > max_words:
        raise RuntimeError(f"{field} too long: {shot_id}")
    return text.rstrip(". ")


def _normalize_optional_clause(raw: object, max_words: int) -> str:
    text = " ".join(str(raw).strip().split()).rstrip(". ")
    if not text:
        return ""
    words = [x for x in text.replace(",", " ").split() if x]
    if len(words) > max_words:
        raise RuntimeError("optional clause too long")
    return text


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


def _is_japanese(code: int) -> bool:
    return (
        0x3040 <= code <= 0x309F
        or 0x30A0 <= code <= 0x30FF
        or 0x4E00 <= code <= 0x9FFF
    )


def _is_korean(code: int) -> bool:
    return 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF
