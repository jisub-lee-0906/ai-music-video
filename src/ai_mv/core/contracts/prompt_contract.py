from __future__ import annotations

SHOT_TYPES = ["CHAR_MASTER", "PERF_WIDE", "EMOTION_CLOSE", "DETAIL_INSERT", "ENV_TRANSITION"]


def tti_schema() -> dict:
    shot = {
        "type": "object",
        "required": [
            "shot_id",
            "prompt_clip_l",
            "prompt_t5xxl",
            "negative_prompt",
            "duration_sec",
            "seed",
            "shot_type",
            "is_chorus",
        ],
        "properties": {
            "shot_id": {"type": "string"},
            "prompt_clip_l": {"type": "string"},
            "prompt_t5xxl": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "duration_sec": {"type": "number"},
            "seed": {"type": "integer"},
            "shot_type": {"type": "string", "enum": SHOT_TYPES},
            "is_chorus": {"type": "boolean"},
        },
    }
    return {"type": "object", "required": ["shots"], "properties": {"shots": {"type": "array", "items": shot}}}


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
            "lines": {"type": "array", "items": {"type": "string"}},
        },
    }
    props = {
        "genre_description": {"type": "string"},
        "bpm": {"type": "integer"},
        "seed": {"type": "integer"},
        "duration": {"type": "integer"},
        "lyrics_blocks": {"type": "array", "items": block},
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
    return {
        "shot_id": str(raw["shot_id"]),
        "prompt_clip_l": str(raw["prompt_clip_l"]).strip(),
        "prompt_t5xxl": str(raw["prompt_t5xxl"]).strip(),
        "negative_prompt": str(raw["negative_prompt"]),
        "duration_sec": float(raw["duration_sec"]),
        "seed": int(raw["seed"]),
        "shot_type": stype,
        "is_chorus": bool(raw["is_chorus"]),
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
