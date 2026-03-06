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
    style_guidance = _style_guidance(config, payload)
    spec = _plan_with_ollama(config, payload, clip_anchors)
    rules = normalize_uso_items(spec["items"], clip_anchors)
    items = [_build_item(a, style_guidance, rules[a["shot_id"]]) for a in clip_anchors]
    return {"items": items}


def _expand_clip_anchors(config: dict, anchors: list[dict]) -> list[dict]:
    fps = parse_target(config.get("video", {}).get("target", "1920x1080@24"))[2]
    max_clip_sec = read_max_clip_sec(config)
    return expand_anchor_clips(anchors, fps, max_clip_sec)


def _plan_with_ollama(config: dict, payload: dict, anchors: list[dict]) -> dict:
    batch_size = min(len(anchors), _uso_planner_batch_size(config))
    items = _plan_with_batches(config, payload, anchors, batch_size)
    return {"items": items}


def _plan_with_batches(config: dict, payload: dict, anchors: list[dict], batch_size: int) -> list[dict]:
    if batch_size <= 0:
        raise RuntimeError("uso planner batch_size must be positive")
    out: list[dict] = []
    carry = ""
    strict = _strict_id_match(config)
    for i in range(0, len(anchors), batch_size):
        chunk = anchors[i : i + batch_size]
        rows = _plan_chunk_rows(config, payload, chunk, carry, strict)
        out.extend(rows)
        carry = _batch_tail(rows)
    return out


def _plan_chunk_rows(config: dict, payload: dict, chunk: list[dict], carry: str, strict: bool) -> list[dict]:
    prompt = _planner_prompt(config, payload, chunk, carry)
    raw = generate_structured(config, prompt, uso_schema())
    return _coerce_item_ids(raw.get("items", []), chunk, strict)


def _planner_prompt(config: dict, payload: dict, anchors: list[dict], carry: str) -> str:
    guidance = _style_guidance(config, payload)
    lyrics = _lyrics_excerpt(payload)
    brief = _brief_summary(payload["visual_brief"])
    summary = _anchor_summary(anchors)
    carry_clause = f"Previous batch continuity hint={carry}. " if carry else ""
    return (
        "You are a senior image-to-image keyframe director for character-consistent music videos. "
        "Return strict JSON only: {\"items\":[...]}. No prose outside JSON. "
        "Each item must include shot_id,delta,prompt_text,negative_prompt. "
        "Use shot_id values exactly from Anchors list, without creating new ids. "
        "All anchors refer to the same master identity image. Preserve exact face, hair, outfit, body proportions, styling, and accessories across every item. "
        "shot_id must be exactly one token from Anchors with no suffix, prefix, or punctuation changes. "
        "prompt_text must be exactly one natural English sentence (18-34 words). "
        "delta describes a small progression from start to end frame, not a scene reset. "
        "Do not change time period, world setting, or character species. "
        "Use concrete visual language: pose shift, gaze shift, hand motion, cloth motion, light direction, camera feel. "
        "Respect each shot blueprint for camera language, pose delta, emotion, scene detail, and motion hint. "
        "Prefer readable, graceful progression over chaotic transformation. "
        "negative_prompt must suppress defects: low quality, blurry, jpeg artifacts, extra fingers, bad hands, bad face, deformed anatomy, text watermark, logo, subtitle. "
        f"{carry_clause}Style guidance={guidance}; Visual brief={brief}; Lyrics context={lyrics}; Anchors={summary}."
    )


def _lyrics_excerpt(payload: dict) -> str:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    text = str(audio_map.get("lyrics", "")).strip() if isinstance(audio_map, dict) else ""
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


def _style_guidance(config: dict, payload: dict) -> str:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    guided = str(audio_map.get("style_guidance", "")).strip() if isinstance(audio_map, dict) else ""
    if guided:
        return guided
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


def _brief_summary(brief: dict) -> str:
    motifs = ", ".join(brief.get("visual_motifs", []))
    rules = ", ".join(brief.get("negative_constraints", []))
    return f"hero={brief['hero_identity']}; world={brief['world_rules']}; motifs={motifs}; avoid={rules}"


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
    return ", ".join(_anchor_summary_row(a) for a in anchors)


def _anchor_summary_row(anchor: dict) -> str:
    sid = str(anchor["shot_id"])
    section = str(anchor.get("section_name", "section"))
    shot_type = str(anchor.get("shot_type", "CHAR_MASTER"))
    emotion = str(anchor.get("emotion", "")).strip() or "steady"
    pose = str(anchor.get("pose_delta", "")).strip() or "small pose shift"
    camera = str(anchor.get("camera_language", "")).strip() or "clean mid framing"
    motion = str(anchor.get("motion_hint", "")).strip() or "smooth motion"
    detail = str(anchor.get("scene_detail", "")).strip() or "hero focus"
    return f"{sid}({section}|{shot_type}|{emotion}|{pose}|{camera}|{motion}|{detail})"


def _build_item(anchor: dict, style_guidance: str, rule: dict) -> dict:
    ref = str(anchor.get("identity_anchor", anchor["anchor"]))
    return {
        "shot_id": anchor["shot_id"],
        "anchor": anchor["anchor"],
        "ref": ref,
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
