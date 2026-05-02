from ai_mv.core.artifacts import publish as publish_module


def test_write_pipeline_summary_publishes_story_contract_coverage_without_scene_hardcoding(monkeypatch):
    summaries: list[dict] = []

    monkeypatch.setattr(publish_module, "write_manifest", lambda _state, _payload: None)
    monkeypatch.setattr(publish_module, "write_run_summary", lambda _state, summary: summaries.append(summary))

    publish_module.write_pipeline_artifacts(
        {
            "run_id": "run-story-summary",
            "status": "done",
            "failure_reason": "",
            "current_stage": "done",
            "completed_stages": ["plan"],
        },
        {
            "shot_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "section_type": "intro",
                    "story_contract": {
                        "why_this_shot": "This intro exists to establish the protagonist wound.",
                        "protagonist_action": "The protagonist hesitates beside the radio tower.",
                        "section_alignment": "Align with the intro section.",
                        "progression_from_previous": "sequence start",
                        "visual_payoff": "radio tower signal glows once",
                        "anti_repetition_constraint": "avoid repeating the same centered pose",
                    },
                },
                {
                    "shot_id": "S002",
                    "section_id": "SEC_002",
                    "section_type": "chorus",
                    "story_contract": {
                        "why_this_shot": "This chorus exists to show release.",
                        "protagonist_action": "The protagonist walks away from the tower road.",
                        "section_alignment": "Align with the chorus section.",
                        "progression_from_previous": "increase action energy",
                        "visual_payoff": "sunrise catches the horizon",
                        "anti_repetition_constraint": "change action and camera distance",
                    },
                },
            ],
            "render_plan": [],
            "review_report": {},
        },
        {},
    )

    summary = summaries[0]
    assert summary["story_contract_shot_count"] == 2
    assert summary["story_contract_coverage_ratio"] == 1.0
    assert summary["story_contract_sections"] == ["intro", "chorus"]
    assert summary["story_contract_missing_shot_ids"] == []
    joined = " ".join(summary["story_contract_action_samples"]).lower()
    assert "radio tower" in joined
    assert "red raincoat" not in joined
