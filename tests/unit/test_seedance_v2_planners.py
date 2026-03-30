from ai_mv.engines.seedance_v2_scene_plan.planner import build_scene_plan_v2
from ai_mv.engines.seedance_v2_director_plan.planner import build_director_plan_v2
from ai_mv.engines.seedance_v2_render_plan.planner import build_render_plan_v2


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

    director = build_director_plan_v2(_config(), {**_payload(), "scene_plan_v2": scene})
    assert director["shot_packages"][0]["camera_intent"]
    assert director["shot_packages"][0]["motion_intent"]
    assert director["shot_packages"][0]["visual_role"] == "opening_frame"

    render = build_render_plan_v2(_config(), {**_payload(), "director_plan_v2": director})
    assert render["master_anchor"]["render_strategy"] == "tti_master"
    assert render["shot_packages"][0]["render_strategy"] == "ref_pair"
    assert render["wan_chain"][0]["start_source"] == "ref_start"
    assert render["wan_chain"][1]["start_source"] == "previous_end"


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
