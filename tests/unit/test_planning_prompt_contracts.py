from ai_mv.core.planning.prompt_contracts import (
    build_clip_positive_prompt,
    build_clip_prompt_seed,
    build_still_prompt_text,
)



def test_prompt_contract_modules_export_still_and_clip_builders():
    assert callable(build_still_prompt_text)
    assert callable(build_clip_prompt_seed)
    assert callable(build_clip_positive_prompt)



def test_prompt_contract_keeps_intro_clip_camera_neutral_for_environment_led_stills():
    prompt = build_clip_positive_prompt(
        "ia2v",
        {"section_type": "intro", "section_name": "Intro", "shot_role": "intro_mood"},
        "late-night city pop walk under wet neon lights, intro mood",
        {"framing_variant": "environment_forward", "environment_variant": "atmospheric", "continuity_variant": "expressive"},
    )

    assert "environment-led camera framing" not in prompt
    assert "restrained camera" in prompt
