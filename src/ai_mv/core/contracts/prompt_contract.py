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
    stype = str(raw.get("shot_type", SHOT_TYPES[idx % len(SHOT_TYPES)]))
    return {
        "shot_id": str(raw.get("shot_id", f"shot_{idx:03d}")),
        "prompt": str(raw.get("prompt", "")).strip(),
        "negative_prompt": str(raw.get("negative_prompt", "lowres, blur, artifacts")),
        "duration_sec": float(raw.get("duration_sec", 4.0)),
        "seed": int(raw.get("seed", 1000 + idx)),
        "shot_type": stype if stype in SHOT_TYPES else SHOT_TYPES[idx % len(SHOT_TYPES)],
        "is_chorus": bool(raw.get("is_chorus", False)),
    }


def normalize_audio_fields(raw: dict, fallback: dict) -> dict:
    out = dict(fallback)
    out["tags"] = str(raw.get("tags", out.get("tags", "")))
    out["lyrics"] = str(raw.get("lyrics", out.get("lyrics", "")))
    out["bpm"] = int(raw.get("bpm", out.get("bpm", 120)))
    out["seed"] = int(raw.get("seed", out.get("seed", 31)))
    out["duration"] = int(raw.get("duration", out.get("duration", 160)))
    return out


def normalize_uso_items(raw_items: list[dict], anchors: list[dict]) -> dict[str, dict]:
    keyed = {str(x.get("shot_id", "")): x for x in raw_items if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for anchor in anchors:
        sid = str(anchor.get("shot_id", ""))
        default_mode = "triple" if bool(anchor.get("is_chorus", False)) else "double"
        out[sid] = {
            "mode": str(keyed.get(sid, {}).get("mode", default_mode)),
            "delta": str(keyed.get(sid, {}).get("delta", "small pose shift")),
        }
    return out


def normalize_wan_clips(raw_clips: list[dict], clips: list[dict]) -> dict[str, dict]:
    keyed = {str(x.get("shot_id", "")): x for x in raw_clips if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for clip in clips:
        sid = str(clip.get("shot_id", ""))
        row = keyed.get(sid, {})
        out[sid] = {
            "prompt": str(row.get("prompt", f"cinematic motion for {sid}")),
            "negative_prompt": str(row.get("negative_prompt", "flicker, low quality")),
            "energy": str(row.get("energy", "mid")),
        }
    return out
