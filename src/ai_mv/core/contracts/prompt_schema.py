from __future__ import annotations

SHOT_TYPES = [
    "CHAR_MASTER",
    "PERF_WIDE",
    "EMOTION_CLOSE",
    "DETAIL_INSERT",
    "ENV_TRANSITION",
    "SYMBOLIC_INSERT",
    "GRAPHIC_EVENT",
    "WORLD_EVENT",
    "TRANSITIONAL_ABSTRACT",
    "RHYTHM_DETAIL",
]
KINETIC_TRANSITIONS = [
    "snap_zoom_in",
    "snap_zoom_out",
    "whip_pan_left",
    "whip_pan_right",
    "crash_push_in",
    "smash_reframe",
    "strobe_jump",
    "match_cut_pose",
]
KINETIC_INTENSITIES = ["low", "medium", "high", "max"]
SCENE_CHANGE_LEVELS = ["hold", "evolve", "shift", "reset"]
ANCHOR_STRATEGIES = ["reuse_anchor", "refine_anchor", "new_anchor"]
CONTINUITY_BASES = ["heroine", "motif", "world", "none"]


def lyrics_timeline_schema() -> dict:
    return {
        "type": "object",
        "required": ["sections"],
        "properties": {
            "sections": {
                "type": "array",
                "items": _lyrics_section_schema(),
                "minItems": 1,
                "maxItems": 24,
            }
        },
    }


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
        "required": ["prompt_text", "seed"],
        "properties": {
            "prompt_text": {"type": "string"},
            "seed": {"type": "integer"},
        },
    }


def _tti_shot_schema() -> dict:
    return {
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
            "space_relation",
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
            "space_relation": {"type": "string"},
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


def audio_outline_schema() -> dict:
    block = {
        "type": "object",
        "required": ["section", "label", "style", "line_count"],
        "properties": {
            "section": {"type": "string", "enum": ["intro", "verse_1", "verse_2", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"]},
            "label": {"type": "string"},
            "style": {"type": "string"},
            "line_count": {"type": "integer", "minimum": 1, "maximum": 8},
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


def audio_lyrics_fill_schema() -> dict:
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
    return {"type": "object", "required": ["lyrics_blocks"], "properties": {"lyrics_blocks": {"type": "array", "items": block, "minItems": 1, "maxItems": 16}}}
def flux2_ref_schema() -> dict:
    item = {
        "type": "object",
        "required": ["shot_id", "prompt_text", "subject_clause", "action_clause", "camera_clause", "continuity_clause"],
        "properties": {
            "shot_id": {"type": "string"},
            "prompt_text": {"type": "string"},
            "subject_clause": {"type": "string"},
            "action_clause": {"type": "string"},
            "camera_clause": {"type": "string"},
            "continuity_clause": {"type": "string"},
        },
    }
    return {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": item}}}


def wan_schema() -> dict:
    clip = {
        "type": "object",
        "required": ["shot_id", "positive_prompt", "negative_prompt", "subject_motion", "camera_relation", "environment_detail", "energy"],
        "properties": {
            "shot_id": {"type": "string"},
            "positive_prompt": {"type": "string"},
            "subject_motion": {"type": "string"},
            "camera_relation": {"type": "string"},
            "environment_detail": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "energy": {"type": "string", "enum": ["low", "normal", "high"]},
        },
    }
    return {"type": "object", "required": ["clips"], "properties": {"clips": {"type": "array", "items": clip}}}
def _lyrics_section_schema() -> dict:
    return {
        "type": "object",
        "required": ["section_name", "section_label", "lines", "hook_lines", "lyric_beats"],
        "properties": {
            "section_name": {"type": "string"},
            "section_label": {"type": "string"},
            "lines": {"type": "array", "items": _lyric_line_schema(), "minItems": 1, "maxItems": 12},
            "hook_lines": {"type": "array", "items": {"type": "integer"}, "minItems": 0, "maxItems": 8},
            "lyric_beats": {"type": "array", "items": _lyric_beat_schema(), "minItems": 1, "maxItems": 5},
        },
    }


def _lyric_line_schema() -> dict:
    return {
        "type": "object",
        "required": ["line_index", "text"],
        "properties": {
            "line_index": {"type": "integer"},
            "text": {"type": "string"},
        },
    }


def _lyric_beat_schema() -> dict:
    return {
        "type": "object",
        "required": [
            "beat_id",
            "line_refs",
            "literal_image",
            "visible_action",
            "emotional_turn",
            "continuity_anchor",
            "payoff_role",
            "repeat_variant_of",
        ],
        "properties": {
            "beat_id": {"type": "string"},
            "line_refs": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 8},
            "literal_image": {"type": "string"},
            "visible_action": {"type": "string"},
            "emotional_turn": {"type": "string"},
            "continuity_anchor": {"type": "string"},
            "payoff_role": {"type": "string"},
            "repeat_variant_of": {"type": "string"},
        },
    }


def _frame_anchor_schema() -> dict:
    return {
        "type": "object",
        "required": ["composition", "subject_scale", "camera_axis", "lighting_state"],
        "properties": {
            "composition": {"type": "string"},
            "subject_scale": {"type": "string"},
            "camera_axis": {"type": "string"},
            "lighting_state": {"type": "string"},
        },
    }


def coverage_review_schema() -> dict:
    props = {
        "reasoning": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
        "risks": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
    }
    return {"type": "object", "required": list(props.keys()), "properties": props}
