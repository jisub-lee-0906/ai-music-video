from ai_mv.core.planning.variation_profile import (
    build_render_seed_for_shot,
    build_variation_profile,
    build_variation_seed_for_shot,
)


def test_variation_profile_module_keeps_performance_peaks_anchor_tight():
    shot = {
        "shot_id": "S020",
        "section_type": "chorus",
        "section_name": "Chorus",
        "shot_role": "chorus_breakout",
        "visual_mode": "chorus_performance",
        "energy": "high",
        "start_sec": 8.0,
    }

    variation_seed = build_variation_seed_for_shot(shot)
    out = build_variation_profile(variation_seed, shot)

    assert out["variation_family"] in {"editorial-a", "editorial-b", "editorial-c"}
    assert out["framing_variant"] in {"balanced", "subject_forward"}
    assert out["continuity_variant"] in {"strict", "anchored"}
    assert out["section_emphasis_variant"] in {"hook_forward", "lifted_release", "performance_peak"}


def test_variation_profile_module_emits_stable_but_distinct_render_and_variation_seeds():
    first_shot = {
        "shot_id": "S001",
        "section_type": "verse",
        "section_name": "Verse A",
        "shot_role": "support",
        "visual_mode": "street_walk",
        "render_mode": "ia2v",
        "start_sec": 3.0,
        "duration_sec": 5.0,
    }
    second_shot = {
        "shot_id": "S002",
        "section_type": "verse",
        "section_name": "Verse A",
        "shot_role": "support",
        "visual_mode": "street_walk",
        "render_mode": "ia2v",
        "start_sec": 8.0,
        "duration_sec": 5.0,
    }

    assert build_render_seed_for_shot(first_shot) == build_render_seed_for_shot(first_shot)
    assert build_variation_seed_for_shot(first_shot) == build_variation_seed_for_shot(first_shot)
    assert build_render_seed_for_shot(first_shot) != build_render_seed_for_shot(second_shot)
    assert build_variation_seed_for_shot(first_shot) != build_variation_seed_for_shot(second_shot)
