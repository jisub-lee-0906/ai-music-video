from ai_mv.engines.acestep_1_5_aio.mapper import _audio_conditioning_text
from ai_mv.engines.visual_story_bible.brief_views import compact_world_atoms
import ai_mv.engines.flux_2_dev_ref.planner as flux2_ref_planner
import ai_mv.engines.flux_2_dev_tti.planner as tti_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_audio_conditioning_text_dedupes_genre_prefix():
    text = _audio_conditioning_text(
        {
            "tags": "k-pop, glossy",
            "genre_description": "K-Pop: punchy drums, sleek synth bass, bright chorus lift.",
        }
    )
    assert text == "K-Pop: punchy drums, sleek synth bass, bright chorus lift"


def test_tti_prompt_removes_hardcoded_beauty_baseline():
    prompt = tti_planner._planner_prompt({}, {"visual_story_bible": _plain_story_bible(), "lyrics_timeline": _timeline()})
    assert "stunningly beautiful" not in prompt
    assert "idol-like" not in prompt
    assert "high-end fashion model aesthetic" not in prompt


def test_flux2_ref_prompt_does_not_inject_house_style_without_profile_support():
    item = flux2_ref_planner._build_item(
        _anchor("S001"),
        {
            "prompt_text": "The same anime girl, now turns into center light. Clean medium shot. Flat cel shading, thick clean outlines.",
            "subject_clause": "The same anime girl",
            "action_clause": "now turns into center light",
            "camera_clause": "Clean medium shot",
            "continuity_clause": "Flat cel shading, thick clean outlines",
        },
        1,
    )
    assert "stunningly beautiful" not in item["prompt_text"]
    assert "idol-like" not in item["prompt_text"]
    assert "high-end fashion model aesthetic" not in item["prompt_text"]
    assert "turns into center light" in item["action_clause"]


def test_wan_prompt_does_not_inject_house_style_without_profile_support():
    clip = wan_planner._apply_llm_prompt(
        _clip("S001_C01"),
        {
            "positive_prompt": "Camera snap-zooms in. The girl moves through the lane and holding the look. Background threshold lights pulse.",
            "negative_prompt": "3d render, photorealistic, morphing",
            "subject_motion": "The girl moves through the lane and holding the look",
            "camera_relation": "Camera snap-zooms in",
            "environment_detail": "Background threshold lights pulse",
            "energy": "high",
        },
    )
    assert "stunningly beautiful" not in clip["positive_prompt"]
    assert "idol-like" not in clip["positive_prompt"]
    assert "high-end fashion model aesthetic" not in clip["positive_prompt"]
    assert "the girl moves through the lane and holding the look" in clip["positive_prompt"].lower()


def test_compact_world_atoms_keeps_identity_constraints_without_house_style_drift():
    world = compact_world_atoms(
        {
            "hero_identity_lock": (
                "One consistent young adult East Asian heroine only, glossy K-pop idol presence, "
                "premium styling, mirror-skin glam, controlled direct gaze, no cast swaps, no age drift, "
                "no hairstyle-color drift beyond subtle styling variation, no wardrobe downgrade, "
                "always the same high-shine night-world protagonist"
            ),
            "world_rules": "same world",
        }
    )
    assert "One consistent young adult East Asian heroine only" in world["hero_identity"]
    assert "glossy K-pop idol presence" in world["hero_identity"]
    assert "stunningly beautiful" not in world["hero_identity"]

def _plain_story_bible() -> dict:
    return {
        "hero_identity_lock": "one performer with a clean direct gaze",
        "world_rules": "single reflective night set, clean lines, no text",
        "recurring_location_families": ["reflective threshold"],
        "forbidden_drift": ["text"],
        "lyric_beats": [
            {
                "beat_id": "LB01",
                "section_name": "chorus",
                "section_label": "Chorus",
                "line_refs": [1],
                "literal_image": "clean reflected light",
                "visible_action": "steps into the lit center and holds",
                "emotional_turn": "control locks in",
                "continuity_anchor": "center lane",
                "payoff_role": "release",
                "repeat_variant_of": "",
                "location_family": "reflective threshold",
                "palette_hint": "silver white",
                "lighting_hint": "hard practical glow",
                "camera_commitment": "front-facing medium",
            }
        ],
        "section_progression": [{"section_name": "chorus", "section_label": "Chorus", "dominant_emotion": "lift", "story_function": "payoff", "lyric_beat_ids": ["LB01"]}],
        "repeat_escalation_rules": ["returns must vary"],
    }


def _timeline() -> dict:
    return {"sections": [{"section_name": "chorus", "section_label": "Chorus", "lines": [{"line_index": 1, "text": "line"}], "hook_lines": [1], "lyric_beats": [{"beat_id": "LB01", "line_refs": [1]}]}]}


def _anchor(shot_id: str) -> dict:
    return {
        "shot_id": shot_id,
        "anchor": "anchor.png",
        "identity_anchor": "anchor.png",
        "duration_sec": 4.0,
        "clip_index": 1,
        "clip_count": 1,
        "shot_type": "PERF_WIDE",
        "section_name": "chorus",
        "section_label": "Chorus",
        "pose_delta": "turns into center light",
        "workflow_motion_clause": "turning into center light and holding the line",
        "scene_detail": "reflective threshold",
        "space_relation": "center lane",
        "kinetic_transition": "snap_zoom_in",
        "kinetic_intensity": "high",
        "lighting_fx": "hard practical glow",
        "lyric_beat_id": "LB01",
    }


def _clip(shot_id: str) -> dict:
    return {
        "shot_id": shot_id,
        "section_name": "chorus",
        "section_label": "Chorus",
        "shot_type": "PERF_WIDE",
        "motion_hint": "steps into the lit center and holds",
        "workflow_motion_clause": "moving through the lane and holding the look",
        "camera_language": "snap zoom into center lock",
        "scene_detail": "reflective threshold",
        "space_relation": "center lane",
        "kinetic_transition": "snap_zoom_in",
        "kinetic_intensity": "high",
        "lighting_fx": "hard practical glow",
        "lyric_beat_id": "LB01",
        "duration_sec": 4.0,
        "clip_index": 1,
        "clip_count": 1,
        "use_ref": False,
    }
