from ai_mv.engines.seedance_v2_scene_plan.planner import build_scene_plan_v2
from ai_mv.engines.seedance_v2_director_plan.planner import build_director_plan_v2
from ai_mv.engines.seedance_v2_render_plan.planner import build_render_plan_v2
from ai_mv.core.stages.wan_interpolation_v2 import build_wan_plan_v2


def _config() -> dict:
    return {
        "brief": "director_brief_example",
        "audio": {"language": "ko", "brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {"brief": "Visual brief", "negative": "Visual negative"},
        "mv": {
            "story_world": "Story world",
            "action_vocabulary": "Actions",
            "payoff_style": "Payoff style",
            "outro_feel": "Outro feel",
            "avoid": "Avoid list",
        },
        "character": {"identity_core": "same heroine", "identity_hooks": ["red ribbon"]},
        "director": {
            "target_style": "anime style",
            "world_core": "night world",
            "camera_bias": "readable anime framing",
            "lighting_bias": "sign glow",
            "shadow_bias": "cel shaded shadows",
            "motion_bias": "stable 2d anime motion",
            "transition_bias": "previous-end continuity",
            "motif_families": ["train window", "ticket gate"],
        },
    }


def _payload() -> dict:
    return {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "lyric_beats": [
                        {
                            "beat_id": "B001",
                            "line_refs": [1],
                            "literal_image": "train window reflection",
                            "visible_action": "she presses her hand to the glass",
                        },
                        {
                            "beat_id": "B002",
                            "line_refs": [2],
                            "literal_image": "ticket gate glow",
                            "visible_action": "she steps through the gate",
                        },
                    ],
                }
            ]
        }
    }


def test_scene_director_render_plan_v2_chain():
    scene = build_scene_plan_v2(_config(), _payload())
    assert len(scene["shot_packages"]) == 2
    assert scene["shot_packages"][0]["beat_refs"] == ["B001"]
    assert scene["shot_packages"][0]["visual_role"] == "opening_frame"
    first_location = scene["shot_packages"][0]["environment_anchor"]
    assert first_location
    assert scene["shot_packages"][0]["location_description"] == first_location
    assert "camera" not in first_location.lower()
    assert "frame" not in first_location.lower()
    assert scene["motif_progression"][0]["environment_anchor"] == first_location

    director = build_director_plan_v2(_config(), {**_payload(), "scene_plan_v2": scene})
    assert "camera_intent" in director["shot_packages"][0]
    assert "motion_intent" in director["shot_packages"][0]
    assert director["shot_packages"][0]["ref_archetype"]
    assert director["shot_packages"][0]["ref_archetype_contract"]
    assert "Variant note" in director["shot_packages"][0]["ref_archetype_contract"] or director["shot_packages"][0]["ref_archetype_contract"]
    assert director["shot_packages"][0]["visual_role"] == "opening_frame"
    assert "ref_start_continuity_line" not in director["shot_packages"][0]
    assert "ref_start_camera_line" not in director["shot_packages"][0]

    render = build_render_plan_v2(_config(), {**_payload(), "director_plan_v2": director})
    assert render["master_anchor"]["render_strategy"] == "tti_master"
    assert render["shot_packages"][0]["render_strategy"] == "ref_pair"
    assert render["wan_chain"][0]["start_source"] == "ref_start"
    assert render["wan_chain"][1]["start_source"] == "previous_end"
    assert render["wan_chain"][0]["environment_anchor"]
    assert render["wan_chain"][0]["location_description"]
    assert render["wan_chain"][0]["duration_sec"] > 0
    assert "press" in render["wan_chain"][0]["visible_action"]
    assert "glass" in render["wan_chain"][0]["visible_action"]
    assert render["wan_chain"][0]["wan_action_line"]
    assert render["shot_packages"][0]["ref_prompt_clauses"]["subject_intro"]
    assert render["shot_packages"][0]["ref_prompt_clauses"]["ref_archetype"]
    assert render["shot_packages"][0]["ref_prompt_clauses"]["ref_archetype_contract"]
    assert render["shot_packages"][0]["ref_start_prompt_text"]
    assert render["shot_packages"][0]["ref_end_prompt_text"]
    assert render["wan_chain"][0]["wan_prompt_clauses"]["bridge_action"]
    assert render["wan_chain"][0]["wan_prompt_clauses"]["wan_transition_family"]
    assert render["wan_chain"][0]["wan_prompt_clauses"]["wan_transition_contract"]
    assert render["wan_chain"][0]["wan_positive_prompt_text"]


def test_scene_plan_v2_motif_assignment_is_section_local_and_stable():
    payload_a = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "lyric_beats": [{"beat_id": "V1_B1", "line_refs": [1]}],
                },
                {
                    "section_name": "Chorus",
                    "section_label": "Chorus",
                    "lyric_beats": [
                        {"beat_id": "C_B1", "line_refs": [1]},
                        {"beat_id": "C_B2", "line_refs": [2]},
                        {"beat_id": "C_B3", "line_refs": [3]},
                        {"beat_id": "C_B4", "line_refs": [4]},
                    ],
                },
            ]
        }
    }
    payload_b = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "lyric_beats": [
                        {"beat_id": "V1_B1", "line_refs": [1]},
                        {"beat_id": "V1_B2", "line_refs": [2]},
                    ],
                },
                {
                    "section_name": "Chorus",
                    "section_label": "Chorus",
                    "lyric_beats": [
                        {"beat_id": "C_B1", "line_refs": [1]},
                        {"beat_id": "C_B2", "line_refs": [2]},
                        {"beat_id": "C_B3", "line_refs": [3]},
                        {"beat_id": "C_B4", "line_refs": [4]},
                    ],
                },
            ]
        }
    }
    scene_a = build_scene_plan_v2(_config(), payload_a)
    scene_b = build_scene_plan_v2(_config(), payload_b)
    chorus_a = {row["shot_id"]: row["motif_family"] for row in scene_a["shot_packages"] if row["shot_id"].startswith("C_")}
    chorus_b = {row["shot_id"]: row["motif_family"] for row in scene_b["shot_packages"] if row["shot_id"].startswith("C_")}
    assert chorus_a == chorus_b


def test_scene_plan_v2_smooths_high_cost_adjacent_family_jumps():
    config = _config()
    config["director"]["motif_families"] = [
        "train window",
        "ticket gate",
        "curb reflection",
        "puddle ring",
        "platform sign glow",
        "stair landing",
    ]
    payload = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Final Chorus",
                    "section_label": "Final Chorus",
                    "lyric_beats": [
                        {"beat_id": "FC_B1", "line_refs": [1]},
                        {"beat_id": "FC_B2", "line_refs": [2]},
                        {"beat_id": "FC_B3", "line_refs": [3]},
                        {"beat_id": "FC_B4", "line_refs": [4]},
                    ],
                }
            ]
        }
    }
    scene = build_scene_plan_v2(config, payload)
    families = [row["environment_family"] for row in scene["shot_packages"]]
    adjacent_pairs = list(zip(families, families[1:]))
    assert "transit_side_edge" not in families
    assert ("vertical_path", "transit_side_edge") not in adjacent_pairs
    assert ("transit_side_edge", "vertical_path") not in adjacent_pairs


def test_scene_plan_v2_open_world_prefers_connected_exterior_families_over_train_window():
    config = _config()
    config["director"]["motif_families"] = [
        "train window",
        "ticket gate",
        "curb reflection",
        "puddle ring",
        "platform sign glow",
    ]
    payload = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Chorus",
                    "section_label": "Chorus",
                    "lyric_beats": [
                        {"beat_id": "C_B1", "line_refs": [1]},
                        {"beat_id": "C_B2", "line_refs": [2]},
                        {"beat_id": "C_B3", "line_refs": [3]},
                    ],
                }
            ]
        }
    }
    scene = build_scene_plan_v2(config, payload)
    families = [row["environment_family"] for row in scene["shot_packages"]]
    assert "transit_side_edge" not in families


def test_director_plan_v2_abstracts_carryover_when_family_changes():
    config = _config()
    config["director"]["motif_families"] = [
        "ticket gate",
        "curb reflection",
        "puddle ring",
        "platform sign glow",
    ]
    payload = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Final Chorus",
                    "section_label": "Final Chorus",
                    "lyric_beats": [
                        {"beat_id": "FC_B1", "line_refs": [1]},
                        {"beat_id": "FC_B2", "line_refs": [2]},
                        {"beat_id": "FC_B3", "line_refs": [3]},
                        {"beat_id": "FC_B4", "line_refs": [4]},
                    ],
                }
            ]
        }
    }
    scene = build_scene_plan_v2(config, payload)
    director = build_director_plan_v2(config, {**payload, "scene_plan_v2": scene})
    shots = {row["shot_id"]: row for row in director["shot_packages"]}
    b3 = shots["FC_B3"]
    assert b3["ref_start_action_line"].startswith("She ")
    assert b3["ref_end_action_line"].startswith("She ")
    assert b3["ref_end_action_line"] != b3["ref_start_action_line"]
    assert "camera" not in b3["ref_end_action_line"].lower()
    assert "frame" not in b3["ref_end_action_line"].lower()


def test_scene_plan_v2_final_chorus_uses_progressive_roles_and_only_last_payoff_is_wide():
    config = _config()
    payload = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "chorus",
                    "section_label": "Final Chorus",
                    "lyric_beats": [
                        {"beat_id": "FC_B1", "line_refs": [1]},
                        {"beat_id": "FC_B2", "line_refs": [2]},
                        {"beat_id": "FC_B3", "line_refs": [3]},
                        {"beat_id": "FC_B4", "line_refs": [4]},
                    ],
                }
            ]
        }
    }
    scene = build_scene_plan_v2(config, payload)
    rows = {row["shot_id"]: row for row in scene["shot_packages"]}
    assert rows["FC_B1"]["visual_role"] == "opening_frame"
    assert rows["FC_B2"]["visual_role"] == "continuity_frame"
    assert rows["FC_B3"]["visual_role"] == "handoff_frame"
    assert rows["FC_B4"]["visual_role"] == "payoff_frame"
    assert rows["FC_B2"]["camera_distance_band"] == "medium_wide"
    assert rows["FC_B3"]["camera_distance_band"] == "medium_wide"
    assert rows["FC_B4"]["camera_distance_band"] == "wide_full_figure"


def test_wan_plan_v2_uses_duration_aware_natural_prompt_lines():
    config = {
        **_config(),
        "video": {"target": "1920x1080@24"},
    }
    scene = build_scene_plan_v2(config, _payload())
    director = build_director_plan_v2(config, {**_payload(), "scene_plan_v2": scene})
    render = build_render_plan_v2(config, {**_payload(), "director_plan_v2": director})
    payload = {
        **_payload(),
        "render_plan_v2": render,
        "clip_routes": [
            {
                "shot_id": "B001",
                "duration_sec": 0.8,
                "section_name": "Verse 1",
                "section_label": "Verse 1",
                "clip_index": 1,
                "clip_count": 2,
                "timeline_index": 1,
            },
            {
                "shot_id": "B002",
                "duration_sec": 2.4,
                "section_name": "Verse 1",
                "section_label": "Verse 1",
                "clip_index": 2,
                "clip_count": 2,
                "timeline_index": 2,
            },
        ],
        "flux2_ref_images": [
            {"shot_id": "B001", "start": "start.png", "end": "end1.png"},
            {"shot_id": "B002", "start": "end1.png", "end": "end2.png"},
        ],
    }
    wan = build_wan_plan_v2(config, payload)
    assert "Use the provided first and last keyframes" not in wan["clips"][0]["positive_prompt"]
    assert "same space" not in wan["clips"][0]["positive_prompt"]
    assert "same space" not in wan["clips"][1]["positive_prompt"]
    assert "The same location light stays grounded" not in wan["clips"][0]["positive_prompt"]


def test_wan_negative_prompt_avoids_camera_language():
    config = {
        **_config(),
        "video": {"target": "1920x1080@24"},
    }
    wan = build_wan_plan_v2(
        config,
        {
            "render_plan_v2": {
                "wan_chain": [
                    {
                        "shot_id": "B001",
                        "location_description": "a station threshold at night beside a convenience store window",
                    }
                ]
            },
            "flux2_ref_images": [{"shot_id": "B001", "start": "start.png", "end": "end.png"}],
            "clip_routes": [{"shot_id": "B001", "duration_sec": 2.0, "section_name": "Intro", "section_label": "Intro"}],
        },
    )
    assert "camera" not in wan["clips"][0]["negative_prompt"].lower()
