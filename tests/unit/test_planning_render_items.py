from ai_mv.core.planning.render_items import build_clip_positive_prompt, build_edit_intent, build_render_item
from ai_mv.styles.citypop.bible import get_citypop_bible
from ai_mv.styles.synthwave.bible import get_synthwave_bible



def test_build_edit_intent_branches_hook_patterns_from_variation_profile():
    punch = build_edit_intent(
        {"edit_role": "hook", "duration_sec": 6.0},
        {"motion_variant": "pulsed", "framing_variant": "subject_forward"},
    )
    sustain = build_edit_intent(
        {"edit_role": "hook", "duration_sec": 6.0},
        {"motion_variant": "gliding", "framing_variant": "balanced"},
    )

    assert punch["pattern_family"] == "hook_punch_in"
    assert punch["target_clip_sec"] == 2.4
    assert punch["transition_in"] == "accent_in"
    assert punch["transition_out"] == "accent_out"

    assert sustain["pattern_family"] == "hook_sustain"
    assert sustain["target_clip_sec"] == 3.6
    assert sustain["transition_in"] == "glide_in"
    assert sustain["transition_out"] == "accent_out"



def test_build_edit_intent_branches_support_patterns_from_variation_profile():
    drive = build_edit_intent(
        {"edit_role": "support", "duration_sec": 6.0},
        {"motion_variant": "pulsed", "framing_variant": "balanced"},
    )
    hold = build_edit_intent(
        {"edit_role": "support", "duration_sec": 6.0},
        {"motion_variant": "restrained", "framing_variant": "environment_forward"},
    )

    assert drive["pattern_family"] == "support_drive"
    assert drive["target_clip_sec"] == 2.7
    assert drive["transition_in"] == "cut_in"
    assert drive["transition_out"] == "cut_out"

    assert hold["pattern_family"] == "support_hold"
    assert hold["target_clip_sec"] == 4.2
    assert hold["transition_in"] == "hold_in"
    assert hold["transition_out"] == "cut_out"



def test_build_edit_intent_branches_bridge_and_release_patterns_from_variation_profile():
    bridge = build_edit_intent(
        {"edit_role": "bridge", "duration_sec": 6.0},
        {"motion_variant": "gliding", "framing_variant": "balanced"},
    )
    release = build_edit_intent(
        {"edit_role": "release", "duration_sec": 6.0},
        {"motion_variant": "restrained", "framing_variant": "environment_forward"},
    )

    assert bridge["pattern_family"] == "bridge_glide"
    assert bridge["target_clip_sec"] == 3.6
    assert bridge["transition_in"] == "glide_in"
    assert bridge["transition_out"] == "handoff_out"

    assert release["pattern_family"] == "release_drift"
    assert release["target_clip_sec"] == 4.2
    assert release["transition_in"] == "hold_in"
    assert release["transition_out"] == "fade_out"



def test_build_edit_intent_clamps_short_shot_target_to_actual_duration():
    out = build_edit_intent(
        {"edit_role": "hook", "duration_sec": 0.5},
        {"motion_variant": "pulsed", "framing_variant": "subject_forward"},
    )

    assert out["target_clip_sec"] == 0.5



def test_render_item_adds_edit_intent_metadata():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S006",
            "section_id": "SEC_003",
            "render_mode": "ia2v",
            "shot_role": "chorus_breakout",
            "section_type": "chorus",
            "section_name": "Chorus",
            "visual_mode": "grid_surge",
            "edit_role": "hook",
            "coverage_role": "anchor",
            "workflow_intent": "audio_reactive_candidate",
            "start_sec": 8.0,
            "duration_sec": 5.0,
        },
    )

    assert out["section_id"] == "SEC_003"
    assert out["edit_intent"]["edit_priority"] == "high"
    assert out["edit_intent"]["section_emphasis"] == "chorus_push"
    assert out["edit_intent"]["pattern_family"] in {"hook_punch_in", "hook_sustain", "hook_surge"}
    assert 0.0 < out["edit_intent"]["target_clip_sec"] <= 5.0
    assert out["edit_intent"]["transition_out"] == "accent_out"



def test_render_item_preserves_material_id_for_material_layer_join():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S006",
            "section_id": "SEC_003",
            "material_id": "MAT_003",
            "render_mode": "ia2v",
            "shot_role": "chorus_breakout",
            "section_type": "chorus",
            "section_name": "Chorus",
            "visual_mode": "grid_surge",
            "start_sec": 8.0,
            "duration_sec": 5.0,
        },
    )

    assert out["material_id"] == "MAT_003"



def test_render_item_builds_prompt_fields_for_ia2v_clip():
    out = build_render_item(
        {},
        "Japanese 80s city pop night drive",
        get_citypop_bible(),
        {
            "shot_id": "S001",
            "render_mode": "ia2v",
            "shot_role": "chorus_arrive",
            "section_name": "Chorus",
            "visual_mode": "chorus_performance",
            "start_sec": 0.0,
            "duration_sec": 5.0,
        },
    )

    assert out["shot_id"] == "S001"
    assert out["prompt_seed"]
    assert out["prompt_draft"]
    assert out["prompt_polish"]


def test_render_item_adds_audio_segment_for_ia2v():
    out = build_render_item(
        {},
        "Japanese 80s city pop night drive",
        get_citypop_bible(),
        {
            "shot_id": "S001",
            "render_mode": "ia2v",
            "shot_role": "chorus_arrive",
            "section_name": "Chorus",
            "visual_mode": "chorus_performance",
            "start_sec": 3.0,
            "duration_sec": 5.0,
        },
    )

    assert out["audio_segment"] == {"start_sec": 3.0, "duration_sec": 5.0}


def test_render_item_surfaces_structured_continuity_and_neighbor_contracts():
    out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        get_citypop_bible(),
        {
            "shot_id": "S002",
            "render_mode": "ia2v",
            "shot_role": "verse_setup",
            "section_type": "verse",
            "section_name": "Verse 1",
            "visual_mode": "night_drive",
            "start_sec": 3.0,
            "duration_sec": 5.0,
            "protagonist_anchor": "same lone night-walk protagonist, stable dark outerwear silhouette, no competing bystanders",
            "world_anchor": "same rain-slick neon boulevard world, wet asphalt reflections, dense urban signage",
            "continuity_contract": {
                "protagonist_anchor": "same lone night-walk protagonist, stable dark outerwear silhouette, no competing bystanders",
                "world_anchor": "same rain-slick neon boulevard world, wet asphalt reflections, dense urban signage",
                "wardrobe_anchor": "stable dark outerwear silhouette",
                "no_competing_subjects": True,
                "time_band_anchor": "same night time band",
            },
            "shot_relation_contract": {
                "relation_to_previous_shot": "continue same protagonist and world from previous shot",
                "camera_distance_progression": "move closer than previous shot",
                "same_block_vs_new_block": "same block, new angle",
                "emotional_delta": "increase intimacy without changing world",
            },
        },
    )

    assert out["continuity_contract"]["wardrobe_anchor"] == "stable dark outerwear silhouette"
    assert out["shot_relation_contract"]["camera_distance_progression"] == "move closer than previous shot"
    assert out["still_prompt_text"].count("move closer than previous shot") == 1
    assert out["still_prompt_text"].count("same block, new angle") == 1


def test_render_item_emits_distinct_seed_and_variation_metadata_per_shot():
    first = build_render_item(
        {},
        "Japanese 80s city pop night drive",
        get_citypop_bible(),
        {
            "shot_id": "S001",
            "render_mode": "ia2v",
            "shot_role": "chorus_arrive",
            "section_name": "Chorus",
            "visual_mode": "chorus_performance",
            "start_sec": 3.0,
            "duration_sec": 5.0,
        },
    )
    second = build_render_item(
        {},
        "Japanese 80s city pop night drive",
        get_citypop_bible(),
        {
            "shot_id": "S002",
            "render_mode": "ia2v",
            "shot_role": "chorus_arrive",
            "section_name": "Chorus",
            "visual_mode": "chorus_performance",
            "start_sec": 8.0,
            "duration_sec": 5.0,
        },
    )

    assert isinstance(first["seed"], int)
    assert isinstance(second["seed"], int)
    assert first["seed"] >= 0
    assert second["seed"] >= 0
    assert first["seed"] != second["seed"]
    assert isinstance(first["variation_seed"], int)
    assert isinstance(second["variation_seed"], int)
    assert first["variation_seed"] != second["variation_seed"]
    assert first["variation_profile"]["variation_family"]
    assert second["variation_profile"]["variation_family"]
    assert set(first["variation_profile"]) == {
        "variation_family",
        "framing_variant",
        "environment_variant",
        "motion_variant",
        "continuity_variant",
        "section_emphasis_variant",
    }


def test_render_item_variation_profile_changes_still_and_clip_prompt_translation():
    first = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S020",
            "render_mode": "ia2v",
            "shot_role": "chorus_breakout",
            "section_type": "chorus",
            "section_name": "Chorus",
            "visual_mode": "grid_surge",
            "start_sec": 8.0,
            "duration_sec": 5.0,
        },
    )
    second = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S021",
            "render_mode": "ia2v",
            "shot_role": "chorus_breakout",
            "section_type": "chorus",
            "section_name": "Chorus",
            "visual_mode": "grid_surge",
            "start_sec": 13.0,
            "duration_sec": 5.0,
        },
    )

    assert first["variation_profile"] != second["variation_profile"]
    assert first["still_prompt_text"] != second["still_prompt_text"]
    assert first["clip_prompt_seed"] != second["clip_prompt_seed"]
    assert first["clip_positive_prompt"] != second["clip_positive_prompt"]
    for out in (first, second):
        assert out["variation_profile"]["framing_variant"] in {"balanced", "subject_forward"}
        assert out["variation_profile"]["continuity_variant"] in {"strict", "anchored"}
        assert "environment-led camera framing" not in out["clip_positive_prompt"]


def test_render_item_uses_reanchored_medium_wide_prompt_for_connective_release_shot():
    out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        "citypop",
        get_citypop_bible(),
        {
            "shot_id": "S012",
            "render_mode": "ia2v",
            "shot_role": "chorus_hold",
            "section_type": "chorus",
            "section_name": "Chorus",
            "visual_mode": "neon_release",
            "edit_role": "hook",
            "coverage_role": "connective",
            "framing_intent": "release_wide",
            "workflow_intent": "section_default",
            "start_sec": 8.0,
            "duration_sec": 4.0,
        },
    )

    assert "wide release frame" in out["still_prompt_text"]
    assert "anchored figure" in out["still_prompt_text"]
    assert "controlled negative space" in out["still_prompt_text"]
    assert "close-up" not in out["still_prompt_text"]
    assert "skyline-led negative space" not in out["still_prompt_text"]


def test_render_item_keeps_ia2v_clip_prompt_compact_for_bridge_sections():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S008",
            "render_mode": "ia2v",
            "shot_role": "bridge_escape",
            "section_name": "Bridge",
            "visual_mode": "tunnel_reveal",
            "start_sec": 12.0,
            "duration_sec": 4.0,
        },
    )

    assert out["clip_prompt_seed"]
    assert out["clip_positive_prompt"]
    assert "bridge escape" in out["clip_prompt_seed"]
    assert "stable performer identity" in out["clip_positive_prompt"]


def test_render_item_keeps_style_seed_inside_clip_prompt_contract():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S010",
            "render_mode": "ia2v",
            "shot_role": "chorus_breakout",
            "section_name": "Chorus",
            "visual_mode": "grid_surge",
            "start_sec": 4.0,
            "duration_sec": 5.0,
        },
    )

    first_seed_token = out["prompt_seed"].split(",")[0].strip()
    assert first_seed_token
    assert first_seed_token in out["clip_prompt_seed"]
    assert first_seed_token in out["clip_positive_prompt"]


def test_render_item_keeps_intro_clip_camera_more_neutral_even_when_still_framing_is_environment_led():
    prompt = build_clip_positive_prompt(
        "ia2v",
        {"section_type": "intro", "section_name": "Intro", "shot_role": "intro_mood"},
        "late-night city pop walk under wet neon lights, intro mood",
        {"framing_variant": "environment_forward", "environment_variant": "atmospheric", "continuity_variant": "expressive"},
    )

    assert "environment-led camera framing" not in prompt
    assert "restrained camera" in prompt


def test_render_item_keeps_bridge_clip_camera_more_neutral_even_when_still_framing_is_environment_led():
    prompt = build_clip_positive_prompt(
        "ia2v",
        {"section_type": "bridge", "section_name": "Bridge", "shot_role": "bridge_shift"},
        "late-night city pop walk under wet neon lights, bridge shift",
        {"framing_variant": "environment_forward", "environment_variant": "spatial", "continuity_variant": "expressive"},
    )

    assert "environment-led camera framing" not in prompt
    assert "restrained camera" in prompt


def test_render_item_keeps_outro_clip_camera_more_neutral_even_when_still_framing_is_environment_led():
    prompt = build_clip_positive_prompt(
        "ia2v",
        {"section_type": "outro", "section_name": "Outro", "shot_role": "outro_release"},
        "late-night city pop walk under wet neon lights, outro release",
        {"framing_variant": "environment_forward", "environment_variant": "spatial", "continuity_variant": "expressive"},
    )

    assert "environment-led camera framing" not in prompt
    assert "restrained camera" in prompt


def test_render_item_keeps_non_intro_bridge_outro_release_roles_scenic_when_requested():
    prompt = build_clip_positive_prompt(
        "ia2v",
        {"section_type": "pre_chorus", "section_name": "Pre-Chorus", "shot_role": "prechorus_release"},
        "late-night city pop walk under wet neon lights, prechorus release",
        {"framing_variant": "environment_forward", "environment_variant": "atmospheric", "continuity_variant": "expressive"},
    )

    assert "environment-led camera framing" in prompt


def test_render_item_requires_explicit_render_mode():
    import pytest

    with pytest.raises(KeyError):
        build_render_item(
            {},
            "dreamy synthwave neon highway night drive",
            "synthwave",
            get_synthwave_bible(),
            {
                "shot_id": "S011",
                "shot_role": "chorus_breakout",
                "section_name": "Chorus",
                "visual_mode": "grid_surge",
                "start_sec": 4.0,
                "duration_sec": 5.0,
            },
        )



def test_render_item_emits_render_planning_metadata_from_appendix_formula():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S013",
            "render_mode": "ia2v",
            "shot_role": "chorus_breakout",
            "section_type": "chorus",
            "section_name": "Chorus",
            "visual_mode": "grid_surge",
            "edit_role": "hook",
            "framing_intent": "performance_medium",
            "continuity_mode": "strict",
            "energy": "high",
            "start_sec": 8.0,
            "duration_sec": 5.0,
        },
    )

    assert out["render_count"] == 1
    assert out["render_planning"]["section_energy_score"] == 0.75
    assert out["render_planning"]["section_emphasis_score"] == 1.0
    assert out["render_planning"]["mode_importance_score"] == 1.0
    assert out["render_planning"]["lane_priority_score"] == 0.85
    assert out["render_planning"]["continuity_need_score"] == 1.0
    assert out["render_priority_score"] == 0.9



def test_render_item_render_count_follows_appendix_duration_bands():
    short_out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        "citypop",
        get_citypop_bible(),
        {
            "shot_id": "S014",
            "render_mode": "ia2v",
            "shot_role": "intro_mood",
            "section_type": "intro",
            "section_name": "Intro",
            "visual_mode": "empty_boulevard_anchor",
            "continuity_mode": "high",
            "energy": "low",
            "start_sec": 0.0,
            "duration_sec": 6.5,
        },
    )
    medium_out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        "citypop",
        get_citypop_bible(),
        {
            "shot_id": "S015",
            "render_mode": "ia2v",
            "shot_role": "verse_drift",
            "section_type": "verse",
            "section_name": "Verse",
            "visual_mode": "street_glance",
            "continuity_mode": "high",
            "energy": "medium",
            "start_sec": 0.0,
            "duration_sec": 9.0,
        },
    )
    long_out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        "citypop",
        get_citypop_bible(),
        {
            "shot_id": "S016",
            "render_mode": "ia2v",
            "shot_role": "verse_drift",
            "section_type": "verse",
            "section_name": "Verse",
            "visual_mode": "street_glance",
            "continuity_mode": "high",
            "energy": "medium",
            "start_sec": 0.0,
            "duration_sec": 15.0,
        },
    )
    capped_out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        "citypop",
        get_citypop_bible(),
        {
            "shot_id": "S017",
            "render_mode": "ia2v",
            "shot_role": "verse_drift",
            "section_type": "verse",
            "section_name": "Verse",
            "visual_mode": "street_glance",
            "continuity_mode": "medium",
            "energy": "medium",
            "start_sec": 0.0,
            "duration_sec": 25.0,
        },
    )

    assert short_out["render_count"] == 1
    assert medium_out["render_count"] == 2
    assert long_out["render_count"] == 3
    assert capped_out["render_count"] == 4