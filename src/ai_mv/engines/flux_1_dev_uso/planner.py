from __future__ import annotations


def build_uso_plan(config: dict, payload: dict) -> dict:
    anchors = payload.get("anchors", [])
    refs = config.get("consistency", {}).get("reference_images", [])
    return {"items": [{"shot_id": x["shot_id"], "anchor": x["anchor"], "ref": refs[0] if refs else ""} for x in anchors]}

