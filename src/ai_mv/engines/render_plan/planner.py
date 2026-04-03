from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_prompt_plan
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.prompt_grammar import golden_structure_guidance, ref_archetype_grammar, wan_transition_family
from ai_mv.core.stages.render_verbalizer import verbalize_ref_prompt_pairs, verbalize_wan_prompts


def build_prompt_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    direction_plan = payload["direction_plan"]
    ref_items: list[dict] = []
    wan_items: list[dict] = []
    for shot in direction_plan.get("shot_packages", []):
        story_function = str(shot.get("story_function", "")).strip()
        archetype = str(shot.get("ref_archetype", "")).strip()
        variant = str(shot.get("archetype_variant", "")).strip()
        guidance = golden_structure_guidance(story_function, archetype, variant)
        ref_atoms = _ref_prompt_atoms(brief, shot, guidance)
        ref_items.append(
            {
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": str(shot.get("section_label", "")).strip(),
                "line_refs": list(shot.get("line_refs", [])),
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
                "story_function": story_function,
                "story_goal": str(shot.get("story_goal", "")).strip(),
                "world_zone": str(shot.get("world_zone", "")).strip(),
                "shot_function": str(shot.get("shot_function", "")).strip(),
                "ref_archetype": archetype,
                "archetype_variant": variant,
                "primary_surface": str(shot.get("primary_surface", "")).strip(),
                "dominant_action": str(shot.get("dominant_action", "")).strip(),
                "continuity_delta": str(shot.get("continuity_delta", "")).strip(),
                "content_trace": str(shot.get("content_trace", "")).strip(),
                "selected_prompt_shape": str(ref_archetype_grammar(archetype).get("preferred_sentence_shape", "")).strip(),
                "applied_grammar_source": str(shot.get("applied_grammar_source", "")).strip(),
                "identity_hook_policy": str(shot.get("identity_hook_policy", "")).strip(),
                "why": str(shot.get("why", "")).strip(),
                "ref_prompt_atoms": ref_atoms,
                "ref_prompt_contract": _ref_prompt_contract(archetype, variant, guidance),
                "ref_start_prompt_text": "",
                "ref_end_prompt_text": "",
            }
        )
    _verbalize_ref_items(config, ref_items)
    for index, current in enumerate(ref_items[1:], start=2):
        previous = ref_items[index - 2]
        transition_family = _infer_wan_transition_family(current)
        transition = wan_transition_family(transition_family)
        guidance = golden_structure_guidance(
            str(current.get("story_function", "")).strip(),
            str(current.get("ref_archetype", "")).strip(),
            str(current.get("archetype_variant", "")).strip(),
        )
        wan_atoms = _wan_prompt_atoms(brief, current, guidance)
        wan_items.append(
            {
                "shot_id": str(current.get("shot_id", "")).strip(),
                "section_name": str(current.get("section_name", "")).strip(),
                "section_label": str(current.get("section_label", "")).strip(),
                "start_ref_shot_id": str(previous.get("shot_id", "")).strip(),
                "end_ref_shot_id": str(current.get("shot_id", "")).strip(),
                "duration_sec": float(current.get("duration_sec", 2.0) or 2.0),
                "story_function": str(current.get("story_function", "")).strip(),
                "wan_transition_family": transition_family,
                "wan_prompt_contract": str(transition.get("contract", "")).strip(),
                "applied_grammar_source": str(current.get("applied_grammar_source", "")).strip(),
                "why": f"Adjacent bridge from {previous.get('shot_id', '')} to {current.get('shot_id', '')} for {current.get('story_function', '')}.",
                "wan_prompt_atoms": wan_atoms,
                "wan_positive_prompt_text": "",
            }
        )
    _verbalize_wan_items(config, wan_items)
    return normalize_prompt_plan(
        {
            "master_anchor": {
                "render_strategy": "tti_master",
                "identity_core": brief["identity_core"],
                "style_contract": brief["style_contract"],
                "environment_anchor": "simple pale backdrop for anchor extraction",
            },
            "ref_items": ref_items,
            "wan_items": wan_items,
        }
    )


def build_render_plan(config: dict, payload: dict) -> dict:
    return build_prompt_plan(config, payload)


def build_prompt_plan_preview_prompt(config: dict, payload: dict) -> str:
    return (
        "Compile direction decisions into prompt atoms and engine-ready prompt contracts. "
        "Use grammar memory to choose the sentence shape, then verbalize without adding new meaning. "
        "REF items should stay independent and WAN items should bridge adjacent REF keyframes only."
    )


def build_render_plan_preview_prompt(config: dict, payload: dict) -> str:
    return build_prompt_plan_preview_prompt(config, payload)


def _ref_prompt_atoms(brief: dict, shot: dict, guidance: dict) -> dict:
    identity_hook = _identity_hook(brief, str(shot.get("identity_hook_policy", "")).strip())
    start_shape = str(guidance.get("start_shape", "")).strip() or str(shot.get("dominant_action", "")).strip()
    end_shape = str(guidance.get("end_shape", "")).strip() or str(shot.get("continuity_delta", "")).strip()
    return {
        "subject_intro": _subject_intro(brief, identity_hook),
        "location": _location_clause(str(shot.get("primary_surface", "")).strip()),
        "primary_surface": str(shot.get("primary_surface", "")).strip(),
        "dominant_action": str(shot.get("dominant_action", "")).strip(),
        "continuity_delta": str(shot.get("continuity_delta", "")).strip(),
        "content_trace": str(shot.get("content_trace", "")).strip(),
        "start_state": start_shape,
        "end_state": end_shape,
        "lighting": "",
    }


def _wan_prompt_atoms(brief: dict, shot: dict, guidance: dict) -> dict:
    identity_hook = _identity_hook(brief, str(shot.get("identity_hook_policy", "")).strip())
    bridge_shape = str(guidance.get("wan_shape", "")).strip() or str(shot.get("continuity_delta", "")).strip()
    return {
        "subject_intro": _subject_intro(brief, identity_hook),
        "location": _location_clause(str(shot.get("primary_surface", "")).strip()),
        "primary_surface": str(shot.get("primary_surface", "")).strip(),
        "bridge_action": bridge_shape,
        "lighting": "",
    }


def _verbalize_ref_items(config: dict, ref_items: list[dict]) -> None:
    rows = []
    for row in ref_items:
        atoms = dict(row.get("ref_prompt_atoms", {}))
        rows.append(
            {
                "shot_id": row["shot_id"],
                "subject_intro": atoms.get("subject_intro", ""),
                "location": atoms.get("location", ""),
                "ref_archetype": row.get("ref_archetype", ""),
                "ref_archetype_variant": row.get("archetype_variant", ""),
                "ref_archetype_contract": row.get("ref_prompt_contract", ""),
                "ref_preferred_sentence_shape": row.get("selected_prompt_shape", ""),
                "golden_shot_guidance": {},
                "dominant_scene_grammar": row.get("story_function", ""),
                "primary_surface": atoms.get("primary_surface", ""),
                "support_detail": atoms.get("content_trace", ""),
                "dominant_action": atoms.get("dominant_action", ""),
                "continuity_delta": atoms.get("continuity_delta", ""),
                "start_state": atoms.get("start_state", ""),
                "end_state": atoms.get("end_state", ""),
                "lighting": atoms.get("lighting", ""),
            }
        )
    prompts = verbalize_ref_prompt_pairs(config, rows)
    for row in ref_items:
        prompt = prompts.get(row["shot_id"], {})
        row["ref_start_prompt_text"] = str(prompt.get("start_prompt_text", "")).strip()
        row["ref_end_prompt_text"] = str(prompt.get("end_prompt_text", "")).strip()


def _verbalize_wan_items(config: dict, wan_items: list[dict]) -> None:
    rows = []
    for row in wan_items:
        atoms = dict(row.get("wan_prompt_atoms", {}))
        rows.append(
            {
                "shot_id": row["shot_id"],
                "subject_intro": atoms.get("subject_intro", ""),
                "location": atoms.get("location", ""),
                "ref_archetype": "",
                "ref_archetype_variant": "",
                "ref_archetype_contract": "",
                "ref_preferred_sentence_shape": "",
                "golden_shot_guidance": {},
                "wan_transition_family": row.get("wan_transition_family", ""),
                "wan_transition_contract": row.get("wan_prompt_contract", ""),
                "dominant_scene_grammar": row.get("story_function", ""),
                "primary_surface": atoms.get("primary_surface", ""),
                "support_detail": "",
                "dominant_action": "",
                "continuity_delta": "",
                "bridge_action": atoms.get("bridge_action", ""),
                "lighting": atoms.get("lighting", ""),
            }
        )
    prompts = verbalize_wan_prompts(config, rows)
    for row in wan_items:
        row["wan_positive_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _subject_intro(brief: dict, identity_hook: str) -> str:
    base = str(brief.get("ref_subject_intro", "")).strip() or "The same Korean female idol"
    if identity_hook:
        return f"{base} {identity_hook}".strip()
    return base


def _identity_hook(brief: dict, policy: str) -> str:
    if policy != "optional_small_hook":
        return ""
    hooks = [str(x).strip() for x in brief.get("identity_hooks", []) if str(x).strip()]
    if not hooks:
        return ""
    return f"with {hooks[0]}"


def _location_clause(surface: str) -> str:
    cleaned = " ".join(surface.strip().split())
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if any(token in lowered for token in ("edge", "threshold", "line", "lane", "crosswalk", "curb", "sidewalk", "pavement", "platform")):
        return f"At the {cleaned}"
    if any(token in lowered for token in ("stairs", "stairwell", "ramp", "passage", "corridor")):
        return f"Along the {cleaned}"
    if any(token in lowered for token in ("window", "glass", "rail", "wall", "door")):
        return f"By the {cleaned}"
    return f"In the {cleaned}"


def _ref_prompt_contract(archetype: str, variant: str, guidance: dict) -> str:
    if str(guidance.get("prompt_contract", "")).strip():
        return str(guidance.get("prompt_contract", "")).strip()
    base = str(ref_archetype_grammar(archetype).get("prompt_contract", "")).strip()
    note = str(ref_archetype_grammar(archetype).get("variants", {}).get(variant, {}).get("note", "")).strip() if variant else ""
    return f"{base} Variant note: {note}".strip() if note else base


def _infer_wan_transition_family(shot: dict) -> str:
    archetype = str(shot.get("ref_archetype", "")).strip()
    story_function = str(shot.get("story_function", "")).strip()
    if archetype in {"threshold_crossing", "doorway_handoff", "gate_pass", "curb_crossing"}:
        return "threshold_bridge" if story_function != "payoff" else "release_crossing"
    if archetype in {"stair_descent", "ramp_descent"}:
        return "descent_bridge"
    if story_function == "pressure" or archetype in {"passage_compression", "brace_pause", "platform_edge"}:
        return "compression_bridge"
    if story_function == "payoff":
        return "release_crossing"
    return "plain_continuation"
