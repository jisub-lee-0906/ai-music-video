from ai_mv.core.stages.plan_mv import build_plan_preview_payload


def test_plan_preview_threads_flexible_story_contract_into_every_shot_and_render_prompt():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "citypop", "max_shot_sec": 4.0}},
        {
            "concept_text": "late-night rain city-pop MV about an unfinished goodbye at the train station",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    treatment = out["director_treatment"]
    assert treatment["protagonist_arc"]["desire"]
    assert treatment["story_logline"]
    assert len(treatment["story_beats"]) == 4

    required_keys = {
        "why_this_shot",
        "protagonist_action",
        "section_alignment",
        "progression_from_previous",
        "visual_payoff",
        "anti_repetition_constraint",
    }
    for shot in out["shot_plan"]:
        story_contract = shot.get("story_contract")
        assert isinstance(story_contract, dict), shot["shot_id"]
        assert required_keys <= story_contract.keys(), shot["shot_id"]
        assert all(str(story_contract[key]).strip() for key in required_keys), shot["shot_id"]
        assert str(shot["section_type"]) in story_contract["section_alignment"]
        assert "generic mood" not in story_contract["why_this_shot"].lower()

    render_by_shot = {item["shot_id"]: item for item in out["render_plan"]}
    for shot in out["shot_plan"]:
        item = render_by_shot[shot["shot_id"]]
        assert item["story_contract"] == shot["story_contract"]
        prompt = " ".join(
            str(item.get(key, ""))
            for key in ("still_prompt_text", "clip_positive_prompt", "prompt_seed", "prompt_draft")
        )
        assert shot["story_contract"]["why_this_shot"] in prompt
        assert shot["story_contract"]["protagonist_action"] in prompt
        assert shot["story_contract"]["visual_payoff"] in prompt


def test_arctic_research_station_story_contract_does_not_invent_transit_or_ocean_motifs():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "synthwave", "max_shot_sec": 4.0}},
        {
            "concept_text": (
                "synthwave arctic research station music video, one explorer in a silver parka "
                "crosses wind-carved snow toward a warm signal beacon with no ocean and no lighthouse, "
                "no city, no rooftop, no satellite, no dark outerwear"
            ),
            "audio_map": {"duration_sec": 32.0},
        },
    )

    joined_contracts = " ".join(
        " ".join(str(value) for value in shot["story_contract"].values())
        for shot in out["shot_plan"]
    ).lower()
    joined_ltx = " ".join(
        item["workflow_prompts"]["ltx_ia2v"]["positive_text"]
        for item in out["render_plan"]
    ).lower()

    assert "arctic ice motif" in joined_contracts
    assert "source-bound direction cue" in joined_contracts
    assert "station timing and platform light" not in joined_contracts
    assert "platform light" not in joined_ltx
    assert "ocean horizon motif" not in joined_contracts
    assert "ocean horizon motif" not in joined_ltx
    assert "lighthouse cliff motif" not in joined_contracts
    assert "lighthouse cliff motif" not in joined_ltx


def test_plan_story_contract_is_not_fixed_to_neon_rain_or_train_scenes_for_other_concepts():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "synthwave", "max_shot_sec": 4.0}},
        {
            "concept_text": "desert sunrise synthwave MV about leaving a radio tower behind",
            "audio_map": {
                "duration_sec": 12.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "chorus", "start_sec": 3.0, "end_sec": 9.0},
                    {"name": "outro", "start_sec": 9.0, "end_sec": 12.0},
                ],
            },
        },
    )

    joined_contracts = " ".join(
        " ".join(str(value) for value in shot["story_contract"].values())
        for shot in out["shot_plan"]
    ).lower()
    assert "desert" in joined_contracts or "radio" in joined_contracts or "sunrise" in joined_contracts
    assert "train station" not in joined_contracts
    assert "rain-slick neon boulevard" not in joined_contracts
    assert "red raincoat" not in joined_contracts
