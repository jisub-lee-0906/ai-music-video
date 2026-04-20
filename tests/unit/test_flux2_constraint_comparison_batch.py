from __future__ import annotations

import json

from ai_mv.analysis import flux2_constraint_comparison_batch as module


def test_build_constraint_comparison_runs_covers_selected_cases_and_modes():
    runs = module.build_constraint_comparison_runs()

    assert len(runs) == 24
    assert runs[0]["run_id"] == "F001_A1_raw_s1001"
    assert runs[-1]["run_id"] == "F004_R3_constrained_s1003"
    assert {row["case_id"] for row in runs} == {"F001", "F002", "F003", "F004"}
    assert {row["prompt_family"] for row in runs} == {"A1", "A3", "R3"}
    assert {row["constraint_mode"] for row in runs} == {"raw", "constrained"}
    assert {row["seed"] for row in runs} == {1001, 1002, 1003}
    assert all(row["workflow_name"] == "image_flux2_text_to_image.json" for row in runs)


def test_build_batch_metadata_matches_constraint_comparison_contract():
    metadata = module.build_batch_metadata(batch_id="flux2-constraint-compare-20260419T020000Z")

    assert metadata["batch_id"] == "flux2-constraint-compare-20260419T020000Z"
    assert metadata["workflow_name"] == "image_flux2_text_to_image.json"
    assert metadata["workflow_target"] == "flux2_repo_constraint_comparison"
    assert metadata["constraint_modes"] == ["raw", "constrained"]
    assert metadata["cases"] == ["F001", "F002", "F003", "F004"]
    assert metadata["prompt_families"] == {"F001": "A1", "F002": "A3", "F003": "A1", "F004": "R3"}


def test_build_constraint_prompt_applies_repo_single_keyframe_layer():
    prompt = module.build_constraint_prompt("A young woman under station light with reflective glass.")

    assert "single cinematic keyframe" in prompt
    assert "one uninterrupted composition" in prompt
    assert "no split screen" in prompt


def test_save_results_writes_json_contract(tmp_path):
    batch_dir = tmp_path / "flux2-constraint-compare-20260419T020000Z"
    batch_dir.mkdir(parents=True)
    metadata = module.build_batch_metadata(batch_id="flux2-constraint-compare-20260419T020000Z")
    runs = [
        {
            "run_id": "F001_A1_raw_s1001",
            "case_id": "F001",
            "prompt_family": "A1",
            "constraint_mode": "raw",
            "seed": 1001,
            "prompt_text": "prompt",
            "workflow_name": "image_flux2_text_to_image.json",
            "workflow_target": "flux2_repo_constraint_comparison",
            "output_path": "/tmp/out.png",
            "review_status": "pending_manual_review",
        }
    ]

    results_path = module.save_results(batch_dir=batch_dir, metadata=metadata, runs=runs)

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["batch_id"] == "flux2-constraint-compare-20260419T020000Z"
    assert payload["runs"][0]["run_id"] == "F001_A1_raw_s1001"
