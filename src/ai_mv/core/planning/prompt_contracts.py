from __future__ import annotations



def build_still_prompt_text(
    prompt_seed: str,
    prompt_draft: str,
    prompt_polish: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
) -> str:
    base = str(prompt_polish or prompt_draft or prompt_seed).strip()
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    relation = shot_relation_contract if isinstance(shot_relation_contract, dict) else {}
    return _join_prompt_tokens(
        [
            base,
            _framing_variant_token(str(variation.get("framing_variant", "")).strip()),
            _environment_variant_token(str(variation.get("environment_variant", "")).strip()),
            _section_emphasis_variant_token(str(variation.get("section_emphasis_variant", "")).strip()),
            str(relation.get("camera_distance_progression", "")).strip(),
            str(relation.get("same_block_vs_new_block", "")).strip(),
        ]
    )



def build_clip_prompt_seed(
    render_mode: str,
    shot: dict,
    prompt_seed: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
) -> str:
    role = str(shot.get("shot_role", "")).replace("_", " ").strip()
    visual_mode = str(shot.get("visual_mode", "")).replace("_", " ").strip()
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    relation = shot_relation_contract if isinstance(shot_relation_contract, dict) else {}
    seed_prefix = str(prompt_seed or "").split(",")[0].strip()
    return _join_prompt_tokens(
        [
            seed_prefix,
            role or "performance shot",
            visual_mode or "music-responsive motion",
            _motion_variant_token(str(variation.get("motion_variant", "")).strip()),
            _continuity_variant_token(str(variation.get("continuity_variant", "")).strip()),
            _section_emphasis_clip_token(str(variation.get("section_emphasis_variant", "")).strip()),
            str(relation.get("relation_to_previous_shot", "")).strip(),
        ]
    )



def build_clip_positive_prompt(
    render_mode: str,
    shot: dict,
    clip_prompt_seed: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
) -> str:
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    relation = shot_relation_contract if isinstance(shot_relation_contract, dict) else {}
    framing_variant = _clip_framing_variant(shot, str(variation.get("framing_variant", "")).strip())
    return _join_prompt_tokens(
        [
            clip_prompt_seed,
            _continuity_identity_token(str(variation.get("continuity_variant", "")).strip()),
            _framing_camera_token(framing_variant),
            _environment_motion_token(str(variation.get("environment_variant", "")).strip()),
            str(relation.get("same_block_vs_new_block", "")).strip(),
            str(relation.get("emotional_delta", "")).strip(),
        ]
    )



def _join_prompt_tokens(parts: list[str]) -> str:
    tokens: list[str] = []
    for part in parts:
        value = str(part or "").strip()
        if value and value not in tokens:
            tokens.append(value)
    return ", ".join(tokens)



def _framing_variant_token(variant: str) -> str:
    return {
        "balanced": "balanced cinematic framing",
        "subject_forward": "subject-forward framing emphasis",
        "environment_forward": "environment-led framing emphasis",
    }.get(variant, "balanced cinematic framing")



def _environment_variant_token(variant: str) -> str:
    return {
        "atmospheric": "atmospheric world detail emphasis",
        "textural": "textural light and surface detail emphasis",
        "spatial": "clear spatial depth emphasis",
    }.get(variant, "atmospheric world detail emphasis")



def _section_emphasis_variant_token(variant: str) -> str:
    return {
        "hook_forward": "hook-first still emphasis",
        "lifted_release": "lifted release still emphasis",
        "performance_peak": "performance-peak still emphasis",
        "contrastive_turn": "contrastive section-turn emphasis",
        "late-night drift": "late-night drift emphasis",
        "reset_suspension": "reset-and-suspension emphasis",
        "world_anchor": "world-anchor still emphasis",
        "afterglow_hold": "afterglow hold emphasis",
        "slow_release": "slow release emphasis",
        "forward_drive": "forward-drive still emphasis",
        "cinematic_push": "cinematic push still emphasis",
        "contained_intensity": "contained intensity emphasis",
        "sequence_support": "sequence-support still emphasis",
        "observational_flow": "observational flow emphasis",
        "ambient_progression": "ambient progression emphasis",
    }.get(variant, "sequence-support still emphasis")



def _motion_variant_token(variant: str) -> str:
    return {
        "restrained": "restrained camera motion",
        "gliding": "gliding camera motion",
        "pulsed": "beat-responsive camera motion",
    }.get(variant, "restrained camera motion")



def _continuity_variant_token(variant: str) -> str:
    return {
        "strict": "strict continuity anchors",
        "anchored": "stable continuity anchors",
        "expressive": "expressive continuity within the same world",
    }.get(variant, "stable continuity anchors")



def _section_emphasis_clip_token(variant: str) -> str:
    return {
        "hook_forward": "audio-reactive hook energy",
        "lifted_release": "lifted release energy",
        "performance_peak": "audio-reactive performance peak",
        "contrastive_turn": "contrastive section turn",
        "late-night drift": "late-night motion drift",
        "reset_suspension": "reset-and-suspension beat",
        "world_anchor": "world-anchor motion restraint",
        "afterglow_hold": "afterglow hold beat",
        "slow_release": "slow release beat",
        "forward_drive": "forward-driving energy",
        "cinematic_push": "cinematic motion push",
        "contained_intensity": "contained motion intensity",
        "sequence_support": "sequence-support motion",
        "observational_flow": "observational motion flow",
        "ambient_progression": "ambient progression motion",
    }.get(variant, "audio-reactive energy")



def _continuity_identity_token(variant: str) -> str:
    return {
        "strict": "strict performer identity lock",
        "anchored": "stable performer identity",
        "expressive": "stable performer identity with expressive motion",
    }.get(variant, "stable performer identity")



def _framing_camera_token(variant: str) -> str:
    return {
        "balanced": "restrained camera",
        "subject_forward": "subject-led camera framing",
        "environment_forward": "environment-led camera framing",
    }.get(variant, "restrained camera")



def _clip_framing_variant(shot: dict, variant: str) -> str:
    normalized_variant = str(variant or "").strip()
    if normalized_variant != "environment_forward":
        return normalized_variant
    section_type = str(shot.get("section_type", "")).strip().lower()
    if section_type in {"intro", "bridge", "outro"}:
        return "balanced"
    return normalized_variant



def _environment_motion_token(variant: str) -> str:
    return {
        "atmospheric": "atmospheric motion continuity",
        "textural": "textural light continuity",
        "spatial": "clear spatial continuity",
    }.get(variant, "no abrupt pose change")
