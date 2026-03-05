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
    prompt = (
        "Return strict JSON {'items':[]} with shot_id,delta,prompt_text,negative_prompt. "
        "prompt_text must be one short natural sentence for a consistent visual keyframe prompt. "
        f"Anchors={[(a['shot_id'], a['shot_type']) for a in anchors]}"
    )
    return generate_structured(config, prompt, uso_schema())


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
