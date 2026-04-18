from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / ".analysis" / "run_flux2_f004_repair_batch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("flux2_f004_repair_batch", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_f004_repair_runs_covers_all_variants_and_seeds():
    module = _load_module()

    runs = module.build_f004_repair_runs()

    assert len(runs) == 9
    assert runs[0]["run_id"] == "F004_R1_s1001"
    assert runs[-1]["run_id"] == "F004_R3_s1003"
    assert {row["case_id"] for row in runs} == {"F004"}
    assert {row["variant_id"] for row in runs} == {"R1", "R2", "R3"}
    assert {row["seed"] for row in runs} == {1001, 1002, 1003}
    assert all(row["workflow_name"] == "image_flux2_text_to_image.json" for row in runs)
    assert all(row["workflow_target"] == "flux2_f004_repair_base_still" for row in runs)


def test_build_batch_metadata_matches_f004_repair_contract():
    module = _load_module()

    metadata = module.build_batch_metadata(batch_id="flux2-f004-repair-20260419T010000Z")

    assert metadata["batch_id"] == "flux2-f004-repair-20260419T010000Z"
    assert metadata["workflow_name"] == "image_flux2_text_to_image.json"
    assert metadata["workflow_target"] == "flux2_f004_repair_base_still"
    assert metadata["case"] == "F004"
    assert metadata["variants"] == ["R1", "R2", "R3"]
    assert metadata["seeds"] == [1001, 1002, 1003]
    assert metadata["negative_mode"] == "none"


def test_save_results_writes_json_contract(tmp_path):
    module = _load_module()

    batch_dir = tmp_path / "flux2-f004-repair-20260419T010000Z"
    batch_dir.mkdir(parents=True)
    metadata = module.build_batch_metadata(batch_id="flux2-f004-repair-20260419T010000Z")
    runs = [
        {
            "run_id": "F004_R1_s1001",
            "case_id": "F004",
            "variant_id": "R1",
            "seed": 1001,
            "prompt_text": "prompt",
            "workflow_name": "image_flux2_text_to_image.json",
            "workflow_target": "flux2_f004_repair_base_still",
            "repo_constraints_mode": "raw_workflow_only",
            "output_path": "/tmp/out.png",
            "review_status": "pending_manual_review",
        }
    ]

    results_path = module.save_results(batch_dir=batch_dir, metadata=metadata, runs=runs)

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["batch_id"] == "flux2-f004-repair-20260419T010000Z"
    assert payload["runs"][0]["run_id"] == "F004_R1_s1001"


def test_pending_runs_skips_already_recorded_run_ids():
    module = _load_module()

    runs = module.build_f004_repair_runs()
    existing = [{"run_id": "F004_R1_s1001"}, {"run_id": "F004_R1_s1002"}]

    pending = module.pending_runs(runs, existing)

    assert len(pending) == 7
    assert pending[0]["run_id"] == "F004_R1_s1003"
