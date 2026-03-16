from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_visual_brief
from ai_mv.core.contracts.prompt_schema import visual_brief_schema
from ai_mv.core.prompt_digests import label_digest
from ai_mv.core.visual_pipeline import location_grammar_digest
from ai_mv.infra.codex_cli_client import generate_structured


def build_visual_brief(config: dict, payload: dict) -> dict:
    audio_map = payload["audio_map"]
    sections = list(audio_map["sections"])
    raw = generate_structured(config, _planner_prompt(config, audio_map, sections), visual_brief_schema())
    return normalize_visual_brief(raw, sections)


def _planner_prompt(config: dict, audio_map: dict, sections: list[dict]) -> str:
    intent = audio_map.get("profile_intent", {})
    audio_intent = intent.get("audio_intent", {}) if isinstance(intent, dict) else {}
    world_intent = intent.get("world_intent", {}) if isinstance(intent, dict) else {}
    negative_intent = intent.get("negative_intent", {}) if isinstance(intent, dict) else {}
    names = _section_names(sections)
    labels = label_digest(sections)
    semantics = _section_semantics(audio_map)
    location_grammar = location_grammar_digest(config)
    return (
        "You are a music-video world planner building the single source of truth for the visual pipeline. "
        "Return strict JSON only. No prose outside JSON. "
        "Required fields: hero_identity,world_rules,recurring_location_families,allowed_visual_variation,negative_constraints,section_briefs. "
        "section_briefs item fields: section_name,emotional_arc,palette_hint,lighting_hint,staging_hint,story_beat,location_anchor,escalation_level,motion_axis. "
        "This brief must be strong enough that downstream render stages do not need to reinvent story or continuity. "
        "hero_identity must contain only stable identity locks. "
        "world_rules must define one coherent world and baseline look. "
        "recurring_location_families must be reusable environment families, not one-off sets. "
        "allowed_visual_variation must describe what may change while preserving identity and world continuity. "
        "negative_constraints must be short forbidden drift items. "
        "Each section_brief must preserve identity and world while advancing a visible story beat. "
        "story_beat must be a visible present-tense action the camera can read. "
        "location_anchor must stay inside the recurring world families. "
        "escalation_level must express whether the section is steady, lift, payoff, interrupt, or residue. "
        "motion_axis must describe the main change axis, such as travel line, pose shift, gaze shift, or stillness hold. "
        "Chorus 2 and Final Chorus must escalate without becoming a new world. "
        "Bridge must interrupt the flow. Outro must leave residue. "
        "section_briefs must match Section names exactly in count and order. "
        "section_name must be a bare section token only. "
        f"Audio intent={audio_intent.get('brief', '')}; Hook intent={audio_intent.get('hook_brief', '')}; "
        f"World intent={world_intent.get('visual_brief', '')}; Story world={world_intent.get('story_world', '')}; "
        f"Action vocabulary={world_intent.get('action_vocabulary', '')}; Payoff intent={world_intent.get('payoff_style', '')}; "
        f"Negative intent={negative_intent.get('visual_negative', '')}; Avoid={negative_intent.get('mv_avoid', '')}; "
        f"Section semantics={semantics}; Location grammar={location_grammar}; "
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
