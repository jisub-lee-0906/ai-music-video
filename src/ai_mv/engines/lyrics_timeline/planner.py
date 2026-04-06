from __future__ import annotations

import json

from ai_mv.core.contracts.prompt_normalize import normalize_lyrics_timeline
from ai_mv.core.contracts.prompt_schema import lyrics_timeline_schema
from ai_mv.infra.codex_cli_client import generate_structured


def build_lyrics_timeline(config: dict, payload: dict) -> dict:
    audio_plan = payload["audio_plan"]
    sections = list(payload["audio_map"]["sections"])
    prompt = _planner_prompt(audio_plan, sections)
    raw = generate_structured(config, prompt, lyrics_timeline_schema(), attempts=1)
    try:
        timeline = normalize_lyrics_timeline(raw, sections)
    except RuntimeError as exc:
        raise RuntimeError(f"lyrics_timeline validation failed: {exc}") from exc
    _attach_time_ranges(timeline, sections)
    return timeline


def build_lyrics_timeline_preview_prompt(audio_plan: dict, sections: list[dict]) -> str:
    return _planner_prompt(audio_plan, sections)


def _planner_prompt(audio_plan: dict, sections: list[dict]) -> str:
    max_beats = _recommended_max_beats(audio_plan, sections)
    return (
        "You are a lyric-to-scene timeline planner for a music video. "
        "Return strict JSON only. No prose outside JSON. "
        "Required field: sections. Each section must include section_name,section_label,lines,hook_lines,lyric_beats. "
        "Every lyric_beat must include beat_id,line_refs,literal_image,visible_action,emotional_turn,continuity_anchor,payoff_role,repeat_variant_of. "
        "Use the final generated lyrics as the source of truth. "
        "For each section, copy the source lyric lines into sections[].lines exactly as provided. "
        "Do not rewrite, shorten, translate, merge, drop, or renumber any line. "
        "Every lines item must contain both line_index and text. "
        "The set of section line_index values in your output must exactly match the source section lines. "
        "If a source section has no lyric lines, keep sections[].lines as an empty array and sections[].lyric_beats as an empty array for that section. "
        f"Break each section into 1-{max_beats} visual beats depending on line count and section length. "
        "Use more beats when a section has many lines, clear image turns, or a hook/release split. "
        "Favor 2 beats for compact sections, 3-4 beats for dense verses or choruses, and 4-5 only when the lyrics genuinely present multiple distinct visual turns. "
        "Cover every lyric line at least once across the section's beat line_refs; do not leave lyric lines unmapped. "
        "Treat line_refs as a complete coverage map for the section. Prefer contiguous or musically coherent line groupings instead of arbitrary scattering. "
        "line_refs must point only to line_index values from that section. "
        "Never invent a line_index that is not present in the source section. "
        "Never output an empty line text when a line exists. "
        "literal_image must stay close to the lyric image. "
        "visible_action must be screen-readable. "
        "Within a section, avoid flattening all beats into the same image or action. "
        "If a chorus repeats, keep the core motif but change at least the emotional_turn or payoff_role and shift the image/action emphasis. "
        "Intro should establish the world cleanly, verses should progress through distinct observations, pre-chorus should tighten and aim, chorus should present the hook image and release, bridge should interrupt or thin the motion, and outro should resolve with a final after-image. "
        "Repeated choruses must not collapse into the same emotional_turn and payoff_role. "
        "Instrumental Intro or Outro sections should remain empty here rather than inventing fake lyric beats. "
        "Before finalizing, check every section: all source lines are present, each has line_index and text, and all beat line_refs refer only to that section's line_index values. "
        f"Sections={_section_digest(sections)}. "
        f"Source section lines JSON={_section_lines_json(sections)}. "
        f"Lyrics={_lyrics_digest(audio_plan)}."
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


def _section_lines_json(sections: list[dict]) -> str:
    payload = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        lines = []
        for row in section.get("lines", []):
            if not isinstance(row, dict):
                continue
            line_index = int(row.get("line_index", 0))
            text = str(row.get("text", "")).strip()
            if line_index > 0 and text:
                lines.append({"line_index": line_index, "text": text})
        payload.append(
            {
                "section_name": str(section.get("name", "section")).strip(),
                "section_label": str(section.get("label", section.get("name", "section"))).strip(),
                "lines": lines,
            }
        )
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


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


def _recommended_max_beats(audio_plan: dict, sections: list[dict]) -> int:
    max_lines = 0
    for section in sections:
        if not isinstance(section, dict):
            continue
        lines = [row for row in section.get("lines", []) if isinstance(row, dict)]
        max_lines = max(max_lines, len(lines))
    for block in audio_plan.get("lyrics_blocks", []):
        if not isinstance(block, dict):
            continue
        indexed = [row for row in block.get("indexed_lines", []) if isinstance(row, dict)]
        if indexed:
            max_lines = max(max_lines, len(indexed))
            continue
        lines = [str(x).strip() for x in block.get("lines", []) if str(x).strip()]
        max_lines = max(max_lines, len(lines))
    if max_lines >= 8:
        return 5
    if max_lines >= 6:
        return 4
    return 3
