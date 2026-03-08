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
    return {
        "type": "object",
        "required": ["prompt_clip_l", "prompt_t5xxl", "negative_prompt", "seed"],
        "properties": {
            "prompt_clip_l": {"type": "string"},
            "prompt_t5xxl": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "seed": {"type": "integer"},
        },
    }


def _tti_shot_schema() -> dict:
    return {
        "type": "object",
        "required": ["shot_id", "shot_type", "is_chorus", "camera_language", "pose_delta", "emotion", "scene_detail", "motion_hint"],
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


def audio_schema() -> dict:
    block = {
        "type": "object",
        "required": ["section", "label", "style", "lines"],
        "properties": {
            "section": {"type": "string", "enum": ["intro", "verse_1", "verse_2", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"]},
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


def visual_brief_schema() -> dict:
    return {
        "type": "object",
        "required": ["hero_identity", "world_rules", "visual_motifs", "negative_constraints", "section_briefs"],
        "properties": {
            "hero_identity": {"type": "string"},
            "world_rules": {"type": "string"},
            "visual_motifs": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
            "negative_constraints": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 10},
            "section_briefs": {"type": "array", "items": _visual_section_schema()},
        },
    }


def _visual_section_schema() -> dict:
    return {
        "type": "object",
        "required": ["section_name", "emotional_arc", "palette_hint", "lighting_hint", "staging_hint"],
        "properties": {
            "section_name": {"type": "string"},
            "emotional_arc": {"type": "string"},
            "palette_hint": {"type": "string"},
            "lighting_hint": {"type": "string"},
            "staging_hint": {"type": "string"},
        },
    }
