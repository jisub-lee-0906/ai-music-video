from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_uso_items, uso_schema
from ai_mv.infra.ollama_client import generate_structured


def build_uso_plan(config: dict, payload: dict) -> dict:
    refs = config.get("consistency", {}).get("reference_images", [])
    style_ref = refs[0] if refs else ""
    anchors = payload.get("anchors", [])
    spec = _plan_with_ollama(config, anchors)
    rules = normalize_uso_items(spec.get("items", []), anchors)
    items = [_build_item(anchor, style_ref, rules.get(anchor["shot_id"], {})) for anchor in anchors]
    return {"items": items}


def _plan_with_ollama(config: dict, anchors: list[dict]) -> dict:
    prompt = (
        "Return JSON {'items':[]} with shot_id,mode(double|triple),delta. "
        f"Anchors={[(a.get('shot_id'), a.get('shot_type')) for a in anchors]}"
    )
    try:
        return generate_structured(config, prompt, uso_schema())
    except Exception:
        return {}


def _build_item(anchor: dict, style_ref: str, rule: dict) -> dict:
    is_chorus = bool(anchor.get("is_chorus", False))
    mode = str(rule.get("mode", "triple" if is_chorus else "double"))
    return {
        "shot_id": anchor["shot_id"],
        "anchor": anchor["anchor"],
        "ref": anchor["anchor"],
        "style_ref": style_ref,
        "mode": mode,
        "delta": str(rule.get("delta", "small pose shift")),
        "duration_sec": float(anchor.get("duration_sec", 4.0)),
        "shot_type": str(anchor.get("shot_type", "CHAR_MASTER")),
    }
