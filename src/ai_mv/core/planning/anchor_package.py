from __future__ import annotations

from ai_mv.core.planning.workflow_prompt_adapters import adapt_flux2_tti_anchor_prompt, parse_user_intent_contract


def build_anchor_package(*, concept_text: str, style_name: str, creative_direction: dict | None = None) -> dict:
    """Build the stable reference-anchor package used before story variants.

    The package intentionally keeps reference anchors character-only. Environment
    continuity belongs in prompts/style contracts; Flux reference images are reserved
    for protagonist identity, outfit, pose, and action continuity.
    """

    direction = creative_direction if isinstance(creative_direction, dict) else {}
    protagonist_anchor = str(direction.get("protagonist_anchor", "")).strip() or "one lead protagonist with story-appropriate presentation"
    wardrobe_anchor = _wardrobe_anchor(style_name, direction)
    workflow_anchor_prompt = adapt_flux2_tti_anchor_prompt(
        parse_user_intent_contract(concept_text),
        {
            "protagonist_anchor": protagonist_anchor,
            "wardrobe_anchor": wardrobe_anchor,
        },
    )
    return {
        "strategy": "white_background_tti_character_anchors_then_flux_reference_keyframes",
        "workflow_family": "flux2_tti_identity_anchor_then_reference_keyframes",
        "anchors": [
            {
                "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                "anchor_type": "character_upper_body_identity",
                "material_class": "character_reference_anchor",
                "workflow_target": "image_flux2_text_to_image",
                "prompt_style": "upper_body_identity_card",
                "prompt_text": _upper_body_identity_prompt(protagonist_anchor, wardrobe_anchor),
                "workflow_prompts": {"flux2_tti_anchor": workflow_anchor_prompt},
                "selection_criteria": [
                    "pure_white_background",
                    "single_subject_only",
                    "clear_face_visibility",
                    "hair_identity_readable",
                    "upper_outfit_readable",
                ],
            },
        ],
        "pose_anchor_bank": [_full_body_anchor_spec(protagonist_anchor, wardrobe_anchor)],
        "pose_anchor_policy": {
            "primary_identity_anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
            "workflow_target": "image_flux2_reference_image",
            "background_contract": "white_background",
            "selection_policy": "full_body_and_story_selected_pose_anchors_are_generated_as_flux_ref_descendants",
            "diversity_guard": "always derive one full-body model card from the upper-body identity anchor; add only story-selected pose/action anchors",
        },
        "variant_policy": {
            "workflow_target": "image_flux2_reference_image",
            "reference_order": ["character_full_body", "character_upper_body_identity"],
            "important_story_functions": ["release", "payoff"],
            "candidates_per_important_shot": 3,
            "selection_criteria": [
                "identity_preservation",
                "outfit_preservation",
                "story_function_readability",
                "foreground_subject_scale",
                "novelty_vs_previous_shot",
                "single_scene_integrity",
            ],
        },
    }



def with_selected_pose_anchor_bank(
    anchor_package: dict,
    *,
    render_plan: list[dict],
    style_name: str,
    creative_direction: dict | None = None,
) -> dict:
    """Attach only the pose/action anchors selected by story/render planning.

    ``build_anchor_package`` stays identity-only so callers can request a pure
    TTI identity package. Full MV planning calls this after render items have
    selected pose anchors from shot/story needs.
    """

    if not isinstance(anchor_package, dict):
        return anchor_package
    selected_ids: list[str] = []
    for item in render_plan:
        if not isinstance(item, dict):
            continue
        anchor_id = str(item.get("selected_pose_anchor_id", "")).strip()
        if anchor_id and anchor_id not in selected_ids:
            selected_ids.append(anchor_id)
    direction = creative_direction if isinstance(creative_direction, dict) else {}
    protagonist_anchor = str(direction.get("protagonist_anchor", "")).strip() or "one lead protagonist with story-appropriate presentation"
    wardrobe_anchor = _wardrobe_anchor(style_name, direction)
    buildable_by_id = {anchor["anchor_id"]: anchor for anchor in _pose_anchor_bank(protagonist_anchor, wardrobe_anchor)}
    base_variants = [row for row in anchor_package.get("pose_anchor_bank", []) if isinstance(row, dict)]
    existing_ids = {str(row.get("anchor_id", "")).strip() for row in base_variants}
    pose_anchor_bank = [*base_variants]
    pose_anchor_bank.extend(
        buildable_by_id[anchor_id]
        for anchor_id in selected_ids
        if anchor_id in buildable_by_id and anchor_id not in existing_ids
    )

    out = dict(anchor_package)
    out["pose_anchor_bank"] = pose_anchor_bank
    pose_anchor_policy = dict(out.get("pose_anchor_policy", {})) if isinstance(out.get("pose_anchor_policy"), dict) else {}
    pose_anchor_policy.update(
        {
            "primary_identity_anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
            "workflow_target": "image_flux2_reference_image",
            "background_contract": "white_background",
            "selection_policy": "full_body_and_story_selected_pose_anchors_are_generated_as_flux_ref_descendants",
            "diversity_guard": "derive the full-body model card plus only pose/action anchors selected by story_contract or shot need; do not emit a fixed pose bank",
            "selected_pose_anchor_ids": selected_ids,
            "materialized_pose_anchor_ids": [anchor["anchor_id"] for anchor in pose_anchor_bank],
        }
    )
    out["pose_anchor_policy"] = pose_anchor_policy
    return out



def _wardrobe_anchor(style_name: str, creative_direction: dict | None = None) -> str:
    direction = creative_direction if isinstance(creative_direction, dict) else {}
    explicit = str(direction.get("wardrobe_anchor", "")).strip()
    if explicit:
        return explicit
    if style_name == "idol_pop":
        return "a bright stage-ready outfit with a clear stable silhouette"
    return "a story-derived stable outfit silhouette with readable color and shape continuity"


def _full_body_character_prompt(protagonist_anchor: str, wardrobe_anchor: str) -> str:
    return (
        "Using the upper-body identity reference as the only face and wardrobe source, create a single clean full-body identity reference card, head-to-toe, on a pure white seamless background, pure white seamless studio background. "
        f"Depict {protagonist_anchor} with the exact face fingerprint from the upper-body identity anchor, keep a stable face fingerprint, exact face fingerprint, same face identity, the same distinctive hairstyle from the identity anchor, expressive readable eyes, and {wardrobe_anchor}. "
        f"{_wardrobe_lock_sentence(wardrobe_anchor)} "
        "The character must be alone, centered, full body visible from head to toe, feet fully visible, shoes and full stance visible, outfit readable, face readable, soft studio lighting, with large white margins around the entire body so no body part is cropped. "
        "This is a Flux reference-image descendant character model anchor, not a story scene and not a fresh text-to-image identity. "
        "No street, no room, no city, no scenery, no umbrella, no microphone, no chair, no text, no logo, no second person, "
        "no distant human silhouettes, no bystanders, no duplicate body, no collage, no split screen, no frame insert, no decorative background, no cropped feet, no cropped legs, no waist-up portrait, no wardrobe change."
    )


def _full_body_anchor_spec(protagonist_anchor: str, wardrobe_anchor: str) -> dict:
    return {
        "anchor_id": "ANCHOR_CHARACTER_FULL_BODY",
        "anchor_type": "character_full_body",
        "material_class": "character_reference_anchor",
        "workflow_target": "image_flux2_reference_image",
        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
        "source_anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
        "background_contract": "white_background",
        "prompt_style": "white_background_full_body_from_upper_body_identity",
        "prompt_text": _full_body_character_prompt(protagonist_anchor, wardrobe_anchor),
        "workflow_prompts": {"flux2_ref_anchor": {"positive_text": _full_body_workflow_prompt(protagonist_anchor, wardrobe_anchor)}},
        "selection_criteria": [
            "pure_white_background",
            "single_subject_only",
            "full_body_visible",
            "face_readable",
            "outfit_silhouette_readable",
        ],
    }


def _upper_body_identity_prompt(protagonist_anchor: str, wardrobe_anchor: str) -> str:
    return (
        f"Create a clean upper-body character identity card of {protagonist_anchor} alone on a seamless pure white studio background. "
        f"Frame the subject from the waist up, centered, with clear face visibility, a stable face fingerprint, distinctive readable hairstyle, expressive readable eyes, and {wardrobe_anchor} clearly visible at the collar and shoulders. "
        f"Preserve one coherent upper-body wardrobe: {wardrobe_anchor}; keep the wardrobe color palette, collar/shoulder details, fabric weight cues, sleeve shape, and main outfit silhouette stable; do not redesign clothing or introduce a new costume. "
        "Use soft even studio lighting and keep it as one continuous clean character card with no street, no room, no city, no props, no scenery, no text, no logo, no collage, no split screen, no distant human silhouettes, and no extra people."
    )



def _wardrobe_lock_sentence(wardrobe_anchor: str) -> str:
    return (
        "Preserve the same upper-body wardrobe from the identity anchor: "
        f"{wardrobe_anchor}; keep the wardrobe color palette, collar/shoulder details, fabric weight cues, sleeve shape, and main outfit silhouette stable; do not redesign clothing or introduce a new costume."
    )


def _pose_anchor_bank(protagonist_anchor: str, wardrobe_anchor: str) -> list[dict]:
    specs = [
        {
            "anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
            "pose_family": "hero_closeup",
            "framing": "close",
            "camera_angle": "front",
            "subject_position": "center",
            "intended_shot_functions": ["threshold", "hero_reveal", "emotional_turn", "performance"],
            "pose_instruction": "a tight hero close-up with clear eyes, shoulders visible, direct emotional presence, centered composition",
        },
        {
            "anchor_id": "ANCHOR_POSE_THREE_QUARTER_MEDIUM",
            "pose_family": "three_quarter",
            "framing": "medium",
            "camera_angle": "three_quarter",
            "subject_position": "left_third",
            "intended_shot_functions": ["wound_setup", "search", "bridge", "emotional_turn"],
            "pose_instruction": "a medium three-quarter view with the torso turned slightly away from camera and the face still readable",
        },
        {
            "anchor_id": "ANCHOR_POSE_FULL_BODY_STANDING",
            "pose_family": "full_body",
            "framing": "full",
            "camera_angle": "front",
            "subject_position": "center",
            "intended_shot_functions": ["wound_setup", "world_bridge", "establishing", "release"],
            "pose_instruction": "a clean full-body standing pose with readable silhouette and feet visible",
        },
        {
            "anchor_id": "ANCHOR_POSE_WALKING_SIDE",
            "pose_family": "walking",
            "framing": "full",
            "camera_angle": "side",
            "subject_position": "right_third",
            "intended_shot_functions": ["search", "movement", "release", "forward_motion"],
            "pose_instruction": "a side-view walking pose, one foot forward, natural arm line, full body visible, face partly readable in profile",
        },
        {
            "anchor_id": "ANCHOR_POSE_WALKING_TOWARD",
            "pose_family": "walking_toward",
            "framing": "full",
            "camera_angle": "front",
            "subject_position": "center",
            "intended_shot_functions": ["search", "movement", "release", "forward_motion", "approach"],
            "pose_instruction": "a full-body walking-toward-camera pose, one foot stepping toward camera, centered subject, readable face and outfit, no duplicate limbs",
        },
        {
            "anchor_id": "ANCHOR_POSE_SEATED_WAITING",
            "pose_family": "seated_waiting",
            "framing": "medium",
            "camera_angle": "front_three_quarter",
            "subject_position": "center",
            "intended_shot_functions": ["waiting", "bridge", "introspection", "quiet_moment"],
            "pose_instruction": "a seated waiting pose on a simple invisible studio stool or clean neutral seat, hands relaxed, torso readable, face readable, no environment scene",
            "allowed_props": ["neutral_seat"],
        },
        {
            "anchor_id": "ANCHOR_POSE_EXPRESSIVE_HAND_GESTURE",
            "pose_family": "expressive_hand_gesture",
            "framing": "medium",
            "camera_angle": "front_three_quarter",
            "subject_position": "center",
            "intended_shot_functions": ["performance", "chorus", "emotional_turn", "vocal_delivery"],
            "pose_instruction": "a medium objectless emotional gesture pose, one open hand near the chest or reaching slightly forward, empty hands, face readable",
        },
        {
            "anchor_id": "ANCHOR_POSE_PROFILE_EMOTIONAL",
            "pose_family": "profile",
            "framing": "medium_close",
            "camera_angle": "profile",
            "subject_position": "left_third",
            "intended_shot_functions": ["threshold", "emotional_turn", "bridge", "search"],
            "pose_instruction": "an emotional profile pose looking slightly downward, medium-close framing, face outline and hair identity readable",
        },
        {
            "anchor_id": "ANCHOR_POSE_FINAL_PAYOFF_FRONT",
            "pose_family": "final_payoff_front",
            "framing": "medium",
            "camera_angle": "front",
            "subject_position": "center",
            "intended_shot_functions": ["payoff", "final_payoff", "resolve"],
            "pose_instruction": "a resolved front-facing medium hero pose with calm confidence and readable face identity",
        },
        {
            "anchor_id": "ANCHOR_POSE_MICROPHONE_PERFORMANCE",
            "pose_family": "microphone_performance",
            "framing": "medium",
            "camera_angle": "front_three_quarter",
            "subject_position": "center",
            "intended_shot_functions": ["performance", "microphone", "singing", "chorus"],
            "pose_instruction": "a medium performance pose holding a simple handheld microphone near the mouth, singing posture, shoulders and hands visible, face readable",
            "allowed_props": ["handheld_microphone"],
        },
    ]
    return [_pose_anchor_spec(spec, protagonist_anchor, wardrobe_anchor) for spec in specs]


def _full_body_workflow_prompt(protagonist_anchor: str, wardrobe_anchor: str) -> str:
    subject = _workflow_safe_anchor_subject(protagonist_anchor)
    return (
        "Use the reference character identity exactly. "
        "Create a full-body white-background character model card with one centered subject, head-to-toe visibility, readable face, readable outfit, visible shoes, and generous white margins. "
        f"Keep {subject} with the exact face identity, distinctive hairstyle, expressive readable eyes, and {wardrobe_anchor}. "
        f"Preserve the same upper-body wardrobe from the identity anchor: {wardrobe_anchor}; keep wardrobe color palette, collar and shoulder details, fabric weight cues, sleeve shape, and main outfit silhouette stable. "
        "Use a pure white seamless studio background with soft even studio lighting."
    )


def _pose_anchor_workflow_prompt(
    protagonist_anchor: str,
    wardrobe_anchor: str,
    pose_instruction: str,
    *,
    allow_microphone: bool = False,
    allow_neutral_seat: bool = False,
) -> str:
    prop_clause = ""
    subject = _workflow_safe_anchor_subject(protagonist_anchor)
    clean_pose_instruction = str(pose_instruction).replace("no duplicate limbs", "clean anatomically coherent limb structure")
    if allow_microphone:
        prop_clause = " Include exactly one simple handheld microphone as the only prop."
    elif allow_neutral_seat:
        prop_clause = " Include only a minimal neutral seat needed for the seated pose."
    return (
        "Use the reference character identity exactly. "
        "Create a white-background pose reference card with one centered subject and stable identity. "
        f"Depict {subject} with the exact face identity, distinctive hairstyle, readable face, and {wardrobe_anchor}. "
        f"Preserve the same wardrobe from the identity anchor: {wardrobe_anchor}; keep wardrobe color palette, collar and shoulder details, fabric weight cues, sleeve shape, and main outfit silhouette stable. "
        f"Pose and framing: {clean_pose_instruction}.{prop_clause} "
        "Use a pure white seamless studio background with soft even studio lighting."
    )


def _workflow_safe_anchor_subject(protagonist_anchor: str) -> str:
    text = str(protagonist_anchor or "").strip() or "one lead protagonist with story-appropriate presentation"
    blocked = ("no competing bystanders", "no bystanders", "no crowd", "no second protagonist", "no extra people")
    for phrase in blocked:
        text = text.replace(phrase, "")
    text = ", ".join(part.strip() for part in text.split(",") if part.strip())
    return text or "one lead protagonist with story-appropriate presentation"


def _pose_anchor_spec(spec: dict, protagonist_anchor: str, wardrobe_anchor: str) -> dict:
    return {
        "anchor_id": spec["anchor_id"],
        "anchor_type": "pose_variant",
        "anchor_role": "pose_variant",
        "material_class": "pose_reference_anchor",
        "workflow_target": "image_flux2_reference_image",
        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
        "source_anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
        "background_contract": "white_background",
        "identity_contract": "same face identity, same distinctive hairstyle from the identity anchor, same outfit, no wardrobe change",
        "pose_family": spec["pose_family"],
        "framing": spec["framing"],
        "camera_angle": spec["camera_angle"],
        "subject_position": spec["subject_position"],
        "intended_shot_functions": list(spec["intended_shot_functions"]),
        "allowed_props": list(spec.get("allowed_props", [])) if isinstance(spec.get("allowed_props"), list) else [],
        "avoid_for": ["unrelated_character", "new_wardrobe", "multi_person_scene"],
        "prompt_style": "white_background_pose_variant_from_upper_body_identity",
        "prompt_text": _pose_anchor_prompt(
            protagonist_anchor,
            wardrobe_anchor,
            str(spec["pose_instruction"]),
            allow_microphone="handheld_microphone" in spec.get("allowed_props", []),
            allow_neutral_seat="neutral_seat" in spec.get("allowed_props", []),
        ),
        "workflow_prompts": {
            "flux2_ref_anchor": {
                "positive_text": _pose_anchor_workflow_prompt(
                    protagonist_anchor,
                    wardrobe_anchor,
                    str(spec["pose_instruction"]),
                    allow_microphone="handheld_microphone" in spec.get("allowed_props", []),
                    allow_neutral_seat="neutral_seat" in spec.get("allowed_props", []),
                )
            }
        },
    }


def _pose_anchor_prompt(
    protagonist_anchor: str,
    wardrobe_anchor: str,
    pose_instruction: str,
    *,
    allow_microphone: bool = False,
    allow_neutral_seat: bool = False,
) -> str:
    forbidden = ["no umbrella", "no microphone", "no chair"]
    if allow_microphone:
        forbidden.remove("no microphone")
    if allow_neutral_seat:
        forbidden.remove("no chair")
    forbidden_props = ", ".join(forbidden)
    prop_contracts = []
    if allow_microphone:
        prop_contracts.append("Allow exactly one simple handheld microphone as the only prop.")
    if allow_neutral_seat:
        prop_contracts.append("Allow only a minimal neutral seat needed for the seated pose, with no environment detail.")
    prop_contract = f" {' '.join(prop_contracts)}" if prop_contracts else ""
    return (
        "Using the upper-body identity reference as the only face and wardrobe source, create a white-background pose reference variant. "
        "This pose card is anchored to the upper-body identity reference, not a full-body re-identity source. "
        f"Depict {protagonist_anchor} with the exact face fingerprint from the upper-body identity anchor, same face identity, the same distinctive hairstyle from the identity anchor, and {wardrobe_anchor}. "
        f"{_wardrobe_lock_sentence(wardrobe_anchor)} "
        f"Pose and framing: {pose_instruction}.{prop_contract} "
        "Keep a pure white seamless background and soft even studio lighting. This is a character pose card, not a story scene. "
        f"No street, no room, no city, no scenery, {forbidden_props}, no text, no logo, no second person, "
        "no distant human silhouettes, no bystanders, no duplicate body, no collage, no split screen, no frame insert, no decorative background, no wardrobe change."
    )

