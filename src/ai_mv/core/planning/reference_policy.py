from __future__ import annotations


def build_reference_policy(shot: dict) -> dict:
    continuity_contract = shot.get("continuity_contract") if isinstance(shot.get("continuity_contract"), dict) else {}
    has_continuity_anchor = bool(
        str(continuity_contract.get("protagonist_anchor", "")).strip()
        or str(continuity_contract.get("world_anchor", "")).strip()
        or str(shot.get("protagonist_anchor", "")).strip()
        or str(shot.get("world_anchor", "")).strip()
    )
    shot_id = str(shot.get("shot_id", "")).strip()
    section_type = str(shot.get("section_type", "")).strip().lower()
    shot_role = str(shot.get("shot_role", "")).strip().lower()
    visual_mode = str(shot.get("visual_mode", "")).strip().lower()
    coverage_role = str(shot.get("coverage_role", "")).strip().lower()
    workflow_intent = str(shot.get("workflow_intent", "")).strip().lower()
    framing_intent = str(shot.get("framing_intent", "")).strip().lower()
    explicit_source = str(shot.get("reference_source_shot_id", "")).strip()
    requested_identity_lock = str(shot.get("identity_lock_strength", "")).strip().lower()
    is_performance = (
        "performance" in shot_role
        or visual_mode in {"chorus_performance", "chorus_front_lights"}
        or workflow_intent == "audio_reactive_candidate"
        or framing_intent == "performance_medium"
    )
    is_first_performance_arrival = shot_role in {"chorus_arrive", "chorus_breakout"} and coverage_role == "anchor"
    is_performance_anchor_source = is_performance and (
        "anchor" in shot_role
        or requested_identity_lock == "performance_anchor"
        or is_first_performance_arrival
        or (workflow_intent == "audio_reactive_candidate" and framing_intent == "performance_medium" and shot_role == "chorus_arrive")
    )
    if has_continuity_anchor and is_performance_anchor_source and not explicit_source:
        return {
            "reference_mode": "performance_anchor_source",
            "reference_source_shot_id": shot_id,
            "identity_lock_strength": "performance_anchor",
        }
    if has_continuity_anchor and (section_type == "intro" or "anchor" in shot_role) and not is_performance:
        return {
            "reference_mode": "anchor_source",
            "reference_source_shot_id": shot_id,
            "identity_lock_strength": "anchor",
        }
    if has_continuity_anchor and explicit_source:
        if requested_identity_lock == "performance_anchor" or is_performance:
            return {
                "reference_mode": "use_performance_anchor_still",
                "reference_source_shot_id": explicit_source,
                "identity_lock_strength": "performance_anchor",
            }
        return {
            "reference_mode": "use_anchor_still",
            "reference_source_shot_id": explicit_source,
            "identity_lock_strength": "high",
        }
    if has_continuity_anchor and is_performance:
        return {
            "reference_mode": "use_performance_anchor_still",
            "reference_source_shot_id": "",
            "identity_lock_strength": "performance_anchor",
        }
    if has_continuity_anchor:
        return {
            "reference_mode": "use_anchor_still",
            "reference_source_shot_id": "",
            "identity_lock_strength": "high",
        }
    return {
        "reference_mode": "",
        "reference_source_shot_id": "",
        "identity_lock_strength": "off",
    }



def build_variation_delta_contract(shot: dict, reference_policy: dict | None = None) -> dict:
    policy = reference_policy if isinstance(reference_policy, dict) else {}
    reference_mode = str(policy.get("reference_mode", "")).strip().lower()
    section_type = str(shot.get("section_type", "")).strip().lower()
    shot_role = str(shot.get("shot_role", "")).strip().lower()
    visual_mode = str(shot.get("visual_mode", "")).strip().lower()
    if reference_mode == "use_performance_anchor_still":
        return {
            "edit_variation_scope": "performance_pose_upgrade",
            "minimum_visual_delta": "pose_or_camera_change_required",
        }
    if reference_mode == "performance_anchor_source":
        return {
            "edit_variation_scope": "free_generate",
            "minimum_visual_delta": "none",
        }
    if section_type == "bridge" or "bridge" in shot_role or "bridge" in visual_mode:
        return {
            "edit_variation_scope": "bridge_reframe",
            "minimum_visual_delta": "lighting_or_framing_change_required",
        }
    if reference_mode == "use_anchor_still":
        return {
            "edit_variation_scope": "framing_only",
            "minimum_visual_delta": "camera_distance_or_angle_change_required",
        }
    if reference_mode == "anchor_source":
        return {
            "edit_variation_scope": "free_generate",
            "minimum_visual_delta": "none",
        }
    return {
        "edit_variation_scope": "free_generate",
        "minimum_visual_delta": "none",
    }
