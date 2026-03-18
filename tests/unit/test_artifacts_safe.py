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


def test_summary_write_skips_non_numeric_line_refs(monkeypatch):
    calls = []

    def _sink(path, data):
        calls.append((path, data))

    monkeypatch.setattr(summary, "write_json", _sink)

    state = {
        "run_id": "r2",
        "status": "done",
        "failure_reason": "",
        "completed_stages": ["acestep_music", "lyrics_timeline"],
        "current_stage": "visual_story_bible",
    }
    payload = {
        "lyrics_timeline": {
            "sections": [
                {
                    "section_name": "intro",
                    "section_label": "Intro",
                    "lines": [
                        {"line_index": 1, "text": "line 1"},
                        {"line_index": 2, "text": "line 2"},
                        {"line_index": 3, "text": "line 3"},
                    ],
                    "lyric_beats": [
                        {
                            "beat_id": "LB01",
                            "line_refs": ["1", "bad", None, -1, "2"],
                        }
                    ],
                }
            ]
        },
        "shot_timeline": {"shots": [{"lyric_beat_id": "LB01"}]},
    }

    summary.write_summary(state, payload)

    assert len(calls) == 3
