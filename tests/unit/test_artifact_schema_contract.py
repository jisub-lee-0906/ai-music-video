import importlib
from pathlib import Path

from ai_mv.core.artifacts import paths as artifact_paths
from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.utils.json_utils import read_json


def test_artifact_schema_module_exposes_canonical_schema_version():
    schema_module = importlib.import_module("ai_mv.core.artifacts.schema")

    assert schema_module.ARTIFACT_SCHEMA_VERSION == "ai_mv_schema_v2"
    assert schema_module.artifact_schema_version() == "ai_mv_schema_v2"



def test_readme_documents_run_summary_review_severity_contract():
    readme = Path(__file__).resolve().parents[2] / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines()
    run_summary_notes = [line for line in lines if "run_summary.json" in line]
    joined_notes = "\n".join(run_summary_notes)

    assert "`run_summary.json` is the compact operational summary" in joined_notes
    assert "`review_severity`" in joined_notes
    assert "`review_severity_drift`" in joined_notes
    assert "`review_severity_coverage`" in joined_notes
    assert "`review_severity_visual_quality`" in joined_notes
    assert "`review_severity_assembly_quality`" in joined_notes
    assert "`review_signal_buckets`" in joined_notes
    assert "`review_signal_bucket_failed_checks`" in joined_notes



def test_readme_documents_validate_latest_review_severity_handoff():
    readme = Path(__file__).resolve().parents[2] / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines()
    validate_latest_notes = [line for line in lines if "validate-latest" in line]

    assert any("validation-summary.json" in line for line in validate_latest_notes)
    assert any("review severity" in line for line in validate_latest_notes)
    assert any("review_signal_buckets" in line for line in validate_latest_notes)
    assert any("review_signal_bucket_failed_checks" in line for line in validate_latest_notes)
    assert any("`review_severity_drift`" in line for line in validate_latest_notes)
    assert any("`review_severity_coverage`" in line for line in validate_latest_notes)
    assert any("`review_severity_visual_quality`" in line for line in validate_latest_notes)
    assert any("`review_severity_assembly_quality`" in line for line in validate_latest_notes)



def test_failed_run_updates_latest_but_preserves_latest_success(monkeypatch, tmp_path):
    schema_module = importlib.import_module("ai_mv.core.artifacts.schema")
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)

    success_state = {
        "run_id": "run-success",
        "status": "done",
        "failure_reason": "",
        "current_stage": "publish",
        "completed_stages": ["plan", "publish"],
        "scope": "run",
    }
    failed_state = {
        "run_id": "run-failed",
        "status": "failed",
        "failure_reason": "render_timeout",
        "current_stage": "publish",
        "completed_stages": ["plan"],
        "scope": "run",
    }
    success_payload = {
        "concept_text": "successful run",
        "style_lane": "citypop",
        "style_resolution": {"style_lane": "citypop", "selection_source": "auto", "confidence": 0.9},
        "final_video": "success.mp4",
        "music_file": "success.mp3",
        "review_report": {"status": "done", "rerender_targets": []},
    }
    failed_payload = {
        "concept_text": "failed run",
        "style_lane": "dream_pop",
        "style_resolution": {"style_lane": "dream_pop", "selection_source": "auto", "confidence": 0.4},
        "final_video": "",
        "music_file": "failed.mp3",
        "review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]},
    }

    write_pipeline_artifacts(success_state, success_payload, {})
    success_latest_success_manifest = read_json(tmp_path / "artifacts" / "latest_success" / "manifest.json")
    success_latest_success_summary = read_json(tmp_path / "artifacts" / "latest_success" / "run_summary.json")

    write_pipeline_artifacts(failed_state, failed_payload, {})

    latest_manifest = read_json(tmp_path / "artifacts" / "latest" / "manifest.json")
    latest_summary = read_json(tmp_path / "artifacts" / "latest" / "run_summary.json")
    latest_success_manifest = read_json(tmp_path / "artifacts" / "latest_success" / "manifest.json")
    latest_success_summary = read_json(tmp_path / "artifacts" / "latest_success" / "run_summary.json")

    assert latest_manifest["run_id"] == "run-failed"
    assert latest_manifest["status"] == "failed"
    assert latest_manifest["schema_version"] == schema_module.ARTIFACT_SCHEMA_VERSION
    assert latest_summary["run_id"] == "run-failed"
    assert latest_summary["status"] == "failed"
    assert latest_summary["schema_version"] == schema_module.ARTIFACT_SCHEMA_VERSION

    assert latest_success_manifest == success_latest_success_manifest
    assert latest_success_summary == success_latest_success_summary
    assert latest_success_manifest["run_id"] == "run-success"
    assert latest_success_summary["run_id"] == "run-success"



def test_done_run_without_real_media_does_not_update_latest_success(monkeypatch, tmp_path):
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)

    fake_success_state = {
        "run_id": "test-smoke-stage",
        "status": "done",
        "failure_reason": "",
        "current_stage": "fake_stage",
        "completed_stages": ["fake_stage"],
        "scope": "run",
    }
    fake_success_payload = {
        "concept_text": "synthetic success",
        "style_lane": "citypop",
        "style_resolution": {"style_lane": "citypop", "selection_source": "auto", "confidence": 0.5},
        "final_video": "",
        "music_file": "",
        "review_report": {"status": ""},
    }

    write_pipeline_artifacts(fake_success_state, fake_success_payload, {})

    assert (tmp_path / "artifacts" / "latest" / "manifest.json").exists()
    assert (tmp_path / "artifacts" / "latest" / "run_summary.json").exists()
    assert not (tmp_path / "artifacts" / "latest_success" / "manifest.json").exists()
    assert not (tmp_path / "artifacts" / "latest_success" / "run_summary.json").exists()
