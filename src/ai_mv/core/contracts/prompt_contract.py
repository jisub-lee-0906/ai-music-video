from __future__ import annotations

SHOT_TYPES = ["CHAR_MASTER", "PERF_WIDE", "EMOTION_CLOSE", "DETAIL_INSERT", "ENV_TRANSITION"]


def tti_schema() -> dict:
    shot = {
        "type": "object",
        "required": ["shot_id", "prompt", "negative_prompt", "duration_sec", "seed", "shot_type", "is_chorus"],
        "properties": {
            "shot_id": {"type": "string"},
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "duration_sec": {"type": "number"},
            "seed": {"type": "integer"},
            "shot_type": {"type": "string", "enum": SHOT_TYPES},
            "is_chorus": {"type": "boolean"},
        },
    }
    return {"type": "object", "required": ["shots"], "properties": {"shots": {"type": "array", "items": shot}}}


def audio_schema() -> dict:
    props = {
        "tags": {"type": "string"},
        "lyrics": {"type": "string"},
        "bpm": {"type": "integer"},
        "seed": {"type": "integer"},
        "duration": {"type": "integer"},
    }
    return {"type": "object", "required": list(props.keys()), "properties": props}


def uso_schema() -> dict:
    item = {
        "type": "object",
        "required": ["shot_id", "mode", "delta"],
        "properties": {
            "shot_id": {"type": "string"},
            "mode": {"type": "string", "enum": ["double", "triple"]},
            "delta": {"type": "string"},
        },
    }
    return {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": item}}}


def wan_schema() -> dict:
    clip = {
        "type": "object",
        "required": ["shot_id", "prompt", "negative_prompt", "energy"],
        "properties": {
            "shot_id": {"type": "string"},
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "energy": {"type": "string", "enum": ["low", "mid", "high"]},
        },
    }
    return {"type": "object", "required": ["clips"], "properties": {"clips": {"type": "array", "items": clip}}}


def normalize_tti_shot(raw: dict, idx: int) -> dict:
    stype = str(raw["shot_type"])
    if stype not in SHOT_TYPES:
        raise RuntimeError(f"invalid shot_type at {idx}: {stype}")
    return {
        "shot_id": str(raw["shot_id"]),
        "prompt": str(raw["prompt"]).strip(),
        "negative_prompt": str(raw["negative_prompt"]),
        "duration_sec": float(raw["duration_sec"]),
        "seed": int(raw["seed"]),
        "shot_type": stype,
        "is_chorus": bool(raw["is_chorus"]),
    }


def normalize_audio_fields(raw: dict) -> dict:
    return {
        "tags": str(raw["tags"]),
        "lyrics": str(raw["lyrics"]),
        "bpm": int(raw["bpm"]),
        "seed": int(raw["seed"]),
        "duration": int(raw["duration"]),
    }


def normalize_uso_items(raw_items: list[dict], anchors: list[dict]) -> dict[str, dict]:
    keyed = {str(x["shot_id"]): x for x in raw_items if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for anchor in anchors:
        sid = str(anchor["shot_id"])
        row = keyed[sid]
        mode = str(row["mode"])
        if mode not in {"double", "triple"}:
            raise RuntimeError(f"invalid uso mode: {mode}")
        out[sid] = {
            "mode": mode,
            "delta": str(row["delta"]),
        }
    return out


def normalize_wan_clips(raw_clips: list[dict], clips: list[dict]) -> dict[str, dict]:
    keyed = {str(x["shot_id"]): x for x in raw_clips if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for clip in clips:
        sid = str(clip["shot_id"])
        row = keyed[sid]
        energy = str(row["energy"])
        if energy not in {"low", "mid", "high"}:
            raise RuntimeError(f"invalid wan energy: {energy}")
        out[sid] = {
            "prompt": str(row["prompt"]),
            "negative_prompt": str(row["negative_prompt"]),
            "energy": energy,
        }
    return out
