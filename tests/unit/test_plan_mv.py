import re

from ai_mv.core.planning.director_treatment import build_director_treatment
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


def test_plan_mv_builds_tti_identity_anchors_for_flux2_reference_keyframes():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights, missed train, unresolved goodbye turning into quiet resolve",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    anchor_package = out["anchor_package"]
    assert anchor_package["strategy"] == "white_background_tti_character_anchors_then_flux_reference_keyframes"
    assert [anchor["anchor_type"] for anchor in anchor_package["anchors"]] == [
        "character_upper_body_identity",
    ]
    assert all("world" not in str(anchor.get("anchor_id", "")).lower() for anchor in anchor_package["anchors"])
    assert all("world" not in str(anchor.get("anchor_type", "")).lower() for anchor in anchor_package["anchors"])
    assert all("world" not in str(anchor.get("material_class", "")).lower() for anchor in anchor_package["anchors"])
    upper_body = anchor_package["anchors"][0]
    assert upper_body["workflow_target"] == "image_flux2_text_to_image"
    assert "reference_anchor_ids" not in upper_body
    assert "upper-body character identity card" in upper_body["prompt_text"]
    assert "clear face visibility" in upper_body["prompt_text"]
    assert "face fingerprint" in upper_body["prompt_text"]
    assert "no distant human silhouettes" in upper_body["prompt_text"]
    full_body = next(anchor for anchor in anchor_package["pose_anchor_bank"] if anchor["anchor_id"] == "ANCHOR_CHARACTER_FULL_BODY")
    assert full_body["material_class"] == "character_reference_anchor"
    assert full_body["workflow_target"] == "image_flux2_reference_image"
    assert full_body["reference_anchor_ids"] == ["ANCHOR_CHARACTER_UPPER_BODY"]
    assert "same face identity" in full_body["prompt_text"]
    assert "exact face fingerprint" in full_body["prompt_text"]
    assert "single clean full-body identity reference card" in full_body["prompt_text"]
    assert "pure white seamless background" in full_body["prompt_text"]
    assert "No street" in full_body["prompt_text"]
    selected_pose_anchor_ids = {
        str(item.get("selected_pose_anchor_id", "")).strip()
        for item in out["render_plan"]
        if str(item.get("selected_pose_anchor_id", "")).strip()
    }
    pose_anchor_ids = {
        str(anchor.get("anchor_id", "")).strip()
        for anchor in anchor_package["pose_anchor_bank"]
        if str(anchor.get("anchor_id", "")).strip() != "ANCHOR_CHARACTER_FULL_BODY"
    }
    assert pose_anchor_ids == selected_pose_anchor_ids
    assert all(anchor["workflow_target"] == "image_flux2_reference_image" for anchor in anchor_package["pose_anchor_bank"])
    assert all(anchor["reference_anchor_ids"] == ["ANCHOR_CHARACTER_UPPER_BODY"] for anchor in anchor_package["pose_anchor_bank"])
    assert anchor_package["pose_anchor_policy"]["selection_policy"] == "full_body_and_story_selected_pose_anchors_are_generated_as_flux_ref_descendants"
    assert "world_character_anchor" not in anchor_package["variant_policy"]["reference_order"]
    assert anchor_package["variant_policy"]["important_story_functions"] == ["release", "payoff"]
    assert anchor_package["variant_policy"]["candidates_per_important_shot"] >= 2


def test_plan_mv_builds_director_treatment_and_threads_story_beats_into_shots_and_materials():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights, missed train, unresolved goodbye turning into quiet resolve",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    treatment = out["director_treatment"]
    assert treatment["story_logline"]
    assert treatment["protagonist_arc"]["start_state"]
    assert treatment["protagonist_arc"]["end_state"]
    assert len(treatment["story_beats"]) == len(out["section_plan"])
    assert treatment["story_beats"][0]["story_function"] == "wound_setup"
    assert any(beat["story_function"] == "release" for beat in treatment["story_beats"])
    assert treatment["story_beats"][-1]["story_function"] == "payoff"
    assert treatment["story_beats"][-1]["payoff_requirement"]
    assert any("Final shot must show a decision" in rule for rule in treatment["anti_repetition_rules"])

    beat_by_section = {beat["section_id"]: beat for beat in treatment["story_beats"]}
    for shot in out["shot_plan"]:
        beat = beat_by_section[shot["section_id"]]
        assert shot["story_beat_id"] == beat["beat_id"]
        assert shot["story_function"] == beat["story_function"]
        assert shot["visual_event"] == beat["visual_event"]
        assert shot["emotional_state"] == beat["emotional_state"]

    payoff_materials = [row for row in out["material_plan"] if row["story_function"] == "payoff"]
    assert payoff_materials
    assert all(row["role"] == "ending_resolution_still" for row in payoff_materials)
    payoff_render = next(item for item in out["render_plan"] if item["shot_id"] == payoff_materials[0]["shot_id"])
    assert "story function: payoff" in payoff_render["clip_positive_prompt"]
    assert "payoff requirement:" in payoff_render["clip_positive_prompt"]


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
    assert all(shot["render_mode"] in {"ia2v"} for shot in shot_plan)
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


def test_plan_mv_caps_hero_face_policy_overuse_in_short_fresh_sequences():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "citypop"}},
        {
            "concept_text": "late-night city walk under wet neon lights with one protagonist moving through the same boulevard world",
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

    roles = [item["production_policy"]["candidate_role"] for item in out["render_plan"]]
    assert roles.count("hero_face_performance") <= 3
    assert any(role in {"symbolic_insert", "world_bridge"} for role in roles[2:5])
    diversified_items = [
        item
        for item in out["render_plan"]
        if "sequence_role_diversity" in item["production_policy"].get("safety_rules", [])
    ]
    assert diversified_items
    diversified = diversified_items[0]
    assert "sequence diversity" in diversified["still_prompt_text"]
    assert "environment-led" in diversified["still_prompt_text"] or "symbolic insert" in diversified["still_prompt_text"]
    assert "sequence diversity" in diversified["clip_positive_prompt"]

    world_bridge_items = [
        item
        for item in out["render_plan"]
        if item["production_policy"]["candidate_role"] == "world_bridge"
    ]
    assert world_bridge_items
    assert all("role diversity world bridge" in item["still_prompt_text"] for item in world_bridge_items)
    assert all("avoid repeated centered front hero street walk" in item["still_prompt_text"] for item in world_bridge_items)


def test_plan_mv_threads_story_action_grammar_for_publishable_short_sequences():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "citypop"}},
        {
            "concept_text": "late-night city walk under wet neon rain with one protagonist following a message and choosing to let go",
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

    action_grammars = [shot["story_action_grammar"] for shot in out["shot_plan"]]
    assert len(set(action_grammars)) >= 4
    assert any("phone message" in grammar or "reflection cue" in grammar for grammar in action_grammars)
    assert any("walks away" in grammar or "turns away" in grammar for grammar in action_grammars)

    prompt_text = " ".join(item["clip_positive_prompt"] for item in out["render_plan"])
    assert "story action grammar:" in prompt_text
    assert "do not default to a static centered portrait" in prompt_text



def test_plan_mv_story_action_grammar_is_concept_specific_not_city_template():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "alt_pop"}},
        {
            "concept_text": "desert radio tower at sunrise, one protagonist follows a fading signal across dunes",
            "audio_map": {
                "duration_sec": 18.024,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.024},
                ],
            },
        },
    )

    grammar_text = " ".join(shot["story_action_grammar"] for shot in out["shot_plan"]).lower()
    prompt_text = " ".join(item["clip_positive_prompt"] for item in out["render_plan"]).lower()

    assert "desert" in grammar_text or "dune" in grammar_text or "radio" in grammar_text or "signal" in grammar_text
    assert "desert" in prompt_text or "dune" in prompt_text or "radio" in prompt_text or "signal" in prompt_text
    for leaked_city_token in ("rainy block", "wet neon", "boulevard", "missed train", "train station", "station timing"):
        assert leaked_city_token not in grammar_text
        assert leaked_city_token not in prompt_text
    assert out["creative_direction"]["wardrobe_anchor"] == "story-derived stable outfit silhouette"
    assert all(
        shot["continuity_contract"]["wardrobe_anchor"] == "story-derived stable outfit silhouette"
        for shot in out["shot_plan"]
    )
    assert "stable dark outerwear silhouette" not in prompt_text



def test_plan_mv_story_action_grammar_does_not_invent_city_fixture_actions_for_non_city_worlds():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "alt_pop"}},
        {
            "concept_text": "alt-pop forest pier music video, one solitary protagonist follows fireflies over moss and water",
            "audio_map": {
                "duration_sec": 18.024,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "bridge", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.024},
                ],
            },
        },
    )

    grammar_text = " ".join(shot["story_action_grammar"] for shot in out["shot_plan"]).lower()
    prompt_text = " ".join(item["clip_positive_prompt"] for item in out["render_plan"]).lower()

    assert "forest" in prompt_text or "fireflies" in prompt_text or "moss" in prompt_text or "water" in prompt_text
    for invented_fixture in (
        "sign or reflection detail",
        "rain-streaked glass",
        "curb",
        "reflective threshold",
        "afterglow",
    ):
        assert invented_fixture not in grammar_text
    for invented_prompt_phrase in (
        "story action grammar: uses a glance, hand, sign, or reflection detail",
        "story action grammar: reads a reflection cue through rain-streaked glass",
        "story action grammar: crosses through the frame or turns at the curb",
        "story action grammar: pauses at a reflective threshold",
        "story action grammar: walks away or turns away into the afterglow",
    ):
        assert invented_prompt_phrase not in prompt_text



def test_plan_mv_can_toggle_narrative_progression_fields_for_planning_spike():
    payload = {
        "concept_text": "desert radio tower at sunrise, one protagonist follows a fading signal across dunes",
        "audio_map": {
            "duration_sec": 18.024,
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                {"name": "outro", "start_sec": 14.0, "end_sec": 18.024},
            ],
        },
    }

    off = build_plan_preview_payload({"planning": {"default_style_name": "alt_pop"}}, payload)
    on = build_plan_preview_payload(
        {"planning": {"default_style_name": "alt_pop", "enable_narrative_progression": True}},
        payload,
    )

    assert all("narrative_progression" not in shot for shot in off["shot_plan"])
    assert all("narrative_progression" in shot for shot in on["shot_plan"])

    progressions = [shot["narrative_progression"] for shot in on["shot_plan"]]
    assert len({row["beat_role"] for row in progressions}) >= 4
    assert len({row["emotional_state"] for row in progressions}) >= 4
    assert len({row["motif_state"] for row in progressions}) >= 4
    assert len({row["pose_intent"] for row in progressions}) >= 4
    assert all(row["visible_change"] for row in progressions)
    assert all(row["motion_intent"] for row in progressions)

    off_prompt_text = " ".join(item["still_prompt_text"] + " " + item["clip_positive_prompt"] for item in off["render_plan"]).lower()
    on_prompt_text = " ".join(item["still_prompt_text"] + " " + item["clip_positive_prompt"] for item in on["render_plan"]).lower()

    assert "narrative motif state:" not in off_prompt_text
    assert "narrative visible change:" not in off_prompt_text
    assert "narrative motion intent:" not in off_prompt_text
    assert "narrative motif state:" in on_prompt_text
    assert "narrative visible change:" in on_prompt_text
    assert "narrative motion intent:" in on_prompt_text
    assert "radio" in on_prompt_text
    assert "signal" in on_prompt_text



def test_director_treatment_defaults_do_not_inject_night_world_for_non_night_concepts():
    treatment = build_director_treatment(
        concept_text="alt-pop forest pier music video, one solitary protagonist follows fireflies over moss and water",
        style_name="alt_pop",
        sections=[
            {"section_id": "SEC_001", "section_name": "Intro", "section_type": "intro"},
            {"section_id": "SEC_002", "section_name": "Outro", "section_type": "outro"},
        ],
    )

    text = str(treatment).lower()

    for leaked in ("night-world", "night-city", "city keeps reflecting", "unfinished goodbye"):
        assert leaked not in text
    assert "concept-world" in text



def test_plan_mv_concept_world_overrides_style_location_when_narrative_progression_enabled():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "alt_pop", "enable_narrative_progression": True}},
        {
            "concept_text": "desert radio tower at sunrise, one protagonist follows a fading signal across dunes",
            "audio_map": {
                "duration_sec": 18.024,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.024},
                ],
            },
        },
    )

    prompt_text = " ".join(
        item["prompt_seed"] + " " + item["still_prompt_text"] + " " + item["clip_positive_prompt"]
        for item in out["render_plan"]
    ).lower()
    world_anchor = out["creative_direction"]["world_anchor"].lower()

    assert "desert" in world_anchor
    assert "radio" in world_anchor
    assert "sunrise" in world_anchor
    assert "desert" in prompt_text
    assert "dune" in prompt_text
    assert "radio" in prompt_text
    assert "sunrise" in prompt_text
    for leaked_token in (
        "night rooftop",
        "glass corridor",
        "club-adjacent",
        "city backlight",
        "night street stride",
        "chrome reflections",
        "modern night-world",
        "night-world wound",
        "night-city world",
        "urban lighting",
        "city geometry",
        "city perspective",
        "chrome blue",
        "acid pink",
        "street walk",
        "wet neon",
        "boulevard",
        "street texture",
        "rooftop_edge",
        "glass_corridor",
        "night_street_stride",
        "chrome_reflections",
        "performance-night stage",
        "glossy performance-night stage",
    ):
        assert leaked_token not in prompt_text



def test_plan_mv_threads_white_background_identity_anchor_into_every_ia2v_clip_prompt():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "alt_pop", "enable_narrative_progression": True}},
        {
            "concept_text": "desert radio tower at sunrise, one protagonist follows a fading signal across dunes",
            "audio_map": {
                "duration_sec": 18.024,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.024},
                ],
            },
        },
    )

    ia2v_items = [item for item in out["render_plan"] if item["render_mode"] == "ia2v"]

    assert ia2v_items
    for item in ia2v_items:
        clip_text = f"{item['clip_prompt_seed']} {item['clip_positive_prompt']}".lower()
        assert "same lead performer identity" in clip_text
        assert "exact face fingerprint from the white-background identity anchor" in clip_text
        assert "one clear solo performer only" in clip_text
        assert "no bystanders or same-outfit background doubles" in clip_text



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


def test_plan_mv_threads_explicit_continuity_anchor_bundle_into_shots_and_render_prompts():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    creative_direction = out["creative_direction"]
    assert creative_direction["protagonist_anchor"]
    assert creative_direction["world_anchor"]
    assert all(shot["protagonist_anchor"] == creative_direction["protagonist_anchor"] for shot in out["shot_plan"])
    assert all(shot["world_anchor"] == creative_direction["world_anchor"] for shot in out["shot_plan"])
    assert all(item["prompt_seed"].count(creative_direction["protagonist_anchor"]) == 1 for item in out["render_plan"])
    assert all(item["prompt_seed"].count(creative_direction["world_anchor"]) == 1 for item in out["render_plan"])
    assert all("young woman" not in item["prompt_seed"] for item in out["render_plan"])


def test_plan_mv_wardrobe_fallback_does_not_inject_dark_outerwear_without_source():
    sample_payloads = [
        (
            {"planning": {"default_style_name": "synthwave"}},
            "synthwave arctic observatory music video, one solitary protagonist follows aurora pulses across ice",
        ),
        (
            {"planning": {"default_style_name": "alt_pop"}},
            "alt-pop night forest pier music video, one solitary protagonist follows fireflies over moss and water",
        ),
        (
            {},
            "late-night city pop walk under wet neon lights",
        ),
    ]

    for config, concept_text in sample_payloads:
        out = build_plan_preview_payload(
            config,
            {
                "concept_text": concept_text,
                "audio_map": {
                    "duration_sec": 18.0,
                    "sections": [
                        {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                        {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                        {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                        {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                    ],
                },
            },
        )

        model_facing_text = " ".join(
            item["workflow_prompts"]["flux2_ref_still"]["positive_text"]
            + " "
            + item["workflow_prompts"]["ltx_ia2v"]["positive_text"]
            for item in out["render_plan"]
        ).lower()
        planning_text = " ".join(
            [
                out["creative_direction"]["protagonist_anchor"],
                out["creative_direction"]["wardrobe_anchor"],
                *[shot["continuity_contract"]["wardrobe_anchor"] for shot in out["shot_plan"]],
            ]
        ).lower()

        assert "dark outerwear" not in planning_text
        assert "dark outerwear" not in model_facing_text
        assert out["creative_direction"]["wardrobe_anchor"] == "story-derived stable outfit silhouette"


def test_plan_mv_preserves_explicit_dark_outerwear_when_user_supplies_it():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights, one protagonist wearing a dark raincoat",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    assert out["creative_direction"]["wardrobe_anchor"] == "dark raincoat"
    assert all(shot["continuity_contract"]["wardrobe_anchor"] == "dark raincoat" for shot in out["shot_plan"])
    model_facing_text = " ".join(
        item["workflow_prompts"]["flux2_tti_anchor"]["positive_text"]
        if "flux2_tti_anchor" in item.get("workflow_prompts", {})
        else item["workflow_prompts"]["flux2_ref_still"]["positive_text"]
        for item in out["render_plan"]
    ).lower()
    assert "dark raincoat" in model_facing_text



def test_plan_mv_preserves_explicit_apron_and_windbreaker_as_identity_anchor_wardrobe():
    samples = [
        (
            "k-indie greenhouse music video, one solitary protagonist in a green apron tends small seedlings under warm glasshouse light, no books, no library, no rain, no city",
            "green apron",
        ),
        (
            "j-rock lighthouse cliff music video, one solitary protagonist in a red windbreaker faces a white lighthouse above dark ocean spray, no desert, no radio, no city",
            "red windbreaker",
        ),
    ]

    for concept_text, wardrobe in samples:
        out = build_plan_preview_payload(
            {},
            {
                "concept_text": concept_text,
                "audio_map": {
                    "duration_sec": 18.0,
                    "sections": [
                        {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                        {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                        {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                        {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                    ],
                },
            },
        )

        assert out["creative_direction"]["wardrobe_anchor"] == wardrobe
        assert all(shot["continuity_contract"]["wardrobe_anchor"] == wardrobe for shot in out["shot_plan"])
        anchor_positive = " ".join(
            anchor.get("workflow_prompts", {}).get("flux2_tti_anchor", {}).get("positive_text", "")
            for anchor in out["anchor_package"]["anchors"]
        ).lower()
        pose_prompt_texts = [
            anchor.get("workflow_prompts", {}).get("flux2_ref_anchor", {}).get("positive_text", "").lower()
            for anchor in out["anchor_package"]["pose_anchor_bank"]
        ]
        pose_positive = " ".join(pose_prompt_texts)
        assert wardrobe in anchor_positive
        assert wardrobe in pose_positive
        if wardrobe == "green apron":
            assert "simple neutral underlayer" in anchor_positive
            assert "simple neutral underlayer" in pose_positive
            assert all("simple neutral underlayer" in text for text in pose_prompt_texts if "green apron" in text)


def _all_positive_prompt_text(out: dict) -> str:
    fragments: list[str] = []
    fragments.append(str(out.get("creative_direction", {})))
    for shot in out.get("shot_plan", []):
        fragments.extend(
            [
                str(shot.get("story_action_grammar", "")),
                str(shot.get("story_contract", "")),
                str(shot.get("shot_relation_contract", "")),
                str(shot.get("continuity_contract", "")),
            ]
        )
    for item in out.get("render_plan", []):
        fragments.extend(
            [
                str(item.get("prompt_seed", "")),
                str(item.get("prompt_draft", "")),
                str(item.get("prompt_polish", "")),
                str(item.get("still_prompt_text", "")),
                str(item.get("clip_prompt_seed", "")),
                str(item.get("clip_positive_prompt", "")),
                str(item.get("workflow_prompts", {}).get("flux2_tti_anchor", {}).get("positive_text", "")),
                str(item.get("workflow_prompts", {}).get("flux2_ref_still", {}).get("positive_text", "")),
                str(item.get("workflow_prompts", {}).get("ltx_ia2v", {}).get("positive_text", "")),
            ]
        )
    return " ".join(fragments).lower()


def _contains_forbidden_literal(text: str, term: str) -> bool:
    if term in {"rain", "reflection", "book", "books", "library", "afterglow"}:
        pattern = {
            "book": r"\bbooks?\b",
            "books": r"\bbooks?\b",
        }.get(term, rf"\b{re.escape(term)}\b")
        return re.search(pattern, text) is not None
    return term in text


def test_plan_mv_residual_style_fixtures_do_not_leak_without_positive_source():
    sample_payloads = [
        (
            {"planning": {"default_style_name": "k_indie"}},
            "k-indie greenhouse music video, one solitary protagonist follows condensation across glass plants, no books or bookstore",
            ("book", "bookstore", "library", "rain", "rain-streaked glass", "afterglow"),
        ),
        (
            {"planning": {"default_style_name": "j_rock"}},
            "j-rock lighthouse cliffside music video, one solitary protagonist climbs toward a beacon over dry rocks, no rain or reflection",
            ("rain", "reflection", "rain-streaked glass"),
        ),
        (
            {"planning": {"default_style_name": "alt_pop"}},
            "alt-pop forest pier music video, one solitary protagonist follows fireflies over moss and water",
            ("afterglow", "rain", "reflection", "book", "library"),
        ),
    ]

    for config, concept_text, forbidden_terms in sample_payloads:
        out = build_plan_preview_payload(
            config,
            {
                "concept_text": concept_text,
                "audio_map": {
                    "duration_sec": 18.0,
                    "sections": [
                        {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                        {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                        {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                        {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                    ],
                },
            },
        )

        positive_text = _all_positive_prompt_text(out)
        for forbidden in forbidden_terms:
            assert not _contains_forbidden_literal(positive_text, forbidden)


def test_plan_mv_broad_static_breadth_fixtures_do_not_leak_into_model_prompts():
    samples = [
        (
            {"planning": {"default_style_name": "alt_pop"}},
            "alt-pop overcast forest pier music video, one solitary protagonist in a white cotton jacket walks from mossy trail to wooden pier, quiet uncertainty turning into calm resolve, no city, no curb, no rain, no reflection, no afterglow",
            ("rooftop", "afterglow"),
        ),
        (
            {"planning": {"default_style_name": "alt_pop"}},
            "bedroom alt-pop music video, one solitary protagonist listens to a small radio on a plain wooden desk, quiet uncertainty turning into calm resolve, stable blue cardigan",
            ("radio tower",),
        ),
    ]

    for config, concept_text, forbidden_terms in samples:
        out = build_plan_preview_payload(
            config,
            {
                "concept_text": concept_text,
                "audio_map": {
                    "duration_sec": 18.0,
                    "sections": [
                        {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                        {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                        {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                        {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                    ],
                },
            },
        )

        positive_text = _all_positive_prompt_text(out)
        story_grammar_text = " ".join(str(shot.get("story_action_grammar", "")) for shot in out["shot_plan"]).lower()
        for forbidden in forbidden_terms:
            assert forbidden not in positive_text
            assert forbidden not in story_grammar_text


def _contains_source_unbound_literal(text: str, term: str) -> bool:
    pattern = re.compile(re.escape(term), re.I) if " " in term or "-" in term else re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.I)
    for match in pattern.finditer(text):
        prefix = text[max(0, match.start() - 40):match.start()].lower()
        if re.search(r"(?:\bno\b|\bwithout\b|\bavoid\b|\bnot\b|\bexclude\b|\bexcluding\b)[^,.;:\n]{0,34}$", prefix):
            continue
        return True
    return False


def test_plan_mv_phase11_style_fixtures_do_not_override_positive_user_worlds():
    samples = [
        (
            {"planning": {"default_style_name": "citypop"}},
            "city-pop greenhouse music video, one solitary protagonist in a green apron tends seedlings under warm glasshouse light, no boulevard, no curb, no rain, no city, no neon",
            ("boulevard", "wet asphalt", "rain", "neon", "afterglow"),
            ("greenhouse", "green apron"),
        ),
        (
            {"planning": {"default_style_name": "k_indie"}},
            "k-indie greenhouse music video, one solitary protagonist in a green apron tends small seedlings under warm glasshouse light, no books, no library, no bookstore, no rain, no city",
            ("book", "books", "bookstore", "library", "rain"),
            ("greenhouse", "green apron"),
        ),
        (
            {"planning": {"default_style_name": "dream_pop"}},
            "dream-pop underwater glass tunnel music video, one solitary protagonist in a silver dress walks through blue aquarium light, no books, no library, no city rooftop, no rain, no afterglow",
            ("book", "books", "bookstore", "library", "rooftop", "street", "afterglow"),
            ("underwater", "aquarium", "silver dress"),
        ),
        (
            {"planning": {"default_style_name": "synthwave"}},
            "synthwave arctic research music video, one solitary protagonist in a silver parka crosses pale ice markers, no satellite, no satellite dish, no city, no rooftop, no dark outerwear, no neon",
            ("satellite", "city", "rooftop", "dark outerwear"),
            ("arctic", "silver parka"),
        ),
        (
            {"planning": {"default_style_name": "idol_pop"}},
            "idol-pop spring meadow music video, one solitary protagonist in a yellow cardigan follows paper kites across open grass, no stage, no crowd, no city, no neon, no dark outerwear",
            ("stage", "crowd", "city", "neon", "dark outerwear"),
            ("meadow", "yellow cardigan"),
        ),
    ]

    for config, concept_text, forbidden_terms, preserved_terms in samples:
        out = build_plan_preview_payload(
            config,
            {
                "concept_text": concept_text,
                "audio_map": {
                    "duration_sec": 18.0,
                    "sections": [
                        {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                        {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                        {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                        {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                    ],
                },
            },
        )
        assert out["workflow_prompt_lint"]["status"] == "pass", out["workflow_prompt_lint"]
        positive_text = _all_positive_prompt_text(out)
        for forbidden in forbidden_terms:
            assert not _contains_source_unbound_literal(positive_text, forbidden), (forbidden, positive_text)
        for preserved in preserved_terms:
            assert _contains_source_unbound_literal(positive_text, preserved), (preserved, positive_text)


def test_plan_mv_preserves_residual_terms_when_user_supplies_positive_source():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "j_rock"}},
        {
            "concept_text": "j-rock rain-soaked lighthouse music video, one protagonist watches reflections in tidal water beside old books",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    positive_text = _all_positive_prompt_text(out)
    assert "rain" in positive_text
    assert "reflection" in positive_text
    assert "books" in positive_text or "book" in positive_text


def test_plan_mv_emits_structured_continuity_and_neighbor_contracts():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    creative_direction = out["creative_direction"]
    first_shot = out["shot_plan"][0]
    second_shot = out["shot_plan"][1]

    assert first_shot["continuity_contract"] == {
        "protagonist_anchor": creative_direction["protagonist_anchor"],
        "world_anchor": creative_direction["world_anchor"],
        "wardrobe_anchor": "story-derived stable outfit silhouette",
        "no_competing_subjects": True,
        "time_band_anchor": "same concept time and lighting band",
    }
    assert first_shot["shot_relation_contract"] == {
        "relation_to_previous_shot": "sequence opener",
        "camera_distance_progression": "set baseline distance",
        "same_block_vs_new_block": "same block baseline",
        "emotional_delta": "establish opening emotional baseline",
    }
    assert second_shot["shot_relation_contract"]["relation_to_previous_shot"] == "continue same protagonist and world from previous shot"
    assert second_shot["shot_relation_contract"]["camera_distance_progression"]
    assert second_shot["shot_relation_contract"]["same_block_vs_new_block"]
    assert second_shot["shot_relation_contract"]["emotional_delta"]


def test_plan_mv_uses_idol_pop_relation_contracts_that_do_not_revert_to_lonely_baseline():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "idol_pop"}},
        {
            "concept_text": "bright idol pop city performance with glossy late-night lights",
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

    first_shot = out["shot_plan"][0]
    chorus_shot = next(shot for shot in out["shot_plan"] if shot["section_type"] == "chorus")
    first_render = out["render_plan"][0]
    chorus_render = next(item for item in out["render_plan"] if item["shot_id"] == chorus_shot["shot_id"])

    assert "dark outerwear silhouette" not in first_shot["protagonist_anchor"]
    assert "rain-slick neon boulevard world" not in first_shot["world_anchor"]
    assert first_shot["continuity_contract"]["wardrobe_anchor"] == "stable bright stage outfit silhouette"
    assert chorus_shot["framing_intent"] == "performance_medium"
    assert chorus_shot["workflow_intent"] == "audio_reactive_candidate"
    assert first_shot["shot_relation_contract"]["same_block_vs_new_block"] == "stage-ready city baseline"
    assert first_shot["shot_relation_contract"]["emotional_delta"] == "establish bright performance-night baseline"
    assert chorus_shot["shot_relation_contract"]["emotional_delta"] == "open into crowd-ready hook lift without losing world continuity"
    assert "opening emotional baseline" not in first_render["clip_positive_prompt"]
    assert "crowd-ready hook lift" in chorus_render["clip_positive_prompt"]


def test_plan_mv_keeps_idol_pop_opener_out_of_empty_boulevard_anchor_when_intro_merges_into_verse():
    from ai_mv.core.planning import shot_plan as shot_plan_module

    rows = [
        {
            'shot_id': 'S001',
            'section_name': 'Intro->Verse',
            'section_type': 'verse',
            'start_sec': 0.0,
            'shot_role': 'verse_confidence',
            'visual_mode': 'city_chorus_walk',
            'energy': 'medium',
        }
    ]

    preserved = shot_plan_module._restore_world_first_opener_after_m1_merge(rows, style_name='idol_pop')
    synthwave_preserved = shot_plan_module._restore_world_first_opener_after_m1_merge(rows, style_name='synthwave')
    restored = shot_plan_module._restore_world_first_opener_after_m1_merge(rows, style_name='citypop')

    assert preserved[0]['shot_role'] == 'verse_confidence'
    assert preserved[0]['visual_mode'] == 'city_chorus_walk'
    assert synthwave_preserved[0]['shot_role'] == 'verse_confidence'
    assert synthwave_preserved[0]['visual_mode'] == 'city_chorus_walk'
    assert restored[0]['shot_role'] == 'intro_mood'
    assert restored[0]['visual_mode'] == 'empty_boulevard_anchor'


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


def test_plan_mv_keeps_ia2v_when_legacy_disable_flag_is_present():
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

    assert all(shot["render_mode"] == "ia2v" for shot in out["shot_plan"])


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


def test_plan_mv_ignores_removed_legacy_clip_planning_keys():
    out = build_plan_preview_payload(
        {
            "planning": {
                "enable_audio_motion": True,
                "max_audio_motion_shots": 1,
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

    assert all(shot["render_mode"] == "ia2v" for shot in out["shot_plan"])
    expected_keys = {
        "shot_id",
        "section_id",
        "material_id",
        "render_mode",
        "render_count",
        "render_planning",
        "render_priority_score",
        "seed",
        "variation_seed",
        "variation_profile",
        "continuity_contract",
        "shot_relation_contract",
        "story_contract",
        "prompt_seed",
        "prompt_draft",
        "prompt_polish",
        "still_prompt_text",
        "clip_prompt_seed",
        "clip_positive_prompt",
        "edit_intent",
        "reference_mode",
        "reference_source_shot_id",
        "identity_lock_strength",
        "edit_variation_scope",
        "minimum_visual_delta",
        "production_policy",
        "candidate_role",
        "ia2v_risk_class",
        "anchor_reference_arm",
        "recommended_duration_sec",
        "pose_anchor_selection",
        "pose_action_need",
        "selected_pose_anchor_id",
        "workflow_prompts",
        "legacy_prompt_fields",
        "still_a",
        "audio_segment",
    }
    assert all(set(item) == expected_keys for item in out["render_plan"])



def test_plan_mv_keeps_anchor_source_prompts_free_of_followup_delta_language():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "late-night city pop walk under wet neon lights",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    anchor_sources = [item for item in out["render_plan"] if item["reference_mode"] in {"anchor_source", "performance_anchor_source"}]

    assert anchor_sources
    assert all("change camera distance or viewing angle from the anchor frame" not in item["still_prompt_text"] for item in anchor_sources)
    assert all("preserve face shape from the anchor still" not in item["still_prompt_text"] for item in anchor_sources)



def test_plan_mv_keeps_followup_reference_prompts_explicitly_delta_aware():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "bright idol-pop performance night on the same city stage",
            "audio_map": {
                "duration_sec": 18.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 3.0},
                    {"name": "verse_1", "start_sec": 3.0, "end_sec": 8.0},
                    {"name": "chorus", "start_sec": 8.0, "end_sec": 14.0},
                    {"name": "outro", "start_sec": 14.0, "end_sec": 18.0},
                ],
            },
        },
    )

    performance_followups = [item for item in out["render_plan"] if item["reference_mode"] == "use_performance_anchor_still"]
    general_followups = [item for item in out["render_plan"] if item["reference_mode"] == "use_anchor_still"]

    assert performance_followups
    assert all(item["edit_variation_scope"] == "performance_pose_upgrade" for item in performance_followups)
    assert all("preserve face shape from the anchor still" in item["still_prompt_text"] for item in performance_followups)
    assert all("avoid near-duplicate framing" in item["still_prompt_text"] for item in performance_followups)

    assert general_followups
    assert all(item["edit_variation_scope"] in {"framing_only", "bridge_reframe"} for item in general_followups)
    assert any("change camera distance or viewing angle from the anchor frame" in item["still_prompt_text"] for item in general_followups if item["edit_variation_scope"] == "framing_only")


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
