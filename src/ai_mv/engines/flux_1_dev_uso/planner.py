from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_uso_items, uso_schema
from ai_mv.engines.common.clip_timing import expand_anchor_clips, read_max_clip_sec
from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.bool_utils import parse_bool
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
    strict = _strict_id_match(config)
    for i in range(0, len(anchors), batch_size):
        chunk = anchors[i : i + batch_size]
        rows = _plan_chunk_rows(config, chunk, carry, strict)
        out.extend(rows)
        carry = _batch_tail(rows)
    return out


def _plan_chunk_rows(config: dict, chunk: list[dict], carry: str, strict: bool) -> list[dict]:
    prompt = _planner_prompt(config, chunk, carry)
    raw = generate_structured(config, prompt, uso_schema())
    try:
        return _coerce_item_ids(raw.get("items", []), chunk, strict)
    except RuntimeError as exc:
        if strict and _is_id_mismatch(exc) and len(chunk) > 1:
            return _plan_chunk_rows_split(config, chunk, carry, strict)
        raise


def _plan_chunk_rows_split(config: dict, chunk: list[dict], carry: str, strict: bool) -> list[dict]:
    out: list[dict] = []
    local_carry = carry
    for anchor in chunk:
        rows = _plan_chunk_rows(config, [anchor], local_carry, strict)
        out.extend(rows)
        local_carry = _batch_tail(rows)
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
        "shot_id must be exactly one token from Anchors with no suffix, prefix, or punctuation changes. "
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


def _coerce_item_ids(items: list[dict], anchors: list[dict], strict: bool) -> list[dict]:
    pool = [_normalize_item_id(x) for x in items if isinstance(x, dict)]
    keyed = {str(x.get("shot_id", "")): x for x in pool if str(x.get("shot_id", "")).strip()}
    out: list[dict] = []
    idx = 0
    for a in anchors:
        sid = str(a["shot_id"])
        row = keyed.get(sid)
        if row is None:
            if strict:
                raise RuntimeError(f"USO planner shot_id mismatch: missing {sid}")
            row = _next_item(pool, idx)
            idx += 1
        out.append(_with_shot_id(row, sid))
    return out


def _strict_id_match(config: dict) -> bool:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("strict_prompt_id_match", True) if isinstance(render, dict) else True
    return parse_bool(raw, default=True)


def _next_item(pool: list[dict], idx: int) -> dict:
    if idx >= len(pool):
        raise RuntimeError("USO planner returned fewer items than anchors")
    return pool[idx]


def _is_id_mismatch(exc: RuntimeError) -> bool:
    return "shot_id mismatch" in str(exc).lower()


def _normalize_item_id(row: dict) -> dict:
    out = dict(row)
    sid = str(out.get("shot_id", "")).strip().strip(".;:")
    if sid:
        out["shot_id"] = sid
    return out


def _with_shot_id(row: dict, shot_id: str) -> dict:
    out = dict(row)
    out["shot_id"] = shot_id
    return out


def _anchor_summary(anchors: list[dict]) -> str:
    return ", ".join(str(a["shot_id"]) for a in anchors)


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
