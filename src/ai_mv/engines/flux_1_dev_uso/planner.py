from __future__ import annotations


def build_uso_plan(config: dict, payload: dict) -> dict:
    refs = config.get("consistency", {}).get("reference_images", [])
    style_ref = refs[0] if refs else ""
    items = [_build_item(anchor, style_ref) for anchor in payload.get("anchors", [])]
    return {"items": items}


def _build_item(anchor: dict, style_ref: str) -> dict:
    is_chorus = bool(anchor.get("is_chorus", False))
    mode = "triple" if is_chorus else "double"
    return {
        "shot_id": anchor["shot_id"],
        "anchor": anchor["anchor"],
        "ref": anchor["anchor"],
        "style_ref": style_ref,
        "mode": mode,
        "duration_sec": float(anchor.get("duration_sec", 4.0)),
        "shot_type": str(anchor.get("shot_type", "CHAR_MASTER")),
    }
