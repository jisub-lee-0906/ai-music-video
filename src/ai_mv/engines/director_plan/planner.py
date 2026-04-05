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
        story_event = str(current.get("story_event", "")).strip()
        shot_function = _shot_function(story_function, str(current.get("world_zone", "")).strip())
        archetype = _ref_archetype_for_shot(current)
        variant = _ref_archetype_variant_for_shot(current, archetype)
        guidance = golden_structure_guidance(story_function, archetype, variant)
        story_visual_intent = str(current.get("story_visual_intent", "")).strip()
        blocking = _blocking_contract(story_function, archetype, str(current.get("world_zone", "")).strip(), story_event)
        primary_surface = _primary_surface(story_function, archetype, variant, guidance, story_event)
        dominant_action = _dominant_action(story_function, archetype, variant, primary_surface, guidance, story_visual_intent, story_event)
        continuity_delta = _continuity_delta(story_function, archetype, variant, primary_surface, guidance, story_visual_intent, story_event)
        content_trace = _content_trace(story_function, archetype, variant, guidance, story_event)
        identity_hook_policy = _identity_hook_policy(archetype, variant)
        current.update(
            {
                "shot_function": shot_function,
                "ref_archetype": archetype,
                "archetype_variant": variant,
                "story_visual_intent": story_visual_intent,
                "blocking_role": blocking["blocking_role"],
                "entry_side": blocking["entry_side"],
                "travel_axis": blocking["travel_axis"],
                "frame_bias": blocking["frame_bias"],
                "arrival_side": blocking["arrival_side"],
                "camera_relation": blocking["camera_relation"],
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
    override = _event_driven_archetype_override(shot)
    if override:
        return override
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
    override = _event_driven_variant_override(shot, archetype)
    if override:
        return override
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


def _primary_surface(story_function: str, archetype: str, variant: str, guidance: dict, story_event: str = "") -> str:
    preferred = str(guidance.get("preferred_surface", "")).strip()
    if preferred:
        return preferred
    grammar = ref_archetype_grammar(archetype)
    priorities = [str(x).strip() for x in grammar.get("surface_priority", []) if str(x).strip()]
    if variant:
        note = ref_archetype_variant(archetype, variant)
        if str(note.get("preferred_surface", "")).strip():
            return str(note.get("preferred_surface", "")).strip()
    story_surface = _story_surface_override(story_function, archetype, variant, story_event)
    if story_surface:
        return story_surface
    return priorities[0] if priorities else "walkable path"


def _dominant_action(
    story_function: str, archetype: str, variant: str, primary_surface: str, guidance: dict, story_visual_intent: str, story_event: str
) -> str:
    surface = primary_surface
    event_tags = _event_tags(story_event)
    special = _event_driven_action(archetype, story_function, surface, event_tags)
    if special:
        return special
    shaped = str(guidance.get("start_shape", "")).strip()
    if shaped:
        return shaped
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
            "continuation": f"She keeps the same crossing stride alive through the middle-right side of the {surface} without falling back to center.",
            "handoff": f"She carries the same stride along the right edge of the {surface} with the open road held to her left.",
            "payoff": f"She walks away from the {surface} into the wider street at night.",
        },
        "sidewalk_continuation": {
            "entry": f"She steps in from the road-side edge of the {surface} with the route opening beside her.",
            "continuation": f"She carries the same stride along the {surface} with the road still riding to her right.",
            "handoff": f"She sets the next sidewalk-side stride on the {surface} with the road clearly to her right.",
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
        "bench_rest": {
            "entry": f"She sits at the end of the {surface} with one foot still planted as if she could rise again.",
            "pressure": f"She sits at the end of the {surface} for one compressed beat with one foot still planted as if she could rise again.",
            "handoff": f"She leans forward from the end of the {surface} and gathers the next step without fully settling.",
        },
        "brace_pause": {
            "entry": f"She pauses at the {surface} with one hand braced on the metal bar.",
            "pressure": f"She braces at the {surface} with one hand fixed on the metal bar while the next step waits.",
            "handoff": f"She lets the braced contact loosen at the {surface} and keeps the next step ready.",
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
    story_function: str, archetype: str, variant: str, primary_surface: str, guidance: dict, story_visual_intent: str, story_event: str
) -> str:
    surface = primary_surface
    event_tags = _event_tags(story_event)
    special = _event_driven_continuity(archetype, story_function, surface, event_tags)
    if special:
        return special
    shaped = str(guidance.get("end_shape", "")).strip()
    if shaped:
        return shaped
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
            "handoff": f"She keeps to the right edge of the {surface} and leaves the next crossing state already formed with the open road held to her left.",
            "payoff": f"She leaves the {surface} behind and keeps walking away as the wider street opens around her.",
        },
        "sidewalk_continuation": {
            "entry": f"She carries the route one readable stride farther from the road-side edge of the {surface} and leaves the road clearly beside her.",
            "continuation": f"She keeps the same stride on the {surface} and moves one step farther with the road still riding to her right.",
            "handoff": f"She lands the next sidewalk-side stride on the {surface} and keeps the road clearly to her right.",
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
        "bench_rest": {
            "entry": f"She stays at the end of the {surface} with one foot planted and the route still waiting in front of her.",
            "pressure": f"She holds the compressed seat at the end of the {surface} for one beat, still planted to rise again.",
            "handoff": f"She tips forward from the end of the {surface} and leaves the rise already forming before the cut.",
        },
        "brace_pause": {
            "entry": f"She keeps one hand braced on the {surface} and leaves the pause able to break at once.",
            "pressure": f"She holds one beat at the {surface} with the braced contact still carrying pressure forward.",
            "handoff": f"She loosens the braced contact at the {surface} and leaves the next step ready to resume.",
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


def _content_trace(story_function: str, archetype: str, variant: str, guidance: dict, story_event: str = "") -> str:
    event_tags = _event_tags(story_event)
    if str(guidance.get("preferred_pattern", "")).strip():
        pattern = str(guidance["preferred_pattern"]).lower()
        if "footprint" in pattern:
            return "footprint trail widening behind her"
        if "arm swinging free" in pattern or "free-arm" in pattern:
            return "one arm swinging free"
    special = _event_driven_trace(archetype, story_function, event_tags)
    if special:
        return special
    if archetype == "platform_edge" and variant == "bridge_motion" and story_function == "pressure":
        return "footprint trail widening behind her"
    if archetype == "stair_descent":
        return "one hand sliding along the handrail"
    if archetype == "passage_compression":
        return "one hand trailing the rail"
    return ""


def _identity_hook_policy(archetype: str, variant: str) -> str:
    if archetype in {"threshold_crossing", "doorway_handoff", "window_contact", "bench_rest", "brace_pause"}:
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


def _story_surface_override(story_function: str, archetype: str, variant: str, story_event: str = "") -> str:
    tags = _event_tags(story_event)
    overrides = {
        ("sidewalk_continuation", "entry"): "wet sidewalk edge outside the station",
        ("sidewalk_continuation", "continuation"): "wet sidewalk edge",
        ("sidewalk_continuation", "handoff"): "wet sidewalk edge",
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
    if archetype == "window_contact":
        return "station window"
    if archetype == "bench_rest":
        return "wet bench end"
    if archetype == "brace_pause":
        return "wet rail"
    if archetype == "sidewalk_continuation" and "changed_street_angle" in tags:
        return "wet curb-side sidewalk edge"
    if archetype == "sidewalk_continuation" and "connected_block" in tags:
        return "wet sidewalk edge with the curb line close"
    if archetype == "curb_crossing" and "release_alive" in tags:
        return "wet crosswalk through the middle-right side"
    if archetype == "curb_crossing" and "crossing_handoff" in tags:
        return "wet crosswalk along the right edge"
    return overrides.get((archetype, story_function), "")


def _event_tags(story_event: str) -> set[str]:
    low = str(story_event or "").strip().lower()
    tags: set[str] = set()
    if any(token in low for token in ("window", "glass")):
        tags.add("window_contact")
    if any(token in low for token in ("hand", "palm", "trailing", "contact")):
        tags.add("contact_detail")
    if any(token in low for token in ("bench", "seat", "sits", "sit")):
        tags.add("bench_rest")
    if "rise again" in low or "rise" in low:
        tags.add("rise_ready")
    if "leans forward" in low or "gathers her next step" in low:
        tags.add("bench_rise_ready")
    if "braced" in low or "brace" in low:
        tags.add("brace_pause")
    if "rail" in low and "hold" in low:
        tags.add("brace_pause")
    if "slightly changed street-side angle" in low:
        tags.add("changed_street_angle")
    if "same connected block" in low:
        tags.add("connected_block")
    if "physically inevitable" in low or "already feels chosen" in low:
        tags.add("inevitable_stride")
    if "visible crossing event" in low or "instead of another neutral walk" in low:
        tags.add("visible_crossing")
    if "keeps the crossing alive" in low or "keeps the release alive" in low:
        tags.add("release_alive")
    if "readable next-state handoff" in low or "carries the crossing into" in low:
        tags.add("crossing_handoff")
    if "wider forward departure" in low or "leaves the crossing behind" in low:
        tags.add("wider_departure")
    return tags


def _event_driven_archetype_override(shot: dict) -> str:
    tags = _event_tags(str(shot.get("story_event", "")).strip())
    if "window_contact" in tags and "contact_detail" in tags:
        return "window_contact"
    if "bench_rest" in tags:
        return "bench_rest"
    if "brace_pause" in tags:
        return "brace_pause"
    return ""


def _event_driven_variant_override(shot: dict, archetype: str) -> str:
    tags = _event_tags(str(shot.get("story_event", "")).strip())
    if archetype == "bench_rest" and "bench_rise_ready" in tags:
        return "rise_ready"
    return ""


def _event_driven_action(archetype: str, story_function: str, surface: str, event_tags: set[str]) -> str:
    if archetype == "window_contact":
        if "window_contact" in event_tags:
            return f"She keeps close to the {surface} and moves forward, one hand trailing the metal edge."
        if "contact_detail" in event_tags:
            return f"She keeps one palm on the {surface} and steadies her breath without fully stopping."
    if archetype == "bench_rest":
        if story_function == "pressure" and "bench_rest" in event_tags:
            return f"She sits at the end of the {surface} for one compressed beat, one foot still planted as if she could rise again."
        if "bench_rise_ready" in event_tags:
            return f"She leans forward from the end of the {surface} and gathers her next step without fully settling."
        if "bench_rest" in event_tags:
            return f"She sits at the end of the {surface}, one foot still planted as if she could rise again."
    if archetype == "brace_pause" and "brace_pause" in event_tags:
        return f"She braces at the {surface} with one hand fixed on the metal bar while the next step waits."
    if archetype == "sidewalk_continuation":
        if "changed_street_angle" in event_tags:
            return f"She re-enters from the road-side edge of the {surface} at night with the road opening hard to her right."
        if "connected_block" in event_tags:
            return f"She carries the same stride along the {surface} at night with the curb line tight at her feet and the same block running beside her."
        if "inevitable_stride" in event_tags:
            return f"She sets the next sidewalk-side stride on the {surface} at night with the curb held under her near side."
    if archetype == "curb_crossing":
        if "visible_crossing" in event_tags:
            return f"She enters the {surface} from the left edge with the road opening ahead of her."
        if "release_alive" in event_tags:
            return f"She keeps the crossing alive through the middle-right side of the {surface} without falling back to center."
        if "crossing_handoff" in event_tags:
            return f"She carries the crossing along the right edge of the {surface} with the open road held to her left."
        if "wider_departure" in event_tags:
            return f"She walks away from the {surface} as the open street widens around her."
    return ""


def _event_driven_continuity(archetype: str, story_function: str, surface: str, event_tags: set[str]) -> str:
    if archetype == "window_contact":
        if "window_contact" in event_tags:
            return f"She lets the contact slide off the {surface} and keeps moving past the edge."
        if "contact_detail" in event_tags:
            return f"She lets the palm contact soften on the {surface} and leaves the threshold commitment ready."
    if archetype == "bench_rest":
        if story_function == "pressure" and "bench_rest" in event_tags:
            return f"She holds the compressed seat at the end of the {surface} for one beat, still planted to rise again."
        if "bench_rise_ready" in event_tags:
            return f"She tips forward from the end of the {surface} and leaves the rise already forming before the cut."
        if "bench_rest" in event_tags:
            return f"She stays at the end of the {surface} with one foot planted and the route still waiting in front of her."
    if archetype == "brace_pause" and "brace_pause" in event_tags:
        return f"She loosens the braced contact at the {surface} and leaves the next step ready to resume."
    if archetype == "sidewalk_continuation":
        if "changed_street_angle" in event_tags:
            return f"She commits one step farther from the road-side edge and keeps the station block stretching behind her."
        if "connected_block" in event_tags:
            return f"She lands the next sidewalk-side stride along the {surface} and keeps the same connected block alive with the road still riding to her right."
        if "inevitable_stride" in event_tags:
            return f"She lands the next sidewalk-side stride and leaves the curb-side line already chosen before the cut."
    if archetype == "curb_crossing":
        if "release_alive" in event_tags:
            return f"She carries one more crossing step through the middle-right side of the {surface} and keeps the release live."
        if "crossing_handoff" in event_tags:
            return f"She leaves the next crossing state already formed at the right edge of the {surface} with the open road held to her left."
        if "wider_departure" in event_tags:
            return f"She leaves the {surface} behind and keeps walking away as the wider street opens around her."
    return ""


def _event_driven_trace(archetype: str, story_function: str, event_tags: set[str]) -> str:
    if archetype == "window_contact":
        return "one hand trailing the metal edge"
    if archetype == "bench_rest":
        return "one foot still planted"
    if archetype == "brace_pause":
        return "one hand braced on the metal bar"
    return ""


def _blocking_contract(story_function: str, archetype: str, world_zone: str, story_event: str) -> dict[str, str]:
    tags = _event_tags(story_event)
    blocking = {
        "blocking_role": "center_carry",
        "entry_side": "center",
        "travel_axis": "forward",
        "frame_bias": "centered",
        "arrival_side": "none",
        "camera_relation": "neutral_eye_level",
    }
    if story_function == "entry":
        blocking.update(
            {
                "blocking_role": "edge_entry",
                "entry_side": "left",
                "travel_axis": "left_to_right",
                "frame_bias": "left_weighted",
                "arrival_side": "center",
                "camera_relation": "three_quarter_follow",
            }
        )
    elif story_function == "handoff":
        blocking.update(
            {
                "blocking_role": "side_handoff",
                "entry_side": "center",
                "travel_axis": "left_to_right",
                "frame_bias": "right_weighted",
                "arrival_side": "right",
                "camera_relation": "side_follow",
            }
        )
    elif story_function == "payoff":
        blocking.update(
            {
                "blocking_role": "walk_away",
                "entry_side": "center",
                "travel_axis": "away",
                "frame_bias": "off_center",
                "arrival_side": "far",
                "camera_relation": "rear_release",
            }
        )
    elif story_function == "pressure":
        blocking.update(
            {
                "blocking_role": "compressed_hold",
                "entry_side": "center",
                "travel_axis": "forward",
                "frame_bias": "off_center",
                "arrival_side": "none",
                "camera_relation": "tight_side_pressure",
            }
        )
    if archetype == "gate_pass":
        blocking.update({"entry_side": "left", "frame_bias": "left_weighted", "travel_axis": "left_to_right"})
    if archetype == "threshold_crossing":
        blocking.update({"camera_relation": "threshold_clearance"})
    if archetype == "platform_edge":
        blocking.update({"travel_axis": "left_to_right", "camera_relation": "platform_edge_track"})
    if archetype == "passage_compression":
        blocking.update({"blocking_role": "compressed_hold", "frame_bias": "right_weighted", "camera_relation": "wall_close_follow"})
    if archetype == "window_contact":
        blocking.update({"frame_bias": "right_weighted", "camera_relation": "contact_side_glide"})
    if archetype == "bench_rest":
        blocking.update(
            {
                "blocking_role": "compressed_hold",
                "entry_side": "right",
                "travel_axis": "forward",
                "frame_bias": "right_weighted",
                "arrival_side": "none",
                "camera_relation": "bench_end_hold",
            }
        )
    if archetype == "brace_pause":
        blocking.update(
            {
                "blocking_role": "compressed_hold",
                "entry_side": "right",
                "travel_axis": "forward",
                "frame_bias": "right_weighted",
                "arrival_side": "none",
                "camera_relation": "rail_brace_hold",
            }
        )
    if world_zone == "compression":
        blocking.update({"blocking_role": "compressed_hold", "frame_bias": "right_weighted"})
    if "changed_street_angle" in tags:
        blocking.update(
            {
                "blocking_role": "edge_entry",
                "entry_side": "right",
                "travel_axis": "right_to_left",
                "frame_bias": "right_weighted",
                "arrival_side": "center",
                "camera_relation": "roadside_reentry",
            }
        )
    if "connected_block" in tags:
        blocking.update(
            {
                "blocking_role": "center_carry",
                "entry_side": "none",
                "travel_axis": "forward",
                "frame_bias": "right_weighted",
                "arrival_side": "none",
                "camera_relation": "block_carry_follow",
            }
        )
    if "inevitable_stride" in tags:
        blocking.update(
            {
                "blocking_role": "side_handoff",
                "entry_side": "center",
                "travel_axis": "left_to_right",
                "frame_bias": "right_weighted",
                "arrival_side": "right",
                "camera_relation": "committed_next_step",
            }
        )
    if "visible_crossing" in tags:
        blocking.update(
            {
                "blocking_role": "edge_entry",
                "entry_side": "left",
                "travel_axis": "left_to_right",
                "frame_bias": "left_weighted",
                "arrival_side": "center",
                "camera_relation": "crossing_entry",
            }
        )
    if "release_alive" in tags:
        blocking.update(
            {
                "blocking_role": "center_carry",
                "entry_side": "none",
                "travel_axis": "left_to_right",
                "frame_bias": "off_center",
                "arrival_side": "right",
                "camera_relation": "middle_right_carry",
            }
        )
    if "crossing_handoff" in tags:
        blocking.update(
            {
                "blocking_role": "side_handoff",
                "entry_side": "center",
                "travel_axis": "left_to_right",
                "frame_bias": "right_weighted",
                "arrival_side": "right",
                "camera_relation": "right_edge_handoff",
            }
        )
    if "wider_departure" in tags:
        blocking.update(
            {
                "blocking_role": "walk_away",
                "entry_side": "none",
                "travel_axis": "away",
                "frame_bias": "off_center",
                "arrival_side": "far",
                "camera_relation": "walk_away_release",
            }
        )
    return blocking
