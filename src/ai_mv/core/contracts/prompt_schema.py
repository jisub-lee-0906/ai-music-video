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


def visual_story_bible_schema() -> dict:
    return {
        "type": "object",
        "required": [
            "hero_identity_lock",
            "world_rules",
            "recurring_location_families",
            "forbidden_drift",
            "lyric_beats",
            "section_progression",
            "repeat_escalation_rules",
        ],
        "properties": {
            "hero_identity_lock": {"type": "string"},
            "world_rules": {"type": "string"},
            "recurring_location_families": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 6},
            "forbidden_drift": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 12},
            "lyric_beats": {"type": "array", "items": _story_bible_beat_schema(), "minItems": 1, "maxItems": 48},
            "section_progression": {"type": "array", "items": _section_progression_schema(), "minItems": 1, "maxItems": 24},
            "repeat_escalation_rules": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 10},
        },
    }


def shot_timeline_schema() -> dict:
    return {
        "type": "object",
        "required": ["master_anchor", "shots"],
        "properties": {
            "master_anchor": _tti_master_schema(),
            "shots": {"type": "array", "items": _shot_timeline_item_schema(), "minItems": 1, "maxItems": 48},
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


def _story_bible_beat_schema() -> dict:
    return {
        "type": "object",
        "required": [
            "beat_id",
            "section_name",
            "section_label",
            "line_refs",
            "literal_image",
            "visible_action",
            "emotional_turn",
            "continuity_anchor",
            "payoff_role",
            "repeat_variant_of",
            "location_family",
            "palette_hint",
            "lighting_hint",
            "camera_commitment",
            "symbolic_image",
            "motif_object",
            "edit_device",
            "prompt_focus",
            "space_event",
            "composition_shape",
            "palette_mode",
            "character_render_mode",
        ],
        "properties": {
            "beat_id": {"type": "string"},
            "section_name": {"type": "string"},
            "section_label": {"type": "string"},
            "line_refs": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 8},
            "literal_image": {"type": "string"},
            "visible_action": {"type": "string"},
            "emotional_turn": {"type": "string"},
            "continuity_anchor": {"type": "string"},
            "payoff_role": {"type": "string"},
            "repeat_variant_of": {"type": "string"},
            "location_family": {"type": "string"},
            "palette_hint": {"type": "string"},
            "lighting_hint": {"type": "string"},
            "camera_commitment": {"type": "string"},
            "symbolic_image": {"type": "string"},
            "motif_object": {"type": "string"},
            "edit_device": {"type": "string"},
            "prompt_focus": {"type": "string", "enum": ["heroine", "object", "space", "graphic"]},
            "space_event": {"type": "string"},
            "composition_shape": {"type": "string"},
            "palette_mode": {"type": "string"},
            "character_render_mode": {"type": "string"},
        },
    }


def _section_progression_schema() -> dict:
    return {
        "type": "object",
        "required": ["section_name", "section_label", "dominant_emotion", "story_function", "lyric_beat_ids"],
        "properties": {
            "section_name": {"type": "string"},
            "section_label": {"type": "string"},
            "dominant_emotion": {"type": "string"},
            "story_function": {"type": "string"},
            "lyric_beat_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 6},
        },
    }


def _shot_timeline_item_schema() -> dict:
    return {
        "type": "object",
        "required": [
            "lyric_beat_id",
            "shot_type",
            "prompt_text",
            "camera_language",
            "pose_delta",
            "emotion",
            "scene_detail",
            "motion_hint",
            "workflow_motion_clause",
            "space_relation",
            "edit_role",
            "continuity_lock",
            "scene_change_level",
            "anchor_strategy",
            "continuity_basis",
            "clip_count",
            "start_frame",
            "end_frame",
            "kinetic_transition",
            "lighting_fx",
            "kinetic_intensity",
        ],
        "properties": {
            "lyric_beat_id": {"type": "string"},
            "shot_type": {"type": "string", "enum": SHOT_TYPES},
            "prompt_text": {"type": "string"},
            "camera_language": {"type": "string"},
            "pose_delta": {"type": "string"},
            "emotion": {"type": "string"},
            "scene_detail": {"type": "string"},
            "motion_hint": {"type": "string"},
            "workflow_motion_clause": {"type": "string"},
            "space_relation": {"type": "string"},
            "edit_role": {"type": "string"},
            "continuity_lock": {"type": "string"},
            "scene_change_level": {"type": "string", "enum": SCENE_CHANGE_LEVELS},
            "anchor_strategy": {"type": "string", "enum": ANCHOR_STRATEGIES},
            "continuity_basis": {"type": "string", "enum": CONTINUITY_BASES},
            "clip_count": {"type": "integer"},
            "start_frame": _frame_anchor_schema(),
            "end_frame": _frame_anchor_schema(),
            "kinetic_transition": {"type": "string", "enum": KINETIC_TRANSITIONS},
            "lighting_fx": {"type": "string"},
            "kinetic_intensity": {"type": "string", "enum": KINETIC_INTENSITIES},
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
