from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.repair_audio_video_sync import run_repair_audio_video_sync
from ai_mv.core.stages.render_clips import run_render_clips
from ai_mv.core.stages.render_stills import run_render_stills


def _stage_runner(stage_name: str):
    if stage_name == "stills":
        return run_render_stills
    if stage_name == "clips":
        return run_render_clips
    if stage_name == "review":
        return run_repair_audio_video_sync
    return None


def run_execute_rerender(stage_input: StageInput) -> StageOutput:
    stage_sequence = [str(name).strip() for name in stage_input.payload.get("rerender_stage_sequence", []) if str(name).strip()]
    stage_inputs = stage_input.payload.get("rerender_stage_inputs") if isinstance(stage_input.payload.get("rerender_stage_inputs"), dict) else {}
    rerendered_stills: list[dict] = []
    rerendered_clips: list[dict] = []
    completed_stages: list[str] = []
    passthrough_payload: dict[str, object] = {}
    artifacts: list[str] = []

    for stage_name in stage_sequence:
        runner = _stage_runner(stage_name)
        payload = stage_inputs.get(stage_name)
        if runner is None or not isinstance(payload, dict):
            continue
        stage_payload = dict(payload)
        if stage_name == "clips":
            stage_payload["still_results"] = _merge_still_results(
                base_results=stage_payload.get("still_results"),
                fresh_results=rerendered_stills,
            )
        result = runner(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=stage_payload))
        if stage_name == "stills":
            rerendered_stills = [row for row in result.payload.get("still_results", []) if isinstance(row, dict)]
        if stage_name == "clips":
            rerendered_clips = [row for row in result.payload.get("clip_results", []) if isinstance(row, dict)]
        if stage_name == "review":
            for key in ("final_video", "music_file", "review_inputs"):
                value = result.payload.get(key)
                if value:
                    passthrough_payload[key] = value
        completed_stages.append(stage_name)
        artifacts.extend(str(path) for path in result.artifacts if str(path).strip())

    return StageOutput(
        "execute_rerender",
        "done",
        {
            "rerender_results": {
                "completed_stages": completed_stages,
                "still_results": rerendered_stills,
                "clip_results": rerendered_clips,
            },
            **passthrough_payload,
        },
        artifacts,
    )



def _merge_still_results(*, base_results: object, fresh_results: list[dict]) -> list[dict]:
    merged: list[dict] = []
    fresh_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in fresh_results
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    for row in base_results if isinstance(base_results, list) else []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if shot_id and shot_id in fresh_map:
            continue
        merged.append(row)
    merged.extend(fresh_map.values())
    return merged
