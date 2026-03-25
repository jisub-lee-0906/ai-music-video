from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import build_stage_payload
from ai_mv.engines.lyrics_timeline.planner import _planner_prompt, build_lyrics_timeline
from ai_mv.engines.lyrics_timeline.planner import build_lyrics_timeline_preview_prompt


def run_lyrics_timeline(stage_input: StageInput) -> StageOutput:
    timeline = build_lyrics_timeline(stage_input.config, stage_input.payload)
    return StageOutput(
        "lyrics_timeline",
        "done",
        build_stage_payload(
            stage_input.payload,
            planner_key="lyrics_timeline",
            planner_value={"prompt": _planner_prompt(stage_input.payload["audio_plan"], stage_input.payload["audio_map"]["sections"])},
            workflow_key="lyrics_timeline",
            workflow_value={"sections": _timeline_preview(timeline)},
            render_updates={"lyrics_timeline": timeline},
            lyrics_timeline=timeline,
        ),
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


def build_lyrics_timeline_preview_payload(config: dict, payload: dict) -> dict:
    timeline = build_lyrics_timeline(config, payload)
    return build_stage_payload(
        payload,
        planner_key="lyrics_timeline",
        planner_value={"prompt": build_lyrics_timeline_preview_prompt(payload["audio_plan"], payload["audio_map"]["sections"])},
        workflow_key="lyrics_timeline",
        workflow_value={"sections": list(timeline.get("sections", []))},
        render_updates={"lyrics_timeline": timeline},
        lyrics_timeline=timeline,
    )


