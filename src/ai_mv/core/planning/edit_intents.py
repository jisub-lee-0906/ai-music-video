from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP



def build_edit_intent(shot: dict, variation_profile: dict | None = None) -> dict:
    edit_role = str(shot.get("edit_role", "support")).strip()
    duration_sec = float(shot.get("duration_sec", 0.0) or 0.0)
    variation = variation_profile if isinstance(variation_profile, dict) else {}
    motion_variant = str(variation.get("motion_variant", "")).strip()
    framing_variant = str(variation.get("framing_variant", "")).strip()
    if edit_role == "hook":
        if motion_variant == "pulsed":
            return {
                "edit_priority": "high",
                "section_emphasis": "chorus_push",
                "pattern_family": "hook_punch_in",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.4),
                "transition_in": "accent_in",
                "transition_out": "accent_out",
            }
        if motion_variant == "gliding":
            return {
                "edit_priority": "high",
                "section_emphasis": "chorus_push",
                "pattern_family": "hook_sustain",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.6),
                "transition_in": "glide_in",
                "transition_out": "accent_out",
            }
        return {
            "edit_priority": "high",
            "section_emphasis": "chorus_push",
            "pattern_family": "hook_surge",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.5),
            "transition_in": "cut_in",
            "transition_out": "accent_out",
        }
    if edit_role == "bridge":
        if motion_variant == "gliding":
            return {
                "edit_priority": "medium",
                "section_emphasis": "bridge_contrast",
                "pattern_family": "bridge_glide",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.6),
                "transition_in": "glide_in",
                "transition_out": "handoff_out",
            }
        return {
            "edit_priority": "medium",
            "section_emphasis": "bridge_contrast",
            "pattern_family": "bridge_pivot",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.45),
            "transition_in": "cut_in",
            "transition_out": "handoff_out",
        }
    if edit_role == "release":
        if motion_variant == "gliding" or framing_variant == "environment_forward":
            return {
                "edit_priority": "medium",
                "section_emphasis": "release_fade",
                "pattern_family": "release_drift",
                "target_clip_sec": _scaled_target_clip(duration_sec, 0.7),
                "transition_in": "hold_in",
                "transition_out": "fade_out",
            }
        return {
            "edit_priority": "medium",
            "section_emphasis": "release_fade",
            "pattern_family": "release_tail",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.5),
            "transition_in": "cut_in",
            "transition_out": "fade_out",
        }
    if motion_variant == "pulsed":
        return {
            "edit_priority": "medium",
            "section_emphasis": "sequence_support",
            "pattern_family": "support_drive",
            "target_clip_sec": _scaled_target_clip(duration_sec, 0.45),
            "transition_in": "cut_in",
            "transition_out": "cut_out",
        }
    return {
        "edit_priority": "medium",
        "section_emphasis": "sequence_support",
        "pattern_family": "support_hold",
        "target_clip_sec": _scaled_target_clip(duration_sec, 0.7),
        "transition_in": "hold_in",
        "transition_out": "cut_out",
    }



def _scaled_target_clip(duration_sec: float, ratio: float) -> float:
    duration = max(0.0, float(duration_sec or 0.0))
    if duration <= 0.0:
        return 0.0
    scaled = max(0.6, duration * float(ratio))
    return float(_round_half_up(min(duration, scaled), 3))



def _round_half_up(value: float, digits: int) -> float:
    quantize_exp = "1." + ("0" * max(0, digits))
    adjusted = Decimal(str(value + 1e-12))
    return float(adjusted.quantize(Decimal(quantize_exp), rounding=ROUND_HALF_UP))
