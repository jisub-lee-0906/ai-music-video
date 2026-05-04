from __future__ import annotations

import re

from ai_mv.core.planning.workflow_prompt_adapters import (
    adapt_acestep_audio_prompt,
    adapt_flux2_ref_still_prompt,
    adapt_flux2_tti_anchor_prompt,
    adapt_ltx_ia2v_prompt,
    parse_user_intent_contract,
)
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
    assert "sunrise desert dunes" in contract["world"]["positive_description"]
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
    assert "sunrise desert" in lower
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
    assert "sunrise desert dunes with a distant radio tower" in combined
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
        "forbidden_positive_terms": ("desert", "radio tower", "sunrise dunes", "young woman"),
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
        "forbidden_positive_terms": ("desert", "radio tower", "sunrise dunes", "young woman"),
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
        "forbidden_positive_terms": ("desert", "radio tower", "sunrise dunes", "young woman"),
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
        "forbidden_positive_terms": ("desert", "radio tower", "sunrise dunes", "young woman"),
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
