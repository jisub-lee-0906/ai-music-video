from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_visual_brief, visual_brief_schema
from ai_mv.infra.ollama_client import generate_structured


def build_visual_brief(config: dict, payload: dict) -> dict:
    audio_map = payload["audio_map"]
    sections = list(audio_map["sections"])
    raw = generate_structured(config, _planner_prompt(audio_map, sections), visual_brief_schema())
    return normalize_visual_brief(raw, sections)


def _planner_prompt(audio_map: dict, sections: list[dict]) -> str:
    tags = str(audio_map.get("tags", "")).strip()
    guidance = str(audio_map.get("style_guidance", "")).strip()
    genre = str(audio_map.get("genre_description", "")).strip()
    lyrics = _lyrics_excerpt(str(audio_map.get("lyrics", "")))
    summary = _section_summary(sections)
    return (
        "You are a senior music-video creative director building a reusable visual brief for downstream planners. "
        "Return strict JSON only. No prose outside JSON. "
        "Required fields: hero_identity,world_rules,visual_motifs,negative_constraints,section_briefs. "
        "section_briefs item fields: section_name,emotional_arc,palette_hint,lighting_hint,staging_hint. "
        "Build one stable hero identity and one stable visual world that can survive TTI, USO, and WAN without drift. "
        "hero_identity must describe only identity locks: face, hair, age impression, styling, signature wardrobe, and hero prop. "
        "When audio direction, tags, or style guidance point to Japanese city-pop or East Asian urban nostalgia, hero_identity should reflect an East Asian heroine by default unless the input clearly says otherwise. "
        "Do not put camera moves, scene actions, or section events inside hero_identity. "
        "world_rules must be 2-3 short sentences covering setting, image texture, atmosphere, and the master palette/lighting baseline only. "
        "visual_motifs must be short reusable noun phrases, not full sentences. "
        "negative_constraints must be short forbidden drift items, not explanations. "
        "Use negative_constraints to lock continuity and camera intensity for the whole song. "
        "Prefer calm, elegant, readable camera language unless the audio clearly demands a stronger lift. "
        "Avoid forbidden combinations such as 'no fast camera' together with running, explosive action, or aggressive zoom language. "
        "Each section_brief should differ by emotion, palette, lighting, and staging emphasis while preserving the same hero and world. "
        "palette_hint must be an accent palette layered on top of the same master palette, not a full palette reset. "
        "lighting_hint must be a section accent that still inherits the same global lighting baseline. "
        "section_briefs should change emphasis, not rewrite the visual grammar. "
        "staging_hint must stay physically simple and camera-safe: one clear setup, one readable action, no frantic verbs. "
        "Keep the brief practical for downstream planners: concise, reusable, and low-ambiguity. "
        "section_briefs must match Sections exactly in count and order. "
        f"Audio tags={tags}; Style guidance={guidance}; Audio direction={genre}; Lyrics excerpt={lyrics}; Sections={summary}."
    )


def _lyrics_excerpt(text: str) -> str:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return " | ".join(lines[:10]) if lines else ""


def _section_summary(sections: list[dict]) -> str:
    out: list[str] = []
    for row in sections:
        name = str(row.get("name", "section")).strip()
        start = round(float(row.get("start_sec", 0.0)), 2)
        end = round(float(row.get("end_sec", 0.0)), 2)
        out.append(f"{name}:{start}-{end}")
    if not out:
        raise RuntimeError("visual brief sections missing")
    return ", ".join(out)
