import ai_mv.core.artifacts.dashboard as dashboard
import ai_mv.core.artifacts.manifest as manifest
import ai_mv.core.artifacts.summary as summary


def test_artifacts_safe_on_partial_payload(monkeypatch):
    calls = []

    def _sink(path, data):
        calls.append((path, data))

    monkeypatch.setattr(manifest, "write_json", _sink)
    monkeypatch.setattr(summary, "write_json", _sink)
    monkeypatch.setattr(dashboard, "write_json", _sink)

    state = {
        "run_id": "r1",
        "status": "failed",
        "failure_reason": "tti failed",
        "completed_stages": ["acestep_music"],
        "current_stage": "tti_anchor",
    }
    payload = {"audio_map": {"duration_sec": 20.0}}

    manifest.write_manifest(state, payload)
    summary.write_summary(state, payload)
    dashboard.write_dashboard(state, payload)

    assert len(calls) == 3
    assert all(isinstance(p, str) and isinstance(d, dict) for p, d in calls)
