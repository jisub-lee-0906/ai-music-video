from __future__ import annotations



def build_render_item_payload(
    *,
    shot: dict,
    render_mode: str,
    render_count: int,
    render_planning: dict,
    render_seed: int,
    variation_seed: int,
    variation_profile: dict,
    continuity_contract: dict,
    shot_relation_contract: dict,
    prompt_bundle: dict,
    still_prompt_text: str,
    clip_prompt_seed: str,
    clip_positive_prompt: str,
    edit_intent: dict,
    reference_policy: dict,
    variation_delta: dict,
    production_policy: dict | None = None,
) -> dict:
    out = {
        "shot_id": shot["shot_id"],
        "section_id": str(shot.get("section_id", "")).strip(),
        "material_id": str(shot.get("material_id", "")).strip(),
        "render_mode": render_mode,
        "render_count": render_count,
        "render_planning": render_planning,
        "render_priority_score": render_planning["render_priority_score"],
        "seed": render_seed,
        "variation_seed": variation_seed,
        "variation_profile": variation_profile,
        "continuity_contract": continuity_contract,
        "shot_relation_contract": shot_relation_contract,
        "prompt_seed": prompt_bundle["prompt_seed"],
        "prompt_draft": prompt_bundle["prompt_draft"],
        "prompt_polish": prompt_bundle["prompt_polish"],
        "still_prompt_text": still_prompt_text,
        "clip_prompt_seed": clip_prompt_seed,
        "clip_positive_prompt": clip_positive_prompt,
        "edit_intent": edit_intent,
        "reference_mode": reference_policy["reference_mode"],
        "reference_source_shot_id": reference_policy["reference_source_shot_id"],
        "identity_lock_strength": reference_policy["identity_lock_strength"],
        "edit_variation_scope": variation_delta["edit_variation_scope"],
        "minimum_visual_delta": variation_delta["minimum_visual_delta"],
        "production_policy": production_policy or {},
        "candidate_role": (production_policy or {}).get("candidate_role", ""),
        "ia2v_risk_class": (production_policy or {}).get("ia2v_risk_class", ""),
        "anchor_reference_arm": (production_policy or {}).get("anchor_reference_arm", ""),
        "recommended_duration_sec": (production_policy or {}).get("recommended_duration_sec", {}),
        "still_a": "",
    }
    if render_mode == "ia2v":
        out["audio_segment"] = {
            "start_sec": shot["start_sec"],
            "duration_sec": shot["duration_sec"],
        }
    return out
