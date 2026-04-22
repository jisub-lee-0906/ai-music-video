from __future__ import annotations
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import ltx_clip_prefix
from ai_mv.engines.ltx_ia2v.runner import run_ltx_ia2v


def run_render_clips(stage_input: StageInput) -> StageOutput:
    shot_plan = [row for row in stage_input.payload.get("shot_plan", []) if isinstance(row, dict)]
    render_plan = [row for row in stage_input.payload.get("render_plan", []) if isinstance(row, dict)]
    still_results = [row for row in stage_input.payload.get("still_results", []) if isinstance(row, dict)]
    render_map = {str(row.get("shot_id", "")).strip(): row for row in render_plan}
    still_map = {str(row.get("shot_id", "")).strip(): row for row in still_results}
    clip_results = []
    for shot in shot_plan:
        shot_id = str(shot.get("shot_id", "")).strip()
        render_item = render_map.get(shot_id, {})
        render_mode = str(render_item.get("render_mode") or shot.get("render_mode", "")).strip()
        if not render_mode:
            raise RuntimeError(f"missing render_mode for shot: {shot_id}")
        video_path = _run_clip(stage_input, shot_id, shot, render_item, still_map, render_mode)
        clip_results.append(
            {
                "shot_id": shot_id,
                "video": video_path,
                "render_mode": render_mode,
                "material_id": _clip_material_id(shot, render_item, still_map.get(shot_id, {})),
                "section_id": _clip_section_id(shot, render_item, still_map.get(shot_id, {})),
                "status": "done",
            }
        )
    return StageOutput(
        "render_clips",
        "done",
        {
            "clip_results": clip_results,
            "workflow_inputs": {
                **dict(stage_input.payload.get("workflow_inputs", {})),
                "clips": {"count": len(clip_results)},
            },
        },
        [],
    )


def _run_clip(stage_input: StageInput, shot_id: str, shot: dict, render_item: dict, still_map: dict, render_mode: str) -> str:
    if render_mode != "ia2v":
        raise RuntimeError(f"unsupported render_mode for shot {shot_id}: {render_mode}")
    prompt_seed = _clip_prompt_text(render_item)
    positive_prompt = str(render_item.get("clip_positive_prompt") or render_item.get("prompt_polish") or render_item.get("prompt_draft") or "").strip()
    negative_prompt = str(stage_input.config.get("render", {}).get("ltx_negative", "")).strip()
    duration_sec = float(shot.get("duration_sec", stage_input.config.get("render", {}).get("ltx_default_shot_sec", 4.0)) or 4.0)
    base_item = {
        "shot_id": shot_id,
        "prompt_seed": prompt_seed,
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "duration_sec": duration_sec,
        "fps": int(stage_input.config.get("render", {}).get("ltx_fps", 24) or 24),
        "filename_prefix": ltx_clip_prefix(stage_input.run_id, shot_id, render_mode),
    }
    still_image = str(still_map.get(shot_id, {}).get("image", "")).strip()
    _validate_clip_assets(stage_input, shot_id, render_mode, still_image, shot, render_item, still_map)
    return run_ltx_ia2v(
        stage_input.config,
        {
            **base_item,
            "image": still_image,
            "audio": str(stage_input.payload.get("music_file", "")).strip(),
            "audio_start_sec": float(shot.get("start_sec", 0.0) or 0.0),
        },
    )


def _clip_prompt_text(render_item: dict) -> str:
    for key in ("clip_prompt_seed", "prompt_seed", "clip_positive_prompt", "prompt_polish", "prompt_draft"):
        value = str(render_item.get(key, "")).strip()
        if value:
            return value
    return "music video shot with a clear cinematic action beat"


def _bridge_target_image(shot_id: str, shot: dict, render_item: dict, still_map: dict) -> str:
    bridge_to_shot_id = str(render_item.get("still_b") or shot.get("bridge_to_shot_id", "")).strip()
    target = str(still_map.get(bridge_to_shot_id, {}).get("image", "")).strip()
    if target:
        return target
    raise RuntimeError(f"missing bridge target still for shot: {shot_id}")


def _clip_material_id(shot: dict, render_item: dict, still_row: dict) -> str:
    return str(
        still_row.get("material_id")
        or render_item.get("material_id")
        or shot.get("material_id")
        or ""
    ).strip()


def _clip_section_id(shot: dict, render_item: dict, still_row: dict) -> str:
    return str(
        still_row.get("section_id")
        or render_item.get("section_id")
        or shot.get("section_id")
        or ""
    ).strip()


def _validate_clip_assets(stage_input: StageInput, shot_id: str, render_mode: str, still_image: str, shot: dict, render_item: dict, still_map: dict) -> None:
    if render_mode == "ia2v" and not still_image:
        raise RuntimeError(f"missing source still for shot: {shot_id}")
    if render_mode == "ia2v" and not str(stage_input.payload.get("music_file", "")).strip():
        raise RuntimeError(f"missing music file for ia2v shot: {shot_id}")
