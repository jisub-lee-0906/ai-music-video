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
