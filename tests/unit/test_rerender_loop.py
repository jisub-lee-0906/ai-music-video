from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages import rerender_loop


def test_rerender_loop_treats_successful_assembly_coverage_revision_as_resolved(monkeypatch):
    def fake_prepare(stage_input: StageInput) -> StageOutput:
        return StageOutput(
            "prepare_rerender",
            "done",
            {
                "rerender_target_ids": ["S001", "S002"],
                "rerender_stage_sequence": ["review"],
                "rerender_stage_inputs": {
                    "review": {
                        "recommended_action": "revise_assembly_coverage_before_sync_pad",
                        "final_video": "final/mv_synced.mp4",
                        "music_file": "audio/song.mp3",
                        "sync_repair_summary": {
                            "clone_tail_sec": 8.8,
                            "clone_tail_excessive": True,
                        },
                    }
                },
            },
            [],
        )

    def fake_repair(stage_input: StageInput) -> StageOutput:
        return StageOutput("repair_rerender_prompts", "done", {}, [])

    def fake_execute(stage_input: StageInput) -> StageOutput:
        return StageOutput(
            "execute_rerender",
            "done",
            {
                "final_video": "final/mv_synced.mp4",
                "assembly_revision_result": {
                    "status": "applied",
                    "action": "revise_assembly_coverage_before_sync_pad",
                    "target": "assembly",
                    "output_final_video": "final/mv_synced.mp4",
                    "target_shots": ["S001", "S002"],
                },
                "rerender_results": {"completed_stages": ["review"], "still_results": [], "clip_results": []},
            },
            ["final/mv_synced.mp4"],
        )

    def fake_review(stage_input: StageInput) -> StageOutput:
        return StageOutput(
            "rerender_review",
            "done",
            {
                "rerender_review_report": {
                    "status": "needs_rerender",
                    "blocking_checks": {
                        "sync_clone_tail_within_threshold": True,
                        "chorus_emphasis_within_threshold": False,
                    },
                    "rerender_targets": [],
                    "rerender_execution_payloads": [],
                },
                "assembly_revision_result": stage_input.payload["assembly_revision_result"],
                "rerender_final_video": stage_input.payload["final_video"],
            },
            [],
        )

    monkeypatch.setattr(rerender_loop, "run_prepare_rerender", fake_prepare)
    monkeypatch.setattr(rerender_loop, "run_repair_rerender_prompts", fake_repair)
    monkeypatch.setattr(rerender_loop, "run_execute_rerender", fake_execute)
    monkeypatch.setattr(rerender_loop, "run_rerender_review", fake_review)

    out = rerender_loop.run_rerender_loop(StageInput(run_id="run", config={}, payload={"review_report": {"status": "needs_rerender"}}))

    assert out.payload["assembly_revision_result"]["status"] == "applied"
    assert out.payload["rerender_final_video"] == "final/mv_synced.mp4"
    assert out.payload["rerender_outcome"] == {"attempted": True, "resolved": True, "exhausted": False}


def test_rerender_loop_repeats_coverage_repair_until_raw_coverage_ok(monkeypatch):
    prepare_attempts: list[dict] = []
    execute_inputs: list[dict] = []

    def fake_prepare(stage_input: StageInput) -> StageOutput:
        prepare_attempts.append(dict(stage_input.payload.get("assembly_plan", {})))
        repair_shot_id = "COV_REPAIR_001" if len(prepare_attempts) == 1 else "COV_REPAIR_002"
        return StageOutput(
            "prepare_rerender",
            "done",
            {
                "rerender_target_ids": [repair_shot_id],
                "rerender_stage_sequence": ["stills", "clips", "assemble"],
                "rerender_stage_inputs": {
                    "stills": {"shot_plan": [{"shot_id": repair_shot_id}], "material_plan": [], "render_plan": [], "still_results": []},
                    "clips": {"shot_plan": [{"shot_id": repair_shot_id}], "render_plan": [], "still_results": [], "music_file": "song.wav"},
                    "assemble": {"shot_plan": [{"shot_id": repair_shot_id}], "render_plan": [], "clip_results": [], "music_file": "song.wav", "audio_map": {}},
                },
            },
            [],
        )

    def fake_repair(stage_input: StageInput) -> StageOutput:
        return StageOutput("repair_rerender_prompts", "done", {}, [])

    def fake_execute(stage_input: StageInput) -> StageOutput:
        execute_inputs.append(dict(stage_input.payload))
        if len(execute_inputs) == 1:
            return StageOutput(
                "execute_rerender",
                "done",
                {
                    "assembly_plan": {
                        "coverage_summary": {
                            "status": "insufficient_raw_coverage",
                            "recommended_action": "revise_assembly_coverage_before_sync_pad",
                            "coverage_deficit_sec": 2.0,
                        },
                        "coverage_repair_plan": {
                            "status": "repair_required",
                            "repair_shots": [{"shot_id": "COV_REPAIR_002", "target_duration_sec": 2.0}],
                        },
                    },
                    "rerender_results": {
                        "completed_stages": ["stills", "clips", "assemble"],
                        "still_results": [],
                        "clip_results": [],
                    },
                },
                [],
            )
        return StageOutput(
            "execute_rerender",
            "done",
            {
                "final_video": "final/mv_synced.mp4",
                "rerender_final_video": "final/mv_synced.mp4",
                "assembly_plan": {
                    "coverage_summary": {"status": "raw_coverage_ok", "recommended_action": "continue_to_sync"},
                    "coverage_repair_plan": {"status": "not_required", "repair_shots": []},
                },
                "rerender_results": {
                    "completed_stages": ["stills", "clips", "assemble", "sync"],
                    "still_results": [],
                    "clip_results": [],
                    "final_video": "final/mv_synced.mp4",
                },
            },
            ["final/mv_synced.mp4"],
        )

    def fake_review(stage_input: StageInput) -> StageOutput:
        coverage_summary = stage_input.payload.get("assembly_plan", {}).get("coverage_summary", {})
        if coverage_summary.get("status") == "insufficient_raw_coverage":
            return StageOutput(
                "rerender_review",
                "done",
                {
                    "assembly_plan": stage_input.payload["assembly_plan"],
                    "rerender_review_report": {
                        "status": "needs_rerender",
                        "rerender_targets": ["coverage"],
                        "rerender_execution_payloads": [],
                    },
                },
                [],
            )
        return StageOutput(
            "rerender_review",
            "done",
            {
                "assembly_plan": stage_input.payload["assembly_plan"],
                "rerender_final_video": stage_input.payload["rerender_final_video"],
                "rerender_review_report": {
                    "status": "passed",
                    "rerender_targets": [],
                    "rerender_execution_payloads": [],
                },
            },
            [],
        )

    monkeypatch.setattr(rerender_loop, "run_prepare_rerender", fake_prepare)
    monkeypatch.setattr(rerender_loop, "run_repair_rerender_prompts", fake_repair)
    monkeypatch.setattr(rerender_loop, "run_execute_rerender", fake_execute)
    monkeypatch.setattr(rerender_loop, "run_rerender_review", fake_review)

    out = rerender_loop.run_rerender_loop(
        StageInput(
            run_id="run",
            config={"coverage_repair_max_attempts": 2},
            payload={
                "assembly_plan": {
                    "coverage_repair_plan": {
                        "status": "repair_required",
                        "repair_shots": [{"shot_id": "COV_REPAIR_001", "target_duration_sec": 3.0}],
                    }
                },
                "review_report": {"status": "needs_rerender"},
            },
        )
    )

    assert len(prepare_attempts) == 2
    assert execute_inputs[1]["rerender_target_ids"] == ["COV_REPAIR_002"]
    assert out.payload["rerender_final_video"] == "final/mv_synced.mp4"
    assert out.payload["rerender_outcome"] == {"attempted": True, "resolved": True, "exhausted": False}
    assert out.payload["coverage_repair_loop"] == {"attempts": 2, "max_attempts": 2, "exhausted": False}
