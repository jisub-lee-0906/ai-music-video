from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_tti_master, normalize_tti_shot
from ai_mv.core.contracts.prompt_schema import SHOT_TYPES, tti_schema
from ai_mv.infra.codex_cli_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    brief = payload["visual_brief"]
    sections = list(payload["audio_map"]["sections"])
    spec = _plan_with_llm(config, payload["audio_map"], brief, sections)
    master = normalize_tti_master(spec["master_anchor"])
    shots = _normalize_shots(spec["shots"], sections)
    return {"master_anchor": master, "shots": shots}


def _plan_with_llm(config: dict, audio_map: dict, brief: dict, sections: list[dict]) -> dict:
    out = generate_structured(config, _planner_prompt(config, audio_map, brief, sections), tti_schema())
    if not isinstance(out, dict):
        raise RuntimeError("invalid TTI planner output")
    if not isinstance(out.get("master_anchor"), dict):
        raise RuntimeError("TTI planner missing master_anchor")
    if not isinstance(out.get("shots"), list):
        raise RuntimeError("TTI planner missing shots")
    return out


def _planner_prompt(config: dict, audio_map: dict, brief: dict, sections: list[dict]) -> str:
    context = _planner_context(config, audio_map, brief, sections)
    return _planner_rules() + _planner_inputs(context)


def _planner_context(config: dict, audio_map: dict, brief: dict, sections: list[dict]) -> dict[str, str]:
    return {
        "guidance": _style_guidance(config, audio_map),
        "desc": str(audio_map.get("genre_description", "")).strip(),
        "lyrics": _lyrics_excerpt(str(audio_map.get("lyrics", ""))),
        "tags": str(audio_map.get("tags", "")).strip(),
        "profile": str(audio_map.get("profile_summary", "")).strip(),
        "visual_direction": str(audio_map.get("visual_direction", "")).strip(),
        "negative_direction": str(audio_map.get("negative_direction", "")).strip(),
        "brief_view": _brief_summary(brief),
        "section_view": _section_summary(sections),
        "section_labels": _section_labels(sections),
        "types": ", ".join(SHOT_TYPES),
    }


def _planner_rules() -> str:
    return (
        "You are a senior music-video visual director and Flux 2 image prompt engineer. "
        "Return strict JSON only with shape {\"master_anchor\":{...},\"shots\":[...]}. No prose outside JSON. "
        "Design one definitive character master anchor image, then design section blueprints that preserve that exact hero identity. "
        "Never force any genre; infer visual language from style guidance and lyrics context. "
        "master_anchor must include: prompt_text,seed. "
        "master_anchor prompt_text must be one compact diffusion prompt string, about 12-18 comma-separated visual phrases. "
        "prompt_text is injected directly into the workflow text encoder, so do not use lists, labels, shot ids, markdown, or prose commentary. "
        "Use raw visual prompt language only: subject identity, face traits, hair, wardrobe, fabric/material, pose, background set, lighting style, lens language, mood, palette, and finish. "
        "Match the workflow example style: short comma-separated noun phrases and modifier phrases, not full sentences and not paragraph prose. "
        "Keep the prompt lexically dense and image-led, more like 'high fashion, vintage couture, street photography' than like a screenplay description. "
        "Keep one consistent hero identity, face geometry, hair, outfit, accessories, and makeup across the whole song. "
        "If the visual brief implies Japanese city-pop or East Asian urban nostalgia, preserve East Asian facial features and styling cues in the master anchor unless the brief explicitly says otherwise. "
        "Treat the signature prop as a supporting identity accent; the face and upper-body performance remain the primary subject. "
        "Do not let the signature prop become the visual anchor of the master image; use face, posture, wardrobe silhouette, and environment first. "
        "Use the visual brief as the source of truth for identity locks, world rules, motifs, and forbidden drift. "
        "master_anchor should absorb hero/world/motif rules, while shot items should absorb section-specific variation only. "
        "Repeated sections should feel like stronger returns, not new worlds: later chorus shots can widen energy or confidence, but must preserve the same heroine and world grammar. "
        "Use section labels as escalation hints: Chorus 2 should feel like a firmer return, and Final Chorus should feel like the visual payoff shot for the song. "
        "Use a stable shot hierarchy across the song: intro/outro favor character master or environment setup, verses favor performance-wide, pre-chorus favors emotion-close, chorus favors performance hero framing, post-chorus favors detail or reflection, bridge favors emotion-close or reflective transition. "
        "Treat profile_summary and visual_direction as the stable lane for future profiles: translate longer tag sets into one coherent heroine, world, and camera grammar. "
        "Each shot item must include: shot_id,shot_type,is_chorus,camera_language,pose_delta,emotion,scene_detail,motion_hint. "
        "Shot items must not redefine identity; they only specify framing, pose, emotion, environmental emphasis, and motion intent. "
        "Negative constraints and world rules override any section staging idea. "
        "camera_language should be a short cinematic phrase for framing/lens behavior only. "
        "camera_language must describe face framing, body framing, or lens feel, not prop framing; avoid phrases like close-up on bag, mirror, prop, or accessory. "
        "camera_language must stay smooth and readable; avoid explosive, frantic, handheld, whip, crash zoom, or fast-pan language unless the brief explicitly allows it. "
        "pose_delta should describe exactly one readable body or gaze change. "
        "emotion should be concise and performance-oriented, not narrative. "
        "scene_detail should name exactly one concrete set or prop emphasis and should preserve the same master palette with only section accent shifts. "
        "scene_detail should default to environment or lighting detail; use prop detail only when the shot_type truly calls for a brief insert. "
        "For CHAR_MASTER, PERF_WIDE, and EMOTION_CLOSE, keep scene_detail focused on environment, lighting, or silhouette rather than handheld objects. "
        "Except for brief detail inserts, do not let props, bags, or accessories become larger or more important than the hero face and performance. "
        "motion_hint should prefer smooth readable motion, not frantic action or multiple simultaneous events. "
        "If the brief discourages fast camera or drift, use stillness, glide, slow dolly, gentle turn, or subtle gaze change instead of running or aggressive movement. "
        "Favor prompts that are directly usable by diffusion models: concrete, visual, and physically readable instead of poetic or abstract. "
        "Avoid empty prestige phrases like cinematic vibes, dramatic aura, stylish composition, or emotional energy without a concrete visible setup. "
        "Shot count must match section count exactly. "
    )


def _planner_inputs(context: dict[str, str]) -> str:
    return (
        f"Use shot_type only from enum: {context['types']}. "
        f"Audio tags={context['tags']}; Audio direction={context['desc']}; "
        f"Style guidance={context['guidance']}; Profile steering={context['profile']}; "
        f"Visual direction={context['visual_direction']}; Avoid={context['negative_direction']}; Visual brief={context['brief_view']}; "
        f"Lyrics excerpt={context['lyrics']}; Section labels in order={context['section_labels']}; Timing reference={context['section_view']}."
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
        item["section_label"] = str(sec.get("label", sec.get("name", "section")))
        item["shot_type"] = _shot_type_for_section(item["section_name"])
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


def _section_labels(sections: list[dict]) -> str:
    out = [str(row.get("label", row.get("name", "section"))).strip() for row in sections]
    vals = [x for x in out if x]
    if not vals:
        raise RuntimeError("sections missing for TTI prompt planner")
    return ", ".join(vals)


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


def _shot_type_for_section(name: str) -> str:
    sec = str(name).strip().lower()
    if sec == "intro":
        return "CHAR_MASTER"
    if sec.startswith("verse"):
        return "PERF_WIDE"
    if sec == "pre_chorus":
        return "EMOTION_CLOSE"
    if sec == "chorus":
        return "PERF_WIDE"
    if sec == "post_chorus":
        return "DETAIL_INSERT"
    if sec == "bridge":
        return "EMOTION_CLOSE"
    if sec == "outro":
        return "ENV_TRANSITION"
    return "PERF_WIDE"
