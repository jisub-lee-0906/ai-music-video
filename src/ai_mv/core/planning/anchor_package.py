from __future__ import annotations


def build_anchor_package(*, concept_text: str, style_name: str, creative_direction: dict | None = None) -> dict:
    """Build the stable reference-anchor package used before story variants.

    The package intentionally separates character-card anchors from the world anchor:
    a pure white card is good for identity/outfit isolation, while a world+character
    anchor carries lighting, camera, and environment continuity for reference edits.
    """

    direction = creative_direction if isinstance(creative_direction, dict) else {}
    protagonist_anchor = str(direction.get("protagonist_anchor", "")).strip() or "one beautiful young Korean woman"
    world_anchor = str(direction.get("world_anchor", "")).strip() or _default_world_anchor(concept_text, style_name)
    if _needs_rainy_neon_hint(concept_text, style_name) and "rainy neon" not in world_anchor.lower():
        world_anchor = f"rainy neon continuity world, {world_anchor}"
    wardrobe_anchor = _wardrobe_anchor(style_name)
    pose_anchor_bank = _pose_anchor_bank(protagonist_anchor, wardrobe_anchor)
    return {
        "strategy": "character_card_plus_world_anchor_then_reference_variants",
        "workflow_family": "flux2_reference_first",
        "anchors": [
            {
                "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                "anchor_type": "character_upper_body_identity",
                "material_class": "character_reference_anchor",
                "workflow_target": "image_flux2_text_to_image",
                "prompt_style": "upper_body_identity_card",
                "prompt_text": _upper_body_identity_prompt(protagonist_anchor, wardrobe_anchor),
                "selection_criteria": [
                    "pure_white_background",
                    "single_subject_only",
                    "clear_face_visibility",
                    "hair_identity_readable",
                    "upper_outfit_readable",
                ],
            },
            {
                "anchor_id": "ANCHOR_CHARACTER_FULL_BODY",
                "anchor_type": "character_full_body",
                "material_class": "character_reference_anchor",
                "workflow_target": "image_flux2_reference_image",
                "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                "prompt_style": "negative_heavy_strict_card",
                "prompt_text": _full_body_character_prompt(protagonist_anchor, wardrobe_anchor),
                "selection_criteria": [
                    "pure_white_background",
                    "single_subject_only",
                    "full_body_visible",
                    "face_readable",
                    "outfit_silhouette_readable",
                ],
            },
            {
                "anchor_id": "ANCHOR_WORLD_CHARACTER",
                "anchor_type": "world_character_anchor",
                "material_class": "world_reference_anchor",
                "workflow_target": "image_flux2_reference_image",
                "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY", "ANCHOR_CHARACTER_FULL_BODY"],
                "prompt_style": "preserve_character_then_establish_world",
                "prompt_text": _world_character_prompt(protagonist_anchor, wardrobe_anchor, world_anchor),
                "selection_criteria": [
                    "same_character_identity",
                    "same_outfit_silhouette",
                    "readable_world_mood",
                    "single_continuous_scene",
                    "motion_safe_keyframe",
                ],
            },
        ],
        "pose_anchor_bank": pose_anchor_bank,
        "pose_anchor_policy": {
            "primary_identity_anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
            "workflow_target": "image_flux2_reference_image",
            "background_contract": "white_background",
            "selection_policy": "shot_intent_pose_family_match_then_identity_fallback",
            "diversity_guard": "do_not_route_all_story_keyframes_through_the_static_upper_body_identity_card",
        },
        "variant_policy": {
            "workflow_target": "image_flux2_reference_image",
            "reference_order": ["character_full_body", "character_upper_body_identity", "world_character_anchor"],
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


def _needs_rainy_neon_hint(concept_text: str, style_name: str) -> bool:
    concept = str(concept_text or "").lower()
    return "rain" in concept or "neon" in concept or style_name == "citypop"


def _default_world_anchor(concept_text: str, style_name: str) -> str:
    concept = str(concept_text or "").lower()
    if "rain" in concept or "neon" in concept or style_name == "citypop":
        return "rainy neon city street at night"
    if style_name == "idol_pop":
        return "glossy night performance stage with bright city lights"
    return "cinematic music-video world from the concept"


def _wardrobe_anchor(style_name: str) -> str:
    if style_name == "idol_pop":
        return "a bright stage-ready outfit with a clear stable silhouette"
    return "a bright red raincoat over simple dark clothes"


def _full_body_character_prompt(protagonist_anchor: str, wardrobe_anchor: str) -> str:
    return (
        f"Using the upper-body identity reference as the face source, make a single clean full-body identity reference card of {protagonist_anchor} on a pure white seamless background. "
        f"Preserve the same face identity from the upper-body reference, same short black bob haircut with straight bangs, and {wardrobe_anchor}. "
        "The character must be alone, centered, full body visible, face readable, outfit readable, soft studio lighting. "
        "No street, no room, no city, no scenery, no umbrella, no microphone, no chair, no text, no logo, no second person, "
        "no duplicate body, no collage, no split screen, no frame insert, no decorative background."
    )


def _upper_body_identity_prompt(protagonist_anchor: str, wardrobe_anchor: str) -> str:
    return (
        f"Create a clean upper-body character reference image of {protagonist_anchor} alone on a seamless pure white studio background. "
        f"Frame her from the waist up, centered, with clear face visibility, short black bob haircut with straight bangs, gentle expressive eyes, and {wardrobe_anchor} clearly visible at the collar and shoulders. "
        "Use soft even studio lighting and keep it as one continuous clean character card with no props, no scenery, no text, no logo, no collage, no split screen, and no extra people."
    )


def _world_character_prompt(protagonist_anchor: str, wardrobe_anchor: str, world_anchor: str) -> str:
    return (
        "Using the same woman as the character reference, create a single cinematic film still of her inside the music-video world. "
        f"Preserve {protagonist_anchor}, short black bob haircut with straight bangs, face identity, and {wardrobe_anchor}. "
        f"Place her in a {world_anchor}, with the character integrated naturally into the environment as the clear main subject. "
        "Use a medium-wide motion-safe frame with readable face, readable outfit silhouette, coherent depth, and one continuous scene. "
        "No text overlay, no collage, no split screen, no duplicate protagonist, and no extra main character."
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
        "identity_contract": "same face identity, same short black bob haircut with straight bangs, same outfit, no wardrobe change",
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
        f"Depict {protagonist_anchor} with the same face identity, same short black bob haircut with straight bangs, and {wardrobe_anchor}. "
        f"Pose and framing: {pose_instruction}.{prop_contract} "
        "Keep a pure white seamless background and soft even studio lighting. This is a character pose card, not a story scene. "
        f"No street, no room, no city, no scenery, {forbidden_props}, no text, no logo, no second person, "
        "no duplicate body, no collage, no split screen, no frame insert, no decorative background, no wardrobe change."
    )

