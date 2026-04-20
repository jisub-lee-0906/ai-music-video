from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.styles.resolver import get_style_bible, resolve_style_name, resolve_style_selection


def test_style_resolver_detects_citypop_and_synthwave_from_concept_text():
    assert resolve_style_name("Japanese 80s city pop night drive") == "citypop"
    assert resolve_style_name("dreamy synthwave neon highway night drive") == "synthwave"



def test_style_resolver_returns_selection_metadata_for_auto_matches():
    out = resolve_style_selection("dreamy synthwave neon highway night drive")

    assert out["style_name"] == "synthwave"
    assert out["selection_source"] == "auto"
    assert 0.58 <= out["confidence"] <= 1.0
    assert out["selection_stability"] in {"stable", "contested"}
    assert isinstance(out["runner_up_lanes"], list)
    assert out["runner_up_lanes"]



def test_style_resolver_returns_override_metadata_for_explicit_default_style():
    out = resolve_style_selection("lonely cinematic road at dusk", default_style_name="synthwave")

    assert out["style_name"] == "synthwave"
    assert out["selection_source"] == "override"
    assert out["confidence"] == 1.0
    assert out["selection_stability"] == "override"



def test_style_resolver_uses_style_pack_metadata_not_citypop_first_fallback():
    assert resolve_style_name("retro coupe under a neon skyline with analog glow") == "synthwave"
    assert resolve_style_name("summer boulevard cassette romance under ocean-blue dusk") == "citypop"



def test_style_resolver_rejects_unknown_style_pack_name():
    import pytest

    with pytest.raises(KeyError):
        get_style_bible("unknown-style")



def test_style_resolver_requires_explicit_default_for_no_match_concept_text():
    import pytest

    with pytest.raises(KeyError):
        resolve_style_name("lonely cinematic road at dusk")



def test_plan_preview_uses_explicit_default_style_when_concept_text_is_ambiguous():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "synthwave"}},
        {
            "concept_text": "lonely cinematic road at dusk",
            "audio_map": {
                "duration_sec": 16.0,
                "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 16.0}],
            },
        },
    )

    assert out["style_name"] == "synthwave"
    assert out["style_resolution"]["style_name"] == "synthwave"
    assert out["style_resolution"]["selection_source"] == "override"
    assert out["style_resolution"]["confidence"] == 1.0
    assert out["style_bible"]["style"] == "retro_synthwave_nightdrive_80s"



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
