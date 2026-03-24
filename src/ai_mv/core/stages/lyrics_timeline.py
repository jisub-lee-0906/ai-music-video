from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_preview
from ai_mv.engines.lyrics_timeline.planner import _planner_prompt, build_lyrics_timeline


def run_lyrics_timeline(stage_input: StageInput) -> StageOutput:
    timeline = build_lyrics_timeline(stage_input.config, stage_input.payload)
    return StageOutput(
        "lyrics_timeline",
        "done",
        {
            "lyrics_timeline": timeline,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), lyrics_timeline=timeline),
            "planner_prompts": merge_preview(stage_input.payload, "lyrics_timeline", {"prompt": _planner_prompt(stage_input.payload["audio_plan"], stage_input.payload["audio_map"]["sections"])}),
            "workflow_inputs_preview": merge_preview(stage_input.payload, "lyrics_timeline", {"sections": _timeline_preview(timeline)}),
        },
        [],
    )


def _timeline_preview(timeline: dict) -> list[dict]:
    out: list[dict] = []
    for section in timeline.get("sections", []):
        out.append(
            {
                "section_name": str(section.get("section_name", "")),
                "section_label": str(section.get("section_label", "")),
                "line_count": len(section.get("lines", [])),
                "hook_lines": list(section.get("hook_lines", [])),
                "lyric_beats": [
                    {
                        "beat_id": str(beat.get("beat_id", "")),
                        "line_refs": list(beat.get("line_refs", [])),
                        "literal_image": str(beat.get("literal_image", "")),
                        "visible_action": str(beat.get("visible_action", "")),
                        "payoff_role": str(beat.get("payoff_role", "")),
                    }
                    for beat in section.get("lyric_beats", [])
                    if isinstance(beat, dict)
                ],
            }
        )
    return out


