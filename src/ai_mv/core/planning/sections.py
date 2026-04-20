from __future__ import annotations


M1_TARGET_DURATION_MIN = 15.0
M1_TARGET_DURATION_MAX = 20.0
M1_MIN_SHOTS = 4
M1_MAX_SHOTS = 6
SECTION_MIN_DURATION_SEC = 2.5
SECTION_MICRO_MERGE_SEC = 3.0
SECTION_NORMALIZATION_STRONG_CONFIDENCE = 0.8
SECTION_NORMALIZATION_WEAK_CONFIDENCE = 0.6

SECTION_LABEL_ALIASES = {
    "intro": "intro",
    "opening": "intro",
    "open": "intro",
    "cold open": "intro",
    "prelude": "intro",
    "verse": "verse",
    "v1": "verse",
    "v2": "verse",
    "verse 1": "verse",
    "verse 2": "verse",
    "rap verse": "verse",
    "pre": "pre_chorus",
    "prechorus": "pre_chorus",
    "pre chorus": "pre_chorus",
    "build": "pre_chorus",
    "lift": "pre_chorus",
    "chorus": "chorus",
    "hook": "chorus",
    "refrain": "chorus",
    "drop hook": "chorus",
    "main hook": "chorus",
    "post": "post_chorus",
    "postchorus": "post_chorus",
    "post chorus": "post_chorus",
    "refrain tail": "post_chorus",
    "bridge": "bridge",
    "breakdown bridge": "bridge",
    "middle8": "bridge",
    "middle 8": "bridge",
    "instrumental": "instrumental_break",
    "instrumental break": "instrumental_break",
    "solo": "instrumental_break",
    "break": "instrumental_break",
    "dance break": "instrumental_break",
    "outro": "outro",
    "ending": "outro",
    "end": "outro",
    "coda": "outro",
}

SECTION_LABEL_ALIAS_CONFIDENCE = {
    "break": 0.7,
}



def normalized_sections(audio_map: dict, duration_sec: float) -> list[dict]:
    rows = [row for row in audio_map.get("sections", []) if isinstance(row, dict)]
    normalized: list[dict] = []
    for idx, row in enumerate(rows, start=1):
        start_sec = max(0.0, min(_float(row.get("start_sec"), 0.0), float(duration_sec)))
        end_sec = max(start_sec, min(_float(row.get("end_sec"), 0.0), float(duration_sec)))
        if end_sec <= start_sec:
            continue
        section_type, normalization_confidence = canonical_section_type(row)
        source_label = str(row.get("label") or row.get("name") or row.get("section_name") or row.get("section") or section_type.upper()).strip()
        normalized.append(
            {
                "index": idx,
                "source_label": source_label,
                "section_name": source_label,
                "section_type": section_type,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 3),
                "normalization_confidence": normalization_confidence,
            }
        )
    if not normalized:
        return fallback_sections(duration_sec)
    normalized.sort(key=lambda row: (float(row["start_sec"]), float(row["end_sec"]), int(row["index"])))
    normalized = merge_micro_sections(normalized)
    for idx, row in enumerate(normalized, start=1):
        row["index"] = idx
    return compress_sections(normalized, duration_sec)



def compress_sections(sections: list[dict], duration_sec: float) -> list[dict]:
    rows = [dict(row) for row in sections]
    if not use_m1_window(duration_sec):
        return rows
    if len(rows) < M1_MIN_SHOTS:
        return rows
    if len(rows) > M1_MAX_SHOTS:
        return merge_shortest_adjacent(rows)
    return rows



def compress_shots_to_m1_window(shots: list[dict]) -> list[dict]:
    rows = [dict(row) for row in shots]
    if len(rows) <= M1_MAX_SHOTS:
        return rows
    while len(rows) > M1_MAX_SHOTS:
        best_index = 0
        best_cost = None
        for idx in range(len(rows) - 1):
            left = rows[idx]
            right = rows[idx + 1]
            cost = float(left["duration_sec"]) + float(right["duration_sec"])
            if str(left.get("section_type", "")) != str(right.get("section_type", "")):
                cost += 1000.0
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_index = idx
        left = rows[best_index]
        right = rows[best_index + 1]
        merged = {
            **left,
            "section_name": merged_section_name(left, right),
            "section_type": merged_shot_section_type(left, right),
            "end_sec": right["end_sec"],
            "duration_sec": round(float(right["end_sec"]) - float(left["start_sec"]), 3),
            "shot_role": f"{left['shot_role']}+{right['shot_role']}",
            "visual_mode": right["visual_mode"] if str(right.get("section_type", "")) == "chorus" else left["visual_mode"],
            "render_mode": "i2v",
            "source_section_index": merged_source_section_index(left, right),
        }
        rows = rows[:best_index] + [merged] + rows[best_index + 2 :]
    return rows



def expand_sparse_sections(sections: list[dict], duration_sec: float) -> list[dict]:
    if len(sections) >= M1_MIN_SHOTS:
        return sections
    expanded = [dict(row) for row in sections]
    while len(expanded) < M1_MIN_SHOTS:
        target_index = max(range(len(expanded)), key=lambda idx: float(expanded[idx]["duration_sec"]))
        target = expanded.pop(target_index)
        midpoint = round((float(target["start_sec"]) + float(target["end_sec"])) / 2.0, 3)
        if midpoint <= float(target["start_sec"]) or midpoint >= float(target["end_sec"]):
            break
        expanded.insert(
            target_index,
            {
                **target,
                "end_sec": midpoint,
                "duration_sec": round(midpoint - float(target["start_sec"]), 3),
            },
        )
        expanded.insert(
            target_index + 1,
            {
                **target,
                "start_sec": midpoint,
                "duration_sec": round(float(target["end_sec"]) - midpoint, 3),
            },
        )
    return expanded



def merge_shortest_adjacent(sections: list[dict]) -> list[dict]:
    rows = [dict(row) for row in sections]
    while len(rows) > M1_MAX_SHOTS:
        best_index = 0
        best_cost = None
        for idx in range(len(rows) - 1):
            cost = float(rows[idx]["duration_sec"]) + float(rows[idx + 1]["duration_sec"])
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_index = idx
        left = rows[best_index]
        right = rows[best_index + 1]
        merged = {
            **left,
            "section_name": merged_section_name(left, right),
            "section_type": merged_shot_section_type(left, right),
            "end_sec": right["end_sec"],
            "duration_sec": round(float(right["end_sec"]) - float(left["start_sec"]), 3),
        }
        rows = rows[:best_index] + [merged] + rows[best_index + 2 :]
    return rows



def merge_micro_sections(sections: list[dict]) -> list[dict]:
    rows = [dict(row) for row in sections]
    merged: list[dict] = []
    for row in rows:
        duration_sec = float(row.get("duration_sec", 0.0) or 0.0)
        confidence = float(row.get("normalization_confidence", 0.0) or 0.0)
        should_merge = duration_sec < SECTION_MIN_DURATION_SEC and (
            confidence < SECTION_NORMALIZATION_STRONG_CONFIDENCE or _force_merge_micro_section(row)
        )
        if not should_merge and duration_sec <= SECTION_MICRO_MERGE_SEC and confidence < SECTION_NORMALIZATION_WEAK_CONFIDENCE and merged:
            should_merge = _same_energy_band(merged[-1], row)
        if not should_merge or not merged:
            merged.append(row)
            continue
        previous = dict(merged.pop())
        merged.append(
            {
                **previous,
                "section_name": merged_section_name(previous, row),
                "end_sec": row["end_sec"],
                "duration_sec": round(float(row["end_sec"]) - float(previous["start_sec"]), 3),
                "normalization_confidence": min(float(previous.get("normalization_confidence", 1.0)), float(row.get("normalization_confidence", 1.0))),
            }
        )
    return merged



def fallback_sections(duration_sec: float) -> list[dict]:
    safe_duration = max(M1_TARGET_DURATION_MIN, min(duration_sec, M1_TARGET_DURATION_MAX))
    section_types = ["intro", "verse", "chorus", "outro"] if safe_duration < 18.0 else ["intro", "verse", "verse", "chorus", "outro"]
    section_len = round(safe_duration / len(section_types), 3)
    out: list[dict] = []
    for idx, section_type in enumerate(section_types, start=1):
        start_sec = round((idx - 1) * section_len, 3)
        end_sec = round(safe_duration if idx == len(section_types) else idx * section_len, 3)
        out.append(
            {
                "index": idx,
                "source_label": section_type.upper(),
                "section_name": section_type.upper(),
                "section_type": section_type,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 3),
                "normalization_confidence": 0.6,
            }
        )
    return out



def canonical_section_type(row: dict) -> tuple[str, float]:
    raw = str(row.get("section") or row.get("name") or row.get("section_name") or row.get("label") or "").strip().lower()
    normalized = raw.replace("-", " ").replace("_", " ")
    compact = normalized.replace(" ", "")
    if normalized in SECTION_LABEL_ALIASES:
        return SECTION_LABEL_ALIASES[normalized], SECTION_LABEL_ALIAS_CONFIDENCE.get(normalized, 0.96)
    if compact in SECTION_LABEL_ALIASES:
        return SECTION_LABEL_ALIASES[compact], SECTION_LABEL_ALIAS_CONFIDENCE.get(compact, 0.96)
    if "pre" in normalized and ("chorus" in normalized or "hook" in normalized):
        return "pre_chorus", 0.98
    if "post" in normalized and ("chorus" in normalized or "hook" in normalized):
        return "post_chorus", 0.96
    if "chorus" in normalized or "refrain" in normalized or "hook" in normalized:
        return "chorus", 0.94
    if "middle 8" in normalized or "middle8" in normalized or "bridge" in normalized:
        return "bridge", 0.92
    if "instrumental" in normalized or "solo" in normalized:
        return "instrumental_break", 0.9
    if "outro" in normalized or "ending" in normalized or "coda" in normalized:
        return "outro", 0.96
    if "intro" in normalized or "opening" in normalized or "prelude" in normalized:
        return "intro", 0.96
    if "break" in normalized:
        return "instrumental_break", 0.7
    return "verse", 0.55



def merged_section_name(left: dict, right: dict) -> str:
    left_name = str(left.get("section_name", "")).strip()
    right_name = str(right.get("section_name", "")).strip()
    return left_name if left_name == right_name else f"{left_name}->{right_name}"



def merged_shot_section_type(left: dict, right: dict) -> str:
    left_type = str(left.get("section_type", "")).strip()
    right_type = str(right.get("section_type", "")).strip()
    if left_type == right_type:
        return left_type
    priority = {"outro": 7, "chorus": 6, "bridge": 5, "post_chorus": 4, "pre_chorus": 3, "instrumental_break": 2, "verse": 1, "intro": 0}
    return right_type if priority.get(right_type, -1) >= priority.get(left_type, -1) else left_type



def merged_source_section_index(left: dict, right: dict) -> int:
    left_index = _int(left.get("source_section_index"), 0)
    right_index = _int(right.get("source_section_index"), 0)
    if str(left.get("section_type", "")).strip() == str(right.get("section_type", "")).strip():
        return left_index
    return right_index or left_index



def _same_energy_band(left: dict, right: dict) -> bool:
    return _section_energy_band(left) == _section_energy_band(right)



def _force_merge_micro_section(row: dict) -> bool:
    return str(row.get("section_type", "")).strip() in {"instrumental_break", "post_chorus"}



def _section_energy_band(row: dict) -> str:
    section_type = str(row.get("section_type", "")).strip()
    if section_type in {"intro", "verse", "pre_chorus", "post_chorus", "outro"}:
        return "narrative"
    if section_type == "chorus":
        return "peak"
    if section_type in {"bridge", "instrumental_break"}:
        return "transition"
    return "other"



def use_m1_window(duration_sec: float) -> bool:
    return float(duration_sec) <= (M1_TARGET_DURATION_MAX + 2.0)



def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default



def _int(value: object, default: int, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(minimum, parsed)
