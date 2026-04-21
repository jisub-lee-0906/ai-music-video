import importlib

from ai_mv.core.artifacts import paths as artifact_paths
from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.utils.json_utils import read_json


def test_artifact_schema_module_exposes_canonical_schema_version():
    schema_module = importlib.import_module("ai_mv.core.artifacts.schema")

    assert schema_module.ARTIFACT_SCHEMA_VERSION == "ai_mv_schema_v1"
    assert schema_module.artifact_schema_version() == "ai_mv_schema_v1"



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
        "style_name": "citypop",
        "style_resolution": {"style_name": "citypop", "selection_source": "auto", "confidence": 0.9},
        "final_video": "success.mp4",
        "music_file": "success.mp3",
        "review_report": {"status": "done", "rerender_targets": []},
    }
    failed_payload = {
        "concept_text": "failed run",
        "style_name": "dream_pop",
        "style_resolution": {"style_name": "dream_pop", "selection_source": "auto", "confidence": 0.4},
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
