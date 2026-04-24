import json
from pathlib import Path

import ai_mv.entrypoints.audio_review_batch_score as entry


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
        },
        {
            "segment_id": "bridge_window",
            "scores": {"section_contrast_payoff": None, "vocal_lyric_delivery": None, "replay_value": None},
            "reason_codes": [],
            "notes": "",
        },
    ],
    "overall": {"weighted_score": None, "verdict": "", "recommended_next_action": ""},
}


def test_run_audio_review_batch_score_updates_multiple_segments_and_overall_fields(tmp_path, capsys):
    rubric_path = tmp_path / "audio-review-rubric.json"
    rubric_path.write_text(json.dumps(BASE_RUBRIC, indent=2) + "\n", encoding="utf-8")

    rc = entry.run_audio_review_batch_score(
        rubric_path=str(rubric_path),
        updates_json='['
        '{"segment_id":"first_chorus","scores":{"hook_memorability":2,"genre_fit":3,"mv_cue_strength":2},"reason_codes":["weak_hook","weak_mv_cues"],"notes":"hook weak"},'
        '{"segment_id":"bridge_window","scores":{"section_contrast_payoff":3,"vocal_lyric_delivery":2,"replay_value":2},"reason_codes":["muddy_vocals"],"notes":"vocal smear"}'
        ']',
        verdict="needs stronger hook and cleaner vocals",
        next_action="regenerate_audio",
    )
    out = capsys.readouterr().out

    payload = json.loads(rubric_path.read_text(encoding="utf-8"))
    first = next(row for row in payload["segments"] if row["segment_id"] == "first_chorus")
    bridge = next(row for row in payload["segments"] if row["segment_id"] == "bridge_window")
    assert rc == 0
    assert first["reason_codes"] == ["weak_hook", "weak_mv_cues"]
    assert bridge["reason_codes"] == ["muddy_vocals"]
    assert payload["overall"]["weighted_score"] == 47.06
    assert payload["overall"]["verdict"] == "needs stronger hook and cleaner vocals"
    assert payload["overall"]["recommended_next_action"] == "regenerate_audio"
    assert "updated_segments=2" in out
    assert "weighted_score=47.06" in out


def test_run_audio_review_batch_score_rejects_unknown_segment_id(tmp_path):
    rubric_path = tmp_path / "audio-review-rubric.json"
    rubric_path.write_text(json.dumps(BASE_RUBRIC, indent=2) + "\n", encoding="utf-8")

    try:
        entry.run_audio_review_batch_score(
            rubric_path=str(rubric_path),
            updates_json='[{"segment_id":"missing_segment","scores":{},"reason_codes":[],"notes":""}]',
            verdict="",
            next_action="",
        )
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "unknown audio review segment_id" in str(exc)

    assert raised
