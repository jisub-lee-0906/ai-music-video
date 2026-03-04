from __future__ import annotations


def map_uso_workflow(config: dict, item: dict) -> dict:
    idx = _shot_index(item.get("shot_id", "0"))
    return {
        "shot.prompt": f"consistent cinematic portrait for {item['shot_id']}",
        "shot.seed": 2000 + idx,
        "shot.reference_image": item["ref"],
    }


def _shot_index(shot_id: str) -> int:
    token = str(shot_id).split("_")[-1]
    digits = "".join(ch for ch in token if ch.isdigit())
    return int(digits) if digits else 0
