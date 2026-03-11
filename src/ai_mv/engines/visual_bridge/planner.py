from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_visual_brief
from ai_mv.core.contracts.prompt_schema import visual_brief_schema
from ai_mv.infra.codex_cli_client import generate_structured


def build_visual_brief(config: dict, payload: dict) -> dict:
    audio_map = payload["audio_map"]
    sections = list(audio_map["sections"])
    raw = generate_structured(config, _planner_prompt(audio_map, sections), visual_brief_schema())
    return normalize_visual_brief(raw, sections)


def _planner_prompt(audio_map: dict, sections: list[dict]) -> str:
    tags = str(audio_map.get("tags", "")).strip()
    guidance = str(audio_map.get("style_guidance", "")).strip()
    genre = str(audio_map.get("genre_description", "")).strip()
    profile = str(audio_map.get("profile_summary", "")).strip()
    direction = str(audio_map.get("visual_direction", "")).strip()
    negative = str(audio_map.get("negative_direction", "")).strip()
    lyrics = _lyrics_excerpt(str(audio_map.get("lyrics", "")))
    names = _section_names(sections)
    labels = _section_labels(sections)
    timing = _timing_reference(sections)
    return (
        "You are a senior music-video creative director building a reusable visual brief for downstream planners. "
        "Return strict JSON only. No prose outside JSON. "
        "Required fields: hero_identity,world_rules,visual_motifs,negative_constraints,section_briefs. "
        "section_briefs item fields: section_name,emotional_arc,palette_hint,lighting_hint,staging_hint. "
        "Build one stable hero identity and one stable visual world that can survive TTI, USO, and WAN without drift. "
        "hero_identity must describe only identity locks: face, hair, age impression, styling, signature wardrobe, and hero prop. "
        "When audio direction, tags, or style guidance point to Japanese city-pop or East Asian urban nostalgia, hero_identity should reflect an East Asian heroine by default unless the input clearly says otherwise. "
        "hero prop is a supporting identity accent, not the primary subject of the frame. "
        "Choose a hero prop only if it can remain visually secondary across most shots; prefer subtle worn accessories like jewelry, hair clips, scarves, or gloves over handheld objects. "
        "If no prop is clearly necessary, keep the hero identity anchored by wardrobe silhouette, hair styling, and jewelry instead of inventing a handheld object. "
        "Do not put camera moves, scene actions, or section events inside hero_identity. "
        "world_rules must be 2-3 short sentences covering setting, image texture, atmosphere, and the master palette/lighting baseline only. "
        "visual_motifs must be short reusable noun phrases, not full sentences. "
        "negative_constraints must be short forbidden drift items, not explanations. "
        "Use negative_constraints to lock continuity and camera intensity for the whole song. "
        "Prefer calm, elegant, readable camera language unless the audio clearly demands a stronger lift. "
        "Avoid forbidden combinations such as 'no fast camera' together with running, explosive action, or aggressive zoom language. "
        "Each section_brief should differ by emotion, palette, lighting, and staging emphasis while preserving the same hero and world. "
        "Use section labels as escalation hints: Chorus 2 should feel like a stronger return than Chorus, and Final Chorus should feel like the emotional and visual peak without changing worlds. "
        "palette_hint must be an accent palette layered on top of the same master palette, not a full palette reset. "
        "lighting_hint must be a section accent that still inherits the same global lighting baseline. "
        "section_briefs should change emphasis, not rewrite the visual grammar. "
        "staging_hint must stay physically simple and camera-safe: one clear setup, one readable action, no frantic verbs. "
        "Repeated chorus briefs should widen confidence, openness, or brightness in small steps; Final Chorus should read as the peak return rather than a separate concept. "
        "Default staging emphasis should favor face, posture, silhouette, and environment over prop display. "
        "Do not let bags, props, or accessories dominate the frame unless the section explicitly calls for a brief detail emphasis. "
        "Keep the brief practical for downstream planners: concise, reusable, and low-ambiguity. "
        "Treat profile_summary and visual_direction as the reusable world brief for future profiles: compress many tags into one stable world instead of echoing tag lists. "
        "section_briefs must match Section names exactly in count and order. "
        "If a section name repeats, return repeated section_briefs entries in the same repeated order; never merge duplicate section names. "
        "section_name must be a bare section token only, never include timing, punctuation ranges, or extra annotation. "
        "Avoid generic section_brief language like cinematic mood, emotional scene, stylish lighting, or dramatic performance unless grounded in a clear visual setup. "
        f"Audio tags={tags}; Style guidance={guidance}; Audio direction={genre}; Profile steering={profile}; "
        f"Visual direction={direction}; Avoid={negative}; Lyrics excerpt={lyrics}; "
        f"Section names only={names}; Section labels in order={labels}; Timing reference={timing}."
    )


def _lyrics_excerpt(text: str) -> str:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return " | ".join(lines[:10]) if lines else ""


def _section_names(sections: list[dict]) -> str:
    out = [str(row.get("name", "section")).strip() for row in sections]
    vals = [x for x in out if x]
    if not vals:
        raise RuntimeError("visual brief sections missing")
    return ", ".join(vals)


def _section_labels(sections: list[dict]) -> str:
    out = [str(row.get("label", row.get("name", "section"))).strip() for row in sections]
    vals = [x for x in out if x]
    if not vals:
        raise RuntimeError("visual brief sections missing")
    return ", ".join(vals)


def _timing_reference(sections: list[dict]) -> str:
    out: list[str] = []
    for row in sections:
        name = str(row.get("name", "section")).strip()
        start = round(float(row.get("start_sec", 0.0)), 2)
        end = round(float(row.get("end_sec", 0.0)), 2)
        out.append(f"{name}({start}-{end})")
    if not out:
        raise RuntimeError("visual brief sections missing")
    return ", ".join(out)
