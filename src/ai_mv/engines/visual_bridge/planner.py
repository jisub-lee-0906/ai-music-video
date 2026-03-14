from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_visual_brief
from ai_mv.core.contracts.prompt_schema import visual_brief_schema
from ai_mv.core.prompt_digests import audio_digest, label_digest, style_digest, visual_digest
from ai_mv.infra.codex_cli_client import generate_structured


def build_visual_brief(config: dict, payload: dict) -> dict:
    audio_map = payload["audio_map"]
    sections = list(audio_map["sections"])
    raw = generate_structured(config, _planner_prompt(audio_map, sections), visual_brief_schema())
    return normalize_visual_brief(raw, sections)


def _planner_prompt(audio_map: dict, sections: list[dict]) -> str:
    guidance = style_digest(audio_map, 1)
    genre = audio_digest(audio_map, 1)
    direction = visual_digest(audio_map, 1)
    names = _section_names(sections)
    labels = label_digest(sections)
    semantics = _section_semantics(audio_map)
    return (
        "You are a senior music-video world-lock planner building a thin reusable visual brief for downstream planners. "
        "Return strict JSON only. No prose outside JSON. "
        "Required fields: hero_identity,world_rules,visual_motifs,negative_constraints,section_briefs. "
        "section_briefs item fields: section_name,emotional_arc,palette_hint,lighting_hint,staging_hint,story_beat,location_anchor. "
        "Build one stable lead identity and one stable visual world that can survive TTI, Flux2 reference, and WAN without drift. "
        "hero_identity must describe only identity locks: face, hair, age impression, styling, signature wardrobe, and only an explicitly required hero prop. "
        "Derive identity strictly from the profile and visual brief; never infer ethnicity, gender, genre-specific styling, or cultural lane unless the input clearly says so. "
        "If the profile implies a youthful or fresh lead, keep the age impression clearly young adult, roughly mid-20s to early-30s, and do not drift older unless the input explicitly asks for mature or older presence. "
        "Do not invent a handheld prop, umbrella, microphone, shopping bag, phone, or instrument unless the input clearly locks it. "
        "If no prop is necessary, anchor identity through silhouette, hair styling, and accessories rather than inventing a handheld object. "
        "Do not put camera moves, scene actions, or section events inside hero_identity. "
        "world_rules must be 2 short sentences covering setting, recurring spaces, and the master palette or lighting baseline only. "
        "visual_motifs must be short reusable noun phrases, not full sentences. "
        "negative_constraints must be short forbidden drift items, not explanations. "
        "Each section_brief should stay short and practical while preserving the same lead identity and world. "
        "Use section labels as escalation hints: Chorus 2 should feel like a stronger return than Chorus, and Final Chorus should feel like the peak return without changing worlds. "
        "Create a small location budget for the whole song: reuse 2-3 recurring spaces rather than inventing a new place every section. "
        "palette_hint and lighting_hint must be short accent cues, not a full reset. "
        "staging_hint must stay physically simple and camera-safe: one clear setup, one readable action, no frantic verbs. "
        "story_beat must be a short plain-English visible action beat for that section, not just a mood label. "
        "Every story_beat must contain at least one visible action verb such as slows, checks, passes, pauses, turns, steps, faces, drifts, walks, stops, holds, leaves, returns, or follows. "
        "Write story_beat as one readable present-tense clause of about 6-14 words, grounded in what the camera can actually see. "
        "Good story_beat pattern: verb + place/object + second readable action. "
        "Good story_beat examples: slows by the glass and checks the reflection; passes the storefront without looking back; pauses at the curb before turning; steps into the open crosswalk and finally faces forward. "
        "Bad story_beat examples: searching, opening up, separation, confidence, romantic release, emotional climax. "
        "If a draft story_beat sounds abstract, replace it with the concrete body action that would make the emotion visible on screen. "
        "location_anchor must be a short recurring place phrase like storefront pavement, station corridor glass, crosswalk under neon, or alley reflection. "
        "Most adjacent sections should reuse the same location_anchor or move to one closely related place, so the video feels like progression inside one world instead of random location hopping. "
        "Keep the brief practical for downstream planners: concise, reusable, and low-ambiguity. "
        "section_briefs must match Section names exactly in count and order. "
        "If a section name repeats, return repeated section_briefs entries in the same repeated order; never merge duplicate section names. "
        "section_name must be a bare section token only, never include timing, punctuation ranges, or extra annotation. "
        "Avoid generic section_brief language like cinematic mood, emotional scene, stylish lighting, or dramatic performance unless grounded in a clear visual setup. "
        f"Style lane={guidance}; Audio direction={genre}; "
        f"Visual direction={direction}; Section semantics={semantics}; "
        f"Section names only={names}; Section labels in order={labels}."
    )

def _section_names(sections: list[dict]) -> str:
    out = [str(row.get("name", "section")).strip() for row in sections]
    vals = [x for x in out if x]
    if not vals:
        raise RuntimeError("visual brief sections missing")
    return ", ".join(vals)

def _section_semantics(audio_map: dict) -> str:
    rows = audio_map.get("section_semantics", []) if isinstance(audio_map, dict) else []
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            f"{row.get('section_label', row.get('section_name', 'section'))}|"
            f"{row.get('movement_bias', '')}|"
            f"{row.get('release_level', '')}"
        )
    return ", ".join(x for x in out if x)
