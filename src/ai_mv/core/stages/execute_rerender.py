from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.repair_audio_video_sync import run_repair_audio_video_sync
from ai_mv.core.stages.render_clips import run_render_clips
from ai_mv.core.stages.render_stills import run_render_stills


REVIEW_ACTIONS_REQUIRING_SYNC_REPAIR = {"repair_audio_video_sync"}
ASSEMBLY_REVIEW_ACTIONS = {
    "revise_assembly_weights_before_clip_rerender",
    "revise_transition_selection",
}


def _stage_runner(stage_name: str):
    if stage_name == "stills":
        return run_render_stills
    if stage_name == "clips":
        return run_render_clips
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
        if stage_name == "review" and isinstance(payload, dict):
            result = _run_review_action(stage_input, payload)
            for key in ("final_video", "music_file", "review_inputs", "review_action", "assembly_revision_result"):
                value = result.payload.get(key)
                if value:
                    passthrough_payload[key] = value
            completed_stages.append(stage_name)
            artifacts.extend(str(path) for path in result.artifacts if str(path).strip())
            continue
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



def _run_review_action(stage_input: StageInput, payload: dict) -> StageOutput:
    recommended_action = str(payload.get("recommended_action", "")).strip()
    stage_payload = {key: value for key, value in payload.items() if key != "recommended_action"}
    if recommended_action in REVIEW_ACTIONS_REQUIRING_SYNC_REPAIR:
        return run_repair_audio_video_sync(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=stage_payload))
    passthrough_payload = {
        key: stage_payload[key]
        for key in ("final_video", "music_file", "review_inputs")
        if key in stage_payload and stage_payload[key]
    }
    if recommended_action in ASSEMBLY_REVIEW_ACTIONS:
        passthrough_payload["review_inputs"] = {
            **(passthrough_payload.get("review_inputs") if isinstance(passthrough_payload.get("review_inputs"), dict) else {}),
            "assembly_revision": {
                "action": recommended_action,
                "target": "assembly",
                "final_video": str(stage_payload.get("final_video", "")).strip(),
                "music_file": str(stage_payload.get("music_file", "")).strip(),
            },
        }
        passthrough_payload["assembly_revision_result"] = {
            "action": recommended_action,
            "status": "ready",
            "target": "assembly",
            "output_final_video": str(stage_payload.get("final_video", "")).strip(),
            "revision_focus": "weights" if recommended_action == "revise_assembly_weights_before_clip_rerender" else "transitions",
        }
    passthrough_payload["review_action"] = recommended_action or "review_failed_checks"
    return StageOutput("review_action", "done", passthrough_payload, [])
