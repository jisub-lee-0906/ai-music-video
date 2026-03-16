from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_lyrics_timeline
from ai_mv.core.contracts.prompt_schema import lyrics_timeline_schema
from ai_mv.infra.codex_cli_client import generate_structured


def build_lyrics_timeline(config: dict, payload: dict) -> dict:
    audio_plan = payload["audio_plan"]
    sections = list(payload["audio_map"]["sections"])
    raw = generate_structured(config, _planner_prompt(audio_plan, sections), lyrics_timeline_schema())
    timeline = normalize_lyrics_timeline(raw, sections)
    _attach_time_ranges(timeline, sections)
    return timeline


def _planner_prompt(audio_plan: dict, sections: list[dict]) -> str:
    return (
        "You are a lyric-to-scene timeline planner for a music video. "
        "Return strict JSON only. No prose outside JSON. "
        "Required field: sections. Each section must include section_name,section_label,lines,hook_lines,lyric_beats. "
        "Every lyric_beat must include beat_id,line_refs,literal_image,visible_action,emotional_turn,continuity_anchor,payoff_role,repeat_variant_of. "
        "Use the final generated lyrics as the source of truth. "
        "Break each section into 1-3 visual beats. "
        "line_refs must point only to line_index values from that section. "
        "literal_image must stay close to the lyric image. "
        "visible_action must be screen-readable. "
        "Repeated choruses must not collapse into the same emotional_turn and payoff_role. "
        f"Sections={_section_digest(sections)}. Lyrics={_lyrics_digest(audio_plan)}."
    )


def _section_digest(sections: list[dict]) -> str:
    return ", ".join(
        f"{section.get('name', 'section')}|{section.get('label', section.get('name', 'section'))}|"
        f"{section.get('start_sec', section.get('start', 0.0))}-{section.get('end_sec', section.get('end', 0.0))}"
        for section in sections
    )


def _lyrics_digest(audio_plan: dict) -> str:
    rows: list[str] = []
    for block_idx, block in enumerate(audio_plan.get("lyrics_blocks", []), start=1):
        if not isinstance(block, dict):
            continue
        lines = block.get("indexed_lines", [])
        if not lines:
            lines = [{"line_index": i, "text": line} for i, line in enumerate(block.get("lines", []), start=1)]
        rows.append(
            f"{block.get('label', block.get('section', f'section_{block_idx}'))}: "
            + " / ".join(f"{line.get('line_index', 0)}:{line.get('text', '')}" for line in lines if str(line.get("text", "")).strip())
        )
    return " ; ".join(rows)


def _attach_time_ranges(timeline: dict, sections: list[dict]) -> None:
    section_map = {
        str(section.get("name", "")).strip(): section
        for section in sections
        if isinstance(section, dict)
    }
    for section in timeline.get("sections", []):
        section_name = str(section.get("section_name", "")).strip()
        row = section_map.get(section_name, {})
        start = float(row.get("start_sec", row.get("start", 0.0)))
        end = float(row.get("end_sec", row.get("end", start)))
        beats = [beat for beat in section.get("lyric_beats", []) if isinstance(beat, dict)]
        span = max(0.001, end - start)
        beat_span = span / float(max(1, len(beats)))
        for idx, beat in enumerate(beats):
            beat["start_sec"] = round(start + beat_span * idx, 3)
            beat["end_sec"] = round(start + beat_span * (idx + 1), 3)
