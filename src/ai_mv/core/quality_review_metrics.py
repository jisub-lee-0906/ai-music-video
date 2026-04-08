from __future__ import annotations

from collections import Counter


def lyric_metrics(payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    shot_rows = [
        {
            "lyric_beat_id": refs[0] if refs else "",
            "line_refs": list(row.get("line_refs", [])),
        }
        for row in payload.get("scene_outline", {}).get("shot_packages", [])
        if isinstance(row, dict)
        for refs in [[str(x).strip() for x in row.get("beat_refs", []) if str(x).strip()]]
    ]
    shot_beat_ids = {str(row.get("lyric_beat_id", "")).strip() for row in shot_rows if str(row.get("lyric_beat_id", "")).strip()}
    all_beat_ids: set[str] = set()
    total_lines = 0
    mapped_lines: set[tuple[str, int]] = set()
    for section_idx, section in enumerate(sections, start=1):
        lines = [row for row in section.get("lines", []) if isinstance(row, dict)]
        total_lines += len(lines)
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if beat_id:
                all_beat_ids.add(beat_id)
            refs = tuple(positive_int_refs(beat.get("line_refs", [])))
            if beat_id in shot_beat_ids:
                for ref in refs:
                    mapped_lines.add((section_idx, ref))
    return {
        "lyric_beat_count": len(all_beat_ids),
        "covered_beat_count": len(all_beat_ids & shot_beat_ids),
        "shot_to_lyric_coverage": round((len(all_beat_ids & shot_beat_ids) / len(all_beat_ids)) if all_beat_ids else 1.0, 3),
        "repeated_hook_variation": 1.0,
        "unmapped_lyric_lines": max(0, total_lines - len(mapped_lines)),
        "beat_timing_monotonic": _beat_timing_monotonic(sections),
    }


def positive_int_refs(raw_values: object) -> list[int]:
    if not isinstance(raw_values, list):
        return []
    out: list[int] = []
    for item in raw_values:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value > 0:
            out.append(value)
    return out


def route_stats(routes: list[dict], payload: dict) -> dict:
    per_section: dict[str, dict[str, int]] = {}
    total = 0
    ref_assisted = 0
    for row in routes:
        if not isinstance(row, dict):
            continue
        total += 1
        use_ref = bool(row.get("use_ref", False))
        if use_ref:
            ref_assisted += 1
        label = str(row.get("section_label", "section")).strip() or "section"
        bucket = per_section.setdefault(label, {"total": 0, "ref": 0})
        bucket["total"] += 1
        if use_ref:
            bucket["ref"] += 1
    return {
        "total_count": total,
        "tti_only_count": max(0, total - ref_assisted),
        "ref_assisted_count": ref_assisted,
        "ref_ratio_by_section": {
            label: round((vals["ref"] / vals["total"]) if vals["total"] else 0.0, 3)
            for label, vals in per_section.items()
        },
    }


def plan_metrics(payload: dict) -> dict:
    scene_outline = payload.get("scene_outline", {}) if isinstance(payload, dict) else {}
    direction_plan = payload.get("direction_plan", {}) if isinstance(payload, dict) else {}
    prompt_plan = payload.get("prompt_plan", {}) if isinstance(payload, dict) else {}
    scene_shots = [row for row in scene_outline.get("shot_packages", []) if isinstance(row, dict)]
    direction_shots = [row for row in direction_plan.get("shot_packages", []) if isinstance(row, dict)]
    ref_items = [row for row in prompt_plan.get("ref_items", []) if isinstance(row, dict)]
    payoff_roles = {str(row.get("payoff_role", "")).strip() for row in scene_shots if str(row.get("payoff_role", "")).strip()}
    shot_functions = {str(row.get("shot_function", "")).strip() for row in direction_shots if str(row.get("shot_function", "")).strip()}
    places = {str(row.get("place", "")).strip() for row in direction_shots if str(row.get("place", "")).strip()}
    return {
        "shot_package_count": len(ref_items or direction_shots or scene_shots),
        "payoff_role_count": len(payoff_roles),
        "shot_function_count": len(shot_functions),
        "place_count": len(places),
    }


def prompt_metrics(payload: dict) -> dict:
    prompt_plan = payload.get("prompt_plan", {}) if isinstance(payload, dict) else {}
    ref_items = [row for row in prompt_plan.get("ref_items", []) if isinstance(row, dict)]
    wan_items = [row for row in prompt_plan.get("wan_items", []) if isinstance(row, dict)]
    ref_prompts = [_normalize_prompt_text(str(row.get("ref_prompt_text", "")).strip()) for row in ref_items]
    wan_prompts = [_normalize_prompt_text(str(row.get("wan_positive_prompt_text", "")).strip()) for row in wan_items]
    ref_adjacent_dup = _adjacent_duplicate_count(ref_prompts)
    wan_adjacent_dup = _adjacent_duplicate_count(wan_prompts)
    ref_any_dup = _any_duplicate_count(ref_prompts)
    wan_any_dup = _any_duplicate_count(wan_prompts)
    return {
        "ref_item_count": len(ref_items),
        "wan_item_count": len(wan_items),
        "ref_adjacent_duplicate_count": ref_adjacent_dup,
        "wan_adjacent_duplicate_count": wan_adjacent_dup,
        "ref_duplicate_count": ref_any_dup,
        "wan_duplicate_count": wan_any_dup,
        "subject_drift_count": _subject_drift_count(ref_prompts),
        "ref_duration_summary": _duration_summary(ref_items),
        "wan_duration_summary": _duration_summary(wan_items),
    }


def duration_metrics(payload: dict) -> dict:
    final_video = float(payload.get("final_duration_sec", 0.0) or 0.0)
    audio = float(payload.get("audio_duration_sec", 0.0) or 0.0)
    if final_video > 0.0 and audio > 0.0:
        return {
            "audio_duration_sec": round(audio, 3),
            "video_duration_sec": round(final_video, 3),
            "duration_drift_sec": round(abs(final_video - audio), 3),
        }
    merge_plan = payload.get("merge_plan", {}) if isinstance(payload, dict) else {}
    ordered = [row for row in merge_plan.get("ordered", []) if isinstance(row, dict)]
    video_guess = sum(float(row.get("duration_sec", 0.0) or 0.0) for row in ordered if str(row.get("kind", "")).strip() == "still")
    video_guess += sum(float(row.get("duration_sec", 0.0) or 0.0) for row in payload.get("clips", []) if isinstance(row, dict))
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    audio_guess = float(audio_map.get("duration_sec", 0.0) or 0.0)
    return {
        "audio_duration_sec": round(audio_guess, 3),
        "video_duration_sec": round(video_guess, 3),
        "duration_drift_sec": round(abs(video_guess - audio_guess), 3) if audio_guess > 0.0 else 0.0,
    }


def _beat_timing_monotonic(sections: list[dict]) -> bool:
    spans: list[tuple[float, float]] = []
    for section in sections:
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            start = float(beat.get("start_sec", 0.0) or 0.0)
            end = float(beat.get("end_sec", start) or start)
            spans.append((start, end))
    last_end = -1.0
    for start, end in spans:
        if start + 1e-6 < last_end:
            return False
        if end + 1e-6 < start:
            return False
        last_end = max(last_end, end)
    return True


def _normalize_prompt_text(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def _adjacent_duplicate_count(rows: list[str]) -> int:
    return sum(1 for prev, cur in zip(rows, rows[1:]) if prev and prev == cur)


def _any_duplicate_count(rows: list[str]) -> int:
    counter = Counter(row for row in rows if row)
    return sum(count - 1 for count in counter.values() if count > 1)


def _subject_drift_count(rows: list[str]) -> int:
    bad = 0
    for row in rows:
        if not row:
            continue
        if "a woman " in row or row.startswith("a woman") or " a man " in row or row.startswith("a man"):
            bad += 1
            continue
        if " their " in row:
            bad += 1
    return bad


def _duration_summary(rows: list[dict]) -> dict:
    values = [float(row.get("duration_sec", 0.0) or 0.0) for row in rows if float(row.get("duration_sec", 0.0) or 0.0) > 0.0]
    if not values:
        return {"count": 0, "min_sec": 0.0, "max_sec": 0.0, "total_sec": 0.0, "avg_sec": 0.0}
    total = sum(values)
    return {
        "count": len(values),
        "min_sec": round(min(values), 3),
        "max_sec": round(max(values), 3),
        "total_sec": round(total, 3),
        "avg_sec": round(total / len(values), 3),
    }
