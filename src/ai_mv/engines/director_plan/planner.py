from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_direction_plan
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.prompt_grammar import golden_structure_guidance, ref_archetype_grammar, ref_archetype_variant


def build_direction_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    outline = payload["scene_outline"]
    shot_packages: list[dict] = []
    for shot in outline.get("shot_packages", []):
        current = dict(shot)
        story_function = str(current.get("story_function", "")).strip()
        shot_function = _shot_function(story_function, str(current.get("world_zone", "")).strip())
        archetype = _ref_archetype_for_shot(current)
        variant = _ref_archetype_variant_for_shot(current, archetype)
        guidance = golden_structure_guidance(story_function, archetype, variant)
        story_visual_intent = str(current.get("story_visual_intent", "")).strip()
        primary_surface = _primary_surface(story_function, archetype, variant, guidance)
        dominant_action = _dominant_action(story_function, archetype, variant, primary_surface, guidance, story_visual_intent)
        continuity_delta = _continuity_delta(story_function, archetype, variant, primary_surface, guidance, story_visual_intent)
        content_trace = _content_trace(story_function, archetype, variant, guidance)
        identity_hook_policy = _identity_hook_policy(archetype, variant)
        current.update(
            {
                "shot_function": shot_function,
                "ref_archetype": archetype,
                "archetype_variant": variant,
                "story_visual_intent": story_visual_intent,
                "primary_surface": primary_surface,
                "dominant_action": dominant_action,
                "continuity_delta": continuity_delta,
                "content_trace": content_trace,
                "identity_hook_policy": identity_hook_policy,
                "selected_prompt_shape": str(ref_archetype_grammar(archetype).get("preferred_sentence_shape", "")).strip(),
                "applied_grammar_source": _applied_grammar_source(story_function, archetype, variant, guidance),
                "why": _director_why(current, archetype, variant, primary_surface, story_visual_intent),
            }
        )
        shot_packages.append(current)
    return normalize_direction_plan(
        {
            "brief_name": brief["brief_name"],
            "story_premise": brief["story_premise"],
            "world_rules": brief["world_rules"],
            "shot_packages": shot_packages,
        }
    )


def build_director_plan(config: dict, payload: dict) -> dict:
    return build_direction_plan(config, payload)


def build_direction_plan_preview_prompt(config: dict, payload: dict) -> str:
    brief = build_director_brief_intent(config)
    return (
        "Translate the story-only scene outline into direction decisions. "
        f"Heroine arc={brief['heroine_arc']}. "
        "For each shot, decide shot function, REF archetype, variant, primary surface, dominant action, continuity delta, "
        "content trace, identity-hook policy, and why. Do not verbalize final prompts here."
    )


def build_director_plan_preview_prompt(config: dict, payload: dict) -> str:
    return build_direction_plan_preview_prompt(config, payload)


def _shot_function(story_function: str, world_zone: str) -> str:
    if story_function == "entry":
        return "entry_crossing"
    if story_function == "pressure":
        return "compressed_forward_motion"
    if story_function == "payoff":
        return "decisive_release_crossing"
    if world_zone in {"threshold", "edge"}:
        return "threshold_progression"
    return "forward_continuation"


def _ref_archetype_for_shot(shot: dict) -> str:
    section = str(shot.get("section_label", "")).strip().lower()
    story_function = str(shot.get("story_function", "")).strip()
    world_zone = str(shot.get("world_zone", "")).strip()
    if story_function == "pressure":
        return "platform_edge" if world_zone == "compression" or "bridge" in section else "passage_compression"
    if story_function == "payoff":
        if world_zone == "open_peak" or "final chorus" in section:
            return "curb_crossing"
        return "threshold_crossing"
    if story_function == "entry":
        if "intro" in section or world_zone == "threshold":
            return "gate_pass"
        if world_zone == "edge":
            return "threshold_crossing"
        if world_zone == "compression":
            return "platform_edge"
        if world_zone in {"open_route", "open_peak"}:
            return "curb_crossing"
        if world_zone in {"narrow_route", "transit_route"}:
            return "sidewalk_continuation"
    if story_function == "handoff":
        if world_zone in {"threshold", "edge"}:
            return "threshold_crossing"
        if world_zone == "compression":
            return "platform_edge"
        if world_zone == "open_peak":
            return "curb_crossing"
        if world_zone == "open_route":
            return "curb_crossing"
        return "sidewalk_continuation"
    if story_function == "continuation":
        if world_zone == "compression":
            return "passage_compression"
        if world_zone in {"open_route", "open_peak"}:
            return "curb_crossing"
        return "sidewalk_continuation"
    if world_zone == "compression":
        return "platform_edge"
    if world_zone in {"open_route", "open_peak"}:
        return "curb_crossing"
    if world_zone == "edge":
        return "threshold_crossing"
    return "sidewalk_continuation"


def _ref_archetype_variant_for_shot(shot: dict, archetype: str) -> str:
    section = str(shot.get("section_label", "")).strip().lower()
    story_function = str(shot.get("story_function", "")).strip()
    world_zone = str(shot.get("world_zone", "")).strip()
    if archetype == "threshold_crossing" and story_function == "handoff" and world_zone in {"threshold", "edge"}:
        return "passage_exit"
    if archetype == "platform_edge" and (
        story_function == "pressure"
        or "bridge" in section
        or world_zone == "compression"
    ):
        return "bridge_motion"
    return ""


def _primary_surface(story_function: str, archetype: str, variant: str, guidance: dict) -> str:
    preferred = str(guidance.get("preferred_surface", "")).strip()
    if preferred:
        return preferred
    grammar = ref_archetype_grammar(archetype)
    priorities = [str(x).strip() for x in grammar.get("surface_priority", []) if str(x).strip()]
    if variant:
        note = ref_archetype_variant(archetype, variant)
        if str(note.get("preferred_surface", "")).strip():
            return str(note.get("preferred_surface", "")).strip()
    story_surface = _story_surface_override(story_function, archetype, variant)
    if story_surface:
        return story_surface
    return priorities[0] if priorities else "walkable path"


def _dominant_action(
    story_function: str, archetype: str, variant: str, primary_surface: str, guidance: dict, story_visual_intent: str
) -> str:
    shaped = str(guidance.get("start_shape", "")).strip()
    if shaped:
        return shaped
    surface = primary_surface
    templates = {
        "gate_pass": {
            "entry": f"She enters the {surface} with one readable forward step.",
            "handoff": f"She moves beyond the {surface} and keeps her line into the station path.",
        },
        "threshold_crossing": {
            "entry": f"She sets her line across the {surface} toward the next surface.",
            "handoff": f"She clears the {surface} and carries the next step into the following route.",
        },
        "doorway_handoff": {
            "entry": f"She reaches the {surface} and commits to the space beyond.",
            "handoff": f"She clears the {surface} and carries the next step into the immediate passage.",
        },
        "curb_crossing": {
            "entry": f"She steps in from one side of the {surface} with the road opening ahead of her.",
            "continuation": f"She keeps the same crossing stride alive through the middle-right side of the {surface}.",
            "handoff": f"She carries the same stride along the right edge of the {surface} with the open road held to the opposite side.",
            "payoff": f"She moves away through the {surface} with the far side opening wider around her.",
        },
        "sidewalk_continuation": {
            "entry": f"She takes the first committed stride along the {surface} and lets the route define her line.",
            "continuation": f"She carries the same stride along the {surface} with the road staying beside her.",
            "handoff": f"She lands the next stride along the {surface} with the road still held beside her.",
        },
        "stair_descent": {
            "entry": f"She steps down the {surface} with one continuous handrail contact.",
            "continuation": f"She keeps descending the {surface} with the handrail still guiding her line.",
            "handoff": f"She lands the next step on the {surface} and keeps descending.",
        },
        "passage_compression": {
            "entry": f"She keeps close to the {surface} and starts moving one beat farther through it.",
            "continuation": f"She keeps close to the {surface} and moves one beat farther through it.",
            "handoff": f"She compresses one more step through the {surface} and carries it forward.",
        },
        "window_contact": {
            "entry": f"She keeps close to the {surface} with one direct contact detail and keeps moving.",
            "handoff": f"She lets the contact slide off the {surface} and carries the next step past it.",
        },
        "platform_edge": {
            "entry": _platform_edge_start(variant, surface),
            "pressure": _platform_edge_start(variant, surface),
            "continuation": f"She keeps the same line along the {surface} with the edge geometry still close at her feet.",
            "handoff": f"She sets the next committed step along the {surface} with the edge geometry close at her feet.",
        },
    }
    archetype_templates = templates.get(archetype, {})
    if isinstance(archetype_templates, dict):
        if story_function in archetype_templates:
            return archetype_templates[story_function]
        if "entry" in archetype_templates:
            return archetype_templates["entry"]
    default = f"She keeps moving along the {surface}."
    if archetype == "platform_edge":
        default = _platform_edge_start(variant, surface)
    elif archetype == "sidewalk_continuation":
        default = f"She keeps moving along the {surface} with a readable forward stride."
    elif archetype == "curb_crossing":
        default = f"She steps onto the {surface} with her line set toward the far curb."
    return default


def _continuity_delta(
    story_function: str, archetype: str, variant: str, primary_surface: str, guidance: dict, story_visual_intent: str
) -> str:
    shaped = str(guidance.get("end_shape", "")).strip()
    if shaped:
        return shaped
    surface = primary_surface
    templates = {
        "gate_pass": {
            "entry": f"She passes through the {surface} and lands just inside the station.",
            "handoff": f"She moves beyond the {surface} and lands on the next pavement.",
        },
        "threshold_crossing": {
            "entry": f"She clears the {surface} and lands beyond it on the next surface.",
            "handoff": f"She lands beyond the {surface} and carries the route forward.",
        },
        "doorway_handoff": {
            "entry": f"She carries the next step beyond the {surface} into the immediate passage.",
            "handoff": f"She leaves the {surface} behind and keeps the next step inside the passage.",
        },
        "curb_crossing": {
            "entry": f"She carries the crossing one beat farther from the entry side of the {surface}.",
            "continuation": f"She crosses one beat farther through the middle-right side of the {surface} and keeps the crossing live.",
            "handoff": f"She keeps to the right edge of the {surface} and leaves the open road clearly opposite her.",
            "payoff": f"She leaves the {surface} behind as more of the open street surrounds her in full release.",
        },
        "sidewalk_continuation": {
            "entry": f"She carries the route one readable stride farther along the {surface} and makes the path feel established.",
            "continuation": f"She keeps the same stride on the {surface} and moves one step farther with the road still beside her.",
            "handoff": f"She lands the next stride on the {surface} and leaves the road clearly beside her.",
        },
        "stair_descent": {
            "entry": f"She lands one step lower on the {surface} and keeps descending.",
            "continuation": f"She keeps descending the {surface} and drops one more step lower.",
            "handoff": f"She takes one more step down the {surface} and carries the descent forward.",
        },
        "passage_compression": {
            "entry": f"She keeps close to the route and compresses one more step forward.",
            "continuation": f"She keeps close to the route and moves one compressed step farther.",
            "handoff": f"She clears the tightest part of the route and carries the compression forward.",
        },
        "window_contact": {
            "entry": f"She changes the contact slightly and keeps moving past the edge.",
            "handoff": f"She lets the contact fall behind and keeps moving past the edge.",
        },
        "platform_edge": {
            "entry": _platform_edge_end(variant, surface),
            "pressure": _platform_edge_end(variant, surface),
            "continuation": f"She takes one more step along the {surface} and keeps the edge line tight at her feet.",
            "handoff": f"She lands the next step along the {surface} and leaves the forward route already committed.",
        },
    }
    archetype_templates = templates.get(archetype, {})
    if isinstance(archetype_templates, dict):
        if story_function in archetype_templates:
            return archetype_templates[story_function]
        if "entry" in archetype_templates:
            return archetype_templates["entry"]
    return f"She carries the same movement one readable step farther on the {surface}."


def _content_trace(story_function: str, archetype: str, variant: str, guidance: dict) -> str:
    if str(guidance.get("preferred_pattern", "")).strip():
        pattern = str(guidance["preferred_pattern"]).lower()
        if "footprint" in pattern:
            return "footprint trail widening behind her"
        if "arm swinging free" in pattern or "free-arm" in pattern:
            return "one arm swinging free"
    if archetype == "platform_edge" and variant == "bridge_motion" and story_function == "pressure":
        return "footprint trail widening behind her"
    if archetype == "curb_crossing" and story_function == "payoff":
        return "more of the open street surrounding her"
    if archetype == "curb_crossing" and story_function == "handoff":
        return "the open road holding to her left"
    if archetype == "sidewalk_continuation" and story_function in {"continuation", "handoff"}:
        return "the road still held beside her"
    if archetype == "stair_descent":
        return "one hand sliding along the handrail"
    if archetype == "passage_compression":
        return "one hand trailing the rail"
    return ""


def _identity_hook_policy(archetype: str, variant: str) -> str:
    if archetype in {"threshold_crossing", "doorway_handoff", "window_contact"}:
        return "optional_small_hook"
    if archetype == "platform_edge" and variant == "bridge_motion":
        return "optional_small_hook"
    return "none"


def _applied_grammar_source(story_function: str, archetype: str, variant: str, guidance: dict) -> str:
    if guidance:
        return f"golden_structures:{story_function}:{archetype}:{variant or 'base'}"
    return f"ref_archetypes:{archetype}:{variant or 'base'}"


def _director_why(shot: dict, archetype: str, variant: str, primary_surface: str, story_visual_intent: str) -> str:
    return (
        f"{shot.get('story_function', '')} beat uses {archetype}"
        f"{f'/{variant}' if variant else ''} on {primary_surface} to serve {shot.get('story_goal', '')}"
        f" Visual intent: {story_visual_intent}"
    ).strip()


def _platform_edge_start(variant: str, surface: str) -> str:
    if variant == "bridge_motion":
        return f"She sets a shorter step along the {surface} with the yellow tactile line close at her feet."
    return f"She sets the next step along the {surface} with the edge geometry close at her feet."


def _platform_edge_end(variant: str, surface: str) -> str:
    if variant == "bridge_motion":
        return f"She takes a crossing step along the {surface} with the yellow tactile line close at her feet and her footprint trail widening behind her."
    return f"She takes the next step along the {surface} and keeps driving forward."


def _infer_ref_archetype(shot: dict, guidance: dict | None = None) -> str:
    guidance = dict(guidance or {})
    if str(guidance.get("ref_archetype", guidance.get("archetype", ""))).strip():
        return str(guidance.get("ref_archetype", guidance.get("archetype", ""))).strip()
    return _ref_archetype_for_shot(shot)


def _infer_ref_archetype_variant(shot: dict, archetype: str, guidance: dict | None = None) -> str:
    guidance = dict(guidance or {})
    if str(guidance.get("variant", "")).strip():
        return str(guidance.get("variant", "")).strip()
    return _ref_archetype_variant_for_shot(shot, archetype)


def _planner_primary_surface(shot: dict, archetype: str) -> str:
    guidance = golden_structure_guidance(
        str(shot.get("story_function", "")).strip(),
        archetype,
        str(shot.get("archetype_variant", shot.get("ref_archetype_variant", ""))).strip(),
    )
    return _primary_surface(str(shot.get("story_function", "")).strip(), archetype, str(shot.get("archetype_variant", "")).strip(), guidance)


def _story_surface_override(story_function: str, archetype: str, variant: str) -> str:
    overrides = {
        ("sidewalk_continuation", "entry"): "station-side sidewalk",
        ("sidewalk_continuation", "continuation"): "wet sidewalk",
        ("sidewalk_continuation", "handoff"): "curb line",
        ("curb_crossing", "entry"): "wet crosswalk",
        ("curb_crossing", "continuation"): "wet crosswalk",
        ("curb_crossing", "handoff"): "wet crosswalk near the far curb",
        ("curb_crossing", "payoff"): "wet crosswalk",
        ("platform_edge", "handoff"): "wet platform edge",
        ("platform_edge", "continuation"): "wet platform edge",
        ("threshold_crossing", "entry"): "gate threshold",
        ("threshold_crossing", "handoff"): "station threshold",
        ("gate_pass", "entry"): "turnstile lane",
    }
    return overrides.get((archetype, story_function), "")
