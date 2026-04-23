from ai_mv.core.planning.edit_intents import build_edit_intent



def test_edit_intents_module_exports_builder():
    assert callable(build_edit_intent)



def test_edit_intents_module_branches_hook_patterns_from_variation_profile():
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
    assert sustain["pattern_family"] == "hook_sustain"
    assert sustain["target_clip_sec"] == 3.6
