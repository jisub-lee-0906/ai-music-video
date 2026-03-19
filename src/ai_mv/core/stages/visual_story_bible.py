from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.visual_story_bible.planner import _planner_prompt, build_visual_story_bible


def run_visual_story_bible(stage_input: StageInput) -> StageOutput:
    story_bible = build_visual_story_bible(stage_input.config, stage_input.payload)
    return StageOutput(
        "visual_story_bible",
        "done",
        {
            "visual_story_bible": story_bible,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), visual_story_bible=story_bible),
            "planner_prompts": _merge(stage_input.payload, "visual_story_bible", {"prompt": _planner_prompt(stage_input.config, stage_input.payload)}),
            "workflow_inputs_preview": _merge(stage_input.payload, "visual_story_bible", {"story_bible_preview": _preview(story_bible)}),
        },
        [],
    )


def _preview(story_bible: dict) -> dict:
    return {
        "hero_identity_lock": str(story_bible.get("hero_identity_lock", "")),
        "heroine_invariants": str(story_bible.get("heroine_invariants", "")),
        "world_rules": str(story_bible.get("world_rules", "")),
        "world_invariants": str(story_bible.get("world_invariants", "")),
        "closeup_rules": str(story_bible.get("closeup_rules", "")),
        "recurring_location_families": list(story_bible.get("recurring_location_families", [])),
        "lyric_beats": [
            {
                "beat_id": str(beat.get("beat_id", "")),
                "section_label": str(beat.get("section_label", "")),
                "line_refs": list(beat.get("line_refs", [])),
                "literal_image": str(beat.get("literal_image", "")),
                "visible_action": str(beat.get("visible_action", "")),
                "location_family": str(beat.get("location_family", "")),
            }
            for beat in story_bible.get("lyric_beats", [])
            if isinstance(beat, dict)
        ],
    }


def _merge(payload: dict, key: str, value: dict) -> dict:
    root = "planner_prompts" if "prompt" in value or "batches" in value else "workflow_inputs_preview"
    out = dict(payload.get(root, {}))
    out[key] = value
    return out
