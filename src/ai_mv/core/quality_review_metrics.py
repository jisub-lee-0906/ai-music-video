from __future__ import annotations


def lyric_metrics(payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    shot_rows = [
        {
            "lyric_beat_id": refs[0] if refs else "",
            "line_refs": list(row.get("line_refs", [])),
            "visible_action": "",
            "payoff_role": "",
        }
        for row in payload.get("scene_plan", {}).get("shot_packages", [])
        if isinstance(row, dict)
        for refs in [[str(x).strip() for x in row.get("beat_refs", []) if str(x).strip()]]
    ]
    shot_beat_ids = {str(row.get("lyric_beat_id", "")).strip() for row in shot_rows if str(row.get("lyric_beat_id", "")).strip()}
    all_beat_ids: set[str] = set()
    total_lines = 0
    mapped_lines: set[tuple[str, int]] = set()
    repeated_groups: dict[tuple[int, ...], list[dict]] = {}
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
            repeated_groups.setdefault(refs, []).append(beat)
            if beat_id in shot_beat_ids:
                for ref in refs:
                    mapped_lines.add((section_idx, ref))
    variation_scores = []
    for refs, beats in repeated_groups.items():
        if len(refs) == 0 or len(beats) <= 1:
            continue
        signatures = {
            (
                str(beat.get("visible_action", "")).strip().lower(),
                str(beat.get("payoff_role", "")).strip().lower(),
            )
            for beat in beats
        }
        variation_scores.append(len(signatures) / float(len(beats)))
    repeated_variation = sum(variation_scores) / len(variation_scores) if variation_scores else 1.0
    return {
        "lyric_beat_count": len(all_beat_ids),
        "covered_beat_count": len(all_beat_ids & shot_beat_ids),
        "shot_to_lyric_coverage": round((len(all_beat_ids & shot_beat_ids) / len(all_beat_ids)) if all_beat_ids else 1.0, 3),
        "repeated_hook_variation": round(repeated_variation, 3),
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
    beat_to_section = beat_to_section_label(payload)
    total = 0
    ref_assisted = 0
    per_section: dict[str, dict[str, int]] = {}
    for row in routes:
        if not isinstance(row, dict):
            continue
        total += 1
        use_ref = bool(row.get("use_ref", False))
        if use_ref:
            ref_assisted += 1
        label = route_section_label(row, beat_to_section)
        bucket = per_section.setdefault(label, {"total": 0, "ref": 0})
        bucket["total"] += 1
        if use_ref:
            bucket["ref"] += 1
    ratios = {
        label: round((vals["ref"] / vals["total"]) if vals["total"] else 0.0, 3)
        for label, vals in per_section.items()
    }
    return {
        "total_count": total,
        "tti_only_count": max(0, total - ref_assisted),
        "ref_assisted_count": ref_assisted,
        "ref_ratio_by_section": ratios,
    }


def plan_metrics(payload: dict) -> dict:
    scene_plan = payload.get("scene_plan", {}) if isinstance(payload, dict) else {}
    director_plan = payload.get("director_plan", {}) if isinstance(payload, dict) else {}
    render_plan = payload.get("render_plan", {}) if isinstance(payload, dict) else {}
    scene_shots = [row for row in scene_plan.get("shot_packages", []) if isinstance(row, dict)]
    director_shots = [row for row in director_plan.get("shot_packages", []) if isinstance(row, dict)]
    render_shots = [row for row in render_plan.get("shot_packages", []) if isinstance(row, dict)]
    shot_rows = render_shots or director_shots or scene_shots
    motifs = {str(row.get("motif_family", "")).strip() for row in scene_shots if str(row.get("motif_family", "")).strip()}
    zones = {str(row.get("zone", "")).strip() for row in scene_shots if str(row.get("zone", "")).strip()}
    continuity_groups = {
        str(row.get("continuity_group", "")).strip()
        for row in scene_shots
        if str(row.get("continuity_group", "")).strip()
    }
    render_strategy_counts: dict[str, int] = {}
    for row in shot_rows:
        strategy = str(row.get("render_strategy", "")).strip() or "ref_pair"
        render_strategy_counts[strategy] = render_strategy_counts.get(strategy, 0) + 1
    return {
        "shot_package_count": len(shot_rows),
        "motif_family_count": len(motifs),
        "zone_count": len(zones),
        "continuity_group_count": len(continuity_groups),
        "render_strategy_counts": render_strategy_counts,
    }


def beat_to_section_label(payload: dict) -> dict[str, str]:
    timeline = payload.get("lyrics_timeline", {}) if isinstance(payload, dict) else {}
    out: dict[str, str] = {}
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        label = str(section.get("section_label", section.get("section_name", "section"))).strip() or "section"
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if beat_id:
                out[beat_id] = label
    return out


def route_section_label(row: dict, beat_to_section: dict[str, str]) -> str:
    beat_id = str(row.get("lyric_beat_id", "")).strip()
    mapped = canonical_section_label("", beat_id, beat_to_section)
    if mapped:
        return mapped
    label = str(row.get("section_label", row.get("section_name", "section"))).strip()
    if "[" in label and "]" in label:
        label = str(row.get("section_name", "section")).strip()
    return canonical_section_label(label, beat_id, beat_to_section) or "section"


def canonical_section_label(raw_label: str, beat_id: str, beat_to_section: dict[str, str]) -> str:
    mapped = beat_to_section.get(beat_id, "").strip()
    if mapped:
        return mapped
    label = str(raw_label).strip()
    if not label:
        return ""
    norm = label.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "intro": "Intro",
        "verse_1": "Verse 1",
        "verse1": "Verse 1",
        "verse_2": "Verse 2",
        "verse2": "Verse 2",
        "pre_chorus": "Pre-Chorus",
        "prechorus": "Pre-Chorus",
        "chorus": "Chorus",
        "bridge": "Bridge",
        "final_chorus": "Final Chorus",
        "finalchorus": "Final Chorus",
        "outro": "Outro",
    }
    return aliases.get(norm, label)
