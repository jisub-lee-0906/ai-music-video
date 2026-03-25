from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_wan_clips
from ai_mv.core.contracts.prompt_schema import wan_schema
from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.engines.wan_2_2_flf2v.prompting import _chain_break, _clip_ids, _clip_summary, _planner_prompt, _ref_chain_key, _wan_planner_batch_size
from ai_mv.infra.codex_cli_client import generate_structured
from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips = [_route_to_clip(item, payload.get("flux2_ref_images", []), fps) for item in payload["clip_routes"]]
    clips = _chain_clip_starts(clips)
    if not clips:
        raise RuntimeError("WAN clips empty")
    _enforce_clip_cap(config, clips, fps)
    spec = _generate_wan_spec(config, payload, clips)
    keyed = normalize_wan_clips(spec.get("clips", []), clips)
    rendered = [_apply_llm_prompt(clip, keyed[str(clip["shot_id"])]) for clip in clips]
    return {"clips": rendered}


def _generate_wan_spec(config: dict, payload: dict, clips: list[dict], attempts: int = 3) -> dict:
    prompt = _planner_prompt(config, payload, clips, "")
    expected_ids = [str(clip["shot_id"]) for clip in clips]
    current_prompt = prompt
    last_exc: Exception | None = None
    for attempt in range(1, max(1, int(attempts)) + 1):
        spec = generate_structured(config, current_prompt, wan_schema(), attempts=1)
        try:
            keyed = normalize_wan_clips(spec.get("clips", []), clips)
            for shot_id in expected_ids:
                row = keyed[shot_id]
                if row["positive_prompt"] != _compose_positive_prompt(
                    {
                        "camera_relation": row["camera_relation"],
                        "subject_motion": row["subject_motion"],
                        "environment_detail": row["environment_detail"],
                    }
                ):
                    raise RuntimeError(f"positive_prompt formula mismatch: {shot_id}")
            return spec
        except RuntimeError as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            actual_ids = [
                str(row.get("shot_id", "")).strip()
                for row in spec.get("clips", [])
                if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
            ]
            current_prompt = (
                f"{prompt}\n\n"
                "Previous output failed validation. "
                f"Failure={exc}. "
                f"Expected shot_id order={', '.join(expected_ids)}. "
                f"Previous shot_id order={', '.join(actual_ids)}. "
                "Rewrite the JSON only and follow the exact positive prompt formula."
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("wan planner failed without validation error")


def _route_to_clip(item: dict, ref_images: list[dict], fps: int) -> dict:
    ref_map = {_ref_chain_key(row): row for row in ref_images if isinstance(row, dict)}
    use_ref = bool(item.get("use_ref", False))
    ref_row = ref_map.get(_ref_chain_key(item))
    start = str(item["anchor"])
    end = str(item["anchor"])
    if use_ref:
        if ref_row is None:
            raise RuntimeError(f"WAN missing ref-assisted clip: {item['shot_id']}")
        start = str(ref_row["start"])
        end = str(ref_row["end"])
    frames = max(_frame_floor(fps), int(round(float(item["duration_sec"]) * fps)))
    return {
        "shot_id": str(item["shot_id"]),
        "start": start,
        "end": end,
        "fps": fps,
        "frames": int(frames),
        "section_name": str(item.get("section_name", "section")),
        "section_label": str(item.get("section_label", item.get("section_name", "section"))),
        "shot_type": str(item.get("shot_type", "CHAR_MASTER")),
        "is_chorus": bool(item.get("is_chorus", False)),
        "camera_language": str(item.get("camera_language", "")),
        "pose_delta": str(item.get("pose_delta", "")),
        "emotion": str(item.get("emotion", "")),
        "scene_detail": str(item.get("scene_detail", "")),
        "motion_hint": str(item.get("motion_hint", "")),
        "workflow_motion_clause": str(item.get("workflow_motion_clause", "")),
        "space_relation": str(item.get("space_relation", "")),
        "start_frame": dict(item.get("start_frame", {})),
        "end_frame": dict(item.get("end_frame", {})),
        "kinetic_transition": str(item.get("kinetic_transition", "")),
        "lighting_fx": str(item.get("lighting_fx", "")),
        "kinetic_intensity": str(item.get("kinetic_intensity", "")),
        "location_family": str(item.get("location_family", "")),
        "symbolic_image": str(item.get("symbolic_image", "")),
        "motif_object": str(item.get("motif_object", "")),
        "edit_device": str(item.get("edit_device", "")),
        "prompt_focus": str(item.get("prompt_focus", "")),
        "space_event": str(item.get("space_event", "")),
        "composition_shape": str(item.get("composition_shape", "")),
        "palette_mode": str(item.get("palette_mode", "")),
        "character_render_mode": str(item.get("character_render_mode", "")),
        "face_exposure_level": str(item.get("face_exposure_level", "")),
        "heroine_visibility": str(item.get("heroine_visibility", "")),
        "continuity_priority": str(item.get("continuity_priority", "")),
        "wardrobe_read": str(item.get("wardrobe_read", "")),
        "continuity_lock": str(item.get("continuity_lock", "")),
        "route_reason": str(item.get("route_reason", "")),
        "scene_change_level": str(item.get("scene_change_level", "")),
        "anchor_strategy": str(item.get("anchor_strategy", "")),
        "use_ref": use_ref,
        "clip_index": int(item.get("clip_index", 1)),
        "clip_count": int(item.get("clip_count", 1)),
        "timeline_index": int(item.get("timeline_index", 0)),
        "chain_key": _ref_chain_key(item),
    }


def _chain_clip_starts(clips: list[dict]) -> list[dict]:
    out: list[dict] = []
    prev_end_path = ""
    prev_clip: dict | None = None
    for clip in clips:
        item = dict(clip)
        if prev_end_path and not _chain_break(item, prev_clip):
            item["start"] = prev_end_path
            item["start_source"] = "previous_end"
            item["prev_chain_key"] = str(prev_clip.get("chain_key", "")) if isinstance(prev_clip, dict) else ""
        else:
            item["start_source"] = "ref_start"
            item["prev_chain_key"] = ""
        prev_end_path = str(item["end"])
        prev_clip = item
        out.append(item)
    return out


def _enforce_clip_cap(config: dict, clips: list[dict], fps: int) -> None:
    sec = read_max_clip_sec(config)
    max_frames = max(_frame_floor(fps), int(round(sec * fps)))
    for clip in clips:
        frames = int(clip["frames"])
        if frames > max_frames:
            raise RuntimeError(f"WAN clip exceeds cap: {clip['shot_id']} frames={frames} cap={max_frames}")


def _apply_llm_prompt(clip: dict, row: dict) -> dict:
    out = dict(clip)
    out["subject_motion"] = str(row["subject_motion"])
    out["camera_relation"] = str(row["camera_relation"])
    out["environment_detail"] = str(row["environment_detail"])
    out["positive_prompt"] = str(row["positive_prompt"])
    out["negative_prompt"] = str(row["negative_prompt"])
    out["energy"] = str(row["energy"])
    return out


def _compose_positive_prompt(row: dict) -> str:
    parts = [
        _sentence(str(row.get("camera_relation", "")).strip()),
        _sentence(str(row.get("subject_motion", "")).strip()),
        _sentence(str(row.get("environment_detail", "")).strip()),
    ]
    text = " ".join(part for part in parts if part).strip()
    if not text:
        raise RuntimeError("empty composed WAN prompt")
    return text


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    if not cleaned:
        return ""
    return f"{cleaned[:1].upper() + cleaned[1:]}."


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))
