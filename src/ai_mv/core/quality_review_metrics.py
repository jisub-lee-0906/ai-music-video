from __future__ import annotations


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
    world_zones = {str(row.get("world_zone", "")).strip() for row in scene_shots if str(row.get("world_zone", "")).strip()}
    story_functions = {str(row.get("story_function", "")).strip() for row in scene_shots if str(row.get("story_function", "")).strip()}
    style_tags = {str(row.get("ref_style_tag", "")).strip() for row in direction_shots if str(row.get("ref_style_tag", "")).strip()}
    return {
        "shot_package_count": len(ref_items or direction_shots or scene_shots),
        "world_zone_count": len(world_zones),
        "story_function_count": len(story_functions),
        "style_tag_count": len(style_tags),
    }
