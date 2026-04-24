import json
from pathlib import Path

import ai_mv.entrypoints.audio_review_session as entry

BASE_RUBRIC = {
    "scoring": {
        "weights": {
            "hook_memorability": 20,
            "section_contrast_payoff": 15,
            "genre_fit": 15,
            "vocal_lyric_delivery": 15,
            "mix_cleanliness": 15,
            "mv_cue_strength": 10,
            "replay_value": 10,
        }
    },
    "segments": [
        {
            "segment_id": "first_chorus",
            "scores": {"hook_memorability": None, "genre_fit": None, "mv_cue_strength": None},
            "reason_codes": [],
            "notes": "",
        }
    ],
    "overall": {"weighted_score": None, "verdict": "", "recommended_next_action": ""},
}


def test_run_audio_review_session_updates_rubric_and_triggers_preflight(monkeypatch, tmp_path, capsys):
    rubric_path = tmp_path / "audio-review-rubric.json"
    rubric_path.write_text(json.dumps(BASE_RUBRIC, indent=2) + "\n", encoding="utf-8")
    seen = {}

    def _fake_batch(rubric_path, updates_json, verdict, next_action):
        seen["batch"] = (rubric_path, updates_json, verdict, next_action)
        payload = json.loads(Path(rubric_path).read_text(encoding="utf-8"))
        payload["segments"][0]["scores"] = {"hook_memorability": 2, "genre_fit": 3, "mv_cue_strength": 2}
        payload["segments"][0]["reason_codes"] = ["weak_hook"]
        payload["overall"]["weighted_score"] = 46.67
        payload["overall"]["verdict"] = verdict
        payload["overall"]["recommended_next_action"] = next_action
        Path(rubric_path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 0

    def _fake_reroll(rubric_path, run_id, concept_text, scope):
        seen["reroll"] = (rubric_path, run_id, concept_text, scope)
        return 0

    monkeypatch.setattr(entry, "run_audio_review_batch_score", _fake_batch)
    monkeypatch.setattr(entry, "run_audio_reroll_preflight", _fake_reroll)

    rc = entry.run_audio_review_session(
        rubric_path=str(rubric_path),
        updates_json='[{"segment_id":"first_chorus","scores":{"hook_memorability":2,"genre_fit":3,"mv_cue_strength":2},"reason_codes":["weak_hook"],"notes":"hook weak"}]',
        verdict="needs stronger hook",
        next_action="regenerate_audio",
        reroll_mode="preflight",
        run_id="audio-session-123",
        concept_text=None,
        scope="run",
    )
    out = capsys.readouterr().out
    payload = json.loads(rubric_path.read_text(encoding="utf-8"))

    assert rc == 0
    assert seen["batch"][0] == str(rubric_path)
    assert seen["reroll"] == (str(rubric_path), "audio-session-123", None, "run")
    assert payload["overall"]["weighted_score"] == 46.67
    assert "reroll_mode=preflight" in out
    assert "weighted_score=46.67" in out



def test_run_audio_review_session_skips_reroll_when_mode_none(monkeypatch, tmp_path, capsys):
    rubric_path = tmp_path / "audio-review-rubric.json"
    rubric_path.write_text(json.dumps(BASE_RUBRIC, indent=2) + "\n", encoding="utf-8")
    seen = {}

    def _fake_batch(rubric_path, updates_json, verdict, next_action):
        seen["batch"] = True
        payload = json.loads(Path(rubric_path).read_text(encoding="utf-8"))
        payload["overall"]["weighted_score"] = 88.0
        payload["overall"]["verdict"] = verdict
        payload["overall"]["recommended_next_action"] = next_action or "publish"
        Path(rubric_path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(entry, "run_audio_review_batch_score", _fake_batch)
    monkeypatch.setattr(
        entry,
        "run_audio_reroll_preflight",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call preflight reroll")),
    )
    monkeypatch.setattr(
        entry,
        "run_audio_reroll_start",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call start reroll")),
    )

    rc = entry.run_audio_review_session(
        rubric_path=str(rubric_path),
        updates_json='[]',
        verdict="good enough",
        next_action="publish",
        reroll_mode="none",
        run_id="audio-session-456",
        concept_text=None,
        scope="run",
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert seen["batch"] is True
    assert "reroll_mode=none" in out
