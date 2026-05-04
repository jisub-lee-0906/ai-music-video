from __future__ import annotations

import re

from ai_mv.core.planning.workflow_prompt_adapters import (
    adapt_acestep_audio_prompt,
    adapt_flux2_ref_still_prompt,
    adapt_flux2_tti_anchor_prompt,
    adapt_ltx_ia2v_prompt,
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
    assert "use the reference character identity exactly" in lower
    assert "radio signal" in lower
    assert "sunrise dunes" in lower
    assert not any(label in lower for label in META_LABELS)
    assert "avoid" not in lower
    assert "no distant human silhouettes" not in lower
    assert "distant human silhouettes" in payload["negative_constraints"]


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
    assert "action:" in positive
    assert "camera:" in positive
    assert "raise the radio" in positive
    assert "story function:" not in positive
    assert not NEGATIVE_CLAUSE_RE.search(positive)
    assert "pc game" in negative
    assert "cartoon" in negative
    assert "bystanders" in negative
    assert "near-duplicate framing" in negative


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
