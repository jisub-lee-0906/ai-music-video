from __future__ import annotations


def build_shot_intent(*, section_type: str, shot_role: str, visual_mode: str) -> dict:
    section = str(section_type or "").strip().lower()
    role = str(shot_role or "").strip().lower()
    visual = str(visual_mode or "").strip().lower()

    if section == "chorus" or role.startswith("chorus") or visual == "chorus_performance":
        return {
            "edit_role": "hook",
            "coverage_role": "anchor",
            "workflow_intent": "audio_reactive_candidate",
        }
    if section == "bridge" or role.startswith("bridge") or visual in {"night_bridge", "bridge_transition"}:
        return {
            "edit_role": "bridge",
            "coverage_role": "connective",
            "workflow_intent": "bridge_candidate",
        }
    if section in {"intro", "outro"}:
        return {
            "edit_role": "hook" if section == "intro" else "release",
            "coverage_role": "anchor",
            "workflow_intent": "stable_i2v",
        }
    return {
        "edit_role": "support",
        "coverage_role": "connective",
        "workflow_intent": "stable_i2v",
    }
