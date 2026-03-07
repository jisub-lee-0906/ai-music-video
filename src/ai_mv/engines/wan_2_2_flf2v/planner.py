from __future__ import annotations

from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.core.contracts.prompt_contract import normalize_wan_clips, wan_schema
from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.bool_utils import parse_bool
from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips = [_item_to_clip(item, fps) for item in payload["uso_images"]]
    if not clips:
        raise RuntimeError("WAN clips empty")
    _enforce_clip_cap(config, clips, fps)
    spec = _plan_with_ollama(config, payload, clips)
    prompts = normalize_wan_clips(spec["clips"], clips)
    clips = [_apply_prompt(x, prompts[x["shot_id"]]) for x in clips]
    return {"clips": clips}


def _plan_with_ollama(config: dict, payload: dict, clips: list[dict]) -> dict:
    batch_size = _wan_planner_batch_size(config, len(clips))
    strict = _strict_id_match(config)
    if len(clips) <= batch_size:
        return {"clips": _plan_chunk_rows(config, payload, clips, "", strict)}
    out: list[dict] = []
    carry = ""
    for i in range(0, len(clips), batch_size):
        chunk = clips[i : i + batch_size]
        rows = _plan_chunk_rows(config, payload, chunk, carry, strict)
        out.extend(rows)
        carry = _carry_hint(rows)
    return {"clips": out}


def _plan_chunk_rows(config: dict, payload: dict, chunk: list[dict], carry: str, strict: bool) -> list[dict]:
    prompt = _planner_prompt(config, payload, chunk, carry)
    raw = generate_structured(config, prompt, wan_schema())
    return _coerce_clip_ids(raw.get("clips", []), chunk, strict)


def _planner_prompt(config: dict, payload: dict, clips: list[dict], carry: str) -> str:
    guidance = _style_guidance(config, payload)
    lyrics = _lyrics_excerpt(payload)
    brief = _brief_summary(payload["visual_brief"])
    summary = _clip_summary(clips)
    carry_clause = f"Previous batch continuity hint={carry}. " if carry else ""
    return (
        "You are a senior first-last-frame video prompt director for WAN FLF2V. "
        "Return strict JSON only: {\"clips\":[...]}. No prose outside JSON. "
        "Each clip item must include shot_id,positive_prompt,negative_prompt,energy. "
        "Use shot_id values exactly from ClipIds list, without creating new ids. "
        "shot_id must be exactly one token from ClipIds with no suffix, prefix, or punctuation changes. "
        "positive_prompt must be 2-3 natural English sentences describing cinematic motion between start and end frames. "
        "Sentence 1: starting state and first movement impulse. "
        "Sentence 2: transition motion arc and camera behavior with concrete dynamic verbs. "
        "Optional sentence 3: environment reaction details. "
        "Use concrete dynamic verbs and visual detail. Avoid vague wording. "
        "Use the visual brief and section rules to preserve hero identity, palette, lighting, and atmosphere during motion. "
        "Prefer one clear motion arc, stable readable subject framing, and deliberate pacing. "
        "Avoid frantic camera swings, hyperactive subject motion, over-cranked action, or too many simultaneous movements. "
        "If the section is emotional or performance-focused, prefer elegant motion and micro-movements over spectacle. "
        "Do not describe multiple competing action arcs in one clip. "
        "negative_prompt must be a comma-separated suppression list for artifacts and defects. "
        "Always include: overexposed, static frame, unclear details, subtitle, watermark, logo, low quality, jpeg artifacts, ugly, defective, extra fingers, poorly drawn hands, poorly drawn face, deformed anatomy, disfigured limbs, fused fingers, cluttered background. "
        "Set energy as low, normal, or high based on motion intensity and pacing. "
        f"{carry_clause}Style guidance={guidance}; Visual brief={brief}; Lyrics context={lyrics}; ClipIds={summary}."
    )


def _style_guidance(config: dict, payload: dict) -> str:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    guided = str(audio_map.get("style_guidance", "")).strip() if isinstance(audio_map, dict) else ""
    if guided:
        return guided
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


def _lyrics_excerpt(payload: dict) -> str:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    text = str(audio_map.get("lyrics", "")).strip() if isinstance(audio_map, dict) else ""
    if not text:
        return ""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return " | ".join(lines[:8])


def _brief_summary(brief: dict) -> str:
    motifs = ", ".join(brief.get("visual_motifs", []))
    rules = ", ".join(brief.get("negative_constraints", []))
    return (
        f"hero={brief['hero_identity']}; world={brief['world_rules']}; "
        f"motifs={motifs}; avoid={rules}; sections={_section_briefs(brief)}"
    )


def _section_briefs(brief: dict) -> str:
    rows = []
    for row in brief.get("section_briefs", []):
        rows.append(
            f"{row['section_name']}|{row['emotional_arc']}|{row['palette_hint']}|"
            f"{row['lighting_hint']}|{row['staging_hint']}"
        )
    return ", ".join(rows)


def _coerce_clip_ids(rows: list[dict], clips: list[dict], strict: bool) -> list[dict]:
    pool = [x for x in rows if isinstance(x, dict)]
    keyed = {str(x.get("shot_id", "")): x for x in pool if str(x.get("shot_id", "")).strip()}
    out: list[dict] = []
    idx = 0
    for clip in clips:
        sid = str(clip["shot_id"])
        row = keyed.get(sid)
        if row is None:
            if strict:
                raise RuntimeError(f"WAN planner shot_id mismatch: missing {sid}")
            row = _next_row(pool, idx)
            idx += 1
        out.append(_with_shot_id(row, sid))
    return out


def _next_row(pool: list[dict], idx: int) -> dict:
    if idx >= len(pool):
        raise RuntimeError("WAN planner returned fewer clips than required")
    return pool[idx]


def _with_shot_id(row: dict, shot_id: str) -> dict:
    out = dict(row)
    out["shot_id"] = shot_id
    return out


def _clip_summary(clips: list[dict]) -> str:
    return ", ".join(_clip_summary_row(c) for c in clips)


def _clip_summary_row(clip: dict) -> str:
    sid = str(clip["shot_id"])
    section = str(clip.get("section_name", "section"))
    camera = str(clip.get("camera_language", "")).strip() or "clean framing"
    emotion = str(clip.get("emotion", "")).strip() or "steady emotion"
    detail = str(clip.get("scene_detail", "")).strip() or "hero detail"
    motion = str(clip.get("motion_hint", "")).strip() or "smooth motion"
    return f"{sid}({section}|{camera}|{emotion}|{detail}|{motion})"


def _item_to_clip(item: dict, fps: int) -> dict:
    frames = max(_frame_floor(fps), int(round(float(item["duration_sec"]) * fps)))
    return {
        "shot_id": str(item["shot_id"]),
        "start": item["start"],
        "end": item["end"],
        "fps": fps,
        "frames": int(frames),
        "section_name": str(item.get("section_name", "section")),
        "shot_type": str(item.get("shot_type", "CHAR_MASTER")),
        "is_chorus": bool(item.get("is_chorus", False)),
        "camera_language": str(item.get("camera_language", "")),
        "pose_delta": str(item.get("pose_delta", "")),
        "emotion": str(item.get("emotion", "")),
        "scene_detail": str(item.get("scene_detail", "")),
        "motion_hint": str(item.get("motion_hint", "")),
    }


def _enforce_clip_cap(config: dict, clips: list[dict], fps: int) -> None:
    sec = read_max_clip_sec(config)
    max_frames = max(_frame_floor(fps), int(round(sec * fps)))
    for clip in clips:
        frames = int(clip["frames"])
        if frames > max_frames:
            raise RuntimeError(f"WAN clip exceeds cap: {clip['shot_id']} frames={frames} cap={max_frames}")


def _wan_planner_batch_size(config: dict, count: int) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("wan_planner_batch_size", 20) if isinstance(render, dict) else 20
    try:
        n = int(raw)
    except Exception:
        n = 20
    return max(1, min(max(1, count), n))


def _strict_id_match(config: dict) -> bool:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("strict_prompt_id_match", True) if isinstance(render, dict) else True
    return parse_bool(raw, default=True)


def _carry_hint(rows: list[dict]) -> str:
    if not rows:
        return ""
    text = str(rows[-1].get("positive_prompt", "")).strip()
    return text[:220]


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _apply_prompt(clip: dict, row: dict) -> dict:
    out = dict(clip)
    out["positive_prompt"] = str(row["positive_prompt"])
    out["negative_prompt"] = str(row["negative_prompt"])
    out["energy"] = _energy_policy(clip, str(row["energy"]))
    return out


def _energy_policy(clip: dict, suggested: str) -> str:
    sec = _section_token(clip)
    if sec == "chorus" or sec.startswith("chorus_"):
        if suggested == "high":
            return "high"
        return "normal"
    if sec in {"bridge", "outro"}:
        return "low" if suggested == "low" else "normal"
    if suggested in {"low", "normal", "high"}:
        return suggested
    return "normal"


def _section_token(clip: dict) -> str:
    return str(clip.get("section_name", "")).strip().lower()
