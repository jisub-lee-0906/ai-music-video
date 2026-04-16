from __future__ import annotations

import math

from ai_mv.core.planning.routing import apply_render_routing
from ai_mv.core.planning.sections import compress_shots_to_m1_window, use_m1_window
from ai_mv.styles.resolver import apply_style_section_variants, style_section_shot_specs



def build_shot_plan(config: dict, sections: list[dict], style_name: str = "citypop") -> list[dict]:
    total_duration = sum(float(section.get("duration_sec", 0.0) or 0.0) for section in sections)
    shots: list[dict] = []
    for section in sections:
        for part in split_section_into_shots(config, section, style_name=style_name):
            shots.append(
                {
                    "shot_id": "",
                    "section_name": section["section_name"],
                    "section_type": section["section_type"],
                    "start_sec": part["start_sec"],
                    "end_sec": part["end_sec"],
                    "duration_sec": round(part["end_sec"] - part["start_sec"], 3),
                    "shot_role": part["shot_role"],
                    "visual_mode": part["visual_mode"],
                    "energy": part["energy"],
                    "render_mode": part["render_mode"],
                    "source_section_index": section["index"],
                }
            )
    normalized = renumber_shots(shots)
    if use_m1_window(total_duration):
        normalized = compress_shots_to_m1_window(normalized)
        normalized = renumber_shots(normalized)
    return apply_render_routing(config, normalized)



def split_section_into_shots(config: dict, section: dict, *, style_name: str = "citypop") -> list[dict]:
    duration_sec = float(section["duration_sec"])
    section_type = str(section["section_type"])
    shot_specs = style_section_shot_specs(style_name, section_type, duration_sec)
    start_sec = float(section["start_sec"])
    out: list[dict] = []
    cursor = start_sec
    for idx, spec in enumerate(shot_specs, start=1):
        is_last = idx == len(shot_specs)
        part_duration = duration_sec * spec["weight"]
        end_sec = float(section["end_sec"]) if is_last else round(cursor + part_duration, 3)
        out.append(
            {
                "start_sec": round(cursor, 3),
                "end_sec": round(end_sec, 3),
                "shot_role": spec["shot_role"],
                "visual_mode": spec["visual_mode"],
                "energy": spec["energy"],
                "render_mode": spec["render_mode"],
            }
        )
        cursor = end_sec
    return apply_style_section_variants(style_name, section_type, split_oversized_parts(config, out))



def split_oversized_parts(config: dict, parts: list[dict]) -> list[dict]:
    max_shot_sec = max_shot_seconds(config)
    if max_shot_sec <= 0:
        return parts
    expanded: list[dict] = []
    for part in parts:
        duration_sec = float(part.get("end_sec", 0.0) or 0.0) - float(part.get("start_sec", 0.0) or 0.0)
        split_count = max(1, int(math.ceil(duration_sec / max_shot_sec)))
        if split_count == 1:
            expanded.append(part)
            continue
        start_sec = float(part["start_sec"])
        step = duration_sec / float(split_count)
        for idx in range(split_count):
            sub_start = round(start_sec + (step * idx), 3)
            sub_end = round(float(part["end_sec"]) if idx == split_count - 1 else start_sec + (step * (idx + 1)), 3)
            expanded.append(
                {
                    **part,
                    "start_sec": sub_start,
                    "end_sec": sub_end,
                }
            )
    return expanded



def renumber_shots(shots: list[dict]) -> list[dict]:
    out: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        row = dict(shot)
        row["shot_id"] = f"S{idx:03d}"
        out.append(row)
    return out



def max_shot_seconds(config: dict) -> float:
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    return max(1.0, _float(planning.get("max_shot_sec"), 8.0))



def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default
