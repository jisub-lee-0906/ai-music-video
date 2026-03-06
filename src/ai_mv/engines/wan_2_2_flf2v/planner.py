from __future__ import annotations

from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.core.contracts.prompt_contract import normalize_wan_clips, wan_schema
from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips = [_item_to_clip(item, fps) for item in payload["uso_images"]]
    if not clips:
        raise RuntimeError("WAN clips empty")
    _enforce_clip_cap(config, clips, fps)
    spec = _plan_with_ollama(config, clips)
    prompts = normalize_wan_clips(spec["clips"], clips)
    clips = [_apply_prompt(x, prompts[x["shot_id"]]) for x in clips]
    return {"clips": clips}


def _plan_with_ollama(config: dict, clips: list[dict]) -> dict:
    batch_size = _wan_planner_batch_size(config, len(clips))
    if len(clips) <= batch_size:
        prompt = _planner_prompt(config, clips, "")
        raw = generate_structured(config, prompt, wan_schema())
        return {"clips": _coerce_clip_ids(raw.get("clips", []), clips)}
    out: list[dict] = []
    carry = ""
    for i in range(0, len(clips), batch_size):
        chunk = clips[i : i + batch_size]
        prompt = _planner_prompt(config, chunk, carry)
        raw = generate_structured(config, prompt, wan_schema())
        rows = _coerce_clip_ids(raw.get("clips", []), chunk)
        out.extend(rows)
        carry = _carry_hint(rows)
    return {"clips": out}


def _planner_prompt(config: dict, clips: list[dict], carry: str) -> str:
    guidance = _style_guidance(config)
    lyrics = _lyrics_excerpt(config)
    summary = _clip_summary(clips)
    carry_clause = f"Previous batch continuity hint={carry}. " if carry else ""
    return (
        "You are a senior first-last-frame video prompt director for WAN FLF2V. "
        "Return strict JSON only: {\"clips\":[...]}. No prose outside JSON. "
        "Each clip item must include shot_id,positive_prompt,negative_prompt,energy. "
        "Use shot_id values exactly from ClipIds list, without creating new ids. "
        "positive_prompt must be 2-3 natural English sentences describing cinematic motion between start and end frames. "
        "Sentence 1: subject and transformation or movement arc. "
        "Sentence 2: camera motion, lighting change, and emotional escalation. "
        "Optional sentence 3: environment reaction details. "
        "negative_prompt must be a comma-separated suppression list for artifacts and defects. "
        "Always include: overexposed, static frame, unclear details, subtitle, watermark, logo, low quality, jpeg artifacts, ugly, defective, extra fingers, poorly drawn hands, poorly drawn face, deformed anatomy, disfigured limbs, fused fingers, cluttered background. "
        f"{carry_clause}Style guidance={guidance}; Lyrics context={lyrics}; ClipIds={summary}."
    )


def _style_guidance(config: dict) -> str:
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


def _lyrics_excerpt(config: dict) -> str:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    text = str(audio.get("lyrics", "")).strip() if isinstance(audio, dict) else ""
    if not text:
        return ""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return " | ".join(lines[:8])


def _coerce_clip_ids(rows: list[dict], clips: list[dict]) -> list[dict]:
    pool = [x for x in rows if isinstance(x, dict)]
    keyed = {str(x.get("shot_id", "")): x for x in pool if str(x.get("shot_id", "")).strip()}
    out: list[dict] = []
    idx = 0
    for clip in clips:
        sid = str(clip["shot_id"])
        row = keyed.get(sid)
        if row is None:
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
    rows: list[str] = []
    for c in clips:
        sid = str(c["shot_id"])
        frames = int(c["frames"])
        fps = int(c["fps"])
        sec = str(c.get("section_name", "section"))
        rows.append(f"{sid}:{sec}:{frames}f@{fps}")
    return ", ".join(rows)


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
        return "high"
    if sec in {"bridge", "outro"}:
        return "low"
    if suggested in {"low", "normal", "high"}:
        return suggested
    return "normal"


def _section_token(clip: dict) -> str:
    return str(clip.get("section_name", "")).strip().lower()
