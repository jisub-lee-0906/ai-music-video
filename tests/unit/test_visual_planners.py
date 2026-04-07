from ai_mv.core.stages.wan_interpolation import build_wan_plan
from ai_mv.engines.director_plan.planner import build_direction_plan
from ai_mv.engines.render_plan.planner import build_prompt_plan
from ai_mv.engines.scene_plan.planner import build_scene_outline


def _config() -> dict:
    return {
        "brief": "director_brief_example",
        "prompt": "비 오는 도시의 밤을 걸으며 끝난 관계를 곱씹는 노래",
        "genre": "synth pop",
        "voice": "solo female, airy and emotional",
        "language": "ko",
        "visual_concept": "grounded cinematic night-world",
        "locations": ["dim late-night diner", "wet city street at night", "concrete rooftop at dawn"],
        "props": ["worn notebook", "half-empty coffee mug", "studio headphones"],
        "video": {"target": "1920x1080@24"},
        "render": {"wan_safe_max_gap_sec": 4.0, "wan_max_frames": 40},
    }


def _payload() -> dict:
    return {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "lines": [{"line_index": 1, "text": "젖은 창가에 네 얼굴이 번져"}],
                    "lyric_beats": [
                        {
                            "beat_id": "verse1_b1",
                            "line_refs": [1],
                            "literal_image": "Rain beads on a diner window and a half-empty coffee mug on the table",
                            "visible_action": "She writes in a worn notebook and looks toward the wet glass",
                            "emotional_turn": "The memory starts to come back into focus",
                            "continuity_anchor": "worn notebook and half-empty coffee mug",
                            "payoff_role": "setup",
                            "start_sec": 0.0,
                            "end_sec": 3.0,
                        }
                    ],
                },
                {
                    "section_name": "Chorus",
                    "section_label": "Chorus",
                    "lines": [{"line_index": 1, "text": "비 내린 거리 끝에서 널 또 되감아"}],
                    "lyric_beats": [
                        {
                            "beat_id": "chorus_b1",
                            "line_refs": [1],
                            "literal_image": "Wet asphalt and blurred headlights stretching across a dark intersection",
                            "visible_action": "She crosses the rainy street with the notebook held close",
                            "emotional_turn": "The feeling opens wider and turns more direct",
                            "continuity_anchor": "worn notebook and wet asphalt",
                            "payoff_role": "release",
                            "start_sec": 3.0,
                            "end_sec": 6.0,
                        }
                    ],
                },
            ]
        }
    }


def test_storyboard_chain_uses_minimal_ref_fields():
    scene = build_scene_outline(_config(), _payload())
    direction = build_direction_plan(_config(), {**_payload(), "scene_outline": scene})
    first = direction["shot_packages"][0]
    assert first["place"] == "dim late-night diner"
    assert "writing in a worn notebook" in first["action"].lower()
    assert "worn notebook" in first["carry"].lower()
    assert first["shot_function"] == "setup"
    assert first["framing"]

    prompt = build_prompt_plan(_config(), {**_payload(), "direction_plan": direction})
    first_ref = prompt["ref_items"][0]
    assert first_ref["place"] == "dim late-night diner"
    assert first_ref["action"]
    assert first_ref["carry"]
    assert first_ref["framing"]
    assert first_ref["ref_prompt_text"].endswith("Keep the face.")
    assert len(prompt["wan_items"]) == 1
    assert prompt["wan_items"][0]["bridge_action"]
    assert prompt["wan_items"][0]["wan_positive_prompt_text"]


def test_scene_outline_splits_long_beats_by_wan_safe_duration():
    config = _config()
    payload = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "lyric_beats": [
                        {
                            "beat_id": "verse1_b1",
                            "line_refs": [1],
                            "literal_image": "Wet street",
                            "visible_action": "She walks forward",
                            "emotional_turn": "The thought lingers",
                            "continuity_anchor": "wet street",
                            "payoff_role": "carry",
                            "start_sec": 0.0,
                            "end_sec": 9.0,
                        },
                    ],
                }
            ]
        }
    }
    scene = build_scene_outline(config, payload)
    assert [row["shot_id"] for row in scene["shot_packages"]] == ["verse1_b1_s1", "verse1_b1_s2"]
    assert max(float(row["duration_sec"]) for row in scene["shot_packages"]) <= 5.0


def test_wan_plan_uses_adjacent_ref_pairs():
    scene = build_scene_outline(_config(), _payload())
    direction = build_direction_plan(_config(), {**_payload(), "scene_outline": scene})
    prompt = build_prompt_plan(_config(), {**_payload(), "direction_plan": direction})
    payload = {
        **_payload(),
        "prompt_plan": prompt,
        "flux2_ref_images": [
            {"shot_id": "verse1_b1", "start": "start1.png", "end": "end1.png"},
            {"shot_id": "chorus_b1", "start": "start2.png", "end": "end2.png"},
        ],
    }
    wan = build_wan_plan(_config(), payload)
    assert len(wan["clips"]) == 1
    assert wan["clips"][0]["start"] == "end1.png"
    assert wan["clips"][0]["end"] == "end2.png"
    assert wan["clips"][0]["positive_prompt"]
