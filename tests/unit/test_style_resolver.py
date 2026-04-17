from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.styles.resolver import resolve_style_name


def test_style_resolver_detects_citypop_and_synthwave_from_concept_text():
    assert resolve_style_name("Japanese 80s city pop night drive") == "citypop"
    assert resolve_style_name("dreamy synthwave neon highway night drive") == "synthwave"



def test_style_resolver_uses_style_pack_metadata_not_citypop_first_fallback():
    assert resolve_style_name("retro coupe under a neon skyline with analog glow") == "synthwave"
    assert resolve_style_name("summer boulevard cassette romance under ocean-blue dusk") == "citypop"


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

    item = out["render_plan"][0]
    assert out["style_bible"]["style"] == "retro_synthwave_nightdrive_80s"
    assert out["workflow_inputs"]["plan"]["style_name"] == "synthwave"
    assert "retro synthwave music video" in item["prompt_seed"]
    assert "city pop" not in item["prompt_seed"].lower()
    assert "city pop" not in item["prompt_draft"].lower()
    assert "city pop" not in item["prompt_polish"].lower()


def test_synthwave_plan_preview_uses_style_specific_visual_modes_and_roles():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "dreamy synthwave neon highway night drive",
            "audio_map": {
                "duration_sec": 24.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 4.0},
                    {"name": "chorus", "start_sec": 4.0, "end_sec": 20.0},
                    {"name": "outro", "start_sec": 20.0, "end_sec": 24.0},
                ],
            },
        },
    )

    visual_modes = {shot["visual_mode"] for shot in out["shot_plan"]}
    shot_roles = {shot["shot_role"] for shot in out["shot_plan"]}
    assert "laser_horizon" in visual_modes
    assert "grid_surge" in visual_modes
    assert "neon_run" in visual_modes
    assert "afterglow_escape" in visual_modes
    assert "chorus_breakout" in shot_roles
    assert "chorus_cruise" in shot_roles
