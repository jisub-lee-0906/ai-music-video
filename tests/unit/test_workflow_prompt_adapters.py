from __future__ import annotations

import re

from ai_mv.core.planning.workflow_prompt_adapters import (
    adapt_acestep_audio_prompt,
    adapt_flux2_ref_still_prompt,
    adapt_flux2_tti_anchor_prompt,
    adapt_ltx_ia2v_prompt,
    build_workflow_prompt_payloads,
    parse_user_intent_contract,
)
from ai_mv.core.planning.workflow_prompt_lint import lint_workflow_prompts
from ai_mv.core.stages.plan_mv import build_plan_preview_payload

DOCS_DEFAULT_CONCEPT = (
    "alt-pop desert radio music video, one solitary protagonist follows a fading signal across sunrise dunes "
    "toward a distant radio tower, quiet uncertainty turning into calm resolve, stable wardrobe silhouette, "
    "no crowd, no second protagonist, no city or neon"
)

META_LABELS = (
    "shot purpose:",
    "story function:",
    "story visual event:",
    "section alignment:",
    "story progression:",
    "visual payoff:",
    "anti repetition:",
    "protagonist action:",
    "story action grammar:",
)

NEGATIVE_CLAUSE_RE = re.compile(r"\b(no|avoid|do not|without|never|exclude|not a)\b", re.I)


def _docs_default_preview() -> dict:
    return build_plan_preview_payload({}, {"concept_text": DOCS_DEFAULT_CONCEPT, "audio_map": {"duration_sec": 24}})


def test_user_intent_contract_splits_positive_world_and_forbidden_clauses():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)

    assert contract["genre"] == "alt-pop music video"
    assert contract["protagonist"]["count"] == "one"
    assert contract["protagonist"]["gender"] == "unspecified"
    assert "desert radio music video" in contract["world"]["positive_description"]
    assert "sunrise dunes" in contract["world"]["positive_description"]
    assert "distant radio tower" in contract["world"]["motifs"]
    assert contract["world"]["forbidden"] == ["crowd", "second protagonist", "city", "neon"]
    assert "no city" not in contract["world"]["positive_description"].lower()


def test_flux2_tti_anchor_prompt_is_concrete_short_and_does_not_reference_prior_anchor():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)

    prompt = adapt_flux2_tti_anchor_prompt(contract, anchor={"anchor_id": "ANCHOR_CHARACTER_UPPER_BODY"})["positive_text"]
    lower = prompt.lower()

    assert len(prompt) <= 900
    assert "adult protagonist" in lower
    assert "seamless pure white studio background" in lower
    assert "stable wardrobe silhouette" in lower
    assert "light olive-gray desert travel overshirt" in lower
    assert contract["protagonist"]["wardrobe_source"] == "docs_default_stable_silhouette_inferred"
    assert contract["protagonist"]["wardrobe_source_text"] == "stable wardrobe silhouette"
    assert contract["protagonist"]["wardrobe_inference_guard"] == "desert_radio_docs_default"
    assert "reference image" not in lower
    assert "from the identity anchor" not in lower
    assert "young woman" not in lower
    assert "city" not in lower
    assert "neon" not in lower


def test_flux2_reference_still_adapter_removes_meta_labels_and_keeps_visual_action():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)
    render_item = {
        "shot_id": "S002",
        "still_prompt_text": (
            "story function: search beat, protagonist action: follow the first radio signal trace across the dunes, "
            "section alignment: quiet uncertainty, anti repetition: avoid repeating centered front hero pose, "
            "preserve the same lead identity, no distant human silhouettes"
        ),
        "story_contract": {
            "protagonist_action": "follow the first radio signal trace across the dunes",
            "section_alignment": "quiet uncertainty",
        },
        "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
    }

    payload = adapt_flux2_ref_still_prompt(contract, render_item)
    text = payload["positive_text"]
    lower = text.lower()

    assert len(text) <= 1200
    assert "use the reference image as the character identity source" in lower
    assert "move the exact same person into the scene" in lower
    assert "same face shape" in lower
    assert "same facial proportions" in lower
    assert "same hairline" in lower
    assert "same hairstyle silhouette" in lower
    assert "same age impression" in lower
    assert "only change the background" in lower
    assert "distant radio tower" in lower
    assert "radio signal" not in lower
    assert "sunrise dunes" in lower
    assert not any(label in lower for label in META_LABELS)
    assert "avoid" not in lower
    assert "no distant human silhouettes" not in lower
    assert "distant human silhouettes" not in payload["negative_constraints"]


def test_flux2_reference_still_prompt_declares_ia2v_source_frame_quality_contract():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)
    render_item = {
        "shot_id": "S002",
        "still_prompt_text": "protagonist walks across sunrise dunes toward the distant radio tower",
        "story_contract": {"protagonist_action": "walk across sunrise dunes toward the distant radio tower"},
        "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
    }

    payload = adapt_flux2_ref_still_prompt(contract, render_item)
    positive = payload["positive_text"].lower()
    negative = ", ".join(payload["negative_constraints"]).lower()

    assert "ia2v source still frame" in positive
    assert "one clear physical action" in positive
    assert "natural grounded body pose" in positive
    assert "readable subject silhouette" in positive
    assert "visible direction of travel" in positive
    assert "concept world remains readable around the protagonist" in positive
    assert "extreme crop" in negative
    assert "cropped limbs" in negative
    assert "missing hands" in negative
    assert "fashion editorial pose" in negative
    assert "poster composition" in negative


def test_flux2_reference_still_prompt_adds_interaction_visibility_without_inventing_objects():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)
    render_item = {
        "shot_id": "S006",
        "still_prompt_text": "the protagonist checks a handheld radio while facing the distant radio tower",
    }

    payload = adapt_flux2_ref_still_prompt(contract, render_item)
    positive = payload["positive_text"].lower()

    assert "hands and source-proven object interaction are visible" in positive
    assert "radio remains readable as the only device" in positive
    assert "antenna spark" not in positive
    assert "broadcast console" not in positive


def test_flux2_reference_still_prompt_does_not_infer_device_from_radio_tower_world_text():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)
    render_item = {
        "shot_id": "S006",
        "still_prompt_text": "the protagonist checks the horizon while facing the distant radio tower",
    }

    payload = adapt_flux2_ref_still_prompt(contract, render_item)
    positive = payload["positive_text"].lower()

    assert "hands and source-proven object interaction are visible" in positive
    assert "radio remains readable as the only device" not in positive


def test_flux2_reference_still_prompt_payoff_prioritizes_face_readability_without_full_body_requirement():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)
    render_item = {
        "shot_id": "S025",
        "still_prompt_text": "calm resolve visible near the sunrise dunes",
        "story_contract": {"visual_payoff": "calm resolve visible"},
        "selected_pose_anchor_id": "ANCHOR_POSE_FINAL_PAYOFF_FRONT",
    }

    payload = adapt_flux2_ref_still_prompt(contract, render_item)
    positive = payload["positive_text"].lower()

    assert "payoff source still" in positive
    assert "face readable" in positive
    assert "wardrobe upper silhouette readable" in positive
    assert "background still recognizable but soft" in positive
    assert "full body visible" not in positive


def test_ltx_adapter_separates_negative_constraints_from_short_motion_prompt():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)
    render_item = {
        "shot_id": "S004",
        "clip_positive_prompt": (
            "story function: chorus release, story visual event: protagonist raises the radio toward the tower, "
            "beat-responsive camera motion, no bystanders or same-outfit background doubles, avoid near-duplicate framing"
        ),
        "story_contract": {
            "protagonist_action": "raise the radio toward the distant tower",
            "visual_payoff": "calm resolve becomes visible",
        },
        "recommended_duration_sec": {"min": 0.8, "max": 1.8},
    }

    payload = adapt_ltx_ia2v_prompt(contract, render_item, base_negative="pc game, cartoon")
    positive = payload["positive_text"].lower()
    negative = payload["negative_text"].lower()

    assert len(payload["positive_text"]) <= 900
    assert positive.startswith("scene:")
    assert "character:" in positive
    assert "exact same solo protagonist from the source still" in positive
    assert "preserve face shape" in positive
    assert "facial proportions" in positive
    assert "hairline" in positive
    assert "hairstyle silhouette" in positive
    assert "age impression" in positive
    assert "action:" in positive
    assert "camera:" in positive
    assert "raise the radio" in positive
    assert "story function:" not in positive
    assert not NEGATIVE_CLAUSE_RE.search(positive)
    assert "pc game" in negative
    assert "cartoon" in negative
    assert "different person" in negative
    assert "face morph" in negative
    assert "hairstyle change" in negative
    assert "hairline change" in negative
    assert "age change" in negative
    assert "wardrobe change" in negative
    assert "extra person" in negative
    assert "duplicate body" in negative
    assert "bystanders" not in negative
    assert "near-duplicate framing" not in negative


def test_acestep_audio_adapter_emits_short_music_tags_without_visual_forbidden_terms():
    contract = parse_user_intent_contract(DOCS_DEFAULT_CONCEPT)
    payload = adapt_acestep_audio_prompt(
        contract,
        {
            "genre_description": "Alt Pop: sparse desert textures, radio-static percussion, intimate solo vocal, calm resolve.",
            "tags": "alt pop, desert, radio, city, neon",
            "audio_direction": DOCS_DEFAULT_CONCEPT,
        },
    )
    tags = payload["tags"]
    lower = tags.lower()

    assert payload["workflow"] == "acestep"
    assert len(tags) <= 500
    assert "alt pop" in lower
    assert "intimate solo vocal" in lower
    assert "calm resolve" in lower
    assert "city" not in lower
    assert "neon" not in lower
    assert not NEGATIVE_CLAUSE_RE.search(tags)
    assert payload["negative_constraints"] == ["crowd", "second protagonist", "city", "neon"]


def test_docs_default_plan_exposes_workflow_optimized_prompt_payloads():
    plan = build_plan_preview_payload(
        {},
        {"concept_text": DOCS_DEFAULT_CONCEPT, "audio_map": {"duration_sec": 24}},
    )

    for item in plan["render_plan"]:
        still_payload = item["workflow_prompts"]["flux2_ref_still"]
        ltx_payload = item["workflow_prompts"]["ltx_ia2v"]
        still_text = still_payload["positive_text"].lower()
        ltx_text = ltx_payload["positive_text"].lower()

        assert len(still_payload["positive_text"]) <= 1200
        assert len(ltx_payload["positive_text"]) <= 900
        assert not any(label in still_text for label in META_LABELS)
        assert not any(label in ltx_text for label in META_LABELS)
        assert not NEGATIVE_CLAUSE_RE.search(ltx_text)
        assert "city" not in still_text
        assert "neon" not in still_text
        assert "city" in ltx_payload["negative_text"].lower()
        assert "neon" in ltx_payload["negative_text"].lower()


def test_docs_default_anchor_package_has_flux2_tti_workflow_prompt():
    from ai_mv.core.stages.plan_mv import build_plan_preview_payload

    plan = build_plan_preview_payload(
        {},
        {"concept_text": DOCS_DEFAULT_CONCEPT, "audio_map": {"duration_sec": 24}},
    )

    upper_anchor = next(
        anchor for anchor in plan["anchor_package"]["anchors"]
        if anchor["anchor_id"] == "ANCHOR_CHARACTER_UPPER_BODY"
    )
    prompt = upper_anchor["workflow_prompts"]["flux2_tti_anchor"]["positive_text"]

    assert len(prompt) <= 900
    assert "seamless pure white studio background" in prompt
    assert "one solitary adult protagonist" in prompt
    assert not NEGATIVE_CLAUSE_RE.search(prompt)
    assert not any(label in prompt.lower() for label in META_LABELS)



def test_docs_default_workflow_prompts_are_polished_and_deduped():
    preview = _docs_default_preview()
    texts = []
    negative_texts = []
    for anchor in preview["anchor_package"]["anchors"]:
        payload = anchor.get("workflow_prompts", {}).get("flux2_tti_anchor", {})
        if payload:
            texts.append(payload.get("positive_text", ""))
    for item in preview["render_plan"]:
        prompts = item["workflow_prompts"]
        texts.append(prompts["flux2_ref_still"]["positive_text"])
        texts.append(prompts["ltx_ia2v"]["positive_text"])
        negative_texts.append(prompts["ltx_ia2v"]["negative_text"])

    combined = "\n".join(texts + negative_texts).lower()
    assert "not a ." not in combined
    assert ".." not in combined
    assert "duplicate subject alt pop music video" not in combined
    assert " ," not in combined
    assert ";." not in combined
    assert "desert radio music video" in combined
    assert "sunrise dunes" in combined
    assert "distant radio tower" in combined
    assert "stable wardrobe silhouette" in combined
    for negative in negative_texts:
        parts = [part.strip().lower() for part in negative.split(",") if part.strip()]
        assert len(parts) == len(set(parts))


def test_plan_preview_publishes_workflow_prompt_lint_for_preflight_gate():
    preview = _docs_default_preview()

    lint = preview.get("workflow_prompt_lint")
    assert lint["status"] == "pass"
    assert lint["violations"] == []
    assert lint["workflow_rows"] >= 10
    assert lint["max_positive_chars_by_workflow"]["flux2_ref_still"] <= 1200
    assert lint["max_positive_chars_by_workflow"]["ltx_ia2v"] <= 900


def test_arctic_signal_beacon_plan_preview_has_polished_workflow_prompt_lint():
    preview = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 4.0, "default_style_name": "synthwave"}},
        {
            "concept_text": (
                "synthwave arctic research station music video, one explorer in a silver parka "
                "crosses wind-carved snow toward a warm signal beacon with no ocean and no lighthouse, "
                "no city, no rooftop, no satellite, no dark outerwear"
            ),
            "audio_map": {"duration_sec": 32.0},
        },
    )

    lint = preview.get("workflow_prompt_lint")
    assert lint["status"] == "pass"
    assert lint["violations"] == []
    combined_ltx = "\n".join(
        item["workflow_prompts"]["ltx_ia2v"]["positive_text"]
        for item in preview["render_plan"]
    )
    assert ";." not in combined_ltx
    assert "with  and" not in combined_ltx.lower()
    assert "with and" not in combined_ltx.lower()
    assert "no ocean" not in combined_ltx.lower()
    assert "no lighthouse" not in combined_ltx.lower()


def test_ltx_action_sentences_do_not_end_with_truncation_fragments():
    preview = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 4.0, "default_style_name": "alt_pop"}},
        {
            "concept_text": (
                "alt-pop desert radio music video, one solitary protagonist follows a fading signal "
                "across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, "
                "stable wardrobe silhouette, no crowd, no second protagonist, no city or neon"
            ),
            "audio_map": {"duration_sec": 168.0},
        },
    )

    bad = []
    for item in preview["render_plan"]:
        text = item["workflow_prompts"]["ltx_ia2v"]["positive_text"].lower()
        if re.search(r"\b(action|staging):[^.]*\b(as|at|for|from|in|into|of|the|through|to|using|with)\.", text):
            bad.append((item["shot_id"], text))
    assert bad == []


def test_default_fullrun_ltx_prompts_have_adjacent_shot_variation():
    preview = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 4.0, "default_style_name": "alt_pop"}},
        {
            "concept_text": (
                "alt-pop desert radio music video, one solitary protagonist follows a fading signal "
                "across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, "
                "stable wardrobe silhouette, no crowd, no second protagonist, no city or neon"
            ),
            "audio_map": {"duration_sec": 168.0},
        },
    )

    previous = None
    duplicates = []
    for item in preview["render_plan"]:
        text = item["workflow_prompts"]["ltx_ia2v"]["positive_text"]
        if previous and previous[1] == text:
            duplicates.append((previous[0], item["shot_id"]))
        previous = (item["shot_id"], text)
    assert duplicates == []


def test_flux_ref_still_prompts_lock_source_world_before_staging_and_reject_studio_fallback():
    preview = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 4.0, "default_style_name": "alt_pop"}},
        {
            "concept_text": (
                "alt-pop desert radio music video, one solitary protagonist follows a fading signal "
                "across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, "
                "stable wardrobe silhouette, no crowd, no second protagonist, no city or neon"
            ),
            "audio_map": {"duration_sec": 168.0},
        },
    )

    for item in preview["render_plan"]:
        prompt = item["workflow_prompts"]["flux2_ref_still"]["positive_text"].lower()
        negative = ", ".join(item["workflow_prompts"]["flux2_ref_still"].get("negative_constraints", [])).lower()
        assert "background/world: alt-pop desert radio music video" in prompt
        assert "sunrise dunes" in prompt
        assert "distant radio tower" in prompt
        assert "soft fill light keeps face and wardrobe readable" in prompt
        assert "radio signal motif" not in prompt
        assert "radio tower signal motif" not in prompt
        assert "floating broadcast icon" not in prompt
        assert "graphic signal icon" not in prompt
        assert prompt.index("background/world:") < prompt.index("shot-specific staging:")
        assert "shot action:" in prompt
        assert "source world" not in prompt
        assert "white background" in negative
        assert "plain studio backdrop" in negative
        assert "floating broadcast icon" in negative
        assert "graphic signal icon" in negative


def test_abstract_radio_signal_input_is_normalized_to_physical_world_and_actions():
    preview = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 4.0, "default_style_name": "alt_pop"}},
        {
            "concept_text": (
                "alt-pop desert radio music video, one solitary protagonist follows a fading signal "
                "across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, "
                "stable wardrobe silhouette, no crowd, no second protagonist, no city or neon"
            ),
            "audio_map": {"duration_sec": 168.0},
        },
    )

    source_contract = preview["render_plan"][0]["workflow_prompts"]["source_contract"]
    visual_brief = source_contract.get("visual_brief", {})
    assert "fading signal" in visual_brief.get("nonliteral_terms", [])
    assert "radio wave icon" in visual_brief.get("forbidden_interpretations", [])
    assert "distant radio tower" in visual_brief.get("physical_motifs", [])
    assert "sunrise dunes" in visual_brief.get("visible_setting", "")

    joined_positive = "\n".join(
        "\n".join(
            item["workflow_prompts"][workflow]["positive_text"]
            for workflow in ("flux2_ref_still", "ltx_ia2v")
        )
        for item in preview["render_plan"]
    ).lower()
    joined_contracts = " ".join(
        " ".join(str(value) for value in shot["story_contract"].values())
        for shot in preview["shot_plan"]
    ).lower()
    joined_negative = "\n".join(
        item["workflow_prompts"]["ltx_ia2v"]["negative_text"]
        for item in preview["render_plan"]
    ).lower()

    assert "distant radio tower" in joined_positive
    assert "sunrise dunes" in joined_positive
    assert "toward a distant radio tower" in joined_positive or "toward the distant radio tower" in joined_positive
    for forbidden_positive in (
        "fading signal",
        "radio signal",
        "signal trace",
        "radio wave",
        "radio signal motif",
        "radio tower signal motif",
        "floating broadcast icon",
        "graphic signal icon",
    ):
        assert forbidden_positive not in joined_positive
        assert forbidden_positive not in joined_contracts
    assert "radio wave icon" in joined_negative
    assert "graphic signal icon" in joined_negative


def test_abstract_signal_variants_and_radio_waves_do_not_literalize_in_positive_prompts():
    concepts = [
        "alt-pop desert radio music video, one solitary protagonist follows a weak signal across dunes toward a distant radio tower, calm resolve, no crowd",
        "alt-pop desert radio music video, one solitary protagonist follows a lost signal across dunes toward a distant radio tower, calm resolve, no crowd",
        "alt-pop desert radio music video, one solitary protagonist follows a dying signal across dunes toward a distant radio tower, calm resolve, no crowd",
        "alt-pop desert radio music video, one solitary protagonist follows radio waves across dunes toward a distant radio tower, calm resolve, no crowd",
    ]
    forbidden = (
        "weak signal",
        "lost signal",
        "dying signal",
        "fading signal",
        "radio signal",
        "radio wave",
        "radio waves",
        "waveform",
        "frequency trail",
        "signal trace",
        "visible setting",
    )
    for concept in concepts:
        preview = build_plan_preview_payload(
            {"planning": {"max_shot_sec": 4.0, "default_style_name": "alt_pop"}},
            {"concept_text": concept, "audio_map": {"duration_sec": 32.0}},
        )
        positive = "\n".join(
            "\n".join(
                item["workflow_prompts"][workflow]["positive_text"].lower()
                for workflow in ("flux2_ref_still", "ltx_ia2v")
            )
            for item in preview["render_plan"]
        )
        negative = "\n".join(item["workflow_prompts"]["ltx_ia2v"]["negative_text"].lower() for item in preview["render_plan"])
        assert "distant radio tower" in positive
        assert "toward a distant radio tower" in positive or "toward the distant radio tower" in positive
        for phrase in forbidden:
            assert phrase not in positive
        assert "radio wave icon" in negative
        assert "graphic signal icon" in negative


def test_desert_radio_without_tower_does_not_invent_tower_destination():
    contract = parse_user_intent_contract(
        "alt-pop desert radio music video, one solitary protagonist carries a small radio across dunes, calm resolve, no crowd"
    )
    payload = adapt_ltx_ia2v_prompt(contract, {"story_contract": {}})
    positive = payload["positive_text"].lower()
    assert "radio" in positive
    assert "desert" in positive or "dunes" in positive
    assert "tower" not in positive


def test_negative_tower_clause_prevents_tower_destination_from_visual_brief():
    contract = parse_user_intent_contract(
        "alt-pop desert radio music video, one solitary protagonist follows a weak signal across dunes with no tower, no crowd"
    )
    brief = contract["visual_brief"]
    assert "tower" not in " ".join(brief.get("physical_motifs", [])).lower()
    payload = adapt_ltx_ia2v_prompt(contract, {"story_contract": {}})
    assert "tower" not in payload["positive_text"].lower()


def test_model_facing_story_fields_are_normalized_even_if_story_contract_reintroduces_signal():
    contract = parse_user_intent_contract(
        "alt-pop desert radio music video, one solitary protagonist follows a fading signal across sunrise dunes toward a distant radio tower, calm resolve, no crowd"
    )
    render_item = {
        "shot_id": "S01",
        "section_type": "verse",
        "story_contract": {
            "protagonist_action": "The protagonist follows a fading signal.",
            "visual_event": "The camera tracks the weak signal trace across dunes.",
            "story_action_grammar": "the camera follows the weak signal trace across dunes",
        },
        "recommended_duration_sec": 4.0,
    }

    prompts = build_workflow_prompt_payloads(contract, render_item)
    positive = "\n".join(
        prompts[workflow]["positive_text"].lower()
        for workflow in ("flux2_ref_still", "ltx_ia2v")
    )

    assert "fading signal" not in positive
    assert "weak signal" not in positive
    assert "signal trace" not in positive
    assert "follows a fading signal" not in positive
    assert "follows the weak across dunes" not in positive
    assert "clear physical direction" in positive or "physical direction" in positive


def test_flux_ref_still_prompt_uses_generic_world_lock_without_source_bound_desert_or_tower():
    contract = parse_user_intent_contract(
        "quiet acoustic room music video, one solitary protagonist sits near a window, calm resolve, no crowd"
    )
    payload = adapt_flux2_ref_still_prompt(contract, {"story_contract": {"story_action_grammar": "hands rest still"}})
    prompt = payload["positive_text"].lower()

    assert "background/world: quiet acoustic room music video" in prompt
    assert "desert" not in prompt
    assert "radio tower" not in prompt
    assert "floating broadcast icon" in ", ".join(payload["negative_constraints"]).lower()


def test_source_bound_motif_state_progression_improves_music_video_arc_without_inventing_objects():
    preview = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 4.0, "default_style_name": "alt_pop"}},
        {
            "concept_text": (
                "alt-pop desert radio music video, one solitary protagonist follows a fading signal "
                "across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, "
                "stable wardrobe silhouette, no crowd, no second protagonist, no city or neon"
            ),
            "audio_map": {"duration_sec": 168.0},
        },
    )

    section_types = {section["section_id"]: section["section_type"] for section in preview["section_plan"]}
    section_texts: dict[str, str] = {}
    for item in preview["render_plan"]:
        section_type = section_types[item["section_id"]]
        section_texts.setdefault(section_type, "")
        section_texts[section_type] += "\n" + item["workflow_prompts"]["ltx_ia2v"]["positive_text"].lower()

    assert "distant radio tower starts as a distant orientation point" in section_texts["intro"]
    assert "distant radio tower becomes the direction of travel" in section_texts["verse"]
    assert "distant radio tower reads clearer as the destination" in section_texts["chorus"]
    assert "distant radio tower settles as the resolved destination" in section_texts["outro"]
    assert "distant radio tower" in "\n".join(section_texts.values())

    contract = parse_user_intent_contract(
        "alt-pop desert radio music video, one solitary protagonist follows a fading signal "
        "across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, "
        "stable wardrobe silhouette, no crowd, no second protagonist, no city or neon"
    )
    pre_chorus = adapt_ltx_ia2v_prompt(
        contract,
        {
            "section_type": "pre_chorus",
            "story_contract": {"protagonist_action": "The protagonist pauses at a visible decision point in the pre_chorus."},
        },
    )["positive_text"].lower()
    bridge = adapt_ltx_ia2v_prompt(
        contract,
        {
            "section_type": "bridge",
            "story_contract": {"protagonist_action": "The protagonist holds still through an internal bridge turn."},
        },
    )["positive_text"].lower()
    assert "distant radio tower pulls the protagonist into a visible turn" in pre_chorus
    assert "distant radio tower holds the frame in a suspended decision" in bridge

    combined = "\n".join(section_texts.values()) + "\n" + pre_chorus + "\n" + bridge
    for invented in ("map", "canteen", "water bottle", "antenna spark", "footprints", "noon heat"):
        assert invented not in combined
    for forbidden in ("no crowd", "no second protagonist", "no city", "no neon"):
        assert forbidden not in combined


def test_motif_state_progression_falls_back_without_radio_or_tower_contamination():
    preview = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 4.0, "default_style_name": "synthwave"}},
        {
            "concept_text": (
                "synthwave arctic research station music video, one explorer in a silver parka "
                "crosses wind-carved snow toward a warm signal beacon with no ocean and no lighthouse, "
                "no city, no rooftop, no satellite, no dark outerwear"
            ),
            "audio_map": {"duration_sec": 32.0},
        },
    )

    combined = "\n".join(
        item["workflow_prompts"]["ltx_ia2v"]["positive_text"].lower()
        for item in preview["render_plan"]
    )
    assert "signal beacon starts faint" in combined
    assert "signal beacon opens wider" in combined or "signal beacon feels more directional" in combined
    assert "radio" not in combined
    assert "tower" not in combined
    assert "ocean" not in combined
    assert "lighthouse" not in combined
    assert "satellite" not in combined


def test_inline_negative_clause_cleanup_leaves_polished_positive_world_text():

    contract = parse_user_intent_contract(
        "synthwave arctic research station music video, one explorer in a silver parka "
        "crosses wind-carved snow toward a warm signal beacon with no ocean and no lighthouse, "
        "no city, no rooftop"
    )

    positive = contract["positive_text"].lower()
    world = contract["world"]["positive_description"].lower()
    combined = f"{positive} {world}"
    assert "warm signal beacon" in combined
    assert "with no" not in combined
    assert "with  and" not in combined
    assert "with and" not in combined
    assert "no ocean" not in combined
    assert "no lighthouse" not in combined
    assert "ocean" not in world
    assert "lighthouse" not in world


def test_docs_default_adjacent_workflow_prompts_preserve_shot_diversity():
    preview = _docs_default_preview()
    stills = [item["workflow_prompts"]["flux2_ref_still"]["positive_text"] for item in preview["render_plan"]]
    clips = [item["workflow_prompts"]["ltx_ia2v"]["positive_text"] for item in preview["render_plan"]]

    for left, right in zip(stills, stills[1:]):
        assert left != right
    for left, right in zip(clips, clips[1:]):
        assert left != right
    lint = preview["workflow_prompt_lint"]
    assert not [v for v in lint["violations"] if "duplicate adjacent" in v["issue"]]


BREADTH_CONCEPT_SAMPLES = [
    {
        "name": "synthwave_arctic_observatory",
        "concept": (
            "synthwave arctic observatory music video, one solitary protagonist follows a pulsing aurora signal "
            "across blue ice toward a snow-covered satellite dish, anxious isolation turning into clear wonder, "
            "silver parka silhouette, no crowd, no second protagonist, no city or neon, avoid desert and radio tower"
        ),
        "required_visual_terms": ("arctic", "observatory", "aurora", "ice"),
        "required_negative_terms": ("city", "neon", "desert", "radio tower"),
        "forbidden_positive_terms": (
            "desert", "radio tower", "sunrise dunes", "young woman", "silent radio", "radio wound",
            "radio signal", "signal world", "neon_highway", "jacket and sand",
            "clear section-specific visual progression", "story-derived stable outfit silhouette",
        ),
    },
    {
        "name": "k_indie_greenhouse_rain",
        "concept": (
            "k-indie rainy greenhouse music video, a solo adult protagonist repairs a flickering cassette recorder "
            "among fogged glass plants before stepping into soft morning rain, grief opening into gentle courage, "
            "olive work jacket silhouette, without crowds or cars, avoid desert, avoid radio tower, no neon"
        ),
        "required_visual_terms": ("greenhouse", "rain", "cassette", "plants"),
        "required_negative_terms": ("crowds", "cars", "desert", "radio tower", "neon"),
        "forbidden_positive_terms": (
            "desert", "radio tower", "sunrise dunes", "young woman", "silent radio", "radio wound",
            "signal world", "crosswalk_wait", "jacket and sand",
            "clear section-specific visual progression", "story-derived stable outfit silhouette",
        ),
    },
    {
        "name": "j_rock_lighthouse_cliff",
        "concept": (
            "j-rock stormy cliffside lighthouse music video, one male protagonist carries a broken signal lantern "
            "up black rocks toward a rotating lighthouse beam, anger turning into release, wind-torn navy coat, "
            "no crowd, no second protagonist, avoid city, avoid school uniforms and choreography"
        ),
        "required_visual_terms": ("cliffside", "lighthouse", "lantern", "rocks"),
        "required_negative_terms": ("crowd", "second protagonist", "city", "school uniforms", "choreography"),
        "forbidden_positive_terms": (
            "desert", "radio tower", "sunrise dunes", "young woman", "live_house_entry",
            "amp_corridor", "jacket and sand", "clear section-specific visual progression",
            "story-derived stable outfit silhouette",
        ),
    },
    {
        "name": "dream_pop_underwater_library",
        "concept": (
            "dream-pop underwater library music video, one female protagonist drifts through floating books and pearl light "
            "toward a moonlit surface door, loneliness becoming soft acceptance, pale linen dress silhouette, "
            "no crowd, no second protagonist, no desert or radio tower, avoid city and neon"
        ),
        "required_visual_terms": ("underwater", "library", "floating books", "pearl light"),
        "required_negative_terms": ("crowd", "second protagonist", "desert", "radio tower", "city", "neon"),
        "forbidden_positive_terms": (
            "desert", "radio tower", "sunrise dunes", "young woman", "silent radio", "radio wound",
            "signal world", "window_haze", "jacket and sand",
            "clear section-specific visual progression", "story-derived stable outfit silhouette",
        ),
    },
]


def _visual_workflow_positive_texts(preview: dict) -> list[str]:
    texts: list[str] = []
    for anchor in preview["anchor_package"]["anchors"]:
        payload = anchor.get("workflow_prompts", {}).get("flux2_tti_anchor", {})
        if payload:
            texts.append(payload.get("positive_text", ""))
    for item in preview["render_plan"]:
        prompts = item["workflow_prompts"]
        texts.append(prompts["flux2_ref_still"]["positive_text"])
        texts.append(prompts["ltx_ia2v"]["positive_text"])
    return texts


def test_breadth_user_input_samples_keep_world_terms_and_do_not_leak_defaults():
    for sample in BREADTH_CONCEPT_SAMPLES:
        preview = build_plan_preview_payload({}, {"concept_text": sample["concept"], "audio_map": {"duration_sec": 24}})
        visual_positive = "\n".join(_visual_workflow_positive_texts(preview)).lower()
        ltx_negative = "\n".join(
            item["workflow_prompts"]["ltx_ia2v"]["negative_text"]
            for item in preview["render_plan"]
        ).lower()

        assert preview["workflow_prompt_lint"]["status"] == "pass", sample["name"]
        for term in sample["required_visual_terms"]:
            assert term in visual_positive, (sample["name"], term)
        for term in sample["required_negative_terms"]:
            assert term in ltx_negative, (sample["name"], term)
        for term in sample["forbidden_positive_terms"]:
            assert term not in visual_positive, (sample["name"], term)
        assert not NEGATIVE_CLAUSE_RE.search(visual_positive), sample["name"]


def test_breadth_user_input_samples_preserve_explicit_gender_without_hardcoding():
    expectations = {
        "synthwave_arctic_observatory": "androgynous presentation",
        "k_indie_greenhouse_rain": "androgynous presentation",
        "j_rock_lighthouse_cliff": "male presentation",
        "dream_pop_underwater_library": "female presentation",
    }
    for sample in BREADTH_CONCEPT_SAMPLES:
        contract = parse_user_intent_contract(sample["concept"])
        prompt = adapt_flux2_tti_anchor_prompt(contract)["positive_text"].lower()

        assert expectations[sample["name"]] in prompt, sample["name"]
        assert "young woman" not in prompt
        assert "young man" not in prompt



def test_workflow_prompt_lint_rejects_director_semantic_placeholders_and_internal_tokens():
    payload = {
        "render_plan": [
            {
                "shot_id": "S001",
                "workflow_prompts": {
                    "flux2_ref_still": {
                        "positive_text": "A protagonist in a greenhouse, crosswalk_wait, clear section-specific visual progression."
                    },
                    "ltx_ia2v": {
                        "positive_text": "camera: locked shot, natural wind motion in jacket and sand.",
                        "negative_text": "",
                    },
                },
            }
        ]
    }

    lint = lint_workflow_prompts(payload)

    assert lint["status"] == "fail"
    issues = "\n".join(v["issue"] for v in lint["violations"])
    assert "director placeholder" in issues
    assert "internal planning token" in issues
    assert "generic desert motion cue" in issues


def test_ltx_motion_cues_are_world_specific():
    expected = {
        "synthwave_arctic_observatory": ("snow gust", "aurora pulse", "satellite-dish"),
        "k_indie_greenhouse_rain": ("rain streaks", "leaves trembling", "condensation"),
        "j_rock_lighthouse_cliff": ("storm spray", "coat whip", "rotating lighthouse beam"),
        "dream_pop_underwater_library": ("floating fabric", "drifting books", "light caustics"),
    }
    for sample in BREADTH_CONCEPT_SAMPLES:
        preview = build_plan_preview_payload({}, {"concept_text": sample["concept"], "audio_map": {"duration_sec": 24}})
        ltx_positive = "\n".join(
            item["workflow_prompts"]["ltx_ia2v"]["positive_text"].lower()
            for item in preview["render_plan"]
        )
        assert "jacket and sand" not in ltx_positive, sample["name"]
        assert any(term in ltx_positive for term in expected[sample["name"]]), sample["name"]


def test_adapter_fallback_actions_are_visible_world_specific_actions():
    concept = (
        "dream-pop underwater library music video, one female protagonist drifts through floating books and pearl light "
        "toward a moonlit surface door, loneliness becoming soft acceptance, pale linen dress silhouette, "
        "no crowd, no second protagonist"
    )
    contract = parse_user_intent_contract(concept)
    render_item = {"shot_id": "S003", "story_contract": {}}

    still = adapt_flux2_ref_still_prompt(contract, render_item)["positive_text"].lower()
    ltx = adapt_ltx_ia2v_prompt(contract, render_item)["positive_text"].lower()

    combined = still + "\n" + ltx
    assert "clear section-specific visual progression" not in combined
    assert "concept-specific visual motif" not in combined
    assert any(
        term in combined
        for term in (
            "drifts through floating books",
            "reaches toward the moonlit surface door",
            "turns through pearl light",
        )
    )


def test_ltx_motion_cues_do_not_invent_unsupplied_world_objects():
    cases = [
        (
            "synthwave arctic aurora music video, one solitary protagonist crosses blue ice under pulsing sky light, "
            "silver parka silhouette, no city, no satellite dish",
            ("satellite-dish", "satellite dish", "city"),
            ("snow", "aurora", "ice"),
        ),
        (
            "dream-pop underwater chamber music video, one solitary protagonist moves through pearl light toward a surface door, "
            "pale linen dress silhouette, no library, no floating books, no city",
            ("drifting books", "floating books", "library", "city"),
            ("underwater", "pearl light", "surface door"),
        ),
    ]

    for concept, forbidden_terms, expected_terms in cases:
        contract = parse_user_intent_contract(concept)
        render_item = {"shot_id": "S003", "story_contract": {}, "selected_pose_anchor_id": "ANCHOR_POSE_THREE_QUARTER_MEDIUM"}
        ltx = adapt_ltx_ia2v_prompt(contract, render_item)["positive_text"].lower()

        for term in forbidden_terms:
            assert term not in ltx, (concept, term, ltx)
        assert any(term in ltx for term in expected_terms), (concept, ltx)


def test_desert_only_final_payoff_does_not_invent_radio_signal_or_tower():
    concept = (
        "alt-pop desert sunrise music video, one solitary protagonist crosses silent dunes toward a warm horizon, "
        "quiet uncertainty turning into calm resolve, linen travel jacket silhouette, no city, no neon"
    )
    contract = parse_user_intent_contract(concept)
    render_item = {
        "shot_id": "S004",
        "selected_pose_anchor_id": "ANCHOR_POSE_FINAL_PAYOFF_FRONT",
        "story_contract": {
            "story_function": "payoff",
            "visual_payoff": "calm resolve becomes visible at the horizon",
        },
    }

    still = adapt_flux2_ref_still_prompt(contract, render_item)["positive_text"].lower()
    ltx = adapt_ltx_ia2v_prompt(contract, render_item)["positive_text"].lower()
    combined = still + "\n" + ltx

    assert "desert" in combined or "dunes" in combined
    assert "radio signal" not in combined
    assert "resolved radio" not in combined
    assert "radio tower" not in combined
    assert "holding the resolved radio" not in combined


def test_docs_default_desert_radio_payoff_preserves_radio_when_source_bound():
    preview = _docs_default_preview()
    final_item = next(item for item in preview["render_plan"] if item["selected_pose_anchor_id"] == "ANCHOR_POSE_FINAL_PAYOFF_FRONT")
    still = final_item["workflow_prompts"]["flux2_ref_still"]["positive_text"].lower()
    ltx = final_item["workflow_prompts"]["ltx_ia2v"]["positive_text"].lower()
    combined = still + "\n" + ltx

    assert "radio" in combined
    assert "tower" in combined
    assert "desert" in combined or "dunes" in combined


def test_internal_visual_mode_tokens_are_not_model_facing():
    contract = parse_user_intent_contract(
        "k-indie rainy greenhouse music video, a solo adult protagonist repairs a flickering cassette recorder "
        "among fogged glass plants, olive work jacket silhouette, avoid desert, avoid radio tower"
    )
    render_item = {
        "shot_id": "S002",
        "still_prompt_text": "visual mode: crosswalk_wait, protagonist action: wait between plant rows beside fogged glass",
        "clip_positive_prompt": "window_haze crosswalk_wait gentle motion",
        "story_contract": {"story_action_grammar": "crosswalk_wait"},
    }

    still = adapt_flux2_ref_still_prompt(contract, render_item)["positive_text"].lower()
    ltx = adapt_ltx_ia2v_prompt(contract, render_item)["positive_text"].lower()
    combined = still + ltx

    assert "crosswalk_wait" not in combined
    assert "window_haze" not in combined
    assert "between wet plant rows" in combined or "fogged glass" in combined


def test_rooftop_and_glass_visual_mode_tokens_are_not_model_facing_or_lint_clean():
    concept = (
        "dream-pop forest fog pier music video, one solitary protagonist walks away into soft mist, "
        "white linen dress silhouette, no city, no neon, no rooftop, no glass corridor"
    )
    preview = build_plan_preview_payload(
        {},
        {
            "concept_text": concept,
            "audio_map": {"duration_sec": 24},
            "shot_plan": [
                {
                    "shot_id": "S001",
                    "section_type": "Verse",
                    "shot_role": "world_bridge",
                    "visual_mode": "rooftop_edge",
                    "story_function": "search",
                    "visual_event": "protagonist crosses the forest pier through rooftop_edge",
                },
                {
                    "shot_id": "S002",
                    "section_type": "Chorus",
                    "shot_role": "hero_closeup",
                    "visual_mode": "glass_corridor",
                    "story_function": "release",
                    "visual_event": "mist opens through glass_corridor",
                },
            ],
        },
    )
    visual_positive = "\n".join(_visual_workflow_positive_texts(preview)).lower()

    assert preview["workflow_prompt_lint"]["status"] == "pass"
    for token in ("rooftop_edge", "glass_corridor", "through rooftop_edge", "through glass_corridor"):
        assert token not in visual_positive
    for forbidden in ("city", "neon", "rooftop", "glass corridor"):
        assert forbidden not in visual_positive


def test_workflow_prompt_lint_rejects_rooftop_and_glass_visual_mode_tokens():
    payload = {
        "render_plan": [
            {
                "shot_id": "S001",
                "workflow_prompts": {
                    "flux2_ref_still": {"positive_text": "A forest protagonist moves through rooftop_edge."},
                    "ltx_ia2v": {
                        "positive_text": "scene: forest pier. action: mist opens through glass_corridor.",
                        "negative_text": "",
                    },
                },
            }
        ]
    }

    lint = lint_workflow_prompts(payload)

    assert lint["status"] == "fail"
    issues = "\n".join(v["issue"] for v in lint["violations"])
    assert "rooftop_edge" in issues
    assert "glass_corridor" in issues


def test_tti_anchor_uses_concept_wardrobe_without_old_defaults():
    contract = parse_user_intent_contract(
        "synthwave arctic observatory music video, one solitary protagonist crosses blue ice, "
        "silver parka silhouette, no city or neon"
    )
    prompt = adapt_flux2_tti_anchor_prompt(contract)["positive_text"].lower()

    assert "silver parka silhouette" in prompt
    assert "red raincoat" not in prompt
    assert "bob" not in prompt
    assert "young woman" not in prompt
    assert "story-derived stable outfit silhouette" not in prompt



def test_non_docs_stable_wardrobe_silhouette_keeps_generic_source_without_olive_fallback():
    contract = parse_user_intent_contract(
        "dream-pop ocean pier music video, one solitary protagonist walks away into fog, "
        "stable wardrobe silhouette, no desert, no radio tower"
    )
    prompt = adapt_flux2_tti_anchor_prompt(contract)["positive_text"].lower()

    assert contract["protagonist"]["wardrobe"] == "stable wardrobe silhouette"
    assert contract["protagonist"]["wardrobe_source"] == "user_generic_silhouette"
    assert contract["protagonist"].get("wardrobe_inference_guard", "") == ""
    assert "light olive-gray" not in prompt
    assert "desert travel overshirt" not in prompt


def test_docs_default_final_payoff_prompt_requires_front_lit_readable_face_without_turn_away_conflict():
    preview = build_plan_preview_payload(
        {},
        {
            "concept_text": DOCS_DEFAULT_CONCEPT,
            "audio_map": {
                "duration_sec": 30.0,
                "sections": [
                    {"section_id": "CHORUS", "section_type": "Chorus", "start_sec": 0.0, "end_sec": 22.0},
                    {"section_id": "OUTRO", "section_type": "Outro", "start_sec": 22.0, "end_sec": 30.0},
                ],
            },
        },
    )
    final_item = next(item for item in preview["render_plan"] if item["selected_pose_anchor_id"] == "ANCHOR_POSE_FINAL_PAYOFF_FRONT")
    prompt = final_item["workflow_prompts"]["flux2_ref_still"]["positive_text"].lower()

    assert "front-facing medium shot" in prompt
    assert "bright front-lit readable face" in prompt
    assert "direct viewer-facing gaze" in prompt
    assert "same shirt color and collar details from the reference image" in prompt
    assert "turns away" not in prompt
    assert "turn away" not in prompt
    assert "walks away" not in prompt
    assert "side-profile" not in prompt


def test_docs_default_pose_anchor_prompts_lock_reference_wardrobe_and_face_readability():
    preview = _docs_default_preview()
    pose_bank = preview["anchor_package"]["pose_anchor_bank"]
    prompts_by_id = {
        anchor["anchor_id"]: anchor["workflow_prompts"]["flux2_ref_anchor"]["positive_text"].lower()
        for anchor in pose_bank
    }

    for anchor_id in ("ANCHOR_POSE_FULL_BODY_STANDING", "ANCHOR_POSE_FINAL_PAYOFF_FRONT"):
        prompt = prompts_by_id[anchor_id]
        assert "exact same shirt or jacket color from the reference image" in prompt
        assert "matching collar and shoulder details" in prompt
        assert "bright front-lit readable face" in prompt
        assert "wardrobe color palette" in prompt
        assert not NEGATIVE_CLAUSE_RE.search(prompt)

def test_docs_default_final_payoff_ltx_prompt_holds_front_facing_payoff_motion():
    preview = build_plan_preview_payload(
        {},
        {
            "concept_text": DOCS_DEFAULT_CONCEPT,
            "audio_map": {
                "duration_sec": 30.0,
                "sections": [
                    {"section_id": "CHORUS", "section_type": "Chorus", "start_sec": 0.0, "end_sec": 22.0},
                    {"section_id": "OUTRO", "section_type": "Outro", "start_sec": 22.0, "end_sec": 30.0},
                ],
            },
        },
    )
    final_item = next(item for item in preview["render_plan"] if item["selected_pose_anchor_id"] == "ANCHOR_POSE_FINAL_PAYOFF_FRONT")
    payload = final_item["workflow_prompts"]["ltx_ia2v"]
    positive = payload["positive_text"].lower()
    negative = payload["negative_text"].lower()

    assert "remain front-facing throughout" in positive
    assert "maintain direct viewer-facing gaze" in positive
    assert "minimal motion" in positive
    assert "walks away" not in positive
    assert "turns away" not in positive
    assert "turn away" not in positive
    assert "back-facing" not in positive
    assert "profile turn" in negative
    assert "back view" in negative
    assert "walking away" in negative


def test_non_front_payoff_ltx_does_not_force_front_facing_or_ban_departure_motion():
    contract = parse_user_intent_contract(
        "dream-pop ocean pier music video, one solitary protagonist resolves the story by walking away into fog, "
        "stable wardrobe silhouette, no desert, no radio tower"
    )
    render_item = {
        "shot_id": "S009",
        "story_function": "payoff",
        "section_type": "outro",
        "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
        "clip_positive_prompt": "protagonist walks away into fog as the story resolves, gentle camera drift",
        "story_contract": {
            "protagonist_action": "walks away into fog as the story resolves",
            "visual_payoff": "resolved departure into fog",
        },
        "recommended_duration_sec": {"min": 1.2, "max": 2.0},
    }

    payload = adapt_ltx_ia2v_prompt(contract, render_item)
    positive = payload["positive_text"].lower()
    negative = payload["negative_text"].lower()

    assert "walks away into fog" in positive
    assert "remain front-facing throughout" not in positive
    assert "direct viewer-facing gaze" not in positive
    assert "profile turn" not in negative
    assert "back view" not in negative
    assert "walking away" not in negative
    assert "turning away" not in negative


def test_prompt_cleanup_does_not_inject_desert_radio_world_for_generic_role_tokens():
    contract = parse_user_intent_contract(
        "dream-pop greenhouse music video, one solitary protagonist moves through fogged glass plants, "
        "stable linen jacket silhouette, no desert, no radio tower"
    )
    render_item = {
        "shot_id": "S003",
        "still_prompt_text": "story visual event: role diversity world bridge, protagonist action: role diversity symbolic insert",
        "story_contract": {
            "protagonist_action": "role diversity world bridge",
            "visual_event": "role diversity symbolic insert",
        },
        "selected_pose_anchor_id": "ANCHOR_POSE_THREE_QUARTER_MEDIUM",
    }

    payload = adapt_flux2_ref_still_prompt(contract, render_item)
    positive = payload["positive_text"].lower()

    assert "desert" not in positive
    assert "radio" not in positive
    assert "cutaway detail" in positive or "bridge shot" in positive


def test_plan_preview_departure_payoff_does_not_select_front_payoff_lock():
    concept = (
        "dream-pop ocean pier music video, one solitary protagonist resolves the story by walking away into fog, "
        "stable wardrobe silhouette, no desert, no radio tower"
    )
    preview = build_plan_preview_payload({}, {"concept_text": concept, "audio_map": {"duration_sec": 24}})
    final_item = preview["render_plan"][-1]
    ltx = final_item["workflow_prompts"]["ltx_ia2v"]

    assert final_item["selected_pose_anchor_id"] != "ANCHOR_POSE_FINAL_PAYOFF_FRONT"
    assert "remain front-facing throughout" not in ltx["positive_text"].lower()
    assert "radio signal" not in ltx["positive_text"].lower()
    assert "radio tower" not in ltx["positive_text"].lower()
    assert "walking away" not in ltx["negative_text"].lower()


def test_world_description_does_not_invent_sample_objects_from_keyword_worlds():
    cases = [
        (
            "k-indie rainy greenhouse music video, one solitary protagonist waits among fogged glass plants, "
            "stable linen jacket silhouette, no cassette recorder, no desert, no radio tower",
            ("cassette", "desert", "radio tower"),
        ),
        (
            "j-rock stormy lighthouse music video, one solitary protagonist climbs black rocks toward a rotating beam, "
            "wind-torn navy coat, no lantern, no city",
            ("lantern", "city"),
        ),
        (
            "dream-pop underwater chamber music video, one solitary protagonist moves through pearl light toward a surface door, "
            "pale linen dress silhouette, no library, no floating books, no city",
            ("library", "floating books", "city"),
        ),
    ]

    for concept, forbidden_terms in cases:
        contract = parse_user_intent_contract(concept)
        description = contract["world"]["positive_description"].lower()

        for term in forbidden_terms:
            assert term not in description, (concept, term, description)


def test_fallback_actions_do_not_invent_world_sample_props_when_not_in_concept():
    cases = [
        (
            "k-indie rainy greenhouse music video, fogged glass plants and soft morning rain, "
            "stable linen jacket silhouette, no desert, no radio tower",
            ("cassette", "desert", "radio tower"),
            ("greenhouse", "fogged glass", "plants", "rain"),
        ),
        (
            "j-rock stormy cliffside lighthouse music video, black rocks and a rotating lighthouse beam, "
            "wind-torn navy coat, no city",
            ("lantern", "city"),
            ("cliffside", "lighthouse", "black rocks", "rotating lighthouse beam"),
        ),
        (
            "dream-pop underwater chamber music video, pearl light and a moonlit surface door, "
            "pale linen dress silhouette, no city",
            ("library", "floating books", "city"),
            ("underwater", "pearl light", "surface door"),
        ),
    ]

    for concept, forbidden_terms, expected_terms in cases:
        contract = parse_user_intent_contract(concept)
        render_item = {"shot_id": "S003", "story_contract": {}, "selected_pose_anchor_id": "ANCHOR_POSE_THREE_QUARTER_MEDIUM"}
        still = adapt_flux2_ref_still_prompt(contract, render_item)["positive_text"].lower()
        ltx = adapt_ltx_ia2v_prompt(contract, render_item)["positive_text"].lower()
        combined = still + "\n" + ltx

        for term in forbidden_terms:
            assert term not in combined, (concept, term, combined)
        assert any(term in combined for term in expected_terms), (concept, combined)



def test_workflow_adapters_ignore_poisoned_legacy_prompt_fields_as_action_source():
    contract = parse_user_intent_contract(
        "dream-pop forest pier music video, one solitary protagonist follows fireflies over mossy water, "
        "white linen dress silhouette, no city, no rooftop, no satellite dish"
    )
    render_item = {
        "shot_id": "S006",
        "story_contract": {},
        "still_prompt_text": "protagonist action: raises a cassette on a neon rooftop beside a satellite dish",
        "prompt_seed": "action: opens floating books inside a glass corridor",
        "clip_positive_prompt": "action: raises a lantern on a city curb under rain-streaked glass",
        "clip_prompt_seed": "story visual event: walks toward a radio tower afterglow",
        "selected_pose_anchor_id": "ANCHOR_POSE_THREE_QUARTER_MEDIUM",
    }

    still = adapt_flux2_ref_still_prompt(contract, render_item)
    ltx = adapt_ltx_ia2v_prompt(contract, render_item)
    combined_positive = (still["positive_text"] + "\n" + ltx["positive_text"]).lower()

    assert "follows fireflies over mossy water" in combined_positive
    for poisoned in (
        "cassette",
        "neon rooftop",
        "satellite dish",
        "floating books",
        "glass corridor",
        "lantern",
        "city curb",
        "rain-streaked glass",
        "radio tower",
        "afterglow",
    ):
        assert poisoned not in combined_positive, (poisoned, combined_positive)



def test_workflow_adapters_do_not_promote_legacy_negative_clauses_to_model_constraints():
    contract = parse_user_intent_contract(
        "k-indie greenhouse music video, one solitary protagonist moves between fogged glass plants, "
        "olive work jacket silhouette, no crowd"
    )
    render_item = {
        "shot_id": "S002",
        "story_contract": {
            "protagonist_action": "moves between fogged glass plants",
            "visual_event": "morning mist brightens the greenhouse path",
        },
        "still_prompt_text": "no greenhouse, no plants, avoid olive work jacket",
        "clip_positive_prompt": "without fogged glass, avoid morning mist, no k-indie texture",
        "prompt_seed": "no source-bound detail",
        "clip_prompt_seed": "avoid visible gesture",
    }

    still = adapt_flux2_ref_still_prompt(contract, render_item)
    ltx = adapt_ltx_ia2v_prompt(contract, render_item)
    combined_negative = "\n".join(
        [
            ", ".join(still["negative_constraints"]),
            ltx["negative_text"],
        ]
    ).lower()

    assert "crowd" in combined_negative
    for legacy_negative in (
        "greenhouse",
        "plants",
        "olive work jacket",
        "fogged glass",
        "morning mist",
        "k-indie texture",
        "source-bound detail",
        "visible gesture",
    ):
        assert legacy_negative not in combined_negative, (legacy_negative, combined_negative)
