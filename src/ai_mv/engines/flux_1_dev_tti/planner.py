from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_tti_master, normalize_tti_shot
from ai_mv.core.contracts.prompt_schema import SHOT_TYPES, tti_schema
from ai_mv.core.prompt_digests import label_digest, section_digest
from ai_mv.core.visual_pipeline import attach_tti_metadata, location_grammar_digest, section_semantics_digest, shot_type_guidance_digest
from ai_mv.infra.codex_cli_client import generate_structured
from ai_mv.engines.visual_bridge.brief_views import section_dramaturgy, world_bible


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
    intent = audio_map.get("profile_intent", {})
    audio_intent = intent.get("audio_intent", {}) if isinstance(intent, dict) else {}
    world_intent = intent.get("world_intent", {}) if isinstance(intent, dict) else {}
    return {
        "audio_intent": str(audio_intent.get("brief", "") or audio_map.get("genre_description", "") or audio_map.get("audio_direction", "")).strip(),
        "hook_intent": str(audio_intent.get("hook_brief", "")).strip(),
        "world_intent": str(world_intent.get("visual_brief", "") or audio_map.get("visual_direction", "")).strip(),
        "story_world": str(world_intent.get("story_world", "") or audio_map.get("profile_summary", "")).strip(),
        "brief_view": _brief_summary(brief),
        "section_view": section_digest(sections),
        "section_labels": label_digest(sections),
        "section_semantics": section_semantics_digest(audio_map),
        "escalation": _escalation_reference(sections),
        "shot_type_guidance": shot_type_guidance_digest(config),
        "location_grammar": location_grammar_digest(config),
        "types": ", ".join(SHOT_TYPES),
    }


def _planner_rules() -> str:
    return (
        "You are a shot planner building the deterministic visual contract for downstream renderers. "
        "Return strict JSON only with shape {\"master_anchor\":{...},\"shots\":[...]}. No prose outside JSON. "
        "Design one definitive character master anchor image, then design one shot blueprint per section. "
        "master_anchor must include: prompt_text,seed. "
        "master_anchor prompt_text must be a compact diffusion prompt string composed of stable identity and world facts only. "
        "Use the visual brief as the source of truth for identity locks, world rules, recurring locations, and forbidden drift. "
        "Each shot must preserve the same lead identity and world while changing only section-specific framing and motion intent. "
        "Honor each section's story_beat, location_anchor, escalation_level, and motion_axis. "
        "Repeated sections must escalate within the same world instead of creating a new concept. "
        "Each shot item must include: shot_id,shot_type,is_chorus,camera_language,pose_delta,emotion,scene_detail,motion_hint,space_relation. "
        "camera_language, pose_delta, scene_detail, motion_hint, and space_relation must be short structural decisions, not prose. "
        "space_relation must stay physically reusable by downstream render stages. "
        "Shot count must match section count exactly. "
        "Use section semantics to decide whether a shot should establish, cover, lift, pay off, interrupt, or leave residue. "
    )


def _planner_inputs(context: dict[str, str]) -> str:
    return (
        f"Use shot_type only from enum: {context['types']}. "
        f"Audio intent={context['audio_intent']}; Hook intent={context['hook_intent']}; "
        f"World intent={context['world_intent']}; Visual direction={context['world_intent']}; Story world={context['story_world']}; "
        f"Visual brief={context['brief_view']}; Shot grammar={context['shot_type_guidance']}; "
        f"Location grammar={context['location_grammar']}; "
        f"Section labels in order={context['section_labels']}; Section semantics={context['section_semantics']}; "
        f"Escalation guide={context['escalation']}; Timing reference={context['section_view']}."
    )


def _normalize_shots(shots: list[dict], sections: list[dict]) -> list[dict]:
    parsed = [normalize_tti_shot(row, idx) for idx, row in enumerate(shots) if isinstance(row, dict)]
    if not parsed:
        raise RuntimeError("no valid shots from TTI planner")
    if not sections:
        raise RuntimeError("sections missing for TTI planner")
    _validate_tti_shot_count(parsed, sections)
    return _assign_one_shot_per_section(parsed, sections)


def _validate_tti_shot_count(shots: list[dict], sections: list[dict]) -> None:
    if len(shots) != len(sections):
        raise RuntimeError(f"TTI planner shot count mismatch: expected={len(sections)} actual={len(shots)}")


def _assign_one_shot_per_section(shots: list[dict], sections: list[dict]) -> list[dict]:
    out: list[dict] = []
    for idx, (row, sec) in enumerate(zip(shots, sections), start=1):
        item = dict(row)
        item["shot_id"] = f"S{idx:03d}"
        item["section_name"] = str(sec.get("name", "section"))
        item["section_label"] = str(sec.get("label", sec.get("name", "section")))
        item["shot_type"] = str(item.get("shot_type", "PERF_WIDE")).strip().upper() or "PERF_WIDE"
        item["is_chorus"] = _is_chorus(item["section_name"])
        item["duration_sec"] = round(max(0.001, _sec_end(sec) - _sec_start(sec)), 3)
        out.append(attach_tti_metadata(item, item["section_name"], item["section_label"]))
    return out


def _is_chorus(name: str) -> bool:
    sec = str(name).strip().lower()
    return sec == "chorus" or sec.startswith("chorus_")


def _sec_start(row: dict) -> float:
    return float(row.get("start_sec", row.get("start", 0.0)))


def _sec_end(row: dict) -> float:
    return float(row.get("end_sec", row.get("end", 0.0)))

def _escalation_reference(sections: list[dict]) -> str:
    labels = {str(row.get("label", row.get("name", "section"))).strip().lower() for row in sections}
    parts: list[str] = []
    if "chorus" in labels:
        parts.append("Chorus=arrival, graceful release, first clear opening")
    if "chorus 2" in labels:
        parts.append("Chorus 2=firmer return, brighter openness, wider confidence")
    if "final chorus" in labels:
        parts.append("Final Chorus=peak return, luminous resolve, clearest environmental payoff")
    if not parts:
        parts.append("Repeated returns should rise in openness, confidence, and visual clarity")
    return "; ".join(parts)


def _brief_summary(brief: dict) -> str:
    world = world_bible(brief)
    return (
        f"hero={world['hero_identity']}; world={world['world_rules']}; "
        f"sections={_section_briefs(brief)}"
    )


def _section_briefs(brief: dict) -> str:
    rows = []
    for row in section_dramaturgy(brief):
        rows.append(
            f"{row['section_name']}|{row['story_beat']}|{row['location_anchor']}"
        )
    return ", ".join(rows)


