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
    return {
        "strategy": "character_card_plus_world_anchor_then_reference_variants",
        "workflow_family": "flux2_reference_first",
        "anchors": [
            {
                "anchor_id": "ANCHOR_CHARACTER_FULL_BODY",
                "anchor_type": "character_full_body",
                "material_class": "character_reference_anchor",
                "workflow_target": "image_flux2_text_to_image",
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
                "anchor_id": "ANCHOR_WORLD_CHARACTER",
                "anchor_type": "world_character_anchor",
                "material_class": "world_reference_anchor",
                "workflow_target": "image_flux2_reference_image",
                "reference_anchor_ids": ["ANCHOR_CHARACTER_FULL_BODY", "ANCHOR_CHARACTER_UPPER_BODY"],
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
        f"Make a single clean full-body identity reference card of {protagonist_anchor} on a pure white seamless background. "
        f"She wears {wardrobe_anchor} and has a short black bob haircut with straight bangs. "
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
