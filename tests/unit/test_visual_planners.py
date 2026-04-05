from ai_mv.core.stages.wan_interpolation import build_wan_plan
from ai_mv.core.stages.backend_preview import build_backend_preview
from ai_mv.engines.director_plan.planner import _infer_ref_archetype, _infer_ref_archetype_variant, _planner_primary_surface, build_direction_plan
from ai_mv.engines.render_plan.planner import build_prompt_plan
from ai_mv.engines.scene_plan.planner import build_scene_outline


def _config() -> dict:
    return {
        "brief": "director_brief_example",
        "audio": {"language": "ko", "brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {
            "story_premise": "A heroine moves through one connected station-side night world.",
            "world_rules": "The world stays physically connected, readable, and grounded.",
            "heroine_arc": "She gains direction through forward movement.",
            "forbidden_story_moves": "Avoid dream resets, symbolic tableaux, and extra characters.",
            "section_story_roles": {
                "Verse 1": "She moves deeper into the same world.",
                "Bridge": "She compresses briefly without fully stopping, then regains direction.",
                "Final Chorus": "She crosses into the widest forward release.",
            },
            "section_event_scripts": {
                "Verse 1": [
                    "She steps onto the outside sidewalk route.",
                    "She keeps the sidewalk-side route alive.",
                ],
                "Bridge": [
                    "She compresses into a shorter step.",
                ],
            },
        },
        "character": {
            "identity_core": "same heroine",
            "identity_hooks": ["with a high ponytail"],
            "anchor_wardrobe_guidance": "polished off-duty idol styling",
            "anchor_avoid": "avoid costume styling",
        },
        "video": {"target": "1920x1080@24"},
    }


def _payload() -> dict:
    return {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "lyric_beats": [
                        {"beat_id": "verse1_b1", "line_refs": [1]},
                        {"beat_id": "verse1_b2", "line_refs": [2]},
                    ],
                },
                {
                    "section_name": "Bridge",
                    "section_label": "Bridge",
                    "lyric_beats": [
                        {"beat_id": "bridge_b1", "line_refs": [3]},
                    ],
                },
            ]
        }
    }


def test_scene_direction_prompt_chain():
    scene = build_scene_outline(_config(), _payload())
    assert len(scene["shot_packages"]) == 3
    assert scene["shot_packages"][0]["story_function"] == "entry"
    assert scene["shot_packages"][0]["story_event"] == "She steps onto the outside sidewalk route."
    assert scene["shot_packages"][1]["story_function"] in {"handoff", "continuation"}
    assert scene["section_progression"][0]["world_zone"]

    direction = build_direction_plan(_config(), {**_payload(), "scene_outline": scene})
    first = direction["shot_packages"][0]
    assert first["shot_function"]
    assert first["ref_archetype"]
    assert first["primary_surface"]
    assert first["dominant_action"]
    assert first["story_event"]
    assert first["story_visual_intent"]
    assert first["blocking_role"]
    assert first["entry_side"]
    assert first["travel_axis"]
    assert first["frame_bias"]
    assert first["arrival_side"]
    assert first["camera_relation"]
    assert first["selected_prompt_shape"]
    assert first["applied_grammar_source"]

    prompt = build_prompt_plan(_config(), {**_payload(), "direction_plan": direction})
    assert prompt["master_anchor"]["render_strategy"] == "tti_master"
    assert len(prompt["ref_items"]) == 3
    assert len(prompt["wan_items"]) == 2
    assert prompt["wan_items"][0]["start_ref_shot_id"] == "verse1_b1"
    assert prompt["wan_items"][0]["end_ref_shot_id"] == "verse1_b2"
    assert prompt["ref_items"][0]["story_event"] == "She steps onto the outside sidewalk route."
    assert prompt["ref_items"][0]["blocking_role"]
    assert prompt["ref_items"][0]["entry_side"]
    assert prompt["ref_items"][0]["travel_axis"]
    assert prompt["ref_items"][0]["ref_prompt_atoms"]["subject_intro"]
    assert prompt["ref_items"][0]["ref_prompt_contract"]
    assert prompt["ref_items"][0]["ref_start_prompt_text"]
    assert prompt["ref_items"][0]["ref_end_prompt_text"]
    assert prompt["wan_items"][0]["wan_positive_prompt_text"]
    assert prompt["master_anchor"]["applied_global_prompt_rules"]
    assert prompt["master_anchor"]["applied_archetype_rules"]
    assert prompt["ref_items"][0]["applied_global_prompt_rules"]
    assert prompt["ref_items"][0]["applied_archetype_rules"]
    assert prompt["ref_items"][0]["rule_precedence_summary"]
    assert "flux2_prompting.ref" in " ".join(prompt["ref_items"][0]["applied_global_prompt_rules"])


def test_director_archetype_prefers_golden_structure_override():
    shot = {
        "story_function": "payoff",
        "section_label": "Final Chorus",
        "world_zone": "open_peak",
    }
    guidance = {
        "ref_archetype": "curb_crossing",
    }
    assert _infer_ref_archetype(shot, guidance) == "curb_crossing"


def test_director_archetype_classifies_bridge_pressure_as_platform_edge():
    shot = {
        "section_label": "Bridge",
        "story_function": "pressure",
        "world_zone": "compression",
    }
    assert _infer_ref_archetype(shot) == "platform_edge"
    assert _infer_ref_archetype_variant(shot, "platform_edge") == "bridge_motion"


def test_director_open_peak_handoff_uses_curb_crossing_release_family():
    shot = {
        "section_label": "Final Chorus",
        "story_function": "handoff",
        "world_zone": "open_peak",
    }
    assert _infer_ref_archetype(shot) == "curb_crossing"
    assert _infer_ref_archetype_variant(shot, "curb_crossing") == ""


def test_director_primary_surface_uses_archetype_priority():
    shot = {
        "story_function": "pressure",
        "archetype_variant": "bridge_motion",
    }
    assert _planner_primary_surface(shot, "platform_edge") == "wet platform edge"


def test_director_story_function_can_override_surface_for_route_readability():
    shot = {
        "story_function": "handoff",
        "archetype_variant": "",
    }
    assert _planner_primary_surface(shot, "sidewalk_continuation") == "wet sidewalk edge"


def test_direction_plan_uses_story_event_to_differentiate_same_sidewalk_family():
    config = _config()
    payload = {
        "scene_outline": {
            "shot_packages": [
                {
                    "shot_id": "verse1_b1",
                    "section_label": "Verse 1",
                    "story_function": "entry",
                    "story_goal": "Verse 1 goal",
                    "story_event": "She steps onto the sidewalk route outside the station and lets the path claim her line.",
                    "world_zone": "narrow_route",
                    "story_visual_intent": "Entry event.",
                    "why": "v1",
                },
                {
                    "shot_id": "verse2_b1",
                    "section_label": "Verse 2",
                    "story_function": "entry",
                    "story_goal": "Verse 2 goal",
                    "story_event": "She re-enters the same route from a slightly changed street-side angle without breaking continuity.",
                    "world_zone": "transit_route",
                    "story_visual_intent": "Entry event.",
                    "why": "v2",
                },
            ]
        }
    }
    direction = build_direction_plan(config, payload)
    first, second = direction["shot_packages"]
    assert first["ref_archetype"] == "sidewalk_continuation"
    assert second["ref_archetype"] == "sidewalk_continuation"
    assert first["dominant_action"] != second["dominant_action"]
    assert first["entry_side"] != second["entry_side"]
    assert first["travel_axis"] != second["travel_axis"]
    assert "road-side edge" in second["dominant_action"].lower()


def test_direction_plan_assigns_distinct_blocking_for_crosswalk_release_sequence():
    config = _config()
    payload = {
        "scene_outline": {
            "shot_packages": [
                {
                    "shot_id": "finalchorus_b1",
                    "section_label": "Final Chorus",
                    "story_function": "entry",
                    "story_goal": "Start release",
                    "story_event": "She starts a visible crossing event instead of another neutral walk.",
                    "world_zone": "open_peak",
                    "story_visual_intent": "Left-edge entry.",
                    "why": "b1",
                },
                {
                    "shot_id": "finalchorus_b2",
                    "section_label": "Final Chorus",
                    "story_function": "continuation",
                    "story_goal": "Keep release alive",
                    "story_event": "She keeps the crossing alive through the center-right lane without falling back to neutral center walking.",
                    "world_zone": "open_peak",
                    "story_visual_intent": "Carry.",
                    "why": "b2",
                },
                {
                    "shot_id": "finalchorus_b3",
                    "section_label": "Final Chorus",
                    "story_function": "handoff",
                    "story_goal": "Hand off release",
                    "story_event": "She carries the crossing into a readable next-state handoff along the right edge.",
                    "world_zone": "open_peak",
                    "story_visual_intent": "Handoff.",
                    "why": "b3",
                },
                {
                    "shot_id": "finalchorus_b4",
                    "section_label": "Final Chorus",
                    "story_function": "payoff",
                    "story_goal": "Release payoff",
                    "story_event": "She leaves the crossing behind in a wider forward departure.",
                    "world_zone": "open_peak",
                    "story_visual_intent": "Walk-away payoff.",
                    "why": "b4",
                },
            ]
        }
    }
    direction = build_direction_plan(config, payload)
    b1, b2, b3, b4 = direction["shot_packages"]
    assert b1["blocking_role"] == "edge_entry"
    assert b1["entry_side"] == "left"
    assert b2["blocking_role"] == "center_carry"
    assert b2["frame_bias"] == "off_center"
    assert b3["blocking_role"] == "side_handoff"
    assert b3["arrival_side"] == "right"
    assert b4["blocking_role"] == "walk_away"
    assert b4["travel_axis"] == "away"
    assert "right edge" in b3["dominant_action"].lower()
    assert "already formed" in b3["continuity_delta"].lower()
    assert "walks away" in b4["dominant_action"].lower()
    assert b3["content_trace"] == ""
    assert b4["content_trace"] == ""


def test_direction_plan_moves_sidewalk_route_detail_out_of_trace_and_into_action():
    config = _config()
    payload = {
        "scene_outline": {
            "shot_packages": [
                {
                    "shot_id": "verse2_b1",
                    "section_label": "Verse 2",
                    "story_function": "entry",
                    "story_goal": "Route variation",
                    "story_event": "She re-enters the same route from a slightly changed street-side angle without breaking continuity.",
                    "world_zone": "transit_route",
                    "story_visual_intent": "Re-entry.",
                    "why": "v2_b1",
                },
                {
                    "shot_id": "verse2_b2",
                    "section_label": "Verse 2",
                    "story_function": "handoff",
                    "story_goal": "Route variation",
                    "story_event": "She keeps the sidewalk-side carry alive through the same connected block.",
                    "world_zone": "transit_route",
                    "story_visual_intent": "Connected carry.",
                    "why": "v2_b2",
                },
            ]
        }
    }
    direction = build_direction_plan(config, payload)
    b1, b2 = direction["shot_packages"]
    assert "road-side edge" in b1["dominant_action"].lower()
    assert b1["content_trace"] == ""
    assert "road clearly" in b2["continuity_delta"].lower() or "road still" in b2["continuity_delta"].lower()
    assert b2["content_trace"] == ""


def test_director_edge_handoff_uses_threshold_passage_exit_variant():
    shot = {
        "section_label": "Pre-Chorus",
        "story_function": "handoff",
        "world_zone": "edge",
    }
    assert _infer_ref_archetype(shot) == "threshold_crossing"
    assert _infer_ref_archetype_variant(shot, "threshold_crossing") == "passage_exit"


def test_wan_plan_uses_adjacent_ref_pairs():
    scene = build_scene_outline(_config(), _payload())
    direction = build_direction_plan(_config(), {**_payload(), "scene_outline": scene})
    prompt = build_prompt_plan(_config(), {**_payload(), "direction_plan": direction})
    payload = {
        **_payload(),
        "prompt_plan": prompt,
        "flux2_ref_images": [
            {"shot_id": "verse1_b1", "start": "start1.png", "end": "end1.png"},
            {"shot_id": "verse1_b2", "start": "start2.png", "end": "end2.png"},
            {"shot_id": "bridge_b1", "start": "start3.png", "end": "end3.png"},
        ],
    }
    wan = build_wan_plan(_config(), payload)
    assert len(wan["clips"]) == 2
    assert wan["clips"][0]["start"] == "end1.png"
    assert wan["clips"][0]["end"] == "end2.png"
    assert wan["clips"][1]["start"] == "end2.png"
    assert wan["clips"][1]["end"] == "end3.png"


def test_backend_preview_exposes_prompt_rule_trace():
    scene = build_scene_outline(_config(), _payload())
    direction = build_direction_plan(_config(), {**_payload(), "scene_outline": scene})
    prompt = build_prompt_plan(_config(), {**_payload(), "direction_plan": direction})
    preview = build_backend_preview(_config(), {"prompt_plan": prompt})
    ref_row = preview["ref_adapter"][0]["raw_prompt_clauses"]
    wan_row = preview["wan_adapter"][0]["raw_prompt_clauses"]
    assert ref_row["applied_global_prompt_rules"]
    assert ref_row["applied_archetype_rules"]
    assert ref_row["story_event"]
    assert ref_row["blocking_role"]
    assert ref_row["entry_side"]
    assert "rule_precedence_summary" in ref_row
    assert "applied_golden_structure" in ref_row
    assert wan_row["applied_global_prompt_rules"]
    assert wan_row["applied_archetype_rules"]
    assert wan_row["blocking_role"]
