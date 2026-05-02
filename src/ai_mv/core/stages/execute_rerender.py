from pathlib import Path

from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.assemble_mv import apply_assembly_revision, run_assemble_mv
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.core.stages.repair_audio_video_sync import run_repair_audio_video_sync
from ai_mv.core.stages.render_clips import run_render_clips
from ai_mv.core.stages.render_stills import run_render_stills
from ai_mv.utils.path_utils import resolve_generated_file
from ai_mv.utils.time_utils import ffprobe_duration


REVIEW_ACTIONS_REQUIRING_SYNC_REPAIR = {"repair_audio_video_sync"}
ASSEMBLY_REVIEW_ACTIONS = {
    "revise_assembly_weights_before_clip_rerender",
    "revise_transition_selection",
    "revise_assembly_coverage_before_sync_pad",
}


def _stage_runner(stage_name: str):
    if stage_name == "stills":
        return run_render_stills
    if stage_name == "clips":
        return run_render_clips
    if stage_name == "assemble":
        return run_assemble_mv
    return None


def run_execute_rerender(stage_input: StageInput) -> StageOutput:
    stage_sequence = [str(name).strip() for name in stage_input.payload.get("rerender_stage_sequence", []) if str(name).strip()]
    stage_inputs = stage_input.payload.get("rerender_stage_inputs") if isinstance(stage_input.payload.get("rerender_stage_inputs"), dict) else {}
    rerendered_stills: list[dict] = []
    rerendered_anchor_results: list[dict] = []
    rerendered_clips: list[dict] = []
    completed_stages: list[str] = []
    passthrough_payload: dict[str, object] = {}
    assembly_result_payload: dict[str, object] = {}
    artifacts: list[str] = []

    for stage_name in stage_sequence:
        runner = _stage_runner(stage_name)
        payload = stage_inputs.get(stage_name)
        if stage_name == "review" and isinstance(payload, dict):
            result = _run_review_action(stage_input, payload)
            for key in ("final_video", "music_file", "review_inputs", "review_action", "assembly_revision_result", "sync_repair_summary"):
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
        if stage_name == "assemble":
            stage_payload = _merged_repair_assembly_payload(stage_payload, rerendered_clips)
        validate_stage_input(stage_name, stage_payload)
        result = runner(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=stage_payload))
        if stage_name == "stills":
            rerendered_stills = [row for row in result.payload.get("still_results", []) if isinstance(row, dict)]
            rerendered_anchor_results = [row for row in result.payload.get("anchor_results", []) if isinstance(row, dict)]
        if stage_name == "clips":
            rerendered_clips = [row for row in result.payload.get("clip_results", []) if isinstance(row, dict)]
        if stage_name == "assemble":
            for key in ("final_video", "assembly_plan", "review_inputs"):
                value = result.payload.get(key)
                if value:
                    passthrough_payload[key] = value
                    assembly_result_payload[key] = value
            if result.payload.get("final_video"):
                passthrough_payload["rerender_final_video"] = result.payload.get("final_video")
        completed_stages.append(stage_name)
        artifacts.extend(str(path) for path in result.artifacts if str(path).strip())

    rerender_results = {
        "completed_stages": completed_stages,
        "still_results": rerendered_stills,
        "clip_results": rerendered_clips,
    }
    for key in ("final_video", "assembly_plan", "review_inputs"):
        if assembly_result_payload.get(key):
            rerender_results[key] = assembly_result_payload[key]
    if rerendered_anchor_results:
        rerender_results["anchor_results"] = rerendered_anchor_results
        passthrough_payload["anchor_results"] = rerendered_anchor_results
    return StageOutput(
        "execute_rerender",
        "done",
        {
            "rerender_results": rerender_results,
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


def _merged_repair_assembly_payload(stage_payload: dict, fresh_clip_results: list[dict]) -> dict:
    merged = dict(stage_payload)
    repair_clip_ids = {
        str(row.get("shot_id", "")).strip()
        for row in fresh_clip_results
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    merged["clip_results"] = _merge_rows_by_shot_id(merged.get("clip_results"), fresh_clip_results)
    for key in ("shot_plan", "render_plan"):
        rows = merged.get(key) if isinstance(merged.get(key), list) else []
        merged[key] = _insert_repair_rows_by_neighbor(rows, repair_clip_ids)
    return merged


def _merge_rows_by_shot_id(base_rows: object, fresh_rows: object) -> list[dict]:
    merged: list[dict] = []
    fresh_items = fresh_rows if isinstance(fresh_rows, list) else []
    fresh_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in fresh_items
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    for row in base_rows if isinstance(base_rows, list) else []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if shot_id and shot_id in fresh_map:
            continue
        merged.append(row)
    merged.extend(fresh_map.values())
    return merged


def _insert_repair_rows_by_neighbor(rows: object, repair_shot_ids: set[str]) -> list[dict]:
    source_rows = [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if not source_rows or not repair_shot_ids:
        return source_rows
    repairs = [row for row in source_rows if str(row.get("shot_id", "")).strip() in repair_shot_ids]
    canonical = [row for row in source_rows if str(row.get("shot_id", "")).strip() not in repair_shot_ids]
    for repair in repairs:
        shot_id = str(repair.get("shot_id", "")).strip()
        if not shot_id:
            continue
        insert_at = _repair_insert_index(repair, canonical)
        canonical.insert(insert_at, repair)
    return canonical


def _repair_insert_index(repair_row: dict, canonical_rows: list[dict]) -> int:
    after_shot_id = str(repair_row.get("after_shot_id", "")).strip()
    before_shot_id = str(repair_row.get("before_shot_id", "")).strip()
    if after_shot_id:
        for index, row in enumerate(canonical_rows):
            if str(row.get("shot_id", "")).strip() == after_shot_id:
                return index + 1
    if before_shot_id:
        for index, row in enumerate(canonical_rows):
            if str(row.get("shot_id", "")).strip() == before_shot_id:
                return index
    return len(canonical_rows)



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
    action_artifacts: list[str] = []
    if recommended_action in ASSEMBLY_REVIEW_ACTIONS:
        target_shots = [str(value).strip() for value in stage_payload.get("target_shots", []) if str(value).strip()] if isinstance(stage_payload.get("target_shots"), list) else []
        target_material_ids = [str(value).strip() for value in stage_payload.get("target_material_ids", []) if str(value).strip()] if isinstance(stage_payload.get("target_material_ids"), list) else []
        target_section_ids = [str(value).strip() for value in stage_payload.get("target_section_ids", []) if str(value).strip()] if isinstance(stage_payload.get("target_section_ids"), list) else []
        base_review_inputs = passthrough_payload.get("review_inputs") if isinstance(passthrough_payload.get("review_inputs"), dict) else {}
        assembly_plan = stage_payload.get("assembly_plan") if isinstance(stage_payload.get("assembly_plan"), dict) else {}
        revised_assembly_plan, revisions_by_shot = apply_assembly_revision(
            assembly_plan,
            action=recommended_action,
            target_shots=target_shots,
            target_material_ids=target_material_ids,
            target_section_ids=target_section_ids,
            coverage_extension_sec=_clone_tail_extension_sec(stage_payload.get("sync_repair_summary")),
        )
        revised_review_inputs = {
            "cadence_profile_by_shot": {shot_id: str(values.get("cadence_profile", "")).strip() for shot_id, values in revisions_by_shot.items() if str(values.get("cadence_profile", "")).strip()},
            "snap_unit_by_shot": {shot_id: str(values.get("snap_unit", "")).strip() for shot_id, values in revisions_by_shot.items() if str(values.get("snap_unit", "")).strip()},
            "trimmed_coverage_by_shot": {shot_id: float(values.get("trimmed_coverage_sec", 0.0) or 0.0) for shot_id, values in revisions_by_shot.items() if float(values.get("trimmed_coverage_sec", 0.0) or 0.0) > 0.0},
            "edit_intent_by_shot": {
                shot_id: {
                    **(base_review_inputs.get("edit_intent_by_shot", {}).get(shot_id) if isinstance(base_review_inputs.get("edit_intent_by_shot"), dict) and isinstance(base_review_inputs.get("edit_intent_by_shot", {}).get(shot_id), dict) else {}),
                    **{
                        key: str(values.get(key, "")).strip()
                        for key in ("transition_in", "transition_out")
                        if str(values.get(key, "")).strip()
                    },
                }
                for shot_id, values in revisions_by_shot.items()
            },
        }
        passthrough_payload["review_inputs"] = {
            **base_review_inputs,
            **{key: {**(base_review_inputs.get(key) if isinstance(base_review_inputs.get(key), dict) else {}), **value} for key, value in revised_review_inputs.items() if value},
            "assembly_revision": {
                "action": recommended_action,
                "target": "assembly",
                "final_video": str(stage_payload.get("final_video", "")).strip(),
                "music_file": str(stage_payload.get("music_file", "")).strip(),
                "target_shots": target_shots,
                "target_material_ids": target_material_ids,
                "target_section_ids": target_section_ids,
                "revised_review_inputs": revised_review_inputs,
            },
        }
        assembly_render = _render_revised_assembly(
            config=stage_input.config,
            run_id=stage_input.run_id,
            music_file=str(stage_payload.get("music_file", "")).strip(),
            final_video=str(stage_payload.get("final_video", "")).strip(),
            review_inputs=passthrough_payload.get("review_inputs") if isinstance(passthrough_payload.get("review_inputs"), dict) else {},
            revised_assembly_plan=revised_assembly_plan,
            revisions_by_shot=revisions_by_shot,
        )
        rendered_final_video = str(assembly_render.get("final_video", "")).strip()
        if rendered_final_video:
            passthrough_payload["final_video"] = rendered_final_video
        action_artifacts.extend(str(path).strip() for path in assembly_render.get("artifacts", []) if str(path).strip())
        passthrough_payload["assembly_revision_result"] = {
            "action": recommended_action,
            "status": "applied",
            "target": "assembly",
            "output_final_video": rendered_final_video or str(stage_payload.get("final_video", "")).strip(),
            "revision_focus": _assembly_revision_focus(recommended_action),
            "target_shots": target_shots,
            "target_material_ids": target_material_ids,
            "target_section_ids": target_section_ids,
            "revised_assembly_plan": revised_assembly_plan,
        }
        passthrough_payload["assembly_plan"] = revised_assembly_plan
    passthrough_payload["review_action"] = recommended_action or "review_failed_checks"
    return StageOutput("review_action", "done", passthrough_payload, action_artifacts)



def _assembly_revision_focus(recommended_action: str) -> str:
    if recommended_action == "revise_assembly_weights_before_clip_rerender":
        return "weights"
    if recommended_action == "revise_assembly_coverage_before_sync_pad":
        return "coverage"
    return "transitions"



def _clone_tail_extension_sec(sync_repair_summary: object) -> float:
    if not isinstance(sync_repair_summary, dict) or not sync_repair_summary.get("clone_tail_excessive"):
        return 0.0
    return _safe_positive_float(sync_repair_summary.get("clone_tail_sec")) or 0.0



def _render_revised_assembly(
    *,
    config: dict,
    run_id: str,
    music_file: str,
    final_video: str,
    review_inputs: dict,
    revised_assembly_plan: dict,
    revisions_by_shot: dict[str, dict[str, object]],
) -> dict[str, object]:
    clip_rows = review_inputs.get("clip_results") if isinstance(review_inputs.get("clip_results"), list) else []
    clip_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in clip_rows
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip() and str(row.get("video", "")).strip()
    }
    section_edits = revised_assembly_plan.get("section_edits") if isinstance(revised_assembly_plan.get("section_edits"), list) else []
    clips: list[dict[str, object]] = []
    for section in section_edits:
        if not isinstance(section, dict):
            continue
        for shot_id in section.get("selected_clip_ids", []) if isinstance(section.get("selected_clip_ids"), list) else []:
            normalized_shot_id = str(shot_id).strip()
            clip_row = clip_map.get(normalized_shot_id)
            if not clip_row:
                continue
            resolved_clip_path = Path(resolve_generated_file(config, str(clip_row.get("video", "")).strip(), {".mp4", ".mov", ".mkv", ".webm"}, "video"))
            revised = revisions_by_shot.get(normalized_shot_id) if isinstance(revisions_by_shot.get(normalized_shot_id), dict) else {}
            trimmed_coverage_sec = _safe_positive_float(revised.get("trimmed_coverage_sec"))
            clips.extend(_revised_clip_segments(normalized_shot_id, resolved_clip_path, trimmed_coverage_sec))
    if not clips:
        return {"final_video": final_video, "artifacts": []}
    resolved_audio = Path(resolve_generated_file(config, music_file, {".wav", ".mp3", ".flac", ".m4a"}, "audio"))
    resolved_final_video = Path(str(final_video).strip())
    ok = run_ffmpeg_mux(clips, resolved_audio, resolved_final_video, config)
    if not ok:
        raise RuntimeError("ffmpeg assemble failed")
    return {"final_video": str(resolved_final_video), "artifacts": [str(resolved_final_video)]}



def _revised_clip_segments(shot_id: str, clip_path: Path, trimmed_coverage_sec: float | None) -> list[dict[str, object]]:
    if trimmed_coverage_sec is None:
        return [{"shot_id": shot_id, "path": clip_path}]
    clip_duration_sec = _safe_positive_float(ffprobe_duration(clip_path))
    if clip_duration_sec is None:
        return [{"shot_id": shot_id, "path": clip_path, "trim_start_sec": 0.0, "trim_end_sec": trimmed_coverage_sec}]
    segments: list[dict[str, object]] = []
    remaining = trimmed_coverage_sec
    while remaining > 0.001:
        segment_duration = min(remaining, clip_duration_sec)
        segments.append(
            {
                "shot_id": shot_id,
                "path": clip_path,
                "trim_start_sec": 0.0,
                "trim_end_sec": round(segment_duration, 3),
            }
        )
        remaining = round(remaining - segment_duration, 6)
        if len(segments) >= 32:
            break
    return segments



def _safe_positive_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if parsed > 0.0 else None
