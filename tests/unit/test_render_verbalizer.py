from ai_mv.core.stages import render_verbalizer


def test_verbalize_ref_prompt_pairs_falls_back_without_codex(monkeypatch):
    rows = [
        {
            "shot_id": "S001",
            "subject_intro": "The same Korean female idol",
            "primary_surface": "rain-streaked station window and worn metal rail",
            "start_state": "She keeps one palm on the glass",
            "end_state": "She lets the contact soften",
            "story_event": "She steadies her breath without stopping",
            "section_label": "Verse 1",
            "support_detail": "raindrops sliding down the glass",
        }
    ]

    out = render_verbalizer.verbalize_ref_prompt_pairs({}, rows)

    assert out["S001"]["start_prompt_text"].startswith("The woman is keeping one palm on the glass.")
    assert "rain-streaked station window and worn metal rail" in out["S001"]["start_prompt_text"]
    assert "Raindrops sliding down the glass" in out["S001"]["start_prompt_text"]
    assert out["S001"]["start_prompt_text"].endswith("Keep the face.")
    assert "letting the contact soften" in out["S001"]["end_prompt_text"]


def test_verbalize_wan_prompts_falls_back_without_codex(monkeypatch):
    monkeypatch.setattr(render_verbalizer, "ping_codex", lambda _cfg: False)
    rows = [
        {
            "shot_id": "S002",
            "subject_intro": "The same Korean female idol",
            "location": "Along the wet platform edge",
            "bridge_action": "She takes the next step forward",
            "story_event": "The route stays tight beside her",
            "lighting": "at night",
        }
    ]

    out = render_verbalizer.verbalize_wan_prompts({}, rows)

    assert out["S002"] == (
        "The same Korean female idol. Along the wet platform edge. "
        "She takes the next step forward. The route stays tight beside her. at night."
    )
