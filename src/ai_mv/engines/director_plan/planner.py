from __future__ import annotations
import re

from ai_mv.core.contracts.visual_plan_normalize import normalize_direction_plan
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.prompt_grammar import golden_structure_guidance, load_director_rules, ref_archetype_grammar, ref_archetype_variant


def build_direction_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    use_generic_profile = bool(str(brief.get("profile_prompt", "")).strip())
    outline = payload.get("wan_safe_scene_outline", payload["scene_outline"])
    shot_packages: list[dict] = []
    for shot in outline.get("shot_packages", []):
        current = dict(shot)
        story_function = str(current.get("story_function", "")).strip()
        story_event = str(current.get("story_event", "")).strip()
        shot_function = _shot_function(story_function, str(current.get("world_zone", "")).strip())
        if use_generic_profile:
            archetype = _generic_ref_archetype(brief, current)
            variant = ""
            guidance = {}
        else:
            archetype = _ref_archetype_for_shot(current)
            variant = _ref_archetype_variant_for_shot(current, archetype)
            guidance = golden_structure_guidance(story_function, archetype, variant)
        story_visual_intent = str(current.get("story_visual_intent", "")).strip()
        if use_generic_profile:
            blocking = _generic_blocking_contract(story_function)
            primary_surface = _generic_primary_surface(brief, current)
            dominant_action = _generic_dominant_action(brief, current, primary_surface)
            continuity_delta = _generic_continuity_delta(current, primary_surface)
            content_trace = _generic_content_trace(brief, current)
            identity_hook_policy = "none"
            selected_prompt_shape = "connected cinematic prose"
            applied_grammar_source = "generic_profile_runtime"
        else:
            blocking = _blocking_contract(story_function, archetype, str(current.get("world_zone", "")).strip(), story_event)
            primary_surface = _primary_surface(story_function, archetype, variant, guidance, story_event)
            dominant_action = _dominant_action(story_function, archetype, variant, primary_surface, guidance, story_visual_intent, story_event)
            continuity_delta = _continuity_delta(story_function, archetype, variant, primary_surface, guidance, story_visual_intent, story_event)
            content_trace = _content_trace(story_function, archetype, variant, guidance, story_event)
            identity_hook_policy = _identity_hook_policy(archetype, variant)
            selected_prompt_shape = str(ref_archetype_grammar(archetype).get("preferred_sentence_shape", "")).strip() or "connected cinematic prose"
            applied_grammar_source = _applied_grammar_source(story_function, archetype, variant, guidance)
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
                "selected_prompt_shape": selected_prompt_shape,
                "applied_grammar_source": applied_grammar_source,
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
        if world_zone in {"threshold", "edge"}:
            return "threshold_crossing"
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
    return priorities[0] if priorities else str(load_director_rules().get("default_primary_surface", "walkable path")).strip()


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
    templates = _render_templates(load_director_rules().get("dominant_action_templates", {}), surface, variant, _platform_edge_start)
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
    templates = _render_templates(load_director_rules().get("continuity_templates", {}), surface, variant, _platform_edge_end)
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
    rules = load_director_rules().get("content_trace_defaults", {})
    nested = (
        rules.get("by_archetype_variant_story", {})
        .get(archetype, {})
        .get(variant, {})
    )
    if str(nested.get(story_function, "")).strip():
        return str(nested.get(story_function, "")).strip()
    if str(rules.get("by_archetype", {}).get(archetype, "")).strip():
        return str(rules.get("by_archetype", {}).get(archetype, "")).strip()
    return ""


def _identity_hook_policy(archetype: str, variant: str) -> str:
    rules = load_director_rules().get("identity_hook_policies", {})
    if archetype in set(rules.get("optional_small_hook_archetypes", [])):
        return "optional_small_hook"
    variants = rules.get("optional_small_hook_variants", {}).get(archetype, [])
    if variant in set(variants):
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
    templates = load_director_rules().get("platform_edge_templates", {}).get("start", {})
    template = str(templates.get(variant, "") or templates.get("base", "")).strip()
    return template.format(surface=surface) if template else f"She sets the next step along the {surface} with the edge geometry close at her feet."


def _platform_edge_end(variant: str, surface: str) -> str:
    templates = load_director_rules().get("platform_edge_templates", {}).get("end", {})
    template = str(templates.get(variant, "") or templates.get("base", "")).strip()
    return template.format(surface=surface) if template else f"She takes the next step along the {surface} and keeps driving forward."


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
    resolved = _primary_surface(str(shot.get("story_function", "")).strip(), archetype, str(shot.get("archetype_variant", "")).strip(), guidance)
    if resolved and resolved != "walkable path":
        return resolved
    defaults = {
        "platform_edge": "wet platform edge",
        "sidewalk_continuation": "wet sidewalk edge",
        "curb_crossing": "wet crosswalk",
        "threshold_crossing": "threshold crossing",
        "gate_pass": "entry threshold",
        "passage_compression": "narrow interior passage",
    }
    return defaults.get(archetype, "grounded real-world surface")


def _story_surface_override(story_function: str, archetype: str, variant: str, story_event: str = "") -> str:
    tags = _event_tags(story_event)
    rules = load_director_rules().get("surface_overrides", {})
    archetype_overrides = rules.get("by_archetype", {})
    if str(archetype_overrides.get(archetype, "")).strip():
        return str(archetype_overrides.get(archetype, "")).strip()
    if archetype == "sidewalk_continuation" and "changed_street_angle" in tags:
        return "wet curb-side sidewalk edge"
    if archetype == "sidewalk_continuation" and "connected_block" in tags:
        return "wet sidewalk edge with the curb line close"
    if archetype == "curb_crossing" and "release_alive" in tags:
        return "wet crosswalk through the middle-right side"
    if archetype == "curb_crossing" and "crossing_handoff" in tags:
        return "wet crosswalk along the right edge"
    by_story = rules.get("by_story_function", {}).get(archetype, {})
    return str(by_story.get(story_function, "")).strip()


def _render_templates(raw: dict, surface: str, variant: str, platform_edge_resolver) -> dict:
    templates: dict[str, dict[str, str]] = {}
    for archetype, rows in raw.items():
        if not isinstance(rows, dict):
            continue
        resolved: dict[str, str] = {}
        for story_function, template in rows.items():
            if archetype == "platform_edge" and story_function in {"entry", "pressure"}:
                resolved[story_function] = platform_edge_resolver(variant, surface)
                continue
            text = str(template).strip()
            if text:
                resolved[story_function] = text.format(surface=surface)
        templates[archetype] = resolved
    return templates


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
    if "leans forward" in low or "gathers her next step" in low or "tips away" in low or "rise already forming" in low:
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
        if story_function == "entry" and "window_contact" in event_tags:
            return f"She keeps one empty palm on the {surface} and steadies her breath without fully stopping."
        if story_function == "handoff" and "window_contact" in event_tags:
            return f"She keeps close to the {surface} at night, one empty palm resting on the lower metal rail as the next step gathers."
        if "window_contact" in event_tags:
            return f"She keeps close to the {surface} at night, one empty palm resting on the lower metal rail as she moves past it."
        if "contact_detail" in event_tags:
            return f"She keeps one empty palm on the {surface} and steadies her breath without fully stopping."
    if archetype == "bench_rest":
        if story_function == "pressure" and "bench_rest" in event_tags:
            return f"She sits on the {surface} for one compressed beat, one foot still planted on the ground as if she could rise again."
        if story_function == "continuation" and "bench_rest" in event_tags:
            return f"She holds one compressed seated beat on the {surface} with one foot still planted on the ground."
        if "bench_rise_ready" in event_tags:
            return f"She leans forward from the {surface} at night, one foot still planted on the ground as the rise gathers into her next step."
        if "bench_rest" in event_tags:
            return f"She sits on the {surface} at night, one foot still planted on the ground as if she could rise again."
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
        if story_function == "entry" and "window_contact" in event_tags:
            return f"She softens the empty-palm contact on the {surface} and leaves the next commitment ready."
        if story_function == "handoff" and "window_contact" in event_tags:
            return f"She lets the empty palm lift from the lower rail of the {surface} and leaves the next step already forming."
        if "window_contact" in event_tags:
            return f"She lets the empty palm lift from the lower rail of the {surface} and keeps moving past the edge."
        if "contact_detail" in event_tags:
            return f"She lets the empty palm contact soften on the {surface} and leaves the threshold commitment ready."
    if archetype == "bench_rest":
        if story_function == "pressure" and "bench_rest" in event_tags:
            return f"She holds the compressed seat on the {surface} for one beat, still planted to rise again."
        if story_function == "continuation" and "bench_rest" in event_tags:
            return f"She keeps the compressed seat on the {surface} with one foot still planted to rise again."
        if "bench_rise_ready" in event_tags:
            return f"She tips forward from the {surface} and leaves the rise already forming before the cut."
        if "bench_rest" in event_tags:
            return f"She stays on the {surface} with one foot planted on the ground and the route still waiting in front of her."
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
        return "one empty palm on the lower metal rail"
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


def _generic_ref_archetype(brief: dict, shot: dict) -> str:
    prompt = str(brief.get("profile_prompt", "")).lower()
    story_function = str(shot.get("story_function", "")).strip()
    if _has_any_term(prompt, "diner", "cafe", "room", "apartment", "notebook"):
        return "interior_cinematic"
    if _has_any_term(prompt, "club", "stage", "synth", "performance", "band"):
        return "performance_cinematic"
    if _has_any_term(prompt, "roof", "dawn", "morning"):
        return "rooftop_release"
    if story_function in {"payoff", "handoff"}:
        return "urban_release"
    return "night_walk_cinematic"


def _generic_primary_surface(brief: dict, shot: dict) -> str:
    prompt = str(brief.get("profile_prompt", "")).lower()
    section = str(shot.get("section_label", "")).lower()
    story_function = str(shot.get("story_function", "")).strip()
    literal_image = str(shot.get("literal_image", "")).strip()
    locations = [str(x).strip() for x in brief.get("profile_locations", []) if str(x).strip()]
    if literal_image:
        return _literal_image_surface(literal_image)
    if locations:
        location = _pick_location_for_section(section, story_function, locations)
        return f"a grounded cinematic view of {location}"
    if _has_any_term(prompt, "diner", "cafe") and "intro" in section:
        return "a dim late-night diner with a rain-streaked window and worn table"
    if _has_any_term(prompt, "club", "synth", "stage", "band") and "bridge" in section:
        return "a cramped rehearsal room with cables, instruments, and practical stage lights"
    if _has_any_term(prompt, "roof", "dawn", "morning") and story_function in {"payoff", "handoff"}:
        return "a concrete rooftop with open skyline and soft early light"
    if _has_any_term(prompt, "bus", "train", "subway", "window"):
        return "a transit interior with window reflections and worn surfaces"
    if _has_any_term(prompt, "rain", "wet", "city", "street", "night"):
        return "a wet city street at night with reflective pavement and practical lights"
    return "a grounded everyday place with readable depth and physical texture"


def _generic_dominant_action(brief: dict, shot: dict, primary_surface: str) -> str:
    story_function = str(shot.get("story_function", "")).strip()
    event = str(shot.get("story_event", "")).strip()
    visible_action = str(shot.get("visible_action", "")).strip()
    if visible_action:
        return _generic_action_from_visible_action(visible_action, primary_surface)
    if story_function == "entry":
        return f"She moves into frame naturally inside {primary_surface}"
    if story_function == "pressure":
        return f"She holds a quieter, more compressed moment inside {primary_surface}"
    if story_function == "payoff":
        return f"She opens into the clearest release moment inside {primary_surface}"
    if event:
        return event
    return f"She keeps moving naturally through {primary_surface}"


def _generic_continuity_delta(shot: dict, primary_surface: str) -> str:
    story_function = str(shot.get("story_function", "")).strip()
    continuity_anchor = str(shot.get("continuity_anchor", "")).strip()
    if continuity_anchor:
        return _generic_continuity_from_anchor(continuity_anchor)
    if story_function == "handoff":
        return "She leaves the shot with the next movement already forming."
    if story_function == "payoff":
        return "She holds the release without losing the grounded reality of the place."
    return "She carries the moment forward without breaking place continuity."


def _generic_content_trace(brief: dict, shot: dict) -> str:
    prompt = str(brief.get("profile_prompt", "")).lower()
    section = str(shot.get("section_label", "")).lower()
    literal_image = str(shot.get("literal_image", "")).strip()
    emotional_turn = str(shot.get("emotional_turn", "")).strip()
    lyric_lines = [str(x).strip() for x in shot.get("lyric_lines", []) if str(x).strip()]
    props = [str(x).strip() for x in brief.get("profile_props", []) if str(x).strip()]
    if literal_image:
        return literal_image
    if emotional_turn:
        return emotional_turn
    if lyric_lines:
        return " / ".join(lyric_lines[:2])
    if props:
        return ", ".join(props[:2])
    if _has_any_term(prompt, "diner", "cafe", "notebook") and "intro" in section:
        return "a worn notebook, a half-empty coffee mug, and raindrops on the window"
    if _has_any_term(prompt, "rain", "wet", "street", "city"):
        return "rain-dark pavement, window reflections, and soft headlight spill"
    if _has_any_term(prompt, "club", "synth", "stage", "band"):
        return "vintage equipment, loose cables, and dim practical lights"
    if _has_any_term(prompt, "roof", "dawn", "morning"):
        return "concrete texture, open air, and low skyline haze"
    return "real textures, grounded props, and natural environmental detail"


def _generic_blocking_contract(story_function: str) -> dict[str, str]:
    if story_function == "entry":
        return {
            "blocking_role": "entry_frame",
            "entry_side": "left",
            "travel_axis": "forward",
            "frame_bias": "left_weighted",
            "arrival_side": "center",
            "camera_relation": "gentle_follow",
        }
    if story_function == "payoff":
        return {
            "blocking_role": "release_frame",
            "entry_side": "center",
            "travel_axis": "forward",
            "frame_bias": "off_center",
            "arrival_side": "far",
            "camera_relation": "wide_release",
        }
    if story_function == "pressure":
        return {
            "blocking_role": "compressed_hold",
            "entry_side": "center",
            "travel_axis": "minimal",
            "frame_bias": "tight_center",
            "arrival_side": "none",
            "camera_relation": "intimate_hold",
        }
    return {
        "blocking_role": "carry_frame",
        "entry_side": "center",
        "travel_axis": "forward",
        "frame_bias": "centered",
        "arrival_side": "center",
        "camera_relation": "natural_follow",
    }


def _has_any_term(text: str, *terms: str) -> bool:
    lowered = str(text).lower()
    for term in terms:
        if " " in term:
            if term in lowered:
                return True
            continue
        if re.search(rf"\b{re.escape(term.lower())}\b", lowered):
            return True
    return False


def _pick_location_for_section(section: str, story_function: str, locations: list[str]) -> str:
    if not locations:
        return "a grounded location"
    low = str(section).lower()
    if "intro" in low:
        return locations[0]
    if "bridge" in low and len(locations) >= 3:
        return locations[min(2, len(locations) - 1)]
    if ("chorus" in low or story_function == "payoff") and len(locations) >= 2:
        return locations[min(len(locations) - 1, 1 if len(locations) == 2 else 2)]
    if len(locations) >= 2:
        return locations[1]
    return locations[0]


def _literal_image_surface(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    if not cleaned:
        return "a grounded everyday place with readable depth and physical texture"
    lowered = cleaned.lower()
    if any(token in lowered for token in ("window", "glass")):
        return f"a lived-in interior framed by {cleaned}"
    if any(token in lowered for token in ("street", "road", "asphalt", "crosswalk", "sidewalk", "rain", "wet")):
        return f"a real nighttime street with {cleaned}"
    if any(token in lowered for token in ("room", "club", "stage", "synth", "cable")):
        return f"a grounded performance space with {cleaned}"
    if any(token in lowered for token in ("roof", "skyline", "dawn", "fog")):
        return f"an open rooftop atmosphere with {cleaned}"
    return f"a grounded real-world scene built around {cleaned}"


def _generic_action_from_visible_action(visible_action: str, primary_surface: str) -> str:
    cleaned = " ".join(str(visible_action).strip().rstrip(". ").split())
    lowered = cleaned.lower()
    if lowered.startswith("she "):
        return cleaned
    if any(lowered.startswith(prefix) for prefix in ("walking", "standing", "sitting", "leaning", "writing", "playing", "crossing", "holding", "pausing")):
        return f"She is {cleaned} within {primary_surface}"
    return f"She {cleaned} within {primary_surface}"


def _generic_continuity_from_anchor(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered.startswith("same ") or lowered.startswith("still ") or lowered.startswith("keep "):
        return cleaned[0].upper() + cleaned[1:] + "."
    return f"Keep {cleaned} consistent from the previous shot."
