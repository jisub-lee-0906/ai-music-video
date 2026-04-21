from __future__ import annotations


def build_shot_intent(*, section_type: str, shot_role: str, visual_mode: str) -> dict:
    section = str(section_type or "").strip().lower()
    role = str(shot_role or "").strip().lower()
    visual = str(visual_mode or "").strip().lower()

    if visual == "chorus_performance":
        return {
            "edit_role": "hook",
            "coverage_role": "anchor",
            "workflow_intent": "audio_reactive_candidate",
            "framing_intent": "performance_medium",
        }
    if section == "chorus" or role.startswith("chorus"):
        return {
            "edit_role": "hook",
            "coverage_role": "connective",
            "workflow_intent": "stable_i2v",
            "framing_intent": "release_wide",
        }
    if section == "pre_chorus":
        return {
            "edit_role": "bridge",
            "coverage_role": "connective",
            "workflow_intent": "bridge_candidate",
            "framing_intent": "connective_medium",
        }
    if section == "bridge" or role.startswith("bridge") or visual in {"night_bridge", "bridge_transition"}:
        return {
            "edit_role": "bridge",
            "coverage_role": "connective",
            "workflow_intent": "bridge_candidate",
            "framing_intent": "connective_medium",
        }
    if section == "intro":
        return {
            "edit_role": "hook",
            "coverage_role": "anchor",
            "workflow_intent": "stable_i2v",
            "framing_intent": "establishing_wide",
        }
    if section == "outro":
        return {
            "edit_role": "release",
            "coverage_role": "anchor",
            "workflow_intent": "stable_i2v",
            "framing_intent": "release_wide",
        }
    return {
        "edit_role": "support",
        "coverage_role": "connective",
        "workflow_intent": "stable_i2v",
        "framing_intent": "hero_medium",
    }
