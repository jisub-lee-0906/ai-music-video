from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.quality_review import build_quality_review, build_run_summary


def test_run_summary_and_quality_review_are_written(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_mv.core.artifacts.paths.PROJECT_ROOT", tmp_path)
    state = {"run_id": "r1", "status": "done", "completed_stages": ["acestep_music"], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_brief": "director_brief_example",
        "audio_map": {"language": "ko", "sections": [{"name": "intro", "label": "Intro"}]},
        "scene_outline": {"shot_packages": []},
    }
    review = {"visual_generation_review": {"reasoning": "best"}}
    summary = build_run_summary(state, payload, review)
    write_quality_review(state, review)
    write_run_summary(state, summary)
    assert run_file("r1", "quality_review.json").exists()
    assert run_file("r1", "run_summary.json").exists()
    assert latest_file("quality_review.json").exists()
    assert latest_file("run_summary.json").exists()
    assert latest_success_file("quality_review.json").exists()
    assert latest_success_file("run_summary.json").exists()


def test_run_summary_includes_plan_metrics():
    state = {"run_id": "r7", "status": "done", "completed_stages": [], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_brief": "director_brief_example",
        "audio_map": {"language": "ko", "sections": [{"name": "intro", "label": "Intro"}]},
        "scene_outline": {
            "shot_packages": [
                {"shot_id": "b1", "section_label": "Intro", "world_zone": "threshold", "story_function": "entry", "continuity_group": "Intro:threshold"},
                {"shot_id": "b2", "section_label": "Chorus", "world_zone": "open_peak", "story_function": "payoff", "continuity_group": "Chorus:open_peak"},
            ]
        },
        "direction_plan": {"shot_packages": [{"shot_id": "b1", "ref_archetype": "gate_pass"}, {"shot_id": "b2", "ref_archetype": "curb_crossing"}]},
        "prompt_plan": {"ref_items": [{"shot_id": "b1"}, {"shot_id": "b2"}]},
    }
    summary = build_run_summary(state, payload, {})
    assert summary["pipeline_version"] == "visual"
    assert summary["shot_package_count"] == 2
    assert summary["world_zone_count"] == 2
    assert summary["story_function_count"] == 2
    assert summary["archetype_count"] == 2


def test_quality_review_uses_new_structure():
    payload = {
        "lyrics_timeline": {
            "sections": [
                {"section_label": "Intro", "lyric_beats": [{"beat_id": "intro_b1"}]},
                {"section_label": "Chorus", "lyric_beats": [{"beat_id": "chorus_b1"}]},
            ]
        },
        "scene_outline": {
            "story_premise": "A heroine crosses a connected night world.",
            "world_rules": "The world stays physically connected.",
            "section_progression": [
                {"section_label": "Intro", "story_goal": "Entry", "world_zone": "threshold"},
                {"section_label": "Chorus", "story_goal": "Release", "world_zone": "open_peak"},
            ],
            "shot_packages": [
                {"shot_id": "intro_b1", "section_label": "Intro", "world_zone": "threshold", "story_function": "entry", "beat_refs": ["intro_b1"], "line_refs": [1]},
                {"shot_id": "chorus_b1", "section_label": "Chorus", "world_zone": "open_peak", "story_function": "payoff", "beat_refs": ["chorus_b1"], "line_refs": [1]},
            ],
        },
        "direction_plan": {
            "shot_packages": [
                {"shot_id": "intro_b1", "world_zone": "threshold", "ref_archetype": "gate_pass", "story_visual_intent": "Show the first committed boundary crossing."},
                {"shot_id": "chorus_b1", "world_zone": "open_peak", "ref_archetype": "curb_crossing", "story_visual_intent": "Show the widest forward release."},
            ]
        },
        "prompt_plan": {
            "ref_items": [
                {
                    "shot_id": "intro_b1",
                    "ref_start_prompt_text": "The same Korean female idol enters the turnstile lane with one readable forward step.",
                },
                {
                    "shot_id": "chorus_b1",
                    "ref_start_prompt_text": "The same Korean female idol steps onto the wet crosswalk with her line set toward the far curb.",
                },
            ]
        },
        "backend_preview": {
            "ref_adapter": [
                {
                    "raw_prompt_clauses": {
                        "story_function": "entry",
                        "primary_surface": "turnstile lane",
                        "ref_archetype": "gate_pass",
                        "dominant_action": "She enters the turnstile lane with one readable forward step.",
                        "continuity_delta": "She moves beyond the turnstile lane and lands on the next pavement.",
                        "content_trace": "",
                        "selected_prompt_shape": "surface_first_crossing",
                    },
                    "start_prompt_preview": "The same Korean female idol enters the turnstile lane with one readable forward step.",
                    "end_prompt_preview": "The same Korean female idol moves beyond the turnstile lane and lands on the next pavement.",
                }
            ],
            "wan_adapter": [
                {
                    "raw_prompt_clauses": {
                        "bridge_action": "She clears the threshold and keeps going.",
                        "start_ref_shot_id": "intro_b1",
                        "end_ref_shot_id": "chorus_b1",
                    },
                    "positive_prompt_preview": "The same Korean female idol clears the threshold and keeps going.",
                }
            ],
        },
    }
    out = build_quality_review({}, payload)
    assert out["story_review"]["strengths"]
    assert out["direction_review"]["strengths"]
    assert out["prompt_review"]["strengths"] or out["prompt_review"]["risks"] == []
    assert out["prompt_execution_review"]["metrics"]["story_function_match"] > 0
    assert out["visual_generation_contracts"]["metrics"]["adjacent_transition_integrity"] > 0
    assert out["prompt_review"]["metrics"]["style_alignment_ratio"] > 0.5
    assert "rule_source_trace" in out["prompt_review"]


def test_quality_review_accepts_platform_edge_directional_step_patterns():
    payload = {
        "backend_preview": {
            "ref_adapter": [
                {
                    "raw_prompt_clauses": {
                        "story_function": "pressure",
                        "primary_surface": "wet platform edge with yellow tactile line",
                        "ref_archetype": "platform_edge",
                        "dominant_action": "She sets a shorter step along the wet platform edge with the yellow tactile line close at her feet.",
                        "continuity_delta": "She takes a crossing step along the wet platform edge with the yellow tactile line close at her feet and her footprint trail widening behind her.",
                        "content_trace": "footprint trail widening behind her",
                        "selected_prompt_shape": "geometry_first_directional_step",
                    },
                    "start_prompt_preview": "The same Korean female idol sets a shorter step along the wet platform edge with the yellow tactile line close at her feet.",
                    "end_prompt_preview": "The same Korean female idol takes a crossing step along the wet platform edge with the yellow tactile line close at her feet and her footprint trail widening behind her.",
                }
            ],
            "wan_adapter": [],
        }
    }
    out = build_quality_review({}, payload)
    assert out["prompt_execution_review"]["metrics"]["archetype_selection_match"] == 1.0
    assert out["prompt_execution_review"]["metrics"]["prompt_shape_match"] == 1.0


def test_quality_review_reports_rule_source_trace_without_scoring_dependency():
    payload = {
        "prompt_plan": {
            "master_anchor": {
                "rule_precedence_summary": "identity_core and identity_hooks > tti_families > flux2_prompting.tti",
            },
            "ref_items": [
                {
                    "applied_global_prompt_rules": ["flux2_prompting.ref.natural_language_contract"],
                    "applied_golden_structure": "bridge_platform_motion",
                }
            ],
            "wan_items": [
                {
                    "applied_global_prompt_rules": ["flux2_prompting.wan.natural_language_contract"],
                    "applied_golden_structure": "",
                }
            ],
        }
    }
    out = build_quality_review({}, payload)
    trace = out["prompt_review"]["rule_source_trace"]
    assert trace["master_anchor_precedence"]
    assert trace["ref_items_with_global_rules"] == 1
    assert trace["ref_items_with_golden_structure"] == 1
    assert trace["wan_items_with_global_rules"] == 1
