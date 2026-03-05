from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_uso_items, uso_schema
from ai_mv.infra.ollama_client import generate_structured


def build_uso_plan(config: dict, payload: dict) -> dict:
    style_ref = ""
    style_guidance = str(config["style"]["guidance"]).strip()
    anchors = payload["anchors"]
    if not anchors:
        raise RuntimeError("anchors missing for USO")
    spec = _plan_with_ollama(config, anchors)
    rules = normalize_uso_items(spec["items"], anchors)
    items = [_build_item(anchor, style_ref, style_guidance, rules[anchor["shot_id"]]) for anchor in anchors]
    return {"items": items}


def _plan_with_ollama(config: dict, anchors: list[dict]) -> dict:
    prompt = _planner_prompt(config, anchors)
    raw = generate_structured(config, prompt, uso_schema())
    items = _coerce_item_ids(raw.get("items", []), anchors)
    return {"items": items}


def _planner_prompt(config: dict, anchors: list[dict]) -> str:
    guidance = str(config["style"]["guidance"]).strip()
    keywords = _keywords(config)
    summary = _anchor_summary(anchors)
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
        f"Style guidance={guidance}; Profile keywords={keywords}; Anchors={summary}."
    )


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


def _keywords(config: dict) -> str:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    raw = audio.get("keywords", []) if isinstance(audio, dict) else []
    vals = [str(x).strip() for x in raw if str(x).strip()]
    return ", ".join(vals)


def _build_item(anchor: dict, style_ref: str, style_guidance: str, rule: dict) -> dict:
    return {
        "shot_id": anchor["shot_id"],
        "anchor": anchor["anchor"],
        "ref": anchor["anchor"],
        "style_ref": style_ref,
        "delta": str(rule["delta"]),
        "prompt_text": str(rule["prompt_text"]),
        "negative_prompt": str(rule["negative_prompt"]),
        "style_guidance": style_guidance,
        "duration_sec": float(anchor["duration_sec"]),
        "shot_type": str(anchor["shot_type"]),
    }
