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


def normalize_uso_items(raw_items: list[dict], anchors: list[dict]) -> dict[str, dict]:
    keyed = {str(x["shot_id"]): x for x in raw_items if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for anchor in anchors:
        sid = str(anchor["shot_id"])
        row = keyed[sid]
        out[sid] = {
            "delta": _normalize_uso_delta(row["delta"], sid),
            "prompt_text": str(row["prompt_text"]).strip(),
            "negative_prompt": str(row["negative_prompt"]).strip(),
        }
        if not out[sid]["prompt_text"]:
            raise RuntimeError(f"empty uso prompt_text: {sid}")
    return out


def normalize_wan_clips(raw_clips: list[dict], clips: list[dict]) -> dict[str, dict]:
    keyed = {str(x["shot_id"]): x for x in raw_clips if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for clip in clips:
        sid = str(clip["shot_id"])
        row = keyed[sid]
        energy = str(row["energy"])
        if energy not in {"low", "normal", "high"}:
            raise RuntimeError(f"invalid wan energy: {energy}")
        out[sid] = {
            "positive_prompt": str(row["positive_prompt"]),
            "negative_prompt": str(row["negative_prompt"]),
            "energy": energy,
        }
    return out


def normalize_visual_brief(raw: dict, sections: list[dict]) -> dict:
    if not sections:
        raise RuntimeError("visual brief sections missing")
    out = {
        "hero_identity": _require_text(raw, "hero_identity"),
        "world_rules": _require_text(raw, "world_rules"),
        "visual_motifs": _normalize_text_list(raw["visual_motifs"], "visual_motifs"),
        "negative_constraints": _normalize_text_list(raw["negative_constraints"], "negative_constraints"),
        "section_briefs": _normalize_section_briefs(raw["section_briefs"], sections),
    }
    out["world_bible"] = {
        "hero_identity": out["hero_identity"],
        "world_rules": out["world_rules"],
        "visual_motifs": list(out["visual_motifs"]),
        "negative_constraints": list(out["negative_constraints"]),
    }
    out["section_dramaturgy"] = [dict(row) for row in out["section_briefs"]]
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
    }


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
    verbs = (
        "walk",
        "walking",
        "move",
        "moves",
        "moving",
        "pause",
        "paused",
        "turn",
        "turning",
        "glance",
        "glancing",
        "look",
        "looking",
        "check",
        "checks",
        "checking",
        "step",
        "stepping",
        "cross",
        "crossing",
        "clear",
        "clears",
        "clearing",
        "drift",
        "drifting",
        "face",
        "facing",
        "pass",
        "passing",
        "stop",
        "stopping",
        "remain",
        "remains",
        "remaining",
        "hold",
        "holding",
        "lean",
        "leaning",
        "enter",
        "entering",
        "leave",
        "leaving",
        "circle",
        "circling",
        "retreat",
        "retreating",
        "slow",
        "slowing",
        "meet",
        "meeting",
        "let",
        "lets",
        "letting",
        "open",
        "opening",
    )
    if not any(word in low for word in verbs):
        raise RuntimeError("visual brief story_beat must include a visible action verb")


def _validate_location_anchor(text: str) -> None:
    low = str(text).strip().lower()
    if len(low.split()) < 2:
        raise RuntimeError("visual brief location_anchor too thin")


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


def _normalize_uso_delta(raw: object, shot_id: str) -> str:
    text = str(raw).strip()
    words = [x for x in text.replace(",", " ").split() if x]
    has_alpha = any(ch.isalpha() for ch in text)
    if len(words) < 3 or not has_alpha:
        raise RuntimeError(f"invalid uso delta: {shot_id}")
    return text


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
