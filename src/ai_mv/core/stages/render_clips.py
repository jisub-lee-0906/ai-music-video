from __future__ import annotations
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import ltx_clip_prefix
from ai_mv.core.stages.still_qa_gate import assert_still_passes_ia2v_gate
from ai_mv.engines.ltx_ia2v.runner import run_ltx_ia2v


def run_render_clips(stage_input: StageInput) -> StageOutput:
    shot_plan = [row for row in stage_input.payload.get("shot_plan", []) if isinstance(row, dict)]
    render_plan = [row for row in stage_input.payload.get("render_plan", []) if isinstance(row, dict)]
    still_results = [row for row in stage_input.payload.get("still_results", []) if isinstance(row, dict)]
    render_map = {str(row.get("shot_id", "")).strip(): row for row in render_plan}
    still_map = {str(row.get("shot_id", "")).strip(): row for row in still_results}
    duration_targets = _duration_targets_by_shot(shot_plan, stage_input.payload, stage_input.config)
    clip_results = []
    for shot in shot_plan:
        shot_id = str(shot.get("shot_id", "")).strip()
        render_item = render_map.get(shot_id, {})
        render_mode = str(render_item.get("render_mode") or shot.get("render_mode", "")).strip()
        if not render_mode:
            raise RuntimeError(f"missing render_mode for shot: {shot_id}")
        video_path, duration_contract = _run_clip(stage_input, shot_id, shot, render_item, still_map, render_mode, duration_targets.get(shot_id))
        clip_results.append(
            {
                "shot_id": shot_id,
                "video": video_path,
                "render_mode": render_mode,
                "material_id": _clip_material_id(shot, render_item, still_map.get(shot_id, {})),
                "section_id": _clip_section_id(shot, render_item, still_map.get(shot_id, {})),
                "status": "done",
                **duration_contract,
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


def _run_clip(
    stage_input: StageInput,
    shot_id: str,
    shot: dict,
    render_item: dict,
    still_map: dict,
    render_mode: str,
    duration_target_sec: float | None = None,
) -> tuple[str, dict[str, float | str]]:
    if render_mode != "ia2v":
        raise RuntimeError(f"unsupported render_mode for shot {shot_id}: {render_mode}")
    prompt_seed = _clip_prompt_text(render_item)
    still_row = still_map.get(shot_id, {})
    positive_prompt = _apply_still_identity_to_clip_prompt(
        str(render_item.get("clip_positive_prompt") or render_item.get("positive_prompt") or prompt_seed).strip(),
        still_row,
    )
    negative_prompt = str(stage_input.config.get("render", {}).get("ltx_negative", "")).strip()
    target_duration_sec = float(duration_target_sec or shot.get("duration_sec", stage_input.config.get("render", {}).get("ltx_default_shot_sec", 4.0)) or 4.0)
    duration_contract = _clip_duration_contract(target_duration_sec, render_item, stage_input.config)
    base_item = {
        "shot_id": shot_id,
        "prompt_seed": prompt_seed,
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "duration_sec": duration_contract["rendered_duration_sec"],
        "fps": int(stage_input.config.get("render", {}).get("ltx_fps", 24) or 24),
        "filename_prefix": ltx_clip_prefix(stage_input.run_id, shot_id, render_mode),
    }
    still_image = str(still_row.get("image", "")).strip()
    _validate_clip_assets(stage_input, shot_id, render_mode, still_image, shot, render_item, still_map)
    assert_still_passes_ia2v_gate(shot_id=shot_id, still_row=still_row, shot=shot, render_item=render_item)
    video_path = run_ltx_ia2v(
        stage_input.config,
        {
            **base_item,
            "image": still_image,
            "audio": str(stage_input.payload.get("music_file", "")).strip(),
            "audio_start_sec": float(shot.get("start_sec", 0.0) or 0.0),
        },
    )
    return video_path, duration_contract


def _clip_prompt_text(render_item: dict) -> str:
    for key in ("clip_prompt_seed", "prompt_seed", "clip_positive_prompt", "positive_prompt"):
        value = str(render_item.get(key, "")).strip()
        if value:
            return value
    return "music video shot with a clear cinematic action beat"


def _clip_duration_contract(target_duration_sec: float, render_item: dict, config: dict) -> dict[str, float | str]:
    target = round(max(0.0, float(target_duration_sec or 0.0)), 3)
    render_cfg = config.get("render", {}) if isinstance(config.get("render"), dict) else {}
    explicit_handle = render_item.get("ia2v_handle_sec") if isinstance(render_item, dict) else None
    handle = _safe_positive_float(explicit_handle)
    if handle is None:
        handle = _safe_positive_float(render_cfg.get("ia2v_handle_sec")) or 0.0
    handle = round(max(0.0, float(handle or 0.0)), 3)
    rendered = round(target + (handle * 2.0), 3) if handle > 0.0 else target
    return {
        "target_clip_sec": target,
        "rendered_duration_sec": rendered,
        "trim_handle_sec": handle,
        "trim_strategy": "stable_middle_handle_trim" if handle > 0.0 else "use_full_clip",
    }



def _duration_targets_by_shot(shot_plan: list[dict], payload: dict, config: dict) -> dict[str, float]:
    base_durations: dict[str, float] = {}
    for shot in shot_plan:
        shot_id = str(shot.get("shot_id", "")).strip()
        if not shot_id:
            continue
        base_durations[shot_id] = _safe_positive_float(
            shot.get("duration_sec", config.get("render", {}).get("ltx_default_shot_sec", 4.0))
        ) or 4.0
    total_planned = sum(base_durations.values())
    audio_duration = _audio_duration_sec(payload.get("audio_map"))
    if total_planned <= 0.0 or audio_duration <= total_planned + 0.05:
        return base_durations
    scale = audio_duration / total_planned
    return {shot_id: round(duration * scale, 3) for shot_id, duration in base_durations.items()}



def _audio_duration_sec(audio_map: object) -> float:
    if not isinstance(audio_map, dict):
        return 0.0
    duration = _safe_positive_float(audio_map.get("duration_sec"))
    if duration is not None:
        return duration
    sections = audio_map.get("sections") if isinstance(audio_map.get("sections"), list) else []
    max_end = 0.0
    for section in sections:
        if not isinstance(section, dict):
            continue
        end_sec = _safe_positive_float(section.get("end_sec"))
        if end_sec is not None:
            max_end = max(max_end, end_sec)
    return max_end



def _apply_still_identity_to_clip_prompt(prompt: str, still_row: dict) -> str:
    markers = _still_identity_markers(still_row)
    if not markers:
        return prompt
    existing = str(prompt).strip()
    lower_existing = existing.lower()
    tokens = [existing] if existing else []
    for marker in markers:
        if marker.lower() not in lower_existing:
            tokens.append(marker)
    return ", ".join(token for token in tokens if token)



def _still_identity_markers(still_row: dict) -> list[str]:
    text = " ".join(
        str(still_row.get(key, "")).strip()
        for key in ("prompt_text", "prompt_seed")
        if str(still_row.get(key, "")).strip()
    ).lower()
    if not text:
        return []
    markers = [
        "preserve the exact same source still identity",
        "no identity drift during motion",
    ]
    if "woman" in text or "she" in text:
        markers.append("same young woman")
        markers.append("no unrelated male singer")
    if "short black bob" in text or ("black bob" in text and "bang" in text):
        markers.append("short black bob with bangs")
    if "bright red" in text and "raincoat" in text:
        markers.append("bright red raincoat remains visible")
        markers.append("preserve visible bright red raincoat as the outerwear continuity marker")
    return markers



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



def _safe_positive_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if parsed > 0.0 else None
