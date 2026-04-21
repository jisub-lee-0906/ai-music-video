from ai_mv.core.artifacts import paths as artifact_paths
from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.utils.json_utils import read_json


def test_preflight_artifacts_write_to_preflight_scope_and_do_not_touch_run_scope(monkeypatch, tmp_path):
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)

    write_pipeline_artifacts(
        {
            "run_id": "preflight-success",
            "status": "done",
            "failure_reason": "",
            "current_stage": "preflight",
            "completed_stages": ["audio", "plan"],
            "scope": "preflight",
        },
        {
            "concept_text": "dreamy synthwave night drive",
            "style_name": "synthwave",
            "style_resolution": {
                "style_name": "synthwave",
                "selection_source": "auto",
                "selection_stability": "stable",
                "confidence": 0.88,
            },
            "review_report": {
                "status": "done",
                "overall_status": "pass",
                "publishability_tier": "publishable",
                "recommended_next_action": "publish",
                "scores": {
                    "overall": 97.0,
                    "technical_completion": 98.0,
                    "material_quality": 96.0,
                    "final_mv_quality": 91.0,
                },
                "rerender_targets": [],
            },
        },
        {},
    )

    preflight_manifest = read_json(tmp_path / "artifacts" / "preflight" / "preflight-success" / "manifest.json")
    preflight_summary = read_json(tmp_path / "artifacts" / "preflight" / "preflight-success" / "run_summary.json")
    preflight_latest_manifest = read_json(tmp_path / "artifacts" / "preflight" / "latest" / "manifest.json")
    preflight_latest_summary = read_json(tmp_path / "artifacts" / "preflight" / "latest" / "run_summary.json")
    preflight_latest_success_manifest = read_json(tmp_path / "artifacts" / "preflight" / "latest_success" / "manifest.json")
    preflight_latest_success_summary = read_json(tmp_path / "artifacts" / "preflight" / "latest_success" / "run_summary.json")

    assert preflight_manifest["artifacts"] == {"scope": "preflight"}
    assert preflight_summary["scope"] == "preflight"
    assert preflight_summary["publishability_tier"] == "publishable"
    assert preflight_summary["overall_score"] == 97.0
    assert preflight_manifest == preflight_latest_manifest == preflight_latest_success_manifest
    assert preflight_summary == preflight_latest_summary == preflight_latest_success_summary
    assert not (tmp_path / "artifacts" / "latest" / "manifest.json").exists()
    assert not (tmp_path / "artifacts" / "latest_success" / "manifest.json").exists()


def test_failed_preflight_updates_preflight_latest_but_preserves_preflight_latest_success(monkeypatch, tmp_path):
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)

    success_state = {
        "run_id": "preflight-success",
        "status": "done",
        "failure_reason": "",
        "current_stage": "preflight",
        "completed_stages": ["audio", "plan"],
        "scope": "preflight",
    }
    failed_state = {
        "run_id": "preflight-failed",
        "status": "failed",
        "failure_reason": "plan: missing template",
        "current_stage": "plan",
        "completed_stages": ["audio"],
        "scope": "preflight",
    }

    write_pipeline_artifacts(
        success_state,
        {
            "concept_text": "successful preflight",
            "style_name": "citypop",
            "style_resolution": {"style_name": "citypop", "selection_source": "auto", "confidence": 0.9},
            "review_report": {
                "status": "done",
                "overall_status": "pass",
                "publishability_tier": "publishable",
                "recommended_next_action": "publish",
                "scores": {
                    "overall": 95.0,
                    "technical_completion": 96.0,
                    "material_quality": 94.0,
                    "final_mv_quality": 89.0,
                },
                "rerender_targets": [],
            },
        },
        {},
    )
    success_latest_success_manifest = read_json(tmp_path / "artifacts" / "preflight" / "latest_success" / "manifest.json")
    success_latest_success_summary = read_json(tmp_path / "artifacts" / "preflight" / "latest_success" / "run_summary.json")

    write_pipeline_artifacts(
        failed_state,
        {
            "concept_text": "failed preflight",
            "style_name": "dream_pop",
            "style_resolution": {"style_name": "dream_pop", "selection_source": "auto", "confidence": 0.4},
            "review_report": {
                "status": "needs_rerender",
                "overall_status": "review_required",
                "publishability_tier": "draft_only",
                "recommended_next_action": "review_failed_checks",
                "scores": {
                    "overall": 40.0,
                    "technical_completion": 30.0,
                    "material_quality": 60.0,
                    "final_mv_quality": 35.0,
                },
                "rerender_targets": ["S001"],
            },
        },
        {},
    )

    latest_manifest = read_json(tmp_path / "artifacts" / "preflight" / "latest" / "manifest.json")
    latest_summary = read_json(tmp_path / "artifacts" / "preflight" / "latest" / "run_summary.json")
    latest_success_manifest = read_json(tmp_path / "artifacts" / "preflight" / "latest_success" / "manifest.json")
    latest_success_summary = read_json(tmp_path / "artifacts" / "preflight" / "latest_success" / "run_summary.json")

    assert latest_manifest["run_id"] == "preflight-failed"
    assert latest_manifest["artifacts"] == {"scope": "preflight"}
    assert latest_summary["run_id"] == "preflight-failed"
    assert latest_summary["scope"] == "preflight"
    assert latest_summary["publishability_tier"] == "draft_only"
    assert latest_summary["overall_score"] == 40.0
    assert latest_success_manifest == success_latest_success_manifest
    assert latest_success_summary == success_latest_success_summary
    assert latest_success_manifest["run_id"] == "preflight-success"
    assert latest_success_summary["run_id"] == "preflight-success"
