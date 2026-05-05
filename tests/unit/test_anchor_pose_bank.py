import sys

import pytest

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.planning.anchor_package import build_anchor_package
from ai_mv.core.planning.creative_direction import build_creative_direction
from ai_mv.core.planning.render_items import build_render_item
from ai_mv.styles.resolver import get_style_bible
from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.core.stages.render_stills import run_render_stills


@pytest.fixture(autouse=True)
def _supply_flux2_ref_workflow_prompt_for_legacy_anchor_stage_fixtures(monkeypatch):
    original = run_render_stills

    def _clean_fixture_positive(text: str) -> str:
        value = str(text or "").replace("No street", "minimal seamless background").replace("no street", "minimal seamless background")
        value = value.replace("do not change", "preserve")
        return value.strip() or "workflow prompt"

    def _with_flux2_ref_workflow_prompts(stage_input: StageInput) -> StageInput:
        render_plan = stage_input.payload.get("render_plan", [])
        if isinstance(render_plan, list):
            for item in render_plan:
                if not isinstance(item, dict):
                    continue
                prompts = item.setdefault("workflow_prompts", {})
                prompts.setdefault(
                    "flux2_ref_still",
                    {
                        "positive_text": ", ".join(
                            part
                            for part in [
                                _clean_fixture_positive(
                                    item.get("still_prompt_text")
                                    or item.get("prompt_seed")
                                    or item.get("positive_prompt")
                                    or item.get("shot_id")
                                    or "workflow still prompt"
                                ),
                                (
                                    "preserve gender, face, hair, upper-body wardrobe, wardrobe color palette, and main outfit silhouette"
                                    if not item.get("selected_pose_anchor_id")
                                    else ""
                                ),
                            ]
                            if part
                        ),
                        "negative_text": "",
                    },
                )
        anchor_package = stage_input.payload.get("anchor_package")
        if isinstance(anchor_package, dict):
            for anchor in [*anchor_package.get("anchors", []), *anchor_package.get("pose_anchor_bank", [])]:
                if not isinstance(anchor, dict):
                    continue
                prompts = anchor.setdefault("workflow_prompts", {})
                target = str(anchor.get("workflow_target", "")).strip().lower()
                if target == "image_flux2_text_to_image":
                    prompts.setdefault(
                        "flux2_tti_anchor",
                        {
                            "positive_text": _clean_fixture_positive(
                                anchor.get("prompt_text") or anchor.get("anchor_id") or "pure white identity anchor"
                            ),
                        },
                    )
                else:
                    prompts.setdefault(
                        "flux2_ref_anchor",
                        {
                            "positive_text": _clean_fixture_positive(
                                anchor.get("prompt_text") or anchor.get("anchor_id") or "pure white pose anchor"
                            ),
                        },
                    )
        return stage_input

    def _wrapped(stage_input: StageInput):
        return original(_with_flux2_ref_workflow_prompts(stage_input))

    monkeypatch.setattr(sys.modules[__name__], "run_render_stills", _wrapped)


def test_anchor_package_default_identity_card_does_not_inject_fixed_wardrobe_hair_or_demographics():
    package = build_anchor_package(
        concept_text="desert radio tower at sunrise, one protagonist follows a fading signal across dunes",
        style_name="alt_pop",
        creative_direction={"protagonist_anchor": "same lone protagonist, stable silhouette, no competing bystanders"},
    )

    prompts = " ".join(
        anchor["prompt_text"]
        for anchor in [*package["anchors"], *package["pose_anchor_bank"]]
    ).lower()

    assert "red raincoat" not in prompts
    assert "bright red" not in prompts
    assert "short black bob" not in prompts
    assert "korean woman" not in prompts
    assert "story-derived stable outfit silhouette" in prompts
    assert "distinctive hairstyle from the identity anchor" in prompts


def test_anchor_package_exposes_docs_default_wardrobe_inference_source():
    package = build_anchor_package(
        concept_text=(
            "alt-pop desert radio music video, one solitary protagonist follows a fading signal across sunrise dunes "
            "toward a distant radio tower, quiet uncertainty turning into calm resolve, stable wardrobe silhouette, "
            "no crowd, no second protagonist, no city or neon"
        ),
        style_name="alt_pop",
    )

    assert package["wardrobe_anchor"] == "stable wardrobe silhouette: light olive-gray desert travel overshirt, neutral shirt collar, dark trousers"
    assert package["wardrobe_anchor_source"] == {
        "source": "docs_default_stable_silhouette_inferred",
        "source_text": "stable wardrobe silhouette",
        "guard": "desert_radio_docs_default",
    }


def test_anchor_package_prefers_user_wardrobe_over_style_night_outerwear_fallback():
    concept = "alt-pop moonlit forest walk, one solitary protagonist in a white linen dress follows fireflies"
    creative_direction = build_creative_direction(
        concept_text=concept,
        style_name="alt_pop",
        sections=[{"section_type": "chorus"}],
    )

    package = build_anchor_package(
        concept_text=concept,
        style_name="alt_pop",
        creative_direction=creative_direction,
    )

    prompts = " ".join(
        anchor["prompt_text"]
        for anchor in [*package["anchors"], *package["pose_anchor_bank"]]
    ).lower()

    assert "white linen dress" in prompts
    assert "stable dark outerwear silhouette" not in prompts
    assert package["wardrobe_anchor_source"]["source"] in {"user_explicit_silhouette", "user_keyword_dress"}


def test_anchor_package_uses_explicit_creative_wardrobe_anchor_when_provided():
    package = build_anchor_package(
        concept_text="night train platform farewell",
        style_name="alt_pop",
        creative_direction={
            "protagonist_anchor": "same lead dancer, silver braid, no competing bystanders",
            "wardrobe_anchor": "oversized ivory coat with a blue scarf",
        },
    )

    prompts = " ".join(
        anchor["prompt_text"]
        for anchor in [*package["anchors"], *package["pose_anchor_bank"]]
    ).lower()

    assert "oversized ivory coat with a blue scarf" in prompts
    assert "red raincoat" not in prompts
    assert "short black bob" not in prompts


def test_anchor_package_builds_one_tti_upper_body_then_flux_ref_white_background_variants():
    package = build_anchor_package(
        concept_text="late-night city pop walk under wet neon lights, missed train, unresolved goodbye turning into quiet resolve",
        style_name="citypop",
        creative_direction={"protagonist_anchor": "one beautiful young Korean woman"},
    )

    anchors = package["anchors"]
    assert [anchor["anchor_id"] for anchor in anchors] == ["ANCHOR_CHARACTER_UPPER_BODY"]
    assert anchors[0]["workflow_target"] == "image_flux2_text_to_image"

    variants = package["pose_anchor_bank"]
    assert [anchor["anchor_id"] for anchor in variants] == ["ANCHOR_CHARACTER_FULL_BODY"]
    assert variants[0]["workflow_target"] == "image_flux2_reference_image"
    assert variants[0]["reference_anchor_ids"] == ["ANCHOR_CHARACTER_UPPER_BODY"]

    for anchor in [*anchors, *variants]:
        prompt_text = anchor["prompt_text"].lower()
        assert "pure white" in prompt_text
        assert "background" in prompt_text
        assert "no street" in prompt_text
        assert "no scenery" in prompt_text
        assert "character" in anchor["material_class"]
    assert "using the upper-body identity reference" not in anchors[0]["prompt_text"].lower()
    assert "from the upper-body reference" not in anchors[0]["prompt_text"].lower()
    assert "using the upper-body identity reference" in variants[0]["prompt_text"].lower()


def test_full_body_identity_anchor_prompt_demands_head_to_toe_visibility():
    package = build_anchor_package(concept_text="rainy neon protagonist", style_name="alt_pop")
    full_body = next(anchor for anchor in package["pose_anchor_bank"] if anchor["anchor_id"] == "ANCHOR_CHARACTER_FULL_BODY")

    text = full_body["prompt_text"].lower()

    assert full_body["workflow_target"] == "image_flux2_reference_image"
    assert full_body["reference_anchor_ids"] == ["ANCHOR_CHARACTER_UPPER_BODY"]
    assert "head-to-toe" in text
    assert "feet fully visible" in text
    assert "large white margin" in text



def test_flux_ref_anchor_prompts_lock_wardrobe_without_promoting_full_body_as_primary_reference():
    package = build_anchor_package(
        concept_text="quiet desert radio tower signal search",
        style_name="alt_pop",
        creative_direction={
            "protagonist_anchor": "same lone signal seeker, dust-swept hair, no competing bystanders",
            "wardrobe_anchor": "faded sand canvas jacket with teal scarf",
        },
    )
    pose_anchor = next(anchor for anchor in package["pose_anchor_bank"] if anchor["anchor_id"] == "ANCHOR_CHARACTER_FULL_BODY")
    # Simulate full planning attaching an actual pose/action variant.
    from ai_mv.core.planning.anchor_package import with_selected_pose_anchor_bank

    package = with_selected_pose_anchor_bank(
        package,
        render_plan=[{"selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE"}],
        style_name="alt_pop",
        creative_direction={
            "protagonist_anchor": "same lone signal seeker, dust-swept hair, no competing bystanders",
            "wardrobe_anchor": "faded sand canvas jacket with teal scarf",
        },
    )
    pose_anchor = next(anchor for anchor in package["pose_anchor_bank"] if anchor["anchor_id"] == "ANCHOR_POSE_WALKING_SIDE")

    text = pose_anchor["prompt_text"].lower()

    assert pose_anchor["reference_anchor_ids"] == ["ANCHOR_CHARACTER_UPPER_BODY"]
    assert pose_anchor["source_anchor_id"] == "ANCHOR_CHARACTER_UPPER_BODY"
    assert "anchored to the upper-body identity reference, not a full-body re-identity source" in text
    assert "preserve the same upper-body wardrobe" in text
    assert "wardrobe color palette" in text
    assert "main outfit silhouette" in text
    assert "faded sand canvas jacket with teal scarf" in text



def test_flux_ref_pose_anchor_workflow_prompt_explicitly_locks_same_person_identity_features():
    package = build_anchor_package(
        concept_text="synthwave arctic solo music video, one protagonist in a silver parka crosses an ice field",
        style_name="synthwave",
        creative_direction={
            "protagonist_anchor": "same solitary arctic protagonist",
            "wardrobe_anchor": "silver parka",
        },
    )
    from ai_mv.core.planning.anchor_package import with_selected_pose_anchor_bank

    package = with_selected_pose_anchor_bank(
        package,
        render_plan=[{"selected_pose_anchor_id": "ANCHOR_POSE_FINAL_PAYOFF_FRONT"}],
        style_name="synthwave",
        creative_direction={
            "protagonist_anchor": "same solitary arctic protagonist",
            "wardrobe_anchor": "silver parka",
        },
    )
    pose_anchor = next(anchor for anchor in package["pose_anchor_bank"] if anchor["anchor_id"] == "ANCHOR_POSE_FINAL_PAYOFF_FRONT")

    positive = pose_anchor["workflow_prompts"]["flux2_ref_anchor"]["positive_text"].lower()

    assert "only character identity source" in positive
    assert "preserve the exact same person from the reference image" in positive
    assert "same face shape" in positive
    assert "same facial proportions" in positive
    assert "same eyes" in positive
    assert "same nose" in positive
    assert "same mouth" in positive
    assert "same jawline" in positive
    assert "same hairline" in positive
    assert "same hairstyle silhouette" in positive
    assert "same age impression" in positive
    assert "only change the body pose" in positive
    assert "do not" not in positive
    assert "no new person" not in positive



def test_plan_anchor_package_materializes_only_story_selected_pose_anchors():
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

    selected_ids = {
        str(item.get("selected_pose_anchor_id", "")).strip()
        for item in out["render_plan"]
        if str(item.get("selected_pose_anchor_id", "")).strip()
    }
    bank = out["anchor_package"]["pose_anchor_bank"]
    bank_ids = {str(anchor.get("anchor_id", "")).strip() for anchor in bank}
    pose_bank_ids = {anchor_id for anchor_id in bank_ids if anchor_id != "ANCHOR_CHARACTER_FULL_BODY"}

    assert selected_ids
    assert pose_bank_ids == selected_ids
    assert "ANCHOR_CHARACTER_FULL_BODY" in bank_ids
    assert "ANCHOR_POSE_MICROPHONE_PERFORMANCE" not in bank_ids
    assert all(anchor["workflow_target"] == "image_flux2_reference_image" for anchor in bank)
    assert all(anchor["reference_anchor_ids"] == ["ANCHOR_CHARACTER_UPPER_BODY"] for anchor in bank)
    assert all(
        "white-background pose reference variant" in anchor["prompt_text"]
        for anchor in bank
        if anchor["anchor_id"] != "ANCHOR_CHARACTER_FULL_BODY"
    )
    assert out["anchor_package"]["pose_anchor_policy"]["selection_policy"] == "full_body_and_story_selected_pose_anchors_are_generated_as_flux_ref_descendants"




def test_render_item_selects_distinct_pose_anchors_from_story_and_shot_needs():
    style_bible = get_style_bible("citypop")
    concept = "late-night city pop walk under wet neon lights"
    base = {
        "render_mode": "ia2v",
        "start_sec": 0.0,
        "duration_sec": 3.0,
        "section_id": "SEC_001",
        "section_type": "verse_1",
    }
    hero = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S001",
            "shot_role": "hero emotional closeup",
            "visual_mode": "hero_closeup",
            "story_function": "threshold",
        },
    )
    walking = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S002",
            "shot_role": "walking through wet neon street",
            "visual_mode": "walking_side_profile",
            "story_function": "search",
        },
    )
    payoff = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S003",
            "shot_role": "final resolve payoff",
            "visual_mode": "final_payoff_front",
            "story_function": "payoff",
        },
    )
    microphone = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S004",
            "shot_role": "chorus microphone performance",
            "visual_mode": "microphone_performance_medium",
            "story_function": "performance",
            "story_contract": {"protagonist_action": "singing into a handheld microphone"},
        },
    )

    assert hero["selected_pose_anchor_id"] == "ANCHOR_POSE_HERO_CLOSEUP"
    assert hero["pose_anchor_selection"]["required_framing"] in {"close", "medium_close"}
    assert walking["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_SIDE"
    assert walking["pose_anchor_selection"]["required_camera_angle"] == "side"
    assert payoff["selected_pose_anchor_id"] == "ANCHOR_POSE_FINAL_PAYOFF_FRONT"
    assert microphone["selected_pose_anchor_id"] == "ANCHOR_POSE_MICROPHONE_PERFORMANCE"
    assert microphone["pose_anchor_selection"]["required_pose_family"] == "microphone_performance"
    assert len({hero["selected_pose_anchor_id"], walking["selected_pose_anchor_id"], payoff["selected_pose_anchor_id"], microphone["selected_pose_anchor_id"]}) == 4


def test_story_contract_action_needs_select_scene_specific_non_microphone_anchors():
    style_bible = get_style_bible("citypop")
    concept = "cinematic MV with changing emotional blocking"
    base = {
        "render_mode": "ia2v",
        "start_sec": 0.0,
        "duration_sec": 3.0,
        "section_id": "SEC_ACTION",
        "section_type": "verse_2",
    }

    walking_toward = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S007",
            "shot_role": "protagonist walks toward camera through the frame",
            "visual_mode": "walk_toward_camera_medium_full",
            "story_function": "release",
            "story_contract": {"protagonist_action": "walks toward camera with determined forward motion"},
        },
    )
    seated_waiting = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S008",
            "shot_role": "quiet seated waiting moment",
            "visual_mode": "seated_waiting_medium",
            "story_function": "bridge",
            "story_contract": {"protagonist_action": "sits alone waiting by the window with hands relaxed"},
        },
    )
    expressive_hand = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S009",
            "shot_role": "objectless expressive hand gesture",
            "visual_mode": "emotional_hand_gesture_medium",
            "story_function": "performance",
            "story_contract": {
                "why_this_shot": "chorus emotion without literal concert props",
                "protagonist_action": "raises one open hand near chest, empty hands, no microphone",
            },
        },
    )

    assert walking_toward["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_TOWARD"
    assert walking_toward["pose_anchor_selection"]["required_motion_direction"] == "toward_camera"
    assert seated_waiting["selected_pose_anchor_id"] == "ANCHOR_POSE_SEATED_WAITING"
    assert seated_waiting["pose_anchor_selection"]["required_body_action"] == "seated_waiting"
    assert expressive_hand["selected_pose_anchor_id"] == "ANCHOR_POSE_EXPRESSIVE_HAND_GESTURE"
    assert expressive_hand["pose_anchor_selection"]["required_prop"] == "none"



def test_performance_shot_without_microphone_action_does_not_select_microphone_anchor():
    style_bible = get_style_bible("citypop")
    item = build_render_item(
        {},
        "cinematic narrative MV about choosing courage at sunrise",
        "citypop",
        style_bible,
        {
            "shot_id": "S005",
            "render_mode": "ia2v",
            "start_sec": 6.0,
            "duration_sec": 3.0,
            "section_id": "SEC_CHORUS",
            "section_type": "chorus",
            "shot_role": "camera-facing emotional delivery without props",
            "visual_mode": "solo_vocal_presence_medium",
            "story_function": "performance",
            "story_contract": {
                "why_this_shot": "the protagonist commits to the chorus without introducing stage props",
                "protagonist_action": "camera-facing emotional vocal delivery with empty hands",
            },
        },
    )

    assert item["selected_pose_anchor_id"] != "ANCHOR_POSE_MICROPHONE_PERFORMANCE"
    assert item["selected_pose_anchor_id"] == "ANCHOR_POSE_HERO_CLOSEUP"


def test_microphone_anchor_is_selected_only_from_positive_story_action_not_negative_copy():
    style_bible = get_style_bible("citypop")
    item = build_render_item(
        {},
        "cinematic narrative MV with no stage-performance props",
        "citypop",
        style_bible,
        {
            "shot_id": "S006",
            "render_mode": "ia2v",
            "start_sec": 9.0,
            "duration_sec": 3.0,
            "section_id": "SEC_BRIDGE",
            "section_type": "bridge",
            "shot_role": "quiet bridge performance, no microphone, no stage prop",
            "visual_mode": "emotional_closeup_no_microphone",
            "story_function": "performance",
            "story_contract": {
                "why_this_shot": "avoid literal concert grammar",
                "protagonist_action": "she sings silently to camera without microphone",
            },
        },
    )

    assert item["selected_pose_anchor_id"] != "ANCHOR_POSE_MICROPHONE_PERFORMANCE"
    assert item["selected_pose_anchor_id"] == "ANCHOR_POSE_HERO_CLOSEUP"


def test_pose_anchor_selection_does_not_treat_unresolved_text_as_final_payoff():
    style_bible = get_style_bible("citypop")
    item = build_render_item(
        {},
        "unresolved goodbye under wet neon lights",
        "citypop",
        style_bible,
        {
            "shot_id": "S004",
            "render_mode": "ia2v",
            "start_sec": 3.0,
            "duration_sec": 3.0,
            "section_id": "SEC_002",
            "section_type": "verse_1",
            "shot_role": "searching walk after unresolved goodbye",
            "visual_mode": "walking_side_profile",
            "story_function": "search",
        },
    )

    assert item["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_SIDE"



def test_pose_anchor_selection_requires_positive_resolution_for_final_payoff_anchor():
    style_bible = get_style_bible("citypop")
    item = build_render_item(
        {},
        "not yet resolved, still searching before the final answer",
        "citypop",
        style_bible,
        {
            "shot_id": "S010",
            "render_mode": "ia2v",
            "start_sec": 12.0,
            "duration_sec": 3.0,
            "section_id": "SEC_BRIDGE",
            "section_type": "bridge",
            "shot_role": "pre-final searching walk, not yet resolved",
            "visual_mode": "walking_side_profile",
            "story_function": "search",
            "story_contract": {
                "why_this_shot": "the protagonist has not reached the final payoff yet",
                "protagonist_action": "keeps walking sideways through uncertainty",
            },
        },
    )

    assert item["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_SIDE"
    assert "final_payoff_positive_resolution" not in item["pose_anchor_selection"].get("reason_codes", [])



def test_pose_anchor_selection_publishes_final_payoff_decision_evidence():
    style_bible = get_style_bible("citypop")
    item = build_render_item(
        {},
        "resolved final chorus payoff with a calm face-to-camera ending",
        "citypop",
        style_bible,
        {
            "shot_id": "S011",
            "render_mode": "ia2v",
            "start_sec": 24.0,
            "duration_sec": 3.5,
            "section_id": "SEC_OUTRO",
            "section_type": "outro",
            "shot_role": "final resolved payoff portrait",
            "visual_mode": "final_payoff_front_medium",
            "story_function": "payoff",
            "story_contract": {
                "why_this_shot": "final visual payoff after the emotional arc resolves",
                "protagonist_action": "faces camera calmly with resolved confidence",
            },
        },
    )

    assert item["selected_pose_anchor_id"] == "ANCHOR_POSE_FINAL_PAYOFF_FRONT"
    assert item["pose_anchor_selection"]["decision_method"] == "structured_shot_semantics"
    assert "final_payoff_positive_resolution" in item["pose_anchor_selection"]["reason_codes"]
    assert item["pose_anchor_selection"]["shot_semantics"]["final_payoff"] is True
    assert item["pose_anchor_selection"]["rejected_anchor_ids"]["ANCHOR_POSE_HERO_CLOSEUP"] == "final payoff needs resolved medium front hero framing, not generic closeup"



def test_render_stills_routes_keyframes_through_selected_pose_anchor(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-pose-anchor-routing",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                        "anchor_type": "character_upper_body_identity",
                        "material_class": "character_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "upper-body identity card, pure white seamless background, clear face visibility",
                    }
                ],
                "pose_anchor_bank": [
                    {
                        "anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                        "anchor_type": "pose_variant",
                        "anchor_role": "pose_variant",
                        "material_class": "pose_reference_anchor",
                        "workflow_target": "image_flux2_reference_image",
                        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                        "pose_family": "hero_closeup",
                        "framing": "close",
                        "camera_angle": "front",
                        "prompt_text": "hero close-up, same face identity, same outfit, pure white seamless background, No street",
                    },
                    {
                        "anchor_id": "ANCHOR_POSE_WALKING_SIDE",
                        "anchor_type": "pose_variant",
                        "anchor_role": "pose_variant",
                        "material_class": "pose_reference_anchor",
                        "workflow_target": "image_flux2_reference_image",
                        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                        "pose_family": "walking",
                        "framing": "full",
                        "camera_angle": "side",
                        "prompt_text": "walking side pose, same face identity, same outfit, pure white seamless background, No street",
                    },
                ],
            },
            "shot_plan": [
                {"shot_id": "S001", "visual_mode": "hero_closeup"},
                {"shot_id": "S002", "visual_mode": "walking_side_profile"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                },
                {
                    "shot_id": "S002",
                    "still_prompt_text": "same lead woman walking through wet neon",
                    "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                },
            ],
        },
    )

    out = run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == [
        "ANCHOR_CHARACTER_UPPER_BODY",
        "ANCHOR_POSE_HERO_CLOSEUP",
        "ANCHOR_POSE_WALKING_SIDE",
        "S001",
        "S002",
    ]
    assert calls[1]["reference_image"] == "D:/renders/ANCHOR_CHARACTER_UPPER_BODY.png"
    assert calls[2]["reference_image"] == "D:/renders/ANCHOR_CHARACTER_UPPER_BODY.png"
    assert calls[3]["reference_image"] == "D:/renders/ANCHOR_POSE_HERO_CLOSEUP.png"
    assert calls[4]["reference_image"] == "D:/renders/ANCHOR_POSE_WALKING_SIDE.png"
    assert out.payload["still_results"][0]["selected_pose_anchor_id"] == "ANCHOR_POSE_HERO_CLOSEUP"
    assert out.payload["still_results"][1]["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_SIDE"
    assert out.payload["workflow_inputs"]["stills"]["pose_anchor_count"] == 2



def test_render_stills_ignores_legacy_world_reference_anchors(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-pose-anchor-strict-upper-ref",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_WORLD_CHARACTER",
                        "anchor_type": "world_character_anchor",
                        "material_class": "world_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "rainy neon city world with one red-coated woman",
                    }
                ],
                "pose_anchor_bank": [
                    {
                        "anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                        "anchor_type": "pose_variant",
                        "anchor_role": "pose_variant",
                        "material_class": "pose_reference_anchor",
                        "workflow_target": "image_flux2_reference_image",
                        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                        "prompt_text": "hero close-up, same face identity, pure white seamless background",
                    }
                ],
            },
            "shot_plan": [],
            "render_plan": [],
        },
    )

    out = run_render_stills(stage_input)

    assert calls == []
    assert out.payload["anchor_results"] == []
    assert out.payload["workflow_inputs"]["stills"]["anchor_count"] == 0
    assert out.payload["workflow_inputs"]["stills"]["pose_anchor_count"] == 0



def test_keyframe_reference_fallback_uses_primary_identity_and_ignores_legacy_world_anchor(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-primary-identity-fallback",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_WORLD_CHARACTER",
                        "anchor_type": "world_character_anchor",
                        "material_class": "world_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "rainy neon city world with one red-coated woman",
                    },
                    {
                        "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                        "anchor_type": "character_upper_body_identity",
                        "material_class": "character_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "upper-body identity card, pure white seamless background, clear face visibility",
                    },
                ],
                "pose_anchor_bank": [],
            },
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_closeup"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                }
            ],
        },
    )

    run_render_stills(stage_input)

    keyframe_call = calls[-1]
    assert [call["shot_id"] for call in calls] == ["ANCHOR_CHARACTER_UPPER_BODY", "S001"]
    assert keyframe_call["reference_image"] == "D:/renders/ANCHOR_CHARACTER_UPPER_BODY.png"
    assert "upper-body wardrobe" in keyframe_call["positive_prompt"]
    assert "main outfit silhouette" in keyframe_call["positive_prompt"]
    assert "coat" not in keyframe_call["positive_prompt"].lower()



def test_keyframe_with_missing_selected_pose_anchor_fails_closed_instead_of_identity_fallback(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-missing-pose-fail-closed",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_WORLD_CHARACTER",
                        "anchor_type": "world_character_anchor",
                        "material_class": "world_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "rainy neon city world with one red-coated woman",
                    },
                    {
                        "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                        "anchor_type": "character_upper_body_identity",
                        "material_class": "character_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "upper-body identity card, pure white seamless background, clear face visibility",
                    }
                ],
                "pose_anchor_bank": [],
            },
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_closeup"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                }
            ],
        },
    )

    with pytest.raises(RuntimeError, match="missing selected pose anchor image.*S001.*ANCHOR_POSE_HERO_CLOSEUP"):
        run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == ["ANCHOR_CHARACTER_UPPER_BODY"]



def test_keyframe_with_failed_selected_pose_anchor_render_fails_closed(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        if item["shot_id"] == "ANCHOR_POSE_HERO_CLOSEUP":
            return ""
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-failed-pose-anchor-fail-closed",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                        "anchor_type": "character_upper_body_identity",
                        "material_class": "character_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "upper-body identity card, pure white seamless background, clear face visibility",
                    }
                ],
                "pose_anchor_bank": [
                    {
                        "anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                        "anchor_type": "pose_variant",
                        "anchor_role": "pose_variant",
                        "material_class": "pose_reference_anchor",
                        "workflow_target": "image_flux2_reference_image",
                        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                        "pose_family": "hero_closeup",
                        "prompt_text": "hero close-up, same face identity, pure white seamless background",
                    }
                ],
            },
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_closeup"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "continuity_contract": {"protagonist_anchor": "same lead woman"},
                }
            ],
        },
    )

    with pytest.raises(RuntimeError, match="missing selected pose anchor image.*S001.*ANCHOR_POSE_HERO_CLOSEUP"):
        run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == ["ANCHOR_CHARACTER_UPPER_BODY", "ANCHOR_POSE_HERO_CLOSEUP"]



def test_keyframe_with_selected_pose_anchor_and_no_anchor_package_fails_closed(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-selected-pose-no-anchor-package",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_closeup"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "continuity_contract": {"protagonist_anchor": "same lead woman"},
                }
            ],
        },
    )

    with pytest.raises(RuntimeError, match="missing selected pose anchor image.*S001.*ANCHOR_POSE_HERO_CLOSEUP"):
        run_render_stills(stage_input)

    assert calls == []



def test_keyframe_with_selected_pose_anchor_does_not_bypass_through_prior_still_reuse(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-selected-pose-prior-reuse-blocked",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {"anchors": [], "pose_anchor_bank": []},
            "still_results": [{"shot_id": "S001", "image": "D:/renders/prior-S001.png"}],
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_closeup"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "reference_mode": "reuse_prior_still",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "continuity_contract": {"protagonist_anchor": "same lead woman"},
                }
            ],
        },
    )

    with pytest.raises(RuntimeError, match="missing selected pose anchor image.*S001.*ANCHOR_POSE_HERO_CLOSEUP"):
        run_render_stills(stage_input)

    assert calls == []
