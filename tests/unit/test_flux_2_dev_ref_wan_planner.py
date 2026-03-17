from ai_mv.engines.flux_2_dev_ref.planner import build_flux2_ref_plan
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan
import ai_mv.engines.flux_2_dev_ref.planner as flux2_ref_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_flux2_ref_plan_is_deterministic():
    payload = {"clip_routes": [_route("a", True), _route("b", True)], "visual_story_bible": _story_bible()}
    out = build_flux2_ref_plan({}, payload)
    shot_ids = [x["shot_id"] for x in out["items"]]
    assert shot_ids == ["a", "b"]
    assert out["items"][0]["prompt_text"]
    assert out["items"][0]["subject_clause"]
    assert "left-to-right" in out["items"][0]["continuity_clause"]


def test_flux2_ref_plan_empty_when_no_ref_routes():
    out = build_flux2_ref_plan({}, {"clip_routes": [], "visual_story_bible": _story_bible()})
    assert out["items"] == []


def test_flux2_ref_prompt_text_includes_subject_action_and_environment():
    payload = {"clip_routes": [_route("a", True)], "visual_story_bible": _story_bible()}
    out = build_flux2_ref_plan({}, payload)
    text = out["items"][0]["prompt_text"]
    assert "silver-haired city-pop heroine" in text
    assert "reflective threshold" in text
    assert text.endswith(".")


def test_wan_plan_uses_start_end_only():
    payload = {
        "clip_routes": [_route("x", False)],
        "flux2_ref_images": [_flux2_ref("x", 4.0)],
        "visual_story_bible": _story_bible(),
    }
    out = build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
    assert len(out["clips"]) == 1
    assert out["clips"][0]["shot_id"] == "x"
    assert out["clips"][0]["camera_language"] == "clean hero framing"
    assert out["clips"][0]["positive_prompt"]
    assert out["clips"][0]["subject_motion"]
    assert out["clips"][0]["camera_relation"]
    assert "reflective threshold" in out["clips"][0]["positive_prompt"].lower()
    assert "she she" not in out["clips"][0]["positive_prompt"].lower()


def test_wan_plan_prefers_ref_frames_when_route_requires_it():
    payload = {
        "clip_routes": [_route("x", True)],
        "flux2_ref_images": [_flux2_ref("x", 4.0)],
        "visual_story_bible": _story_bible(),
    }
    out = build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
    assert out["clips"][0]["start"] == "s.png"
    assert out["clips"][0]["end"] == "e.png"


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


def test_wan_energy_policy_pre_chorus_not_forced_high():
    out = build_wan_plan(
        {"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}},
        {
            "clip_routes": [{**_route("x", False), "section_name": "pre_chorus", "section_label": "Pre-Chorus"}],
            "flux2_ref_images": [_flux2_ref("x", 4.0)],
            "visual_story_bible": _story_bible_with_section("pre_chorus", "pre chorus lift", "lit passage", "lift", "travel line"),
        },
    )
    assert out["clips"][0]["energy"] == "normal"


def test_wan_chains_split_clip_starts_from_previous_end():
    clips = build_wan_plan(
        {"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}},
        {
            "clip_routes": [
                {**_route("S001_C01", False), "shot_id": "S001_C01"},
                {**_route("S001_C02", False), "shot_id": "S001_C02"},
                {**_route("S001_C03", False), "shot_id": "S001_C03"},
            ],
            "flux2_ref_images": [],
            "visual_story_bible": _story_bible(),
        },
    )["clips"]
    assert clips[0]["start"] == "S001_C01.png"
    assert clips[1]["start"] == clips[0]["end"]
    assert clips[2]["start"] == clips[1]["end"]


def test_wan_plan_varies_subject_motion_by_clip_phase():
    clips = build_wan_plan(
        {"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}},
        {
            "clip_routes": [
                {**_route("S001_C01", False), "shot_id": "S001_C01", "clip_index": 1, "clip_count": 3},
                {**_route("S001_C02", False), "shot_id": "S001_C02", "clip_index": 2, "clip_count": 3},
                {**_route("S001_C03", False), "shot_id": "S001_C03", "clip_index": 3, "clip_count": 3},
            ],
            "flux2_ref_images": [],
            "visual_story_bible": _story_bible(),
        },
    )["clips"]
    motions = [clip["subject_motion"].lower() for clip in clips]
    assert motions[0] != motions[1]
    assert motions[1] != motions[2]
    assert "sets the" in motions[0]
    assert "carries the" in motions[1]
    assert "lands the" in motions[2]


def test_flux2_ref_action_clause_is_not_prefixed_with_duplicate_subject():
    payload = {"clip_routes": [_route("a", True)], "visual_story_bible": _story_bible()}
    out = build_flux2_ref_plan({}, payload)
    assert "she she" not in out["items"][0]["prompt_text"].lower()


def test_flux2_ref_action_clause_uses_workflow_motion_clause():
    anchor = {
        **_route("S020_C01", True),
        "clip_index": 1,
        "clip_count": 3,
        "workflow_motion_clause": "taking a deep breath and lifting her chin into the height",
        "pose_delta": "takes a deep breath and lifts her chin",
    }
    item = flux2_ref_planner._build_item(anchor, _story_bible(), 1)
    assert "with takes" not in item["action_clause"].lower()
    assert "by taking a deep breath" in item["action_clause"].lower()


def test_flux2_ref_action_clause_uses_workflow_motion_clause_for_hits_pattern():
    anchor = {
        **_route("S020_C03", True),
        "clip_index": 3,
        "clip_count": 3,
        "workflow_motion_clause": "hitting the hook entry faster and holding a colder direct stare",
        "pose_delta": "hits the hook entry faster and holds a colder direct stare",
    }
    item = flux2_ref_planner._build_item(anchor, _story_bible(), 1)
    assert "with hits" not in item["action_clause"].lower()
    assert "by hitting the hook entry faster" in item["action_clause"].lower()


def test_flux2_ref_requires_workflow_motion_clause():
    anchor = dict(_route("S020_C03", True), workflow_motion_clause="")
    try:
        flux2_ref_planner._build_item(anchor, _story_bible(), 1)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "workflow_motion_clause missing" in str(exc)


def test_wan_single_clip_subject_motion_avoids_hits_through_stays():
    clip = wan_planner._apply_prompt(
        {
            **_route("S025", False),
            "shot_id": "S025",
            "clip_index": 1,
            "clip_count": 1,
            "use_ref": False,
            "workflow_motion_clause": "staying centered and perfectly clear",
            "motion_hint": "stays centered and perfectly clear",
        },
        _story_bible_with_section("outro", "stays centered and perfectly clear", "reflective threshold", "residue", "stillness hold"),
    )
    assert "hits through stays" not in clip["positive_prompt"].lower()
    assert "she stays centered and perfectly clear" in clip["positive_prompt"].lower()


def test_wan_requires_workflow_motion_clause():
    clip = dict(_route("S025", False), workflow_motion_clause="")
    try:
        wan_planner._apply_prompt(clip, _story_bible())
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "workflow_motion_clause missing" in str(exc)


def _flux2_ref(shot_id: str, duration: float) -> dict:
    return {
        "shot_id": shot_id,
        "start": "s.png",
        "end": "e.png",
        "duration_sec": duration,
        "section_name": "verse",
        "shot_type": "CHAR_MASTER",
        "is_chorus": False,
        "camera_language": "clean hero framing",
        "pose_delta": "small pose shift",
        "emotion": "steady confidence",
        "scene_detail": "concert light wall",
        "motion_hint": "smooth motion",
        "workflow_motion_clause": "moving through the lane and holding a steady line",
    }


def _route(shot_id: str, chorus: bool, duration: float = 4.0) -> dict:
    return {
        "shot_id": shot_id,
        "lyric_beat_id": "LB02_01" if chorus else "LB01_01",
        "anchor": f"{shot_id}.png",
        "identity_anchor": f"{shot_id}.png",
        "is_chorus": chorus,
        "duration_sec": duration,
        "section_name": "chorus" if chorus else "verse",
        "section_label": "Final Chorus" if chorus else "Verse 1",
        "shot_type": "EMOTION_CLOSE" if chorus else "CHAR_MASTER",
        "camera_language": "clean hero framing",
        "pose_delta": "small pose shift",
        "emotion": "steady confidence",
        "scene_detail": "concert light wall",
        "motion_hint": "smooth motion",
        "workflow_motion_clause": "moving through the lane and holding a steady line",
        "space_relation": "glass stays camera-right and holds the same left-to-right walk line",
        "clip_index": 1,
        "clip_count": 1,
        "hero_frame_score": 4 if chorus else 2,
        "consistency_need": "high" if chorus else "low",
        "mv_function": "payoff" if chorus else "coverage",
        "return_weight": 4 if chorus else 1,
        "use_ref": chorus,
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
            },
        ],
        "section_progression": [
            {"section_name": "verse", "section_label": "Verse 1", "dominant_emotion": "steady confidence", "story_function": "coverage", "lyric_beat_ids": ["LB01_01"]},
            {"section_name": "chorus", "section_label": "Final Chorus", "dominant_emotion": "bright release", "story_function": "payoff", "lyric_beat_ids": ["LB02_01"]},
        ],
        "repeat_escalation_rules": ["final chorus should escalate"],
    }


def _story_bible_with_section(name: str, beat: str, location: str, escalation: str, motion_axis: str) -> dict:
    return {
        "hero_identity_lock": "silver-haired city-pop heroine",
        "world_rules": "retro neon nightlife with polished stage depth",
        "recurring_location_families": [location],
        "forbidden_drift": ["identity drift"],
        "lyric_beats": [
            {
                "beat_id": "LB01_01",
                "section_name": name,
                "section_label": name,
                "line_refs": [1],
                "literal_image": location,
                "visible_action": beat,
                "emotional_turn": "lift",
                "continuity_anchor": motion_axis,
                "payoff_role": escalation,
                "repeat_variant_of": "",
                "location_family": location,
                "palette_hint": "teal glow",
                "lighting_hint": "soft rim light",
                "camera_commitment": "clean stage depth",
            }
        ],
        "section_progression": [
            {"section_name": name, "section_label": name, "dominant_emotion": "lift", "story_function": escalation, "lyric_beat_ids": ["LB01_01"]}
        ],
        "repeat_escalation_rules": ["repeats must vary"],
    }
