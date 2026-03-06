from __future__ import annotations

SHOT_TYPES = ["CHAR_MASTER", "PERF_WIDE", "EMOTION_CLOSE", "DETAIL_INSERT", "ENV_TRANSITION"]


def tti_schema() -> dict:
    return {
        "type": "object",
        "required": ["master_anchor", "shots"],
        "properties": {
            "master_anchor": _tti_master_schema(),
            "shots": {"type": "array", "items": _tti_shot_schema()},
        },
    }


def _tti_master_schema() -> dict:
    anchor = {
        "type": "object",
        "required": ["prompt_clip_l", "prompt_t5xxl", "negative_prompt", "seed"],
        "properties": {
            "prompt_clip_l": {"type": "string"},
            "prompt_t5xxl": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "seed": {"type": "integer"},
        },
    }
    return anchor


def _tti_shot_schema() -> dict:
    shot = {
        "type": "object",
        "required": [
            "shot_id",
            "shot_type",
            "is_chorus",
            "camera_language",
            "pose_delta",
            "emotion",
            "scene_detail",
            "motion_hint",
        ],
        "properties": {
            "shot_id": {"type": "string"},
            "shot_type": {"type": "string", "enum": SHOT_TYPES},
            "is_chorus": {"type": "boolean"},
            "camera_language": {"type": "string"},
            "pose_delta": {"type": "string"},
            "emotion": {"type": "string"},
            "scene_detail": {"type": "string"},
            "motion_hint": {"type": "string"},
        },
    }
    return shot


def audio_schema() -> dict:
    block = {
        "type": "object",
        "required": ["section", "label", "style", "lines"],
        "properties": {
            "section": {
                "type": "string",
                "enum": ["intro", "verse_1", "verse_2", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"],
            },
            "label": {"type": "string"},
            "style": {"type": "string"},
            "lines": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
        },
    }
    props = {
        "genre_description": {"type": "string"},
        "bpm": {"type": "integer"},
        "keyscale": {"type": "string"},
        "seed": {"type": "integer"},
        "duration": {"type": "integer"},
        "lyrics_blocks": {"type": "array", "items": block, "minItems": 1, "maxItems": 16},
    }
    return {"type": "object", "required": list(props.keys()), "properties": props}


def uso_schema() -> dict:
    item = {
        "type": "object",
        "required": ["shot_id", "delta", "prompt_text", "negative_prompt"],
        "properties": {
            "shot_id": {"type": "string"},
            "delta": {"type": "string"},
            "prompt_text": {"type": "string"},
            "negative_prompt": {"type": "string"},
        },
    }
    return {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": item}}}


def wan_schema() -> dict:
    clip = {
        "type": "object",
        "required": ["shot_id", "positive_prompt", "negative_prompt", "energy"],
        "properties": {
            "shot_id": {"type": "string"},
            "positive_prompt": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "energy": {"type": "string", "enum": ["low", "normal", "high"]},
        },
    }
    return {"type": "object", "required": ["clips"], "properties": {"clips": {"type": "array", "items": clip}}}


def normalize_tti_shot(raw: dict, idx: int) -> dict:
    stype = str(raw["shot_type"])
    if stype not in SHOT_TYPES:
        raise RuntimeError(f"invalid shot_type at {idx}: {stype}")
    out = {
        "shot_id": str(raw["shot_id"]).strip(),
        "shot_type": stype,
        "is_chorus": bool(raw["is_chorus"]),
        "camera_language": str(raw["camera_language"]).strip(),
        "pose_delta": str(raw["pose_delta"]).strip(),
        "emotion": str(raw["emotion"]).strip(),
        "scene_detail": str(raw["scene_detail"]).strip(),
        "motion_hint": str(raw["motion_hint"]).strip(),
    }
    if not all(out[key] for key in ("shot_id", "camera_language", "pose_delta", "emotion", "scene_detail", "motion_hint")):
        raise RuntimeError(f"incomplete TTI shot blueprint at {idx}")
    return out


def normalize_tti_master(raw: dict) -> dict:
    clip_l = str(raw["prompt_clip_l"]).strip()
    t5 = str(raw["prompt_t5xxl"]).strip()
    neg = str(raw["negative_prompt"]).strip()
    if not clip_l or not t5 or not neg:
        raise RuntimeError("invalid TTI master anchor")
    return {
        "prompt_clip_l": clip_l,
        "prompt_t5xxl": t5,
        "negative_prompt": neg,
        "seed": int(raw["seed"]),
    }


def normalize_audio_fields(raw: dict) -> dict:
    blocks = raw["lyrics_blocks"]
    if not isinstance(blocks, list) or not blocks:
        raise RuntimeError("lyrics_blocks missing")
    return {
        "genre_description": str(raw["genre_description"]).strip(),
        "lyrics_blocks": blocks,
        "lyrics": _render_lyrics_blocks(blocks),
        "bpm": int(raw["bpm"]),
        "keyscale": str(raw.get("keyscale", "")).strip(),
        "seed": int(raw["seed"]),
        "duration": int(raw["duration"]),
    }


def _render_lyrics_blocks(blocks: list[dict]) -> str:
    lines: list[str] = []
    for row in blocks:
        label = str(row["label"]).strip()
        style = str(row["style"]).strip()
        arr = [str(x).strip() for x in row["lines"] if str(x).strip()]
        if not label or not style or not arr:
            raise RuntimeError("invalid lyrics block")
        lines.append(f"[{label} - {style}]")
        lines.extend(arr)
        lines.append("")
    text = "\n".join(lines).strip()
    if not text:
        raise RuntimeError("rendered lyrics empty")
    return text


def normalize_uso_items(raw_items: list[dict], anchors: list[dict]) -> dict[str, dict]:
    keyed = {str(x["shot_id"]): x for x in raw_items if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for anchor in anchors:
        sid = str(anchor["shot_id"])
        row = keyed[sid]
        out[sid] = {
            "delta": str(row["delta"]),
            "prompt_text": str(row["prompt_text"]).strip(),
            "negative_prompt": str(row["negative_prompt"]).strip(),
        }
        if not out[sid]["prompt_text"]:
            raise RuntimeError(f"empty uso prompt_text: {sid}")
    return out


def normalize_wan_clips(raw_clips: list[dict], clips: list[dict]) -> dict[str, dict]:
    keyed = {str(x["shot_id"]): x for x in raw_clips if isinstance(x, dict)}
    out: dict[str, dict] = {}
    for clip in clips:
        sid = str(clip["shot_id"])
        row = keyed[sid]
        energy = str(row["energy"])
        if energy not in {"low", "normal", "high"}:
            raise RuntimeError(f"invalid wan energy: {energy}")
        out[sid] = {
            "positive_prompt": str(row["positive_prompt"]),
            "negative_prompt": str(row["negative_prompt"]),
            "energy": energy,
        }
    return out
