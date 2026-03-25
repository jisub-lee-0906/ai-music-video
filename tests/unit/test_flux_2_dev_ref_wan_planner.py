from ai_mv.engines.flux_2_dev_ref.planner import build_flux2_ref_plan
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan, _compose_positive_prompt
import ai_mv.engines.flux_2_dev_ref.planner as flux2_ref_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_flux2_ref_plan_uses_llm_output_verbatim(monkeypatch):
    def fake_generate_structured(config, prompt, schema, attempts=1):
        return {
            "items": [
                {
                    "shot_id": "a",
                    "prompt_text": "The same anime girl, now turns sharply to the left. Tight profile shot. Flat cel shading, thick clean outlines.",
                    "subject_clause": "The same anime girl",
                    "action_clause": "now turns sharply to the left",
                    "camera_clause": "Tight profile shot",
                    "continuity_clause": "Flat cel shading, thick clean outlines",
                },
                {
                    "shot_id": "b",
                    "prompt_text": "The same anime girl, now raises the guitar above her shoulder. Extreme low-angle dynamic shot. Flat cel shading, thick clean outlines.",
                    "subject_clause": "The same anime girl",
                    "action_clause": "now raises the guitar above her shoulder",
                    "camera_clause": "Extreme low-angle dynamic shot",
                    "continuity_clause": "Flat cel shading, thick clean outlines",
                },
            ]
        }

    monkeypatch.setattr(flux2_ref_planner, "generate_structured", fake_generate_structured)
    payload = {"clip_routes": [_route("a", True), _route("b", True)], "visual_story_bible": _story_bible()}
    out = build_flux2_ref_plan({}, payload)
    assert [x["shot_id"] for x in out["items"]] == ["a", "b"]
    assert out["items"][0]["prompt_text"] == fake_generate_structured({}, "", {}, 1)["items"][0]["prompt_text"]
    assert out["items"][0]["camera_clause"] == "Tight profile shot"


def test_flux2_ref_plan_empty_when_no_ref_routes():
    out = build_flux2_ref_plan({}, {"clip_routes": [], "visual_story_bible": _story_bible()})
    assert out["items"] == []


def test_flux2_ref_prompt_text_matches_short_continuity_formula(monkeypatch):
    expected = "The same anime girl, now fiercely smashing the guitar onto the ground, bending her knees. Extreme low-angle dynamic shot. Flat cel shading, thick clean outlines."

    def fake_generate_structured(config, prompt, schema, attempts=1):
        return {
            "items": [
                {
                    "shot_id": "a",
                    "prompt_text": expected,
                    "subject_clause": "The same anime girl",
                    "action_clause": "now fiercely smashing the guitar onto the ground, bending her knees",
                    "camera_clause": "Extreme low-angle dynamic shot",
                    "continuity_clause": "Flat cel shading, thick clean outlines",
                }
            ]
        }

    monkeypatch.setattr(flux2_ref_planner, "generate_structured", fake_generate_structured)
    payload = {"clip_routes": [_route("a", True)], "visual_story_bible": _story_bible()}
    out = build_flux2_ref_plan({}, payload)
    assert out["items"][0]["prompt_text"] == expected


def test_wan_plan_uses_llm_prompt_and_ref_frames(monkeypatch):
    def fake_generate_structured(config, prompt, schema, attempts=1):
        return {
            "clips": [
                {
                    "shot_id": "x",
                    "positive_prompt": "Camera crashes forward on impact. The girl swings the guitar down with extreme force. Background neon lights flicker rapidly.",
                    "negative_prompt": "3d render, photorealistic, morphing, static",
                    "subject_motion": "The girl swings the guitar down with extreme force",
                    "camera_relation": "Camera crashes forward on impact",
                    "environment_detail": "Background neon lights flicker rapidly",
                    "energy": "normal",
                }
            ]
        }

    monkeypatch.setattr(wan_planner, "generate_structured", fake_generate_structured)
    payload = {
        "clip_routes": [_route("x", True)],
        "flux2_ref_images": [_flux2_ref("x", 4.0)],
        "visual_story_bible": _story_bible(),
    }
    out = build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
    clip = out["clips"][0]
    assert clip["start"] == "s.png"
    assert clip["end"] == "e.png"
    assert clip["positive_prompt"].startswith("Camera crashes forward on impact.")


def test_wan_plan_requires_ref_frames_for_ref_routed_clip():
    payload = {
        "clip_routes": [_route("x", True)],
        "flux2_ref_images": [],
        "visual_story_bible": _story_bible(),
    }
    try:
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "missing ref-assisted clip" in str(exc)


def test_wan_planner_clip_cap_guard():
    payload = {"clip_routes": [_route("x", False, duration=6.0)], "flux2_ref_images": [_flux2_ref("x", 6.0)], "visual_story_bible": _story_bible()}
    try:
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 5.0}}, payload)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "exceeds cap" in str(exc)


def test_wan_positive_prompt_formula():
    text = _compose_positive_prompt(
        {
            "camera_relation": "Camera is completely locked off and static",
            "subject_motion": "The girl's eyes dart quickly to the left",
            "environment_detail": "The floating holographic UI elements slowly rotate clockwise",
        }
    )
    assert text == (
        "Camera is completely locked off and static. "
        "The girl's eyes dart quickly to the left. "
        "The floating holographic UI elements slowly rotate clockwise."
    )


def test_wan_plan_chains_across_section_names_when_not_explicit_reset(monkeypatch):
    def fake_generate_structured(config, prompt, schema, attempts=1):
        return {
            "clips": [
                {
                    "shot_id": "a",
                    "positive_prompt": "Camera glides left. The girl steps through the gate. Background sign lights flicker rapidly.",
                    "negative_prompt": "3d render, photorealistic, morphing, static",
                    "subject_motion": "The girl steps through the gate",
                    "camera_relation": "Camera glides left",
                    "environment_detail": "Background sign lights flicker rapidly",
                    "energy": "normal",
                },
                {
                    "shot_id": "b",
                    "positive_prompt": "Camera pushes forward. The girl turns toward the train window. Background window bands slide across the glass.",
                    "negative_prompt": "3d render, photorealistic, morphing, static",
                    "subject_motion": "The girl turns toward the train window",
                    "camera_relation": "Camera pushes forward",
                    "environment_detail": "Background window bands slide across the glass",
                    "energy": "normal",
                },
            ]
        }

    monkeypatch.setattr(wan_planner, "generate_structured", fake_generate_structured)
    payload = {
        "clip_routes": [
            _route("a", True, duration=4.0, section_name="verse_1"),
            _route("b", True, duration=4.0, section_name="chorus"),
        ],
        "flux2_ref_images": [
            _flux2_ref("a", 4.0, start="a_s.png", end="a_e.png"),
            _flux2_ref("b", 4.0, start="b_s.png", end="b_e.png"),
        ],
        "visual_story_bible": _story_bible(),
    }
    out = build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
    assert out["clips"][0]["start"] == "a_s.png"
    assert out["clips"][0]["end"] == "a_e.png"
    assert out["clips"][1]["start"] == "a_e.png"
    assert out["clips"][1]["end"] == "b_e.png"
    assert out["clips"][1]["start_source"] == "previous_end"


def test_wan_plan_breaks_chain_on_explicit_reset(monkeypatch):
    def fake_generate_structured(config, prompt, schema, attempts=1):
        return {
            "clips": [
                {
                    "shot_id": "a",
                    "positive_prompt": "Camera glides left. The girl steps through the gate. Background sign lights flicker rapidly.",
                    "negative_prompt": "3d render, photorealistic, morphing, static",
                    "subject_motion": "The girl steps through the gate",
                    "camera_relation": "Camera glides left",
                    "environment_detail": "Background sign lights flicker rapidly",
                    "energy": "normal",
                },
                {
                    "shot_id": "b",
                    "positive_prompt": "Camera pushes forward. The girl turns toward the train window. Background window bands slide across the glass.",
                    "negative_prompt": "3d render, photorealistic, morphing, static",
                    "subject_motion": "The girl turns toward the train window",
                    "camera_relation": "Camera pushes forward",
                    "environment_detail": "Background window bands slide across the glass",
                    "energy": "normal",
                },
            ]
        }

    monkeypatch.setattr(wan_planner, "generate_structured", fake_generate_structured)
    payload = {
        "clip_routes": [
            _route("a", True, duration=4.0, section_name="verse_1"),
            _route("b", True, duration=4.0, section_name="chorus", scene_change_level="reset"),
        ],
        "flux2_ref_images": [
            _flux2_ref("a", 4.0, start="a_s.png", end="a_e.png"),
            _flux2_ref("b", 4.0, start="b_s.png", end="b_e.png"),
        ],
        "visual_story_bible": _story_bible(),
    }
    out = build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
    assert out["clips"][1]["start"] == "b_s.png"
    assert out["clips"][1]["start_source"] == "ref_start"


def _flux2_ref(shot_id: str, duration: float, start: str = "s.png", end: str = "e.png") -> dict:
    return {
        "shot_id": shot_id,
        "start": start,
        "end": end,
        "duration_sec": duration,
        "section_name": "verse",
        "shot_type": "CHAR_MASTER",
        "is_chorus": False,
        "camera_language": "clean hero framing",
        "pose_delta": "small pose shift",
        "emotion": "steady confidence",
        "scene_detail": "concert light wall",
        "motion_hint": "smooth motion",
        "workflow_motion_clause": "moves through the lane and holds a steady line",
    }


def _route(shot_id: str, chorus: bool, duration: float = 4.0, section_name: str | None = None, scene_change_level: str = "evolve") -> dict:
    name = section_name or ("chorus" if chorus else "verse")
    label = "Final Chorus" if "chorus" in name else "Verse 1"
    return {
        "shot_id": shot_id,
        "lyric_beat_id": "LB02_01" if chorus else "LB01_01",
        "anchor": f"{shot_id}.png",
        "identity_anchor": f"{shot_id}.png",
        "is_chorus": chorus,
        "duration_sec": duration,
        "section_name": name,
        "section_label": label,
        "shot_type": "EMOTION_CLOSE" if chorus else "CHAR_MASTER",
        "camera_language": "clean hero framing",
        "pose_delta": "small pose shift",
        "emotion": "steady confidence",
        "scene_detail": "concert light wall",
        "motion_hint": "smooth motion",
        "workflow_motion_clause": "moves through the lane and holds a steady line",
        "space_relation": "glass stays camera-right and holds the same left-to-right walk line",
        "clip_index": 1,
        "clip_count": 1,
        "hero_frame_score": 4 if chorus else 2,
        "consistency_need": "high" if chorus else "low",
        "mv_function": "payoff" if chorus else "coverage",
        "return_weight": 4 if chorus else 1,
        "use_ref": chorus,
        "scene_change_level": scene_change_level,
        "anchor_strategy": "new_anchor" if scene_change_level == "reset" else "refine_anchor",
        "route_reason": "priority return section" if chorus else "tti-only coverage shot",
    }


def _story_bible() -> dict:
    return {
        "hero_identity_lock": "silver-haired city-pop heroine",
        "world_rules": "retro neon nightlife with polished stage depth",
        "recurring_location_families": ["reflective threshold", "lit passage"],
        "forbidden_drift": ["identity drift", "random fantasy props"],
        "lyric_beats": [
            {
                "beat_id": "LB01_01",
                "section_name": "verse",
                "section_label": "Verse 1",
                "line_refs": [1],
                "literal_image": "reflective threshold",
                "visible_action": "passes the reflective threshold with a calm step",
                "emotional_turn": "steady confidence",
                "continuity_anchor": "travel line",
                "payoff_role": "develop",
                "repeat_variant_of": "",
                "location_family": "reflective threshold",
                "palette_hint": "teal-magenta glow",
                "lighting_hint": "soft rim light",
                "camera_commitment": "clean stage depth",
                "space_event": "The threshold light ripples across the glass",
            },
            {
                "beat_id": "LB02_01",
                "section_name": "chorus",
                "section_label": "Final Chorus",
                "line_refs": [1],
                "literal_image": "reflective threshold",
                "visible_action": "opens up in the same lane and holds the look",
                "emotional_turn": "bright release",
                "continuity_anchor": "gaze shift",
                "payoff_role": "release",
                "repeat_variant_of": "",
                "location_family": "reflective threshold",
                "palette_hint": "rose-cyan bloom",
                "lighting_hint": "wide glow",
                "camera_commitment": "hero frontal release",
                "space_event": "The lane opens and the sign light pulses",
            },
        ],
        "section_progression": [
            {"section_name": "verse", "section_label": "Verse 1", "dominant_emotion": "steady confidence", "story_function": "coverage", "lyric_beat_ids": ["LB01_01"]},
            {"section_name": "chorus", "section_label": "Final Chorus", "dominant_emotion": "bright release", "story_function": "payoff", "lyric_beat_ids": ["LB02_01"]},
        ],
        "repeat_escalation_rules": ["final chorus should escalate"],
    }
