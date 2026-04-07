from __future__ import annotations

import json

from ai_mv.core.contracts.prompt_normalize import normalize_lyrics_timeline
from ai_mv.core.contracts.prompt_schema import lyrics_timeline_schema
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.infra.codex_cli_client import generate_structured


def build_lyrics_timeline(config: dict, payload: dict) -> dict:
    audio_plan = payload["audio_plan"]
    sections = list(payload["audio_map"]["sections"])
    prompt = _planner_prompt(config, audio_plan, sections)
    raw = generate_structured(config, prompt, lyrics_timeline_schema(), attempts=1)
    try:
        timeline = normalize_lyrics_timeline(raw, sections)
    except RuntimeError as exc:
        raise RuntimeError(f"lyrics_timeline validation failed: {exc}") from exc
    _attach_time_ranges(timeline, sections)
    return timeline


def build_lyrics_timeline_preview_prompt(config: dict, audio_plan: dict, sections: list[dict]) -> str:
    return _planner_prompt(config, audio_plan, sections)


def _planner_prompt(config: dict, audio_plan: dict, sections: list[dict]) -> str:
    max_beats = _recommended_max_beats(audio_plan, sections)
    brief = build_director_brief_intent(config)
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
        "literal_image must stay close to the lyric image and name concrete physical things the camera can actually show. "
        "visible_action must be screen-readable and describe exactly what the performer is doing in that beat. "
        "emotional_turn must describe the feeling shift in plain cinematic language, not abstract criticism or analysis. "
        "continuity_anchor must name the specific person/place/prop/detail that should carry into the next beat. "
        "payoff_role must explain what that beat does in the sequence: setup, carry, tighten, release, payoff, or residue. "
        "Use grounded cinematic shot-card thinking, not symbolic analysis. "
        "Use profile information only to keep the same world coherent: preferred locations describe possible places, and carry-friendly props describe reusable physical details. "
        "Do not force every beat into the profile locations or props if the lyric image clearly demands something else. "
        "Let the lyric line decide the current image and action; let the profile only stabilize the world around it. "
        "Prefer tangible nouns like window, mug, notebook, wet asphalt, headlights, cables, rooftop wind, or empty chair over vague mood language. "
        "Prefer visible actions like writing, walking, turning, crossing, sitting, holding, looking, stepping, or pausing over internal-only statements. "
        "Do not write meta phrases like 'the scene shows', 'the sequence', 'visual metaphor', 'emotional thread', 'continuity', or 'camera-ready'. "
        "Do not mention editing, camera instructions, lens names, film grain, or prompt-writing advice here. "
        "Within a section, avoid flattening all beats into the same image or action. "
        "If a chorus repeats, keep the core motif but change at least the emotional_turn or payoff_role and shift the image/action emphasis. "
        "Intro should establish the world cleanly, verses should progress through distinct observations, pre-chorus should tighten and aim, chorus should present the hook image and release, bridge should interrupt or thin the motion, and outro should resolve with a final after-image. "
        "Repeated choruses must not collapse into the same emotional_turn and payoff_role. "
        "Instrumental Intro or Outro sections should remain empty here rather than inventing fake lyric beats. "
        "Before finalizing, check every section: all source lines are present, each has line_index and text, and all beat line_refs refer only to that section's line_index values. "
        f"Visual concept={_brief_visual_context(brief)}. "
        f"Preferred locations={_preferred_locations(brief)}. "
        f"Carry-friendly props={_preferred_props(brief)}. "
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
    source_sections = [section for section in sections if isinstance(section, dict)]
    indexed_by_name: dict[str, list[dict]] = {}
    indexed_by_name_and_label: dict[tuple[str, str], list[dict]] = {}
    for section in source_sections:
        section_name = str(section.get("name", "")).strip()
        section_label = str(section.get("label", section.get("name", ""))).strip()
        indexed_by_name.setdefault(section_name, []).append(section)
        indexed_by_name_and_label.setdefault((section_name, section_label), []).append(section)
    name_counts: dict[str, int] = {}
    name_and_label_counts: dict[tuple[str, str], int] = {}
    for section_index, section in enumerate(timeline.get("sections", [])):
        section_name = str(section.get("section_name", "")).strip()
        section_label = str(section.get("section_label", section_name)).strip()
        row = {}
        label_key = (section_name, section_label)
        label_bucket = indexed_by_name_and_label.get(label_key, [])
        if label_bucket:
            label_idx = name_and_label_counts.get(label_key, 0)
            if label_idx < len(label_bucket):
                row = label_bucket[label_idx]
                name_and_label_counts[label_key] = label_idx + 1
        if not row:
            name_bucket = indexed_by_name.get(section_name, [])
            name_idx = name_counts.get(section_name, 0)
            if name_idx < len(name_bucket):
                row = name_bucket[name_idx]
                name_counts[section_name] = name_idx + 1
        if not row and section_index < len(source_sections):
            row = source_sections[section_index]
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


def _brief_visual_context(brief: dict) -> str:
    parts = [
        str(brief.get("visual_concept", "")).strip(),
        str(brief.get("profile_genre", "")).strip(),
        str(brief.get("profile_voice", "")).strip(),
    ]
    return " | ".join(part for part in parts if part) or "grounded cinematic music video"


def _preferred_locations(brief: dict) -> str:
    rows = [str(x).strip() for x in brief.get("profile_locations", []) if str(x).strip()]
    return ", ".join(rows) if rows else "no fixed location list"


def _preferred_props(brief: dict) -> str:
    rows = [str(x).strip() for x in brief.get("profile_props", []) if str(x).strip()]
    return ", ".join(rows) if rows else "no fixed prop list"
