import ai_mv.core.artifacts.manifest as manifest
import ai_mv.core.artifacts.summary as summary


def test_artifacts_safe_on_partial_payload(monkeypatch):
    calls = []

    def _sink(path, data):
        calls.append((path, data))

    monkeypatch.setattr(manifest, "write_json", _sink)
    monkeypatch.setattr(summary, "write_json", _sink)

    state = {
        "run_id": "r1",
        "status": "failed",
        "failure_reason": "tti failed",
        "completed_stages": ["acestep_music"],
        "current_stage": "shot_timeline",
    }
    payload = {"audio_map": {"duration_sec": 20.0}}

    manifest.write_manifest(state, payload)
    summary.write_summary(state, payload)

    assert len(calls) == 4
    paths = [str(p) for p, _ in calls]
    assert "artifacts/runs/r1/manifest.json" in paths[0].replace("\\", "/") or any("artifacts/runs/r1/manifest.json" in x.replace("\\", "/") for x in paths)
    assert any("artifacts/latest/manifest.json" in x.replace("\\", "/") for x in paths)
    assert any("artifacts/runs/r1/summary.json" in x.replace("\\", "/") for x in paths)
    assert any("artifacts/latest/summary.json" in x.replace("\\", "/") for x in paths)
    assert all(isinstance(d, dict) for _, d in calls)
