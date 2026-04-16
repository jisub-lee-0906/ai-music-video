from ai_mv.core.planning.render_items import build_render_item
from ai_mv.styles.citypop.bible import get_citypop_bible


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