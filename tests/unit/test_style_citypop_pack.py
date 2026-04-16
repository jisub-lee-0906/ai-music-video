from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.styles.citypop.bible import get_citypop_bible
from ai_mv.styles.citypop.prompting import build_citypop_prompt_draft, build_citypop_prompt_seed
from ai_mv.styles.citypop.rules import apply_citypop_section_variants, citypop_section_shot_specs


def test_citypop_style_pack_exposes_bible():
    bible = get_citypop_bible()

    assert bible["style"] == "japanese_citypop_80s_90s"
    assert "sunset amber" in bible["palette"]
    assert "city lights" in bible["motifs"]
    assert "k-pop look" in bible["negative_rules"]


def test_plan_preview_uses_citypop_style_pack_bible():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 16.0,
                "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 16.0}],
            },
        },
    )

    assert out["style_bible"] == get_citypop_bible()


def test_citypop_prompting_builds_seed_from_style_pack_helpers():
    seed = build_citypop_prompt_seed(
        "Japanese 80s city pop night drive",
        get_citypop_bible(),
        {
            "section_name": "Chorus",
            "shot_role": "chorus_arrive",
            "visual_mode": "chorus_performance",
        },
    )

    assert "Japanese 80s city pop music video" in seed
    assert "scene event:" in seed
    assert "a close-up of a singer facing the camera" in seed


def test_citypop_prompting_builds_draft_from_style_pack_helpers():
    draft = build_citypop_prompt_draft({"visual_mode": "profile_mood"})

    assert "elegant station reflection styling" in draft
    assert "tight portrait close-up" in draft
    assert "film grain" in draft


def test_citypop_rules_expose_section_shot_specs():
    specs = citypop_section_shot_specs("chorus", 8.0)

    assert [item["shot_role"] for item in specs] == ["chorus_arrive", "chorus_hold"]
    assert [item["visual_mode"] for item in specs] == ["chorus_performance", "neon_release"]


def test_citypop_rules_apply_progressive_section_variants():
    out = apply_citypop_section_variants(
        "verse",
        [
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
        ],
    )

    assert [item["shot_role"] for item in out] == ["verse_setup", "verse_detail", "verse_flow", "verse_glow"]
    assert [item["visual_mode"] for item in out] == ["night_drive", "window_reflection", "night_drive", "city_glance"]