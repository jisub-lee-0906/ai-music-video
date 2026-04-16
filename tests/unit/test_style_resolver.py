from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.styles.resolver import resolve_style_name


def test_style_resolver_detects_citypop_and_synthwave_from_concept_text():
    assert resolve_style_name("Japanese 80s city pop night drive") == "citypop"
    assert resolve_style_name("dreamy synthwave neon highway night drive") == "synthwave"


def test_plan_preview_uses_synthwave_style_bible_and_prompting():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "dreamy synthwave neon highway night drive",
            "audio_map": {
                "duration_sec": 16.0,
                "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 16.0}],
            },
        },
    )

    assert out["style_bible"]["style"] == "retro_synthwave_nightdrive_80s"
    assert out["workflow_inputs"]["plan"]["style_name"] == "synthwave"
    assert "retro synthwave music video" in out["render_plan"][0]["prompt_seed"]