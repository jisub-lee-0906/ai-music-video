from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import SHOT_TYPES, normalize_tti_master, normalize_tti_shot, tti_schema
from ai_mv.infra.ollama_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    brief = payload["visual_brief"]
    sections = list(payload["audio_map"]["sections"])
    spec = _plan_with_ollama(config, payload["audio_map"], brief, sections)
    master = normalize_tti_master(spec["master_anchor"])
    shots = _normalize_shots(spec["shots"], sections)
    return {"master_anchor": master, "shots": shots}


def _plan_with_ollama(config: dict, audio_map: dict, brief: dict, sections: list[dict]) -> dict:
    out = generate_structured(config, _planner_prompt(config, audio_map, brief, sections), tti_schema())
    if not isinstance(out, dict):
        raise RuntimeError("invalid TTI planner output")
    if not isinstance(out.get("master_anchor"), dict):
        raise RuntimeError("TTI planner missing master_anchor")
    if not isinstance(out.get("shots"), list):
        raise RuntimeError("TTI planner missing shots")
    return out


def _planner_prompt(config: dict, audio_map: dict, brief: dict, sections: list[dict]) -> str:
    guidance = _style_guidance(config, audio_map)
    desc = str(audio_map.get("genre_description", "")).strip()
    lyrics = _lyrics_excerpt(str(audio_map.get("lyrics", "")))
    tags = str(audio_map.get("tags", "")).strip()
    brief_view = _brief_summary(brief)
    section_view = _section_summary(sections)
    types = ", ".join(SHOT_TYPES)
    return (
        "You are a senior music-video visual director and FLUX prompt engineer. "
        "Return strict JSON only with shape {\"master_anchor\":{...},\"shots\":[...]}. No prose outside JSON. "
        "Design one definitive character master anchor image, then design section blueprints that preserve that exact hero identity. "
        "Never force any genre; infer visual language from style guidance and lyrics context. "
        "master_anchor must include: prompt_clip_l,prompt_t5xxl,negative_prompt,seed. "
        "master_anchor prompt_clip_l must be 18-36 unique tags, comma+space separated, all lowercase natural phrases. "
        "No snake_case, no brackets, no markdown, no full sentence. "
        "Required slot order in master clip_l: subject identity, face traits, hair, eyes, wardrobe, fabric/material, pose, "
        "signature prop, background set, lighting style, lens/camera language, mood, color palette, cinematic quality. "
        "master_anchor prompt_t5xxl must be exactly 2 natural English sentences. "
        "Sentence 1 = hero identity + wardrobe + environment + signature prop with concrete detail. "
        "Sentence 2 = camera + lighting + emotional presence with cinematic language and no motion event. "
        "Keep one consistent hero identity, face geometry, hair, outfit, accessories, and makeup across the whole song. "
        "Use the visual brief as the source of truth for identity locks, world rules, motifs, and forbidden drift. "
        "master_anchor should absorb hero/world/motif rules, while shot items should absorb section-specific variation only. "
        "Each shot item must include: shot_id,shot_type,is_chorus,camera_language,pose_delta,emotion,scene_detail,motion_hint. "
        "Shot items must not redefine identity; they only specify framing, pose, emotion, environmental emphasis, and motion intent. "
        "Negative constraints and world rules override any section staging idea. "
        "camera_language should be a short cinematic phrase for framing/lens behavior only. "
        "camera_language must stay smooth and readable; avoid explosive, frantic, handheld, whip, crash zoom, or fast-pan language unless the brief explicitly allows it. "
        "pose_delta should describe exactly one readable body or gaze change. "
        "emotion should be concise and performance-oriented, not narrative. "
        "scene_detail should name exactly one concrete set or prop emphasis. "
        "motion_hint should prefer smooth readable motion, not frantic action or multiple simultaneous events. "
        "If the brief discourages fast camera or drift, use stillness, glide, slow dolly, gentle turn, or subtle gaze change instead of running or aggressive movement. "
        "Shot count must match section count exactly. "
        f"Use shot_type only from enum: {types}. "
        f"Audio tags={tags}; Audio direction={desc}; Style guidance={guidance}; Visual brief={brief_view}; Lyrics excerpt={lyrics}; Sections={section_view}."
    )


def _normalize_shots(shots: list[dict], sections: list[dict]) -> list[dict]:
    parsed = [normalize_tti_shot(row, idx) for idx, row in enumerate(shots) if isinstance(row, dict)]
    if not parsed:
        raise RuntimeError("no valid shots from TTI planner")
    if not sections:
        raise RuntimeError("sections missing for TTI planner")
    if len(parsed) != len(sections):
        raise RuntimeError(f"TTI planner shot count mismatch: expected={len(sections)} actual={len(parsed)}")
    return _assign_one_shot_per_section(parsed, sections)


def _assign_one_shot_per_section(shots: list[dict], sections: list[dict]) -> list[dict]:
    out: list[dict] = []
    for idx, (row, sec) in enumerate(zip(shots, sections), start=1):
        item = dict(row)
        item["shot_id"] = f"S{idx:03d}"
        item["section_name"] = str(sec.get("name", "section"))
        item["is_chorus"] = _is_chorus(item["section_name"])
        item["duration_sec"] = round(max(0.001, _sec_end(sec) - _sec_start(sec)), 3)
        out.append(item)
    return out


def _is_chorus(name: str) -> bool:
    sec = str(name).strip().lower()
    return sec == "chorus" or sec.startswith("chorus_")


def _sec_start(row: dict) -> float:
    return float(row.get("start_sec", row.get("start", 0.0)))


def _sec_end(row: dict) -> float:
    return float(row.get("end_sec", row.get("end", 0.0)))


def _lyrics_excerpt(text: str) -> str:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return " | ".join(lines[:12]) if lines else ""


def _style_guidance(config: dict, audio_map: dict) -> str:
    guided = str(audio_map.get("style_guidance", "")).strip()
    if guided:
        return guided
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


def _section_summary(sections: list[dict]) -> str:
    out: list[str] = []
    for row in sections:
        name = str(row.get("name", "section")).strip()
        out.append(f"{name}:{round(_sec_start(row), 2)}-{round(_sec_end(row), 2)}")
    if not out:
        raise RuntimeError("sections missing for TTI prompt planner")
    return ", ".join(out)


def _brief_summary(brief: dict) -> str:
    motifs = ", ".join(brief.get("visual_motifs", []))
    rules = ", ".join(brief.get("negative_constraints", []))
    return (
        f"hero={brief['hero_identity']}; world={brief['world_rules']}; "
        f"motifs={motifs}; avoid={rules}; section_rules={_section_briefs(brief)}"
    )


def _section_briefs(brief: dict) -> str:
    rows = []
    for row in brief.get("section_briefs", []):
        rows.append(
            f"{row['section_name']}|{row['emotional_arc']}|{row['palette_hint']}|"
            f"{row['lighting_hint']}|{row['staging_hint']}"
        )
    return ", ".join(rows)
