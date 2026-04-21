from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.core.planning.sections import merged_shot_section_type, normalized_sections
from ai_mv.styles.citypop.rules import BRIDGE_CONNECTIVE_FAMILIES, INTRO_WORLD_FIRST_FAMILIES, OUTRO_RELEASE_FAMILIES


def test_plan_mv_builds_creative_direction_payload():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "dreamy synthwave night drive with lonely neon romance",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse", "start_sec": 3.0, "end_sec": 9.0},
                    {"name": "chorus", "start_sec": 9.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    creative_direction = out["creative_direction"]
    assert creative_direction["mv_mode"] == "visualizer"
    assert creative_direction["hook_visual"]
    assert creative_direction["emotional_arc"]
    assert creative_direction["chorus_intent"]
    assert creative_direction["bridge_intent"]
    assert creative_direction["continuity_rules"]
    assert creative_direction["continuity_mode"] == "strict"
    assert creative_direction["style_lane"] == out["style_lane"]
    assert creative_direction["section_count"] == 4
    assert out["section_plan"]
    assert out["section_plan"][0]["section_type"] == "intro"
    assert out["section_plan"][0]["section_id"] == "SEC_001"
    assert out["material_plan"]
    first_material = out["material_plan"][0]
    assert first_material["material_id"].startswith("MAT_")
    assert first_material["role"]
    assert first_material["style_lane"] == out["style_lane"]
    assert first_material["section_id"] == "SEC_001"
    assert first_material["mode_hint"]


def test_plan_mv_uses_audio_sections_and_stays_within_m1_bounds():
    payload = {
        "concept_text": "Japanese 80s city pop night drive, neon coast, bittersweet summer romance",
        "audio_map": {
            "duration_sec": 19.0,
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                {"name": "outro", "start_sec": 14.0, "end_sec": 19.0},
            ],
        },
    }

    out = build_plan_preview_payload({}, payload)

    shot_plan = out["shot_plan"]
    render_plan = out["render_plan"]
    assert 4 <= len(shot_plan) <= 6
    assert len(render_plan) == len(shot_plan)
    assert any(shot["section_type"] == "chorus" for shot in shot_plan)
    assert all(shot["render_mode"] in {"ia2v", "flf2v"} for shot in shot_plan)
    assert round(sum(float(shot["duration_sec"]) for shot in shot_plan), 3) == 19.0


def test_plan_mv_splits_long_sections_for_m1():
    payload = {
        "concept_text": "Japanese 80s city pop summer dusk",
        "audio_map": {
            "duration_sec": 18.0,
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                {"name": "verse", "start_sec": 3.0, "end_sec": 10.5},
                {"name": "chorus", "start_sec": 10.5, "end_sec": 15.0},
                {"name": "outro", "start_sec": 15.0, "end_sec": 18.0},
            ],
        },
    }

    out = build_plan_preview_payload({}, payload)

    verse_shots = [shot for shot in out["shot_plan"] if shot["section_type"] == "verse"]
    assert len(verse_shots) >= 2
    assert any(shot["visual_mode"] == "rain_window_detail" for shot in verse_shots)


def test_plan_mv_assigns_progressive_variants_within_long_section():
    out = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 8.0}},
        {
            "concept_text": "Japanese 80s city pop summer dusk",
            "audio_map": {
                "duration_sec": 40.0,
                "sections": [
                    {"name": "verse_1", "start_sec": 0.0, "end_sec": 28.0},
                    {"name": "chorus", "start_sec": 28.0, "end_sec": 40.0},
                ],
            },
        },
    )

    verse_shots = [shot for shot in out["shot_plan"] if shot["section_type"] == "verse"]
    assert [shot["shot_role"] for shot in verse_shots[:4]] == ["verse_setup", "verse_detail", "verse_flow", "verse_glow"]


def test_plan_mv_falls_back_without_audio_sections():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop summer dusk",
            "audio_map": {"duration_sec": 16.0, "sections": []},
        },
    )

    section_types = [shot["section_type"] for shot in out["shot_plan"]]
    assert section_types[0] == "intro"
    assert "chorus" in section_types
    assert section_types[-1] == "outro"
    assert [section["section_id"] for section in out["section_plan"]] == [f"SEC_{idx:03d}" for idx in range(1, len(out["section_plan"]) + 1)]
    intro_shot = out["shot_plan"][0]
    outro_shot = out["shot_plan"][-1]
    assert intro_shot["visual_mode"] in INTRO_WORLD_FIRST_FAMILIES
    assert outro_shot["visual_mode"] in OUTRO_RELEASE_FAMILIES


def test_plan_mv_keeps_world_first_opener_when_m1_window_merges_intro_into_verse():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights",
            "audio_map": {
                "duration_sec": 18.024,
                "sections": [
                    {"name": "intro", "label": "Intro", "start_sec": 0.0, "end_sec": 2.06},
                    {"name": "verse_1", "label": "Verse 1", "start_sec": 2.06, "end_sec": 4.305},
                    {"name": "pre_chorus", "label": "Pre-Chorus", "start_sec": 4.305, "end_sec": 6.536},
                    {"name": "chorus", "label": "Chorus", "start_sec": 6.536, "end_sec": 8.796},
                    {"name": "verse_2", "label": "Verse 2", "start_sec": 8.796, "end_sec": 11.019},
                    {"name": "bridge", "label": "Bridge", "start_sec": 11.019, "end_sec": 12.156},
                    {"name": "chorus", "label": "Final Chorus", "start_sec": 12.156, "end_sec": 16.478},
                    {"name": "outro", "label": "Outro", "start_sec": 16.478, "end_sec": 18.024},
                ],
            },
        },
    )

    opener = out["shot_plan"][0]
    opener_render = out["render_plan"][0]
    assert opener["section_name"] == "Intro->Verse 1"
    assert opener["visual_mode"] in INTRO_WORLD_FIRST_FAMILIES
    assert opener["framing_intent"] == "establishing_wide"
    assert any(
        token in opener_render["prompt_seed"]
        for token in (
            "rain-slick boulevard",
            "roadway depth",
            "small figure",
            "distant human presence",
            "city lights",
        )
    )


def test_plan_mv_uses_allowed_connective_family_for_bridge_sections():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "verse_1", "start_sec": 0.0, "end_sec": 5.0},
                    {"name": "bridge", "start_sec": 5.0, "end_sec": 9.0},
                    {"name": "chorus", "start_sec": 9.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    bridge_shots = [shot for shot in out["shot_plan"] if shot["section_type"] == "bridge"]
    assert bridge_shots
    assert all(shot["visual_mode"] in BRIDGE_CONNECTIVE_FAMILIES for shot in bridge_shots)
    assert all(shot["framing_intent"] == "connective_medium" for shot in bridge_shots)


def test_plan_mv_builds_rich_render_prompts():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 15.0,
                "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 15.0}],
            },
        },
    )

    item = out["render_plan"][0]
    assert "Japanese 80s city pop music video" in item["prompt_seed"]
    assert "same protagonist" in item["prompt_seed"]
    assert "same summer night-drive world" in item["prompt_seed"]
    assert "scene event:" not in item["prompt_seed"]
    assert item["prompt_draft"]
    assert item["prompt_polish"]
    assert item["audio_segment"] == {"start_sec": 0.0, "duration_sec": 7.5}


def test_plan_mv_threads_expressive_continuity_mode_into_direction_and_prompts():
    out = build_plan_preview_payload(
        {"planning": {"continuity_mode": "expressive"}},
        {
            "concept_text": "late-night city pop walk under wet neon lights",
            "audio_map": {
                "duration_sec": 12.0,
                "sections": [{"name": "bridge", "start_sec": 0.0, "end_sec": 12.0}],
            },
        },
    )

    assert out["creative_direction"]["continuity_mode"] == "expressive"
    assert any("allow intentional visual resets" in rule for rule in out["creative_direction"]["continuity_rules"])
    item = out["render_plan"][0]
    assert "same protagonist" not in item["prompt_seed"]
    assert "same summer night-drive world" not in item["prompt_seed"]
    assert "allowing a deliberate visual reset" in item["prompt_seed"]


def test_plan_mv_uses_prechorus_progression_hint_before_chorus_hint():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 12.0,
                "sections": [{"name": "pre_chorus", "start_sec": 0.0, "end_sec": 12.0}],
            },
        },
    )

    item = out["render_plan"][0]
    assert "anticipation tightens before the lift" in item["prompt_seed"]


def test_plan_mv_can_route_ia2v_for_chorus_when_enabled():
    out = build_plan_preview_payload(
        {
            "planning": {
                "enable_ia2v": True,
                "max_ia2v_shots": 2,
                "ia2v_min_sec": 4.0,
                "ia2v_max_sec": 8.0,
            }
        },
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 19.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "chorus_2", "start_sec": 14.0, "end_sec": 19.0},
                ],
            },
        },
    )

    chorus_shots = [shot for shot in out["shot_plan"] if shot["section_type"] == "chorus"]
    ia2v_shots = [shot for shot in chorus_shots if shot["render_mode"] == "ia2v"]
    assert ia2v_shots
    assert len(ia2v_shots) <= 2
    assert all(4.0 <= float(shot["duration_sec"]) <= 8.0 for shot in ia2v_shots)


def test_plan_mv_keeps_i2v_when_ia2v_is_disabled():
    out = build_plan_preview_payload(
        {"planning": {"enable_ia2v": False}},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "chorus", "start_sec": 3.0, "end_sec": 9.0},
                    {"name": "chorus_2", "start_sec": 9.0, "end_sec": 15.0},
                    {"name": "outro", "start_sec": 15.0, "end_sec": 18.0},
                ],
            },
        },
    )

    assert all(shot["render_mode"] == "i2v" for shot in out["shot_plan"])


def test_plan_mv_defaults_to_ia2v_centered_render_modes():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights",
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

    assert all(shot["render_mode"] == "ia2v" for shot in out["shot_plan"])


def test_plan_mv_can_route_flf2v_for_bridge_when_enabled():
    out = build_plan_preview_payload(
        {
            "planning": {
                "enable_flf2v": True,
                "max_flf2v_shots": 1,
                "flf2v_min_sec": 3.0,
                "flf2v_max_sec": 6.0,
            }
        },
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "pre_chorus", "start_sec": 8.0, "end_sec": 12.0},
                    {"name": "chorus", "start_sec": 12.0, "end_sec": 18.0},
                ],
            },
        },
    )

    flf2v_shots = [shot for shot in out["shot_plan"] if shot["render_mode"] == "flf2v"]
    assert len(flf2v_shots) == 1
    assert flf2v_shots[0]["bridge_to_shot_id"]
    render_item = next(item for item in out["render_plan"] if item["shot_id"] == flf2v_shots[0]["shot_id"])
    assert render_item["still_b"] == flf2v_shots[0]["bridge_to_shot_id"]
    assert flf2v_shots[0]["shot_role"] == "bridge_transition"
    assert flf2v_shots[0]["visual_mode"] == "bridge_transition"


def test_plan_mv_does_not_drop_tail_when_shot_count_exceeds_m1_max():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 20.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 2.0},
                    {"name": "verse_1", "start_sec": 2.0, "end_sec": 6.5},
                    {"name": "pre_chorus", "start_sec": 6.5, "end_sec": 10.0},
                    {"name": "chorus", "start_sec": 10.0, "end_sec": 14.5},
                    {"name": "verse_2", "start_sec": 14.5, "end_sec": 17.5},
                    {"name": "outro", "start_sec": 17.5, "end_sec": 20.0},
                ],
            },
        },
    )

    shot_plan = out["shot_plan"]
    assert len(shot_plan) <= 6
    assert round(float(shot_plan[-1]["end_sec"]), 3) == 20.0
    assert round(sum(float(shot["duration_sec"]) for shot in shot_plan), 3) == 20.0


def test_plan_mv_sorts_and_clamps_sections_before_building_shots():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 20.0,
                "sections": [
                    {"name": "chorus", "start_sec": 10.0, "end_sec": 25.0},
                    {"name": "intro", "start_sec": -1.0, "end_sec": 2.0},
                    {"name": "verse", "start_sec": 2.0, "end_sec": 10.0},
                ],
            },
        },
    )

    shot_plan = out["shot_plan"]
    assert float(shot_plan[0]["start_sec"]) == 0.0
    assert float(shot_plan[-1]["end_sec"]) == 20.0
    assert [shot["section_type"] for shot in shot_plan][:2] == ["intro", "verse"]


def test_plan_mv_prefers_more_prominent_section_type_when_merging_across_boundary():
    assert merged_shot_section_type({"section_type": "verse"}, {"section_type": "pre_chorus"}) == "pre_chorus"
    assert merged_shot_section_type({"section_type": "pre_chorus"}, {"section_type": "chorus"}) == "chorus"


def test_normalized_sections_can_be_used_from_core_planning_module():
    out = normalized_sections(
        {
            "sections": [
                {"name": "chorus", "start_sec": 10.0, "end_sec": 25.0},
                {"name": "intro", "start_sec": -1.0, "end_sec": 2.0},
                {"name": "verse", "start_sec": 2.0, "end_sec": 10.0},
            ]
        },
        20.0,
    )

    assert out[0]["section_type"] == "intro"
    assert out[0]["section_id"] == "SEC_001"
    assert [row["section_id"] for row in out] == [f"SEC_{idx:03d}" for idx in range(1, len(out) + 1)]
    assert float(out[-1]["end_sec"]) == 20.0
