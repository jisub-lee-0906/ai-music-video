from ai_mv.core.planning.render_items import build_render_item
from ai_mv.styles.citypop.bible import get_citypop_bible
from ai_mv.styles.synthwave.bible import get_synthwave_bible


def test_render_item_adds_edit_intent_metadata():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S006",
            "render_mode": "i2v",
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

    assert out["edit_intent"]["edit_priority"] == "high"
    assert out["edit_intent"]["section_emphasis"] == "chorus_push"
    assert out["edit_intent"]["target_clip_sec"] == 5.0
    assert out["edit_intent"]["transition_in"] == "accent_in"
    assert out["edit_intent"]["transition_out"] == "accent_out"


def test_render_item_builds_prompt_fields_and_still_bridge():
    out = build_render_item(
        {},
        "Japanese 80s city pop night drive",
        get_citypop_bible(),
        {
            "shot_id": "S001",
            "render_mode": "flf2v",
            "bridge_to_shot_id": "S002",
            "shot_role": "chorus_arrive",
            "section_name": "Chorus",
            "visual_mode": "chorus_performance",
            "start_sec": 0.0,
            "duration_sec": 5.0,
        },
    )

    assert out["shot_id"] == "S001"
    assert out["still_b"] == "S002"
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


def test_render_item_emits_distinct_seed_per_shot():
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


def test_render_item_separates_still_and_clip_prompt_contracts():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S007",
            "render_mode": "i2v",
            "shot_role": "chorus_breakout",
            "section_name": "Chorus",
            "visual_mode": "grid_surge",
            "start_sec": 8.0,
            "duration_sec": 5.0,
        },
    )

    assert out["still_prompt_text"]
    assert out["clip_prompt_seed"]
    assert out["clip_positive_prompt"]
    assert "motion-safe keyframe" in out["still_prompt_text"]
    assert "single cinematic keyframe" not in out["clip_prompt_seed"]
    assert "single cinematic keyframe" not in out["clip_positive_prompt"]


def test_render_item_uses_environment_led_medium_wide_prompt_for_connective_release_shot():
    out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        "citypop",
        get_citypop_bible(),
        {
            "shot_id": "S012",
            "render_mode": "i2v",
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
    assert "skyline-led negative space" in out["still_prompt_text"]
    assert "close-up" not in out["still_prompt_text"]


def test_render_item_uses_short_transition_prompt_for_flf2v():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S008",
            "render_mode": "flf2v",
            "bridge_to_shot_id": "S009",
            "shot_role": "bridge_escape",
            "section_name": "Bridge",
            "visual_mode": "tunnel_reveal",
            "start_sec": 12.0,
            "duration_sec": 4.0,
        },
    )

    assert out["still_b"] == "S009"
    assert out["clip_prompt_seed"]
    assert out["clip_positive_prompt"]
    assert len(out["clip_positive_prompt"].split(",")) <= 6


def test_render_item_keeps_style_seed_inside_clip_prompt_contract():
    out = build_render_item(
        {},
        "dreamy synthwave neon highway night drive",
        "synthwave",
        get_synthwave_bible(),
        {
            "shot_id": "S010",
            "render_mode": "i2v",
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
            "framing_intent": "performance_closeup",
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
            "render_mode": "i2v",
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
            "render_mode": "i2v",
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
            "render_mode": "i2v",
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
            "render_mode": "i2v",
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