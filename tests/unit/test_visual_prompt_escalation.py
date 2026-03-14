import ai_mv.engines.flux_1_dev_tti.planner as tti_planner
import ai_mv.engines.flux2_reference.planner as flux2_ref_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_tti_prompt_uses_section_labels_for_escalation():
    brief = {
        "hero_identity": "hero",
        "world_rules": "world",
        "visual_motifs": ["rain"],
        "negative_constraints": ["drift"],
        "section_briefs": [
            {"section_name": "chorus", "emotional_arc": "lift", "palette_hint": "red", "lighting_hint": "glow", "staging_hint": "front portrait"}
        ],
    }
    audio_map = {
        "genre_description": "desc",
        "tags": "city pop",
        "style_guidance": "guide",
        "profile_summary": "retro city-pop lane",
        "visual_direction": "harbor neon romance",
        "section_semantics": [{"section_name": "chorus", "section_label": "Final Chorus", "movement_bias": "clear hero payoff", "release_level": "peak", "hero_frame_priority": "peak"}],
    }
    sections = [{"name": "chorus", "label": "Final Chorus", "start_sec": 0.0, "end_sec": 8.0}]
    prompt = tti_planner._planner_prompt({}, audio_map, brief, sections)
    assert "Section labels in order=Final Chorus" in prompt
    assert "Final Chorus=peak return, luminous resolve, clearest environmental payoff" in prompt
    assert "Visual direction=harbor neon romance" in prompt
    assert "Use the profile-driven shot grammar guidance instead of a single global hierarchy" in prompt


def test_flux2_ref_prompt_mentions_return_intensity():
    payload = {
        "audio_map": {
            "style_guidance": "guide",
            "profile_summary": "retro city-pop lane",
            "visual_direction": "harbor neon romance",
            "section_semantics": [{"section_name": "chorus", "section_label": "Final Chorus", "movement_bias": "clear hero payoff", "release_level": "peak", "hero_frame_priority": "peak"}],
        },
        "visual_brief": _brief(),
    }
    anchors = [_anchor("S010", "chorus", "Final Chorus")]
    prompt = flux2_ref_planner._planner_prompt({}, payload, anchors, "")
    assert "Final Chorus should feel like the visual peak" in prompt
    assert "Profile steering=" not in prompt
    assert "Do not write full final prompt sentences" in prompt
    assert "subject_clause must be a short identity clause" in prompt
    assert "Lyrics context=" not in prompt
    assert "Avoid=" not in prompt


def test_wan_prompt_mentions_final_chorus_payoff():
    payload = {
        "audio_map": {
            "style_guidance": "guide",
            "profile_summary": "retro city-pop lane",
            "visual_direction": "harbor neon romance",
            "section_semantics": [{"section_name": "chorus", "section_label": "Final Chorus", "movement_bias": "clear hero payoff", "release_level": "peak", "hero_frame_priority": "peak"}],
        },
        "visual_brief": _brief(),
    }
    clips = [_clip("S010_C01", "chorus", "Final Chorus")]
    prompt = wan_planner._planner_prompt({}, payload, clips, "")
    assert "Final Chorus should feel like the motion payoff" in prompt
    assert "Visual direction=harbor neon romance" in prompt
    assert "Profile steering=" not in prompt
    assert "motifs=" not in prompt
    assert "subject_motion must combine the visible starting state and the main body motion" in prompt
    assert "Do not write the final positive_prompt prose" in prompt


def _brief() -> dict:
    return {
        "hero_identity": "hero",
        "world_rules": "world",
        "visual_motifs": ["rain"],
        "negative_constraints": ["drift"],
        "section_briefs": [
            {"section_name": "chorus", "emotional_arc": "lift", "palette_hint": "red", "lighting_hint": "glow", "staging_hint": "front portrait"}
        ],
    }


def _anchor(shot_id: str, section_name: str, section_label: str) -> dict:
    return {
        "shot_id": shot_id,
        "section_name": section_name,
        "section_label": section_label,
        "shot_type": "PERF_WIDE",
        "emotion": "lift",
        "pose_delta": "small turn",
        "scene_detail": "rain glow",
        "motion_hint": "slow move",
    }


def _clip(shot_id: str, section_name: str, section_label: str) -> dict:
    return {
        "shot_id": shot_id,
        "section_name": section_name,
        "section_label": section_label,
        "camera_language": "clean frame",
        "emotion": "lift",
        "scene_detail": "rain glow",
        "motion_hint": "slow move",
    }
