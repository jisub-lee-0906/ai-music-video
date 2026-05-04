import re

from ai_mv.core.stages.plan_mv import build_plan_preview_payload


DOCS_DEFAULT_CONCEPT = (
    "alt-pop desert radio music video, one solitary protagonist follows a fading signal across sunrise dunes "
    "toward a distant radio tower, quiet uncertainty turning into calm resolve, stable wardrobe silhouette, "
    "no crowd, no second protagonist, no city or neon"
)


def _docs_default_plan() -> dict:
    return build_plan_preview_payload(
        {"planning": {"default_style_name": "alt_pop", "max_shot_sec": 4.0, "narrative_progression": True}},
        {
            "concept_text": DOCS_DEFAULT_CONCEPT,
            "audio_map": {
                "duration_sec": 24.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 4.0},
                    {"name": "verse", "start_sec": 4.0, "end_sec": 10.0},
                    {"name": "chorus", "start_sec": 10.0, "end_sec": 18.0},
                    {"name": "outro", "start_sec": 18.0, "end_sec": 24.0},
                ],
            },
        },
    )


def _joined_render_prompt_text(plan: dict) -> str:
    return "\n".join(
        " ".join(
            str(item.get(key, ""))
            for key in ("prompt_seed", "prompt_draft", "still_prompt_text", "clip_prompt_seed", "clip_positive_prompt")
        )
        for item in plan["render_plan"]
    ).lower()


def test_docs_default_alt_pop_prompts_do_not_invent_demographic_or_negative_world_tokens():
    plan = _docs_default_plan()
    prompt_text = _joined_render_prompt_text(plan)

    assert "desert" in prompt_text
    assert "radio" in prompt_text
    assert "sunrise" in prompt_text
    forbidden = [
        "young woman",
        "young man",
        "night-city light",
        "night city light",
        "modern style-world",
        "same world anchor",
        "world-anchor still",
        "curb",
        "bridge_glass",
        "bridge glass",
        "glass corridor",
        "rooftop",
        "chrome",
        "neon",
        "city",
    ]
    for token in forbidden:
        assert re.search(rf"(?<![a-z0-9_-]){re.escape(token)}(?![a-z0-9_-])", prompt_text) is None


def test_docs_default_identity_anchor_prompt_is_standalone_and_not_self_referential():
    plan = _docs_default_plan()
    upper = next(
        item for item in plan["anchor_package"]["anchors"] if item["anchor_id"] == "ANCHOR_CHARACTER_UPPER_BODY"
    )
    prompt = upper["prompt_text"].lower()

    assert "pure white" in prompt
    assert "reference image" not in prompt
    assert "reference as" not in prompt
    assert "from the identity anchor" not in prompt
    assert "from the upper-body identity anchor" not in prompt
    assert "same lone night-walk protagonist" not in prompt


def test_docs_default_face_critical_shots_do_not_use_side_profile_as_identity_reference():
    plan = _docs_default_plan()
    face_critical = []
    for item in plan["render_plan"]:
        text = " ".join(
            str(item.get(key, ""))
            for key in ("candidate_role", "anchor_reference_arm", "reference_mode", "identity_lock_strength")
        ).lower()
        if any(token in text for token in ("close", "front", "hero", "threshold", "performance")):
            face_critical.append(item)

    assert face_critical
    for item in face_critical:
        assert item["selected_pose_anchor_id"] != "ANCHOR_POSE_WALKING_SIDE", item["shot_id"]
