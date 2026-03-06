from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_uso_items, uso_schema
from ai_mv.engines.common.clip_timing import expand_anchor_clips, read_max_clip_sec
from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.text_utils import parse_target


def build_uso_plan(config: dict, payload: dict) -> dict:
    anchors = payload["anchors"]
    if not anchors:
        raise RuntimeError("anchors missing for USO")
    clip_anchors = _expand_clip_anchors(config, anchors)
    style_guidance = str(config["style"]["guidance"]).strip()
    spec = _plan_with_ollama(config, clip_anchors)
    rules = normalize_uso_items(spec["items"], clip_anchors)
    items = [_build_item(a, style_guidance, rules[a["shot_id"]]) for a in clip_anchors]
    return {"items": items}


def _expand_clip_anchors(config: dict, anchors: list[dict]) -> list[dict]:
    fps = parse_target(config.get("video", {}).get("target", "1920x1080@24"))[2]
    max_clip_sec = read_max_clip_sec(config)
    return expand_anchor_clips(anchors, fps, max_clip_sec)


def _plan_with_ollama(config: dict, anchors: list[dict]) -> dict:
    batch_size = min(len(anchors), _uso_planner_batch_size(config))
    items = _plan_with_batches(config, anchors, batch_size)
    return {"items": items}


def _plan_with_batches(config: dict, anchors: list[dict], batch_size: int) -> list[dict]:
    if batch_size <= 0:
        raise RuntimeError("uso planner batch_size must be positive")
    out: list[dict] = []
    carry = ""
    for i in range(0, len(anchors), batch_size):
        chunk = anchors[i : i + batch_size]
        prompt = _planner_prompt(config, chunk, carry)
        raw = generate_structured(config, prompt, uso_schema())
        rows = _coerce_item_ids(raw.get("items", []), chunk)
        out.extend(rows)
        carry = _batch_tail(rows)
    return out


def _planner_prompt(config: dict, anchors: list[dict], carry: str) -> str:
    guidance = str(config["style"]["guidance"]).strip()
    lyrics = _lyrics_excerpt(config)
    summary = _anchor_summary(anchors)
    carry_clause = f"Previous batch continuity hint={carry}. " if carry else ""
    return (
        "You are a senior image-to-image keyframe director for music videos. "
        "Return strict JSON only: {\"items\":[...]}. No prose outside JSON. "
        "Each item must include shot_id,delta,prompt_text,negative_prompt. "
        "Use shot_id values exactly from Anchors list, without creating new ids. "
        "prompt_text must be exactly one natural English sentence (18-34 words). "
        "Keep the same character identity, face, hair, and outfit as the anchor image. "
        "delta describes a small progression from start to end frame, not a scene reset. "
        "Do not change time period, world setting, or character species. "
        "Use concrete visual language: pose shift, gaze shift, hand motion, cloth motion, light direction, camera feel. "
        "negative_prompt must suppress defects: low quality, blurry, jpeg artifacts, extra fingers, bad hands, bad face, deformed anatomy, text watermark, logo, subtitle. "
        f"{carry_clause}Style guidance={guidance}; Lyrics context={lyrics}; Anchors={summary}."
    )


def _lyrics_excerpt(config: dict) -> str:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    text = str(audio.get("lyrics", "")).strip() if isinstance(audio, dict) else ""
    if not text:
        return ""
    lines = [x.strip()[:120] for x in text.splitlines() if x.strip()]
    return " | ".join(lines[:8])


def _uso_planner_batch_size(config: dict) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict):
        return 4
    raw = render.get("uso_planner_batch_size", 4)
    try:
        n = int(raw)
    except Exception:
        return 4
    return max(1, min(20, n))


def _batch_tail(rows: list[dict]) -> str:
    if not rows:
        return ""
    last = rows[-1]
    text = str(last.get("prompt_text", "")).strip()
    return text[:220]


def _coerce_item_ids(items: list[dict], anchors: list[dict]) -> list[dict]:
    pool = [x for x in items if isinstance(x, dict)]
    keyed = {str(x.get("shot_id", "")): x for x in pool if str(x.get("shot_id", "")).strip()}
    out: list[dict] = []
    idx = 0
    for a in anchors:
        sid = str(a["shot_id"])
        row = keyed.get(sid)
        if row is None:
            row = _next_item(pool, idx)
            idx += 1
        out.append(_with_shot_id(row, sid))
    return out


def _next_item(pool: list[dict], idx: int) -> dict:
    if idx >= len(pool):
        raise RuntimeError("USO planner returned fewer items than anchors")
    return pool[idx]


def _with_shot_id(row: dict, shot_id: str) -> dict:
    out = dict(row)
    out["shot_id"] = shot_id
    return out


def _anchor_summary(anchors: list[dict]) -> str:
    rows: list[str] = []
    for a in anchors:
        sid = str(a["shot_id"])
        stype = str(a["shot_type"])
        dur = round(float(a["duration_sec"]), 2)
        rows.append(f"{sid}:{stype}:{dur}s")
    return ", ".join(rows)


def _build_item(anchor: dict, style_guidance: str, rule: dict) -> dict:
    return {
        "shot_id": anchor["shot_id"],
        "anchor": anchor["anchor"],
        "ref": anchor["anchor"],
        "style_ref": "",
        "delta": str(rule["delta"]),
        "prompt_text": str(rule["prompt_text"]),
        "negative_prompt": str(rule["negative_prompt"]),
        "style_guidance": style_guidance,
        "duration_sec": float(anchor["duration_sec"]),
        "shot_type": str(anchor["shot_type"]),
        "section_name": str(anchor.get("section_name", "section")),
        "is_chorus": bool(anchor.get("is_chorus", False)),
    }
