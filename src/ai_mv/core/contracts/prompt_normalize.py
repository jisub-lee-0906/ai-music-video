from __future__ import annotations

import string

from ai_mv.core.contracts.prompt_schema import KINETIC_INTENSITIES, KINETIC_TRANSITIONS, SHOT_TYPES


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


def normalize_visual_story_bible(raw: dict, sections: list[dict]) -> dict:
    beats = [row for row in raw.get("lyric_beats", []) if isinstance(row, dict)]
    if not beats:
        raise RuntimeError("visual story bible lyric_beats missing")
    progression = [row for row in raw.get("section_progression", []) if isinstance(row, dict)]
    if len(progression) != len(sections):
        raise RuntimeError("visual story bible section progression mismatch")
    out_beats = []
    for row in beats:
        out_beats.append(
            {
                "beat_id": _require_text(row, "beat_id"),
                "section_name": _require_text(row, "section_name"),
                "section_label": _require_text(row, "section_label"),
                "line_refs": [int(x) for x in row.get("line_refs", []) if int(x) > 0],
                "literal_image": _require_text(row, "literal_image"),
                "visible_action": _require_text(row, "visible_action"),
                "emotional_turn": _require_text(row, "emotional_turn"),
                "continuity_anchor": _require_text(row, "continuity_anchor"),
                "payoff_role": _require_text(row, "payoff_role"),
                "repeat_variant_of": _normalize_optional_clause(row.get("repeat_variant_of", ""), 8),
                "location_family": _require_text(row, "location_family"),
                "palette_hint": _require_text(row, "palette_hint"),
                "lighting_hint": _require_text(row, "lighting_hint"),
                "camera_commitment": _require_text(row, "camera_commitment"),
            }
        )
    out = {
        "hero_identity_lock": _require_text(raw, "hero_identity_lock"),
        "world_rules": _require_text(raw, "world_rules"),
        "recurring_location_families": _normalize_text_list(raw.get("recurring_location_families", []), "recurring_location_families"),
        "forbidden_drift": _normalize_text_list(raw.get("forbidden_drift", []), "forbidden_drift"),
        "lyric_beats": out_beats,
        "section_progression": [
            {
                "section_name": _require_text(row, "section_name"),
                "section_label": _require_text(row, "section_label"),
                "dominant_emotion": _require_text(row, "dominant_emotion"),
                "story_function": _require_text(row, "story_function"),
                "lyric_beat_ids": [str(x).strip() for x in row.get("lyric_beat_ids", []) if str(x).strip()],
            }
            for row in progression
        ],
        "repeat_escalation_rules": _normalize_text_list(raw.get("repeat_escalation_rules", []), "repeat_escalation_rules"),
    }
    return out


def normalize_shot_timeline(raw: dict, lyric_beats: list[dict]) -> dict:
    beats = {str(row.get("beat_id", "")).strip(): row for row in lyric_beats if isinstance(row, dict)}
    master = normalize_tti_master(raw["master_anchor"])
    shots = [row for row in raw.get("shots", []) if isinstance(row, dict)]
    if len(shots) != len(beats):
        raise RuntimeError("shot count mismatch")
    out: list[dict] = []
    for idx, row in enumerate(shots, start=1):
        beat_id = str(row.get("lyric_beat_id", "")).strip()
        beat = beats.get(beat_id)
        if beat is None:
            raise RuntimeError(f"unknown lyric beat id: {beat_id}")
        shot_type = str(row.get("shot_type", "")).strip().upper()
        if shot_type not in SHOT_TYPES:
            raise RuntimeError(f"invalid shot type: {shot_type}")
        kinetic_transition = str(row.get("kinetic_transition", "")).strip()
        if kinetic_transition not in KINETIC_TRANSITIONS:
            raise RuntimeError(f"invalid kinetic transition: {kinetic_transition}")
        kinetic_intensity = str(row.get("kinetic_intensity", "")).strip().lower()
        if kinetic_intensity not in KINETIC_INTENSITIES:
            raise RuntimeError(f"invalid kinetic intensity: {kinetic_intensity}")
        out.append(
            {
                "shot_id": f"S{idx:03d}",
                "lyric_beat_id": beat_id,
                "section_name": str(beat.get("section_name", "")),
                "section_label": str(beat.get("section_label", beat.get("section_name", ""))),
                "is_chorus": _is_chorus_section(str(beat.get("section_name", ""))),
                "shot_type": shot_type,
                "camera_language": _require_text(row, "camera_language"),
                "pose_delta": _require_text(row, "pose_delta"),
                "emotion": _require_text(row, "emotion"),
                "scene_detail": _require_text(row, "scene_detail"),
                "motion_hint": _require_text(row, "motion_hint"),
                "space_relation": _require_text(row, "space_relation"),
                "edit_role": _require_text(row, "edit_role"),
                "continuity_lock": _require_text(row, "continuity_lock"),
                "clip_count": max(1, int(row.get("clip_count", 1))),
                "start_frame": _normalize_frame_anchor(row.get("start_frame", {}), "start_frame"),
                "end_frame": _normalize_frame_anchor(row.get("end_frame", {}), "end_frame"),
                "kinetic_transition": kinetic_transition,
                "lighting_fx": _require_text(row, "lighting_fx"),
                "kinetic_intensity": kinetic_intensity,
            }
        )
    return {"master_anchor": master, "shots": out}


def _normalize_frame_anchor(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise RuntimeError(f"{label} missing")
    return {
        "composition": _require_text(raw, "composition"),
        "subject_scale": _require_text(raw, "subject_scale"),
        "camera_axis": _require_text(raw, "camera_axis"),
        "lighting_state": _require_text(raw, "lighting_state"),
    }


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
