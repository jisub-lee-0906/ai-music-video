from pathlib import Path

from ai_mv.core.review.audio_review import load_audio_review_summary


def test_load_audio_review_summary_computes_weighted_score_and_prescription(tmp_path):
    rubric_path = tmp_path / "audio-review-rubric.json"
    rubric_path.write_text(
        """
{
  "scoring": {
    "weights": {
      "hook_memorability": 20,
      "section_contrast_payoff": 15,
      "genre_fit": 15,
      "vocal_lyric_delivery": 15,
      "mix_cleanliness": 15,
      "mv_cue_strength": 10,
      "replay_value": 10
    }
  },
  "segments": [
    {
      "segment_id": "first_chorus",
      "scores": {
        "hook_memorability": 2,
        "genre_fit": 3,
        "mv_cue_strength": 2
      },
      "reason_codes": ["weak_hook", "weak_mv_cues"],
      "notes": "hook is not landing"
    },
    {
      "segment_id": "bridge_window",
      "scores": {
        "section_contrast_payoff": 3,
        "vocal_lyric_delivery": 2,
        "replay_value": 2
      },
      "reason_codes": ["muddy_vocals"],
      "notes": "bridge vocal is smeared"
    }
  ],
  "overall": {
    "weighted_score": null,
    "verdict": "",
    "recommended_next_action": ""
  }
}
""".strip() + "\n",
        encoding="utf-8",
    )

    summary = load_audio_review_summary(str(rubric_path))

    assert summary["status"] == "reviewed"
    assert summary["weighted_score"] == 47.06
    assert summary["recommended_next_action"] == "regenerate_audio"
    assert summary["reason_codes"] == ["muddy_vocals", "weak_hook", "weak_mv_cues"]
    assert summary["prescription"]["fix_strategy"] == "strengthen_hook_and_clean_vocal_delivery"
    assert "hook_brief" in summary["prescription"]["prompt_contract_focus"]
