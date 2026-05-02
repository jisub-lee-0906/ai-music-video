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



def test_still_prompt_contract_adds_performance_anchor_identity_and_stage_readability_tokens():
    prompt = build_still_prompt_text(
        "same lead performer on the same glossy performance-night stage",
        "front-facing performance frame",
        "same lead performer on the same glossy performance-night stage",
        {"framing_variant": "subject_forward", "environment_variant": "atmospheric", "section_emphasis_variant": "performance_peak"},
        {"camera_distance_progression": "move into performance distance", "same_block_vs_new_block": "same stage lane, new move"},
        {"reference_mode": "performance_anchor_source", "identity_lock_strength": "performance_anchor"},
        {"edit_variation_scope": "performance_pose_upgrade", "minimum_visual_delta": "pose_or_camera_change_required"},
    )

    assert "front-facing performance-ready face visibility" in prompt
    assert "same lead performer identity" in prompt
    assert "stable bright stage outfit silhouette" in prompt
    assert "same glossy performance-night stage" in prompt
    assert "one clear solo performer only" in prompt
    assert "upper-body or full-body readability" in prompt
    assert "no ambiguous secondary silhouettes" in prompt
    assert "exact face fingerprint from the white-background identity anchor" in prompt
    assert "no distant human silhouettes" in prompt
    assert "no bystanders or second red-coated figure" in prompt



def test_still_prompt_contract_adds_required_delta_tokens_for_performance_followup():
    prompt = build_still_prompt_text(
        "same lead performer on the same glossy performance-night stage",
        "chorus front lights follow-up",
        "same lead performer under chorus front lights on the same glossy performance-night stage",
        {"framing_variant": "subject_forward", "environment_variant": "textural", "section_emphasis_variant": "performance_peak"},
        {"camera_distance_progression": "move into performance distance", "same_block_vs_new_block": "same stage lane, new move"},
        {"reference_mode": "use_performance_anchor_still", "identity_lock_strength": "performance_anchor"},
        {"edit_variation_scope": "performance_pose_upgrade", "minimum_visual_delta": "pose_or_camera_change_required"},
    )

    assert "preserve face shape from the anchor still" in prompt
    assert "preserve exact face fingerprint from the anchor still" in prompt
    assert "change pose silhouette or camera distance from the anchor frame" in prompt
    assert "avoid near-duplicate framing" in prompt
    assert "avoid straight-on duplicate stance" in prompt
    assert "change arm line or torso angle from the anchor frame" in prompt
    assert "shift lighting emphasis for the follow-up frame" in prompt
    assert "choose either a tighter upper-body frame or a wider full-body frame than the anchor" in prompt
    assert "show a visible weight shift or one-step stance change" in prompt
    assert "prefer side-rim or backlight emphasis instead of repeating the anchor lighting setup" in prompt
