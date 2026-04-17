from ai_mv.core.planning.render_items import build_render_item
from ai_mv.styles.citypop.bible import get_citypop_bible
from ai_mv.styles.synthwave.bible import get_synthwave_bible


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