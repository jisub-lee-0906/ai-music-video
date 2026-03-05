from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_wan_clips, wan_schema
from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips: list[dict] = []
    for item in payload["uso_images"]:
        clips.extend(_item_to_clips(item, fps))
    if not clips:
        raise RuntimeError("WAN clips empty")
    spec = _plan_with_ollama(config, clips)
    prompts = normalize_wan_clips(spec["clips"], clips)
    clips = [_apply_prompt(x, prompts[x["shot_id"]]) for x in clips]
    return {"clips": clips}


def _plan_with_ollama(config: dict, clips: list[dict]) -> dict:
    prompt = _planner_prompt(config, clips)
    raw = generate_structured(config, prompt, wan_schema())
    rows = _coerce_clip_ids(raw.get("clips", []), clips)
    return {"clips": rows}


def _planner_prompt(config: dict, clips: list[dict]) -> str:
    guidance = _style_guidance(config)
    lyrics = _lyrics_excerpt(config)
    summary = _clip_summary(clips)
    return (
        "You are a senior first-last-frame video prompt director for WAN FLF2V. "
        "Return strict JSON only: {\"clips\":[...]}. No prose outside JSON. "
        "Each clip item must include shot_id,positive_prompt,negative_prompt,energy. "
        "Use shot_id values exactly from ClipIds list, without creating new ids. "
        "positive_prompt must be 2-3 natural English sentences describing cinematic motion between start and end frames. "
        "Sentence 1: subject and transformation or movement arc. "
        "Sentence 2: camera motion, lighting change, and emotional escalation. "
        "Optional sentence 3: environment reaction details. "
        "Use concrete dynamic verbs and visual detail. Avoid vague wording. "
        "negative_prompt must be a comma-separated suppression list for artifacts and defects. "
        "Always include: overexposed, static frame, unclear details, subtitle, watermark, logo, low quality, jpeg artifacts, ugly, defective, extra fingers, poorly drawn hands, poorly drawn face, deformed anatomy, disfigured limbs, fused fingers, cluttered background. "
        "Set energy as low, normal, or high based on motion intensity and pacing. "
        f"Style guidance={guidance}; Lyrics context={lyrics}; ClipIds={summary}."
    )


def _style_guidance(config: dict) -> str:
    style = config.get("style", {}) if isinstance(config, dict) else {}
    if not isinstance(style, dict):
        return ""
    return str(style.get("guidance", "")).strip()


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
        rows.append(f"{sid}:{frames}f@{fps}")
    return ", ".join(rows)


def _item_to_clips(item: dict, fps: int) -> list[dict]:
    duration = float(item["duration_sec"])
    total = max(24, int(round(duration * fps)))
    return [_clip(item["shot_id"], item["start"], item["end"], fps, total)]


def _clip(shot_id: str, start: str, end: str, fps: int, frames: int) -> dict:
    return {"shot_id": shot_id, "start": start, "end": end, "fps": fps, "frames": frames}


def _apply_prompt(clip: dict, row: dict) -> dict:
    out = dict(clip)
    out["positive_prompt"] = str(row["positive_prompt"])
    out["negative_prompt"] = str(row["negative_prompt"])
    out["energy"] = str(row["energy"])
    return out
