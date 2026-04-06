from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.director_plan.planner import build_direction_plan
from ai_mv.engines.lyrics_timeline.planner import build_lyrics_timeline
from ai_mv.engines.render_plan.planner import build_prompt_plan
from ai_mv.engines.scene_plan.planner import build_scene_outline


def run_storyboard(stage_input: StageInput) -> StageOutput:
    payload = dict(stage_input.payload)
    timeline = build_lyrics_timeline(stage_input.config, payload)
    payload["lyrics_timeline"] = timeline
    scene = build_scene_outline(stage_input.config, payload)
    payload["scene_outline"] = scene
    direction = build_direction_plan(stage_input.config, payload)
    payload["direction_plan"] = direction
    prompt_plan = build_prompt_plan(stage_input.config, payload)
    shots = [row for row in prompt_plan.get("ref_items", []) if isinstance(row, dict)]
    return StageOutput(
        "storyboard",
        "done",
        {
            "lyrics_timeline": timeline,
            "scene_outline": scene,
            "direction_plan": direction,
            "prompt_plan": prompt_plan,
            "storyboard": {
                "section_count": len([row for row in timeline.get("sections", []) if isinstance(row, dict)]),
                "shot_count": len(shots),
                "transition_count": len([row for row in prompt_plan.get("wan_items", []) if isinstance(row, dict)]),
            },
        },
        [],
    )


def build_storyboard_preview_payload(config: dict, payload: dict) -> dict:
    timeline = build_lyrics_timeline(config, payload)
    preview_payload = dict(payload)
    preview_payload["lyrics_timeline"] = timeline
    scene = build_scene_outline(config, preview_payload)
    preview_payload["scene_outline"] = scene
    direction = build_direction_plan(config, preview_payload)
    preview_payload["direction_plan"] = direction
    prompt_plan = build_prompt_plan(config, preview_payload)
    shots = [row for row in prompt_plan.get("ref_items", []) if isinstance(row, dict)]
    return {
        "lyrics_timeline": timeline,
        "scene_outline": scene,
        "direction_plan": direction,
        "prompt_plan": prompt_plan,
        "storyboard": {
            "section_count": len([row for row in timeline.get("sections", []) if isinstance(row, dict)]),
            "shot_count": len(shots),
            "transition_count": len([row for row in prompt_plan.get("wan_items", []) if isinstance(row, dict)]),
        },
    }
