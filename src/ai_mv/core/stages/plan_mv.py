from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.planning.anchor_package import build_anchor_package, with_selected_pose_anchor_bank
from ai_mv.core.planning.creative_direction import build_creative_direction
from ai_mv.core.planning.director_treatment import build_director_treatment
from ai_mv.core.planning.render_items import build_render_item
from ai_mv.core.planning.sections import normalized_sections
from ai_mv.core.planning.shot_plan import build_shot_plan
from ai_mv.core.planning.story_contracts import build_story_contract
from ai_mv.styles.resolver import get_style_bible, resolve_style_selection



def run_plan_mv(stage_input: StageInput) -> StageOutput:
    payload = build_plan_preview_payload(stage_input.config, stage_input.payload)
    return StageOutput("plan_mv", "done", payload, [])



def build_plan_preview_payload(config: dict, payload: dict) -> dict:
    concept_text = str(payload.get("concept_text") or config.get("concept_text", "")).strip()
    audio_map = dict(payload.get("audio_map", {}))
    duration = float(audio_map.get("duration_sec", 16.0) or 16.0)
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    default_style_name = str(planning.get("default_style_name", "")).strip() or None
    continuity_mode = str(planning.get("continuity_mode", "strict")).strip() or "strict"
    style_resolution = resolve_style_selection(concept_text, default_style_name=default_style_name)
    style_lane = style_resolution["style_lane"]
    style_bible = get_style_bible(style_lane)
    sections = normalized_sections(audio_map, duration)
    creative_direction = build_creative_direction(
        concept_text=concept_text,
        style_name=style_lane,
        sections=sections,
        continuity_mode=continuity_mode,
    )
    director_treatment = build_director_treatment(
        concept_text=concept_text,
        style_name=style_lane,
        sections=sections,
    )
    anchor_package = build_anchor_package(
        concept_text=concept_text,
        style_name=style_lane,
        creative_direction=creative_direction,
    )
    shot_plan = build_shot_plan(config, sections, style_name=style_lane)
    _thread_continuity_anchor_bundle(shot_plan, creative_direction)
    _thread_director_story_beats(shot_plan, director_treatment)
    _thread_story_action_grammar(shot_plan, concept_text=concept_text)
    if _narrative_progression_enabled(planning):
        _thread_narrative_progression(shot_plan, concept_text=concept_text)
    _thread_story_contracts(shot_plan, concept_text=concept_text)
    _thread_shot_relation_contracts(shot_plan, style_name=style_lane)
    material_plan = build_material_plan(style_lane, shot_plan)
    render_plan = [build_render_item(config, concept_text, style_lane, style_bible, shot) for shot in shot_plan]
    _apply_sequence_role_diversity(render_plan)
    _repair_role_diversity_prompt_contracts(render_plan)
    anchor_package = with_selected_pose_anchor_bank(
        anchor_package,
        render_plan=render_plan,
        style_name=style_lane,
        creative_direction=creative_direction,
    )
    return {
        "style_lane": style_lane,
        "style_resolution": style_resolution,
        "style_bible": style_bible,
        "creative_direction": creative_direction,
        "director_treatment": director_treatment,
        "anchor_package": anchor_package,
        "section_plan": sections,
        "shot_plan": shot_plan,
        "material_plan": material_plan,
        "render_plan": render_plan,
        "workflow_inputs": {
            **dict(payload.get("workflow_inputs", {})),
            "plan": {
                "shot_count": len(shot_plan),
                "material_count": len(material_plan),
                "concept_text": concept_text,
                "style_lane": style_lane,
                "section_count": len(sections),
                "music_section_count": len(sections),
            },
        },
    }


def _apply_sequence_role_diversity(render_plan: list[dict]) -> None:
    if len(render_plan) < 5:
        return
    hero_count = 0
    recent_roles: list[str] = []
    for item in render_plan:
        policy = item.get("production_policy") if isinstance(item, dict) else None
        if not isinstance(policy, dict):
            recent_roles.append("")
            continue
        role = str(policy.get("candidate_role", "")).strip()
        if role != "hero_face_performance":
            recent_roles.append(role)
            continue
        should_diversify = hero_count >= 3 or recent_roles[-2:] == ["hero_face_performance", "hero_face_performance"]
        if should_diversify:
            _set_render_item_candidate_role(item, _sequence_diversity_role_for_item(item))
            recent_roles.append(str(item.get("production_policy", {}).get("candidate_role", "")).strip())
            continue
        hero_count += 1
        recent_roles.append(role)


def _repair_role_diversity_prompt_contracts(render_plan: list[dict]) -> None:
    for item in render_plan:
        if not isinstance(item, dict):
            continue
        policy = item.get("production_policy")
        if not isinstance(policy, dict):
            continue
        role = str(policy.get("candidate_role", "")).strip()
        if role == "world_bridge":
            still_clause, clip_clause = _role_diversity_prompt_clauses(item, "world_bridge")
            _append_role_prompt_contract(item, still_clause=still_clause, clip_clause=clip_clause)
        elif role == "symbolic_insert":
            still_clause, clip_clause = _role_diversity_prompt_clauses(item, "symbolic_insert")
            _append_role_prompt_contract(item, still_clause=still_clause, clip_clause=clip_clause)


def _role_diversity_prompt_clauses(item: dict, role: str) -> tuple[str, str]:
    if _is_desert_radio_item(item):
        if role == "symbolic_insert":
            return (
                "role diversity symbolic insert: readable desert-radio cutaway detail such as radio dial, signal light, hand, antenna silhouette, sand texture, or sunrise flare; avoid repeated centered front hero pose",
                "role diversity symbolic insert motion: short cutaway with subtle radio light, hand, sand, antenna, or sunrise movement; avoid hero performance hold",
            )
        return (
            "role diversity world bridge: environment-led desert wide, profile, rear, over-shoulder, radio-object, or small-figure composition; changed camera distance and spatial reset; avoid repeated centered front hero pose",
            "role diversity world bridge motion: environment-led desert drift, wind pass, walking-away continuity, or radio-signal movement; avoid another centered hero performance hold",
        )
    if role == "symbolic_insert":
        return (
            "role diversity symbolic insert: readable cutaway detail such as reflection, signage, hand, object, rain texture, or light motif; avoid repeated centered front hero street walk",
            "role diversity symbolic insert motion: short cutaway with subtle reflection, light, hand, object, or rain movement; avoid hero walk/performance hold",
        )
    return (
        "role diversity world bridge: environment-led wide, profile, rear, over-shoulder, reflection, or small-figure composition; changed camera distance and spatial reset; avoid repeated centered front hero street walk",
        "role diversity world bridge motion: environment-led drift, lateral pass, walking-away continuity, or reflection movement; avoid another centered hero walk/performance hold",
    )



def _is_desert_radio_item(item: dict) -> bool:
    text = " ".join(
        str(item.get(key, ""))
        for key in ("world_anchor", "prompt_seed", "prompt_draft", "still_prompt_text", "clip_positive_prompt")
    ).lower()
    return "desert" in text and any(token in text for token in ("radio", "signal", "tower", "antenna"))



def _append_role_prompt_contract(item: dict, *, still_clause: str, clip_clause: str) -> None:
    for key in ("prompt_seed", "prompt_draft", "still_prompt_text"):
        item[key] = _append_prompt_clause(str(item.get(key, "")).strip(), still_clause)
    item["clip_positive_prompt"] = _append_prompt_clause(str(item.get("clip_positive_prompt", "")).strip(), clip_clause)


def _sequence_diversity_role_for_item(item: dict) -> str:
    text = " ".join(
        str(item.get(key, ""))
        for key in (
            "section_id",
            "material_id",
            "prompt_seed",
            "prompt_draft",
            "still_prompt_text",
            "clip_positive_prompt",
        )
    ).replace("_", " ").lower()
    if any(token in text for token in ("final", "outro", "payoff", "bridge", "world", "wide", "small figure", "skyline")):
        return "world_bridge"
    return "symbolic_insert"


def _set_render_item_candidate_role(item: dict, role: str) -> None:
    policy = dict(item.get("production_policy", {}))
    policy["candidate_role"] = role
    policy["anchor_reference_arm"] = {
        "world_bridge": "F_FULLBODY_UPPER_WORLD",
        "symbolic_insert": "A_FULLBODY_ONLY",
    }.get(role, policy.get("anchor_reference_arm", "D_FULLBODY_UPPER"))
    policy["ia2v_risk_class"] = "yellow" if role == "symbolic_insert" else "green"
    policy["recommended_duration_sec"] = {"min": 0.3, "max": 0.8} if role == "symbolic_insert" else {"min": 0.8, "max": 2.0}
    safety_rules = list(policy.get("safety_rules", []))
    if "sequence_role_diversity" not in safety_rules:
        safety_rules.append("sequence_role_diversity")
    policy["safety_rules"] = safety_rules
    review_focus = list(policy.get("review_focus", []))
    if role == "world_bridge":
        review_focus.extend(token for token in ("world_continuity", "silhouette_readability") if token not in review_focus)
    if role == "symbolic_insert":
        review_focus.extend(token for token in ("symbolic_readability", "insert_duration_control") if token not in review_focus)
    policy["review_focus"] = review_focus
    item["production_policy"] = policy
    item["candidate_role"] = role
    item["anchor_reference_arm"] = policy["anchor_reference_arm"]
    item["ia2v_risk_class"] = policy["ia2v_risk_class"]
    item["recommended_duration_sec"] = policy["recommended_duration_sec"]
    _repair_sequence_diversity_prompts(item, role)


def _repair_sequence_diversity_prompts(item: dict, role: str) -> None:
    still_clause, clip_clause = _sequence_diversity_prompt_clauses(item, role)
    for key in ("prompt_seed", "prompt_draft", "still_prompt_text"):
        item[key] = _append_prompt_clause(str(item.get(key, "")).strip(), still_clause)
    item["clip_positive_prompt"] = _append_prompt_clause(str(item.get("clip_positive_prompt", "")).strip(), clip_clause)


def _sequence_diversity_prompt_clauses(item: dict, role: str) -> tuple[str, str]:
    if _is_desert_radio_item(item):
        if role == "symbolic_insert":
            return (
                "sequence diversity symbolic insert: cut away from hero performance into a readable desert-radio object, hand, signal light, antenna silhouette, sand texture, or sunrise flare; keep the same desert signal continuity but avoid another centered hero portrait",
                "sequence diversity symbolic insert motion: short held insert with subtle radio light, sand, antenna, or sunrise movement; no new hero performance pose; preserve continuity as an editorial breaker",
            )
        return (
            "sequence diversity world bridge: environment-led desert wide or over-shoulder frame with dune depth, smaller anchored figure, changed camera distance, and clear spatial reset; avoid another centered front performance pose",
            "sequence diversity world bridge motion: gentle desert environment-led camera drift or walking-away continuity beat; emphasize spatial reset, wind-shaped dunes, sunrise horizon, and changed camera distance rather than another hero performance hold",
        )
    if role == "symbolic_insert":
        return (
            "sequence diversity symbolic insert: cut away from hero performance into a readable object, reflection, light motif, hand detail, or wet street texture; keep the same world continuity but avoid another centered street-performance portrait",
            "sequence diversity symbolic insert motion: short held insert with subtle light/reflection movement; no new hero performance pose; preserve continuity as an editorial breaker",
        )
    return (
        "sequence diversity world bridge: environment-led wide or over-shoulder frame with boulevard depth, smaller anchored figure, changed camera distance, and clear spatial reset; avoid another centered front street-performance pose",
        "sequence diversity world bridge motion: gentle environment-led camera drift or walking-away continuity beat; emphasize spatial reset, wet neon reflections, and changed camera distance rather than another hero performance hold",
    )


def _append_prompt_clause(text: str, clause: str) -> str:
    if clause in text:
        return text
    if not text:
        return clause
    return f"{text}, {clause}"


def build_material_plan(style_name: str, shot_plan: list[dict]) -> list[dict]:
    material_plan: list[dict] = []
    for idx, shot in enumerate(shot_plan, start=1):
        role = _material_role_for_shot(shot)
        material_plan.append(
            {
                "material_id": f"MAT_{idx:03d}",
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "section_id": str(shot.get("section_id", "")).strip(),
                "role": role,
                "style_lane": style_name,
                "mode_hint": _mode_hint_for_shot(shot),
                "shot_intent": str(shot.get("shot_role", "")).strip(),
                "story_beat_id": str(shot.get("story_beat_id", "")).strip(),
                "story_function": str(shot.get("story_function", "")).strip(),
                "visual_event": str(shot.get("visual_event", "")).strip(),
                "emotional_state": str(shot.get("emotional_state", "")).strip(),
                "target_aspect": "1280x720",
                "needs_front_readability": role == "performance_source",
                "continuity_constraints": {
                    "same_subject": True,
                    "same_world": True,
                    "same_time_band": True,
                },
            }
        )
        shot["material_id"] = material_plan[-1]["material_id"]
    return material_plan


def _material_role_for_shot(shot: dict) -> str:
    workflow_intent = str(shot.get("workflow_intent", "")).strip()
    section_type = str(shot.get("section_type", "")).strip()
    story_function = str(shot.get("story_function", "")).strip()
    if story_function == "payoff":
        return "ending_resolution_still"
    if story_function == "release":
        return "chorus_release_still"
    if workflow_intent == "audio_reactive_candidate" or section_type == "chorus":
        return "performance_source"
    if workflow_intent == "bridge_candidate" or section_type == "bridge":
        return "bridge_target"
    if section_type == "intro":
        return "anchor_source"
    return "general_source"


def _mode_hint_for_shot(shot: dict) -> str:
    workflow_intent = str(shot.get("workflow_intent", "")).strip()
    section_type = str(shot.get("section_type", "")).strip()
    if workflow_intent == "audio_reactive_candidate" or section_type == "chorus":
        return "performance"
    if workflow_intent == "bridge_candidate" or section_type == "bridge":
        return "bridge_transition"
    if section_type == "intro":
        return "anchor"
    return "general_narrative"


def _thread_continuity_anchor_bundle(shot_plan: list[dict], creative_direction: dict) -> None:
    protagonist_anchor = str(creative_direction.get("protagonist_anchor", "")).strip() if isinstance(creative_direction, dict) else ""
    world_anchor = str(creative_direction.get("world_anchor", "")).strip() if isinstance(creative_direction, dict) else ""
    for shot in shot_plan:
        if not isinstance(shot, dict):
            continue
        if protagonist_anchor:
            shot["protagonist_anchor"] = protagonist_anchor
        if world_anchor:
            shot["world_anchor"] = world_anchor
        wardrobe_anchor = str(creative_direction.get("wardrobe_anchor", "")).strip()
        if not wardrobe_anchor:
            wardrobe_anchor = "stable bright stage outfit silhouette" if str(creative_direction.get("style_lane", "")).strip() == "idol_pop" else "story-derived stable outfit silhouette"
        shot["continuity_contract"] = {
            "protagonist_anchor": protagonist_anchor,
            "world_anchor": world_anchor,
            "wardrobe_anchor": wardrobe_anchor,
            "no_competing_subjects": True,
            "time_band_anchor": "same night time band",
        }



def _thread_director_story_beats(shot_plan: list[dict], director_treatment: dict) -> None:
    beats = director_treatment.get("story_beats", []) if isinstance(director_treatment, dict) else []
    beat_by_section = {
        str(beat.get("section_id", "")).strip(): beat
        for beat in beats
        if isinstance(beat, dict) and str(beat.get("section_id", "")).strip()
    }
    for shot in shot_plan:
        if not isinstance(shot, dict):
            continue
        beat = beat_by_section.get(str(shot.get("section_id", "")).strip())
        if not isinstance(beat, dict):
            continue
        shot["story_beat_id"] = str(beat.get("beat_id", "")).strip()
        shot["story_function"] = str(beat.get("story_function", "")).strip()
        shot["visual_event"] = str(beat.get("visual_event", "")).strip()
        shot["emotional_state"] = str(beat.get("emotional_state", "")).strip()
        shot["required_change_from_previous"] = str(beat.get("required_change_from_previous", "")).strip()
        shot["payoff_requirement"] = str(beat.get("payoff_requirement", "")).strip()


def _narrative_progression_enabled(planning: dict) -> bool:
    if not isinstance(planning, dict):
        return False
    return bool(planning.get("enable_narrative_progression"))



def _thread_narrative_progression(shot_plan: list[dict], *, concept_text: str) -> None:
    total = len([shot for shot in shot_plan if isinstance(shot, dict)])
    if total <= 0:
        return
    previous_visible_change = "sequence start"
    for idx, shot in enumerate([shot for shot in shot_plan if isinstance(shot, dict)]):
        progression = _narrative_progression_for_shot(
            shot,
            concept_text=concept_text,
            sequence_index=idx,
            total_shots=total,
            previous_visible_change=previous_visible_change,
        )
        shot["narrative_progression"] = progression
        shot["beat_role"] = progression["beat_role"]
        shot["motif_state"] = progression["motif_state"]
        shot["visible_change"] = progression["visible_change"]
        shot["pose_intent"] = progression["pose_intent"]
        shot["motion_intent"] = progression["motion_intent"]
        shot["emotional_state"] = progression["emotional_state"]
        shot["required_change_from_previous"] = progression["why_this_follows_previous"]
        shot["visual_event"] = progression["visible_change"]
        previous_visible_change = progression["visible_change"]



def _narrative_progression_for_shot(
    shot: dict,
    *,
    concept_text: str,
    sequence_index: int,
    total_shots: int,
    previous_visible_change: str,
) -> dict:
    motif = _narrative_motif_family(concept_text)
    role = _narrative_beat_role(shot, sequence_index=sequence_index, total_shots=total_shots)
    state = _narrative_state_for_role(role, motif)
    return {
        "beat_role": role,
        "emotional_state": state["emotional_state"],
        "motif_state": state["motif_state"],
        "visible_change": state["visible_change"],
        "pose_intent": state["pose_intent"],
        "motion_intent": state["motion_intent"],
        "why_this_follows_previous": f"progress from {previous_visible_change} into {state['visible_change']}",
    }



def _narrative_beat_role(shot: dict, *, sequence_index: int, total_shots: int) -> str:
    section_type = str(shot.get("section_type", "")).strip().lower()
    story_function = str(shot.get("story_function", "")).strip().lower()
    if sequence_index == 0 or section_type == "intro" or story_function == "wound_setup":
        return "setup"
    if sequence_index >= total_shots - 1 or section_type == "outro" or story_function == "payoff":
        return "release"
    if section_type == "bridge":
        return "recognition"
    if section_type in {"chorus", "post_chorus"} or story_function == "release":
        return "confrontation"
    if section_type == "pre_chorus" or story_function == "threshold":
        return "approach"
    if sequence_index >= max(1, total_shots // 2):
        return "discovery"
    return "search"



def _narrative_motif_family(concept_text: str) -> str:
    text = str(concept_text or "").lower()
    if any(token in text for token in ("radio", "tower", "antenna", "signal")):
        return "radio_signal"
    if any(token in text for token in ("message", "phone", "call", "text")):
        return "phone_message"
    if any(token in text for token in ("train", "station", "subway")):
        return "station_timing"
    if any(token in text for token in ("rain", "neon", "city", "wet")):
        return "city_reflection"
    return "signature_motif"



def _narrative_state_for_role(role: str, motif: str) -> dict:
    motif_states = {
        "radio_signal": {
            "setup": ("numb", "radio silent", "she is alone with a dead radio in the concept space", "holding the radio low with a still guarded posture", "coat and hair move subtly while she looks down at the silent radio"),
            "search": ("curious", "faint radio signal", "the radio light flickers for the first time", "raising the radio toward her ear and changing gaze direction", "the signal light flickers and her posture shifts from stillness to attention"),
            "approach": ("urgent", "stronger radio interference", "the signal gives her a clear direction across the space", "leaning into movement while tracking the signal", "she follows the interference as the camera drifts with her direction change"),
            "discovery": ("pulled_forward", "tower signal revealed", "a distant transmission source becomes visible", "stopping mid-step as the signal source is revealed", "the background source becomes clearer while she slows into recognition"),
            "confrontation": ("overwhelmed", "distorted radio voice", "the signal becomes loud enough to confront her", "bracing against the sound with the radio near her face", "static intensifies as she turns into the hook energy"),
            "recognition": ("shocked", "recognizable voice in static", "she realizes the voice in the radio is familiar", "pulling the radio away from her ear with a stunned expression", "the camera holds while her expression changes from urgency to recognition"),
            "release": ("accepting", "radio switched off at sunrise", "she stops chasing the signal and lets the radio fall silent", "placing the radio down or turning away toward the sunrise", "the radio light dies as the frame opens into the ending light"),
        },
        "phone_message": {
            "setup": ("stuck", "unread phone message", "the unanswered message anchors the first wound", "holding the phone low without opening it", "screen glow pulses while she hesitates"),
            "search": ("curious", "message opened", "she reads the message and changes direction", "lifting the phone into readable light", "her gaze moves from screen to destination"),
            "approach": ("urgent", "reply cursor blinking", "she moves before deciding what to send", "walking with the phone held close", "street light slides over the phone as she advances"),
            "discovery": ("pulled_forward", "old photo or contact revealed", "the screen reveals what she was avoiding", "stopping at a reflection with the phone visible", "reflection and screen align for a readable reveal"),
            "confrontation": ("overwhelmed", "message unsent", "she faces the choice instead of hiding it", "hand hovering over send/delete", "the camera tightens as the hand pauses"),
            "recognition": ("clear", "message deleted or saved", "she understands what the message meant", "lowering the phone after the decision", "screen glow fades as her posture settles"),
            "release": ("accepting", "phone screen dark", "she leaves the message behind", "walking away with the phone lowered", "the dark screen catches final light as she exits"),
        },
    }
    default_states = {
        "setup": ("stuck", "signature motif hidden", "the protagonist starts before the motif changes", "still guarded posture around the key object or location", "subtle environmental motion establishes the starting state"),
        "search": ("curious", "signature motif appears", "the first visible clue appears", "gaze or hand shifts toward the clue", "the clue moves or glows subtly as attention changes"),
        "approach": ("urgent", "signature motif intensifies", "the clue gives a direction to follow", "body leans into a clear direction change", "camera follows the directional shift"),
        "discovery": ("pulled_forward", "signature motif source revealed", "the source of the motif becomes visible", "stopping mid-step to register the reveal", "background detail sharpens into a readable source"),
        "confrontation": ("overwhelmed", "signature motif peaks", "the motif reaches its strongest visual state", "bracing or turning into the peak", "motion swells with hook energy"),
        "recognition": ("shocked", "signature motif becomes personal", "the protagonist understands the motif differently", "pulling back with a changed expression", "camera holds on the emotional shift"),
        "release": ("accepting", "signature motif resolved", "the protagonist leaves the motif in a changed state", "turning away or lowering the object", "motion opens into final light or space"),
    }
    emotion, motif_state, visible_change, pose_intent, motion_intent = motif_states.get(motif, default_states).get(role, default_states["search"])
    return {
        "emotional_state": emotion,
        "motif_state": motif_state,
        "visible_change": visible_change,
        "pose_intent": pose_intent,
        "motion_intent": motion_intent,
    }



def _thread_story_contracts(shot_plan: list[dict], *, concept_text: str) -> None:
    previous_shot: dict | None = None
    for shot in shot_plan:
        if not isinstance(shot, dict):
            continue
        shot["story_contract"] = build_story_contract(shot, previous_shot=previous_shot, concept_text=concept_text)
        previous_shot = shot


def _thread_story_action_grammar(shot_plan: list[dict], *, concept_text: str) -> None:
    previous_grammar = ""
    for idx, shot in enumerate(shot_plan):
        if not isinstance(shot, dict):
            continue
        grammar = _story_action_grammar_for_shot(shot, concept_text=concept_text, sequence_index=idx)
        if grammar == previous_grammar:
            grammar = _fallback_story_action_grammar(shot, sequence_index=idx, concept_cue=_concept_action_cue(concept_text))
        shot["story_action_grammar"] = grammar
        previous_grammar = grammar


def _story_action_grammar_for_shot(shot: dict, *, concept_text: str, sequence_index: int) -> str:
    section_type = str(shot.get("section_type", "")).strip().lower()
    visual_mode = str(shot.get("visual_mode", "")).strip().lower()
    story_function = str(shot.get("story_function", "")).strip().lower()
    concept = str(concept_text or "").lower()
    concept_cue = _concept_action_cue(concept)

    if visual_mode in {"empty_boulevard_anchor", "curbside_silhouette", "street_establishing", "roadway_overview"}:
        return f"establish {concept_cue} with a small off-center protagonist entering the frame; do not default to a static centered portrait"
    if ("message" in concept or "phone" in concept) and (section_type in {"verse", "pre_chorus"} or story_function in {"search", "threshold"}):
        return "uses a phone message or reflection cue as the visible decision trigger, then changes gaze or walking direction; do not default to a static centered portrait"
    if visual_mode in {"rain_window_detail", "window_reflection"}:
        return "reads a reflection cue through rain-streaked glass with partial face or hand detail, not a front-facing pose; do not default to a static centered portrait"
    if visual_mode == "partial_figure_transition" or section_type == "pre_chorus":
        return "crosses through the frame or turns at the curb so the next beat has visible direction change; do not default to a static centered portrait"
    if section_type == "chorus" or story_function == "release":
        return "moves forward into hook release with a clear step, turn, or shoulder-line change while staying solo; do not default to a static centered portrait"
    if section_type == "bridge":
        return "pauses at a reflective threshold, then turns away from the previous direction with inward restraint; do not default to a static centered portrait"
    if section_type == "outro" or story_function == "payoff":
        return "walks away or turns away into the afterglow so the ending resolves as a changed state; do not default to a static centered portrait"
    return _fallback_story_action_grammar(shot, sequence_index=sequence_index, concept_cue=concept_cue)



def _concept_action_cue(concept_text: str) -> str:
    text = str(concept_text or "").lower()
    cues: list[str] = []
    if any(token in text for token in ("desert", "dune", "sand")):
        cues.append("desert dune space")
    if any(token in text for token in ("radio", "tower", "antenna", "signal")):
        cues.append("radio signal motif")
    if any(token in text for token in ("sunrise", "dawn")):
        cues.append("sunrise horizon light")
    if any(token in text for token in ("rain", "wet")):
        cues.append("rain reflection texture")
    if any(token in text for token in ("neon", "city", "night")):
        cues.append("night-city light")
    return "; ".join(dict.fromkeys(cues)) if cues else "concept-specific visual motif"



def _fallback_story_action_grammar(shot: dict, *, sequence_index: int, concept_cue: str = "concept space") -> str:
    framing_intent = str(shot.get("framing_intent", "")).strip().lower()
    if framing_intent in {"establishing_wide", "release_wide"} or sequence_index % 3 == 0:
        return f"uses off-center walking direction and readable {concept_cue} depth to advance the beat; do not default to a static centered portrait"
    if sequence_index % 3 == 1:
        return "uses a glance, hand, sign, or reflection detail as the action cue; do not default to a static centered portrait"
    return "uses a side angle, over-shoulder turn, or walking-away beat to change silhouette; do not default to a static centered portrait"



def _thread_shot_relation_contracts(shot_plan: list[dict], *, style_name: str = "") -> None:
    previous_shot: dict | None = None
    normalized_style = str(style_name or "").strip()
    for shot in shot_plan:
        if not isinstance(shot, dict):
            continue
        if previous_shot is None:
            shot["shot_relation_contract"] = {
                "relation_to_previous_shot": "sequence opener",
                "camera_distance_progression": "set baseline distance",
                "same_block_vs_new_block": _opening_block_baseline(normalized_style),
                "emotional_delta": _opening_emotional_delta(normalized_style, shot),
            }
        else:
            shot["shot_relation_contract"] = {
                "relation_to_previous_shot": "continue same protagonist and world from previous shot",
                "camera_distance_progression": _camera_distance_progression(shot),
                "same_block_vs_new_block": _same_block_vs_new_block(shot, previous_shot, style_name=normalized_style),
                "emotional_delta": _emotional_delta(shot, style_name=normalized_style),
            }
        previous_shot = shot


def _opening_block_baseline(style_name: str) -> str:
    if style_name == "idol_pop":
        return "stage-ready city baseline"
    return "same block baseline"


def _opening_emotional_delta(style_name: str, shot: dict | None = None) -> str:
    world_anchor = str(shot.get("world_anchor", "")).strip().lower() if isinstance(shot, dict) else ""
    if "desert" in world_anchor and any(token in world_anchor for token in ("radio", "signal", "tower")):
        return "establish desert radio sunrise baseline"
    if style_name == "idol_pop":
        return "establish bright performance-night baseline"
    return "establish lonely night-world baseline"


def _camera_distance_progression(shot: dict) -> str:

    framing_intent = str(shot.get("framing_intent", "")).strip()
    return {
        "establishing_wide": "hold or widen from previous shot",
        "hero_medium": "move closer than previous shot",
        "connective_medium": "shift laterally while keeping distance readable",
        "performance_medium": "move into performance distance",
        "release_wide": "step wider for release",
    }.get(framing_intent, "adjust distance without breaking continuity")



def _same_block_vs_new_block(current_shot: dict, previous_shot: dict, *, style_name: str = "") -> str:
    current_section = str(current_shot.get("section_type", "")).strip()
    previous_section = str(previous_shot.get("section_type", "")).strip()
    if style_name == "idol_pop" and current_section == previous_section:
        return "same stage lane, new move"
    if current_section == previous_section:
        return "same block, new angle"
    return "same block, evolved staging"



def _emotional_delta(shot: dict, *, style_name: str = "") -> str:
    section_type = str(shot.get("section_type", "")).strip().lower()
    if style_name == "idol_pop":
        return {
            "chorus": "open into crowd-ready hook lift without losing world continuity",
            "bridge": "tighten focus before the next performance release",
            "outro": "resolve into bright afterglow on the same city stage",
        }.get(section_type, "increase performer confidence without losing world continuity")
    return {
        "chorus": "open into hook release without changing world",
        "bridge": "turn inward without changing world",
        "outro": "resolve into afterglow on the same block",
    }.get(section_type, "increase intimacy without changing world")
